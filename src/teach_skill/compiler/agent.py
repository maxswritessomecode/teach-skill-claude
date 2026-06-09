import base64
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PureWindowsPath

from PIL import Image

from teach_skill.compiler.parser import parse_recording, Recording
from teach_skill.compiler.prompt import build_system_prompt, build_user_message
from teach_skill.runtime_log import get_logger


logger = get_logger("compiler.agent")
MAX_SCREENSHOT_PAYLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_COMPILE_MAX_IMAGE_EDGE = 1568
RESAMPLE_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
SDK_ERROR_TEXT_PATTERNS = (
    "api error:",
    "internal server error",
    "request too large",
    "max 32mb",
    "error result",
)


@dataclass(frozen=True)
class ScreenshotImageRecord:
    path: Path
    media_type: str
    frame_id: str
    raw_path: str
    event: dict
    event_index: int


def check_agent_sdk() -> bool:
    try:
        import claude_agent_sdk
        return True
    except ImportError:
        return False


def check_claude_cli() -> bool:
    return shutil.which("claude") is not None


def detect_image_media_type(path: Path) -> str | None:
    header = path.read_bytes()[:32]
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    return None


def _screenshot_frame_id(raw_path: str, event: dict) -> str:
    frame_id = event.get("frame_id")
    if frame_id:
        return str(frame_id)
    return Path(*PureWindowsPath(raw_path).parts).stem


class SkillCompiler:
    def __init__(
        self,
        recording_path: Path,
        compile_max_image_edge: int = DEFAULT_COMPILE_MAX_IMAGE_EDGE,
    ):
        self.recording_path = recording_path
        self.recording: Recording | None = None
        try:
            image_edge = int(compile_max_image_edge)
        except (TypeError, ValueError):
            image_edge = DEFAULT_COMPILE_MAX_IMAGE_EDGE
        if image_edge <= 0:
            image_edge = DEFAULT_COMPILE_MAX_IMAGE_EDGE
        self.compile_max_image_edge = image_edge
        self._image_bytes_cache: dict[tuple[Path, str], tuple[bytes, str]] = {}

    def load(self) -> None:
        self.recording = parse_recording(self.recording_path)

    def collect_screenshot_paths(self) -> list[Path]:
        if not self.recording:
            return []
        return [path for path, _media_type in self.collect_screenshot_images()]

    def collect_screenshot_images(self) -> list[tuple[Path, str]]:
        return [
            (path, media_type)
            for path, media_type, _frame_id, _raw_path in
            self.collect_screenshot_image_details()
        ]

    def collect_screenshot_image_details(self) -> list[tuple[Path, str, str, str]]:
        return [
            (record.path, record.media_type, record.frame_id, record.raw_path)
            for record in self._collect_screenshot_image_records()
        ]

    def _collect_screenshot_image_records(self) -> list[ScreenshotImageRecord]:
        if not self.recording:
            return []

        base_dir = self.recording_path.parent.resolve()
        images = []
        for event_index, event in enumerate(self.recording.events):
            raw_path = event.get("screenshot")
            if not raw_path:
                continue
            if raw_path.startswith("suppressed:"):
                continue

            windows_path = PureWindowsPath(raw_path)
            if (
                Path(raw_path).is_absolute()
                or windows_path.is_absolute()
                or raw_path.startswith("\\")
            ):
                continue

            normalized_path = Path(*windows_path.parts)
            if ".." in normalized_path.parts:
                continue

            path = (base_dir / normalized_path).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError:
                continue

            if not path.is_file():
                continue

            media_type = detect_image_media_type(path)
            if media_type is None:
                continue

            images.append(
                ScreenshotImageRecord(
                    path=path,
                    media_type=media_type,
                    frame_id=_screenshot_frame_id(raw_path, event),
                    raw_path=str(normalized_path),
                    event=event,
                    event_index=event_index,
                )
            )

        return images

    def build_prompt_payload(self) -> dict:
        if not self.recording:
            raise RuntimeError("Call load() before building prompt payload")
        return {
            "system": build_system_prompt(),
            "user_message": build_user_message(self.recording),
            "screenshot_paths": [str(p) for p in self.collect_screenshot_paths()],
        }

    def build_image_block(self, path: Path, media_type: str) -> dict:
        image_bytes, prompt_media_type = self._image_bytes_for_prompt(path, media_type)
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": prompt_media_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        }

    def collect_screenshot_image_details_for_prompt(self) -> list[tuple[Path, str, str, str]]:
        records = self._collect_screenshot_image_records()
        sized_records = [
            (
                record,
                self._encoded_size_for_prompt(record.path, record.media_type),
            )
            for record in records
        ]
        total_bytes = sum(encoded_size for _record, encoded_size in sized_records)
        if total_bytes <= MAX_SCREENSHOT_PAYLOAD_BYTES:
            return [
                (record.path, record.media_type, record.frame_id, record.raw_path)
                for record, _encoded_size in sized_records
            ]

        kept_indexes = self._select_prompt_image_indexes(sized_records)
        images = [
            (record.path, record.media_type, record.frame_id, record.raw_path)
            for index, (record, _encoded_size) in enumerate(sized_records)
            if index in kept_indexes
        ]
        omitted = len(records) - len(images)
        kept_bytes = sum(
            encoded_size
            for index, (_record, encoded_size) in enumerate(sized_records)
            if index in kept_indexes
        )
        if omitted:
            logger.warning(
                "omitted screenshots over payload budget attached=%s omitted=%s bytes=%s budget=%s",
                len(images),
                omitted,
                kept_bytes,
                MAX_SCREENSHOT_PAYLOAD_BYTES,
            )
        return images

    def _image_bytes_for_prompt(self, path: Path, media_type: str) -> tuple[bytes, str]:
        cache_key = (path, media_type)
        if cache_key in self._image_bytes_cache:
            return self._image_bytes_cache[cache_key]

        raw_bytes = path.read_bytes()
        try:
            with Image.open(BytesIO(raw_bytes)) as img:
                width, height = img.size
                longest_edge = max(width, height)
                if longest_edge <= self.compile_max_image_edge:
                    result = (raw_bytes, media_type)
                else:
                    resized = img.copy()
                    resized.thumbnail(
                        (self.compile_max_image_edge, self.compile_max_image_edge),
                        RESAMPLE_LANCZOS,
                    )
                    if resized.mode not in ("RGB", "RGBA"):
                        resized = resized.convert("RGB")
                    output = BytesIO()
                    resized.save(output, format="PNG")
                    result = (output.getvalue(), "image/png")
        except Exception:
            logger.warning("could not downscale screenshot for prompt path=%s", path)
            result = (raw_bytes, media_type)

        self._image_bytes_cache[cache_key] = result
        return result

    def _encoded_size_for_prompt(self, path: Path, media_type: str) -> int:
        image_bytes, _prompt_media_type = self._image_bytes_for_prompt(path, media_type)
        return ((len(image_bytes) + 2) // 3) * 4

    def _select_prompt_image_indexes(
        self,
        sized_records: list[tuple[ScreenshotImageRecord, int]],
    ) -> set[int]:
        if not sized_records:
            return set()

        kept = set()
        total_bytes = 0
        for index in (0, len(sized_records) - 1):
            if index in kept:
                continue
            encoded_size = sized_records[index][1]
            if total_bytes + encoded_size <= MAX_SCREENSHOT_PAYLOAD_BYTES:
                kept.add(index)
                total_bytes += encoded_size

        candidates = [
            (index, record, encoded_size)
            for index, (record, encoded_size) in enumerate(sized_records)
            if index not in kept
        ]
        candidates.sort(
            key=lambda item: (
                -self._frame_priority(item[1].event, item[1].event_index),
                item[1].event_index,
            )
        )

        for index, _record, encoded_size in candidates:
            if total_bytes + encoded_size > MAX_SCREENSHOT_PAYLOAD_BYTES:
                continue
            kept.add(index)
            total_bytes += encoded_size

        return kept

    def _frame_priority(self, event: dict, event_index: int) -> int:
        event_type = event.get("type")
        if event_type == "window_switch":
            return 100
        if self._event_is_adjacent_to_clipboard(event_index):
            return 90
        if self._event_mentions_save_or_download(event):
            return 90
        if event_type in {"post_action_capture", "click", "drag_select"} and not event.get("ui_context"):
            return 80
        return 10

    def _event_is_adjacent_to_clipboard(self, event_index: int) -> bool:
        if not self.recording:
            return False
        for adjacent_index in (event_index - 1, event_index + 1):
            if 0 <= adjacent_index < len(self.recording.events):
                if self.recording.events[adjacent_index].get("type") == "clipboard_text":
                    return True
        return False

    def _event_mentions_save_or_download(self, event: dict) -> bool:
        text = " ".join(self._event_text_values(event)).lower()
        return any(
            marker in text
            for marker in (
                "save",
                "save as",
                "file dialog",
                "download",
            )
        )

    def _event_text_values(self, value) -> list[str]:
        if isinstance(value, dict):
            values = []
            for nested in value.values():
                values.extend(self._event_text_values(nested))
            return values
        if isinstance(value, list):
            values = []
            for nested in value:
                values.extend(self._event_text_values(nested))
            return values
        if isinstance(value, str):
            return [value]
        return []

    async def iter_prompt_messages(self):
        if not self.recording:
            raise RuntimeError("Call load() before building prompt messages")

        content = [{"type": "text", "text": build_user_message(self.recording)}]
        all_images = self.collect_screenshot_image_details()
        prompt_images = self.collect_screenshot_image_details_for_prompt()
        omitted_count = len(all_images) - len(prompt_images)
        if omitted_count:
            content.append({
                "type": "text",
                "text": (
                    f"Screenshots omitted: {omitted_count} image(s) were left out "
                    "because the Agent SDK request size limit would be exceeded."
                ),
            })
        for path, media_type, frame_id, raw_path in prompt_images:
            content.append({
                "type": "text",
                "text": f"Screen {frame_id}: {raw_path}",
            })
            content.append(self.build_image_block(path, media_type))

        yield {
            "type": "user",
            "session_id": "",
            "message": {"role": "user", "content": content},
            "parent_tool_use_id": None,
        }

    async def compile(self) -> str:
        if not check_agent_sdk():
            raise RuntimeError(
                "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"
            )

        self.load()
        payload = self.build_prompt_payload()

        from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

        options = ClaudeAgentOptions(
            system_prompt=payload["system"],
            max_turns=15,
        )

        skill_text_blocks = []
        try:
            async for message in query(
                prompt=self.iter_prompt_messages(),
                options=options,
            ):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text"):
                            skill_text_blocks.append(block.text)
        except Exception as exc:
            logger.exception("agent sdk compile failed")
            if skill_text_blocks:
                logger.warning("using streamed skill text after sdk exception")
                return "".join(skill_text_blocks)
            raise RuntimeError(f"Agent SDK compile failed: {exc}") from exc

        if skill_text_blocks:
            skill_text = "".join(skill_text_blocks)
            if _looks_like_sdk_error_text(skill_text):
                raise RuntimeError(skill_text)
            return skill_text

        raise RuntimeError("No text response received from Claude")


def save_skill(skill_text: str, task_name: str, global_save: bool = True) -> Path:
    if global_save:
        base = Path.home() / ".claude" / "skills" / task_name
    else:
        base = Path.cwd() / ".claude" / "skills" / task_name

    base.mkdir(parents=True, exist_ok=True)
    skill_path = base / "SKILL.md"
    skill_path.write_text(skill_text, encoding="utf-8")
    return skill_path


def _looks_like_sdk_error_text(text: str) -> bool:
    normalized = text.strip().lower()
    return any(pattern in normalized for pattern in SDK_ERROR_TEXT_PATTERNS)
