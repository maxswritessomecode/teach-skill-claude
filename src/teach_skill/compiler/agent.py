import base64
import shutil
from pathlib import Path, PureWindowsPath

from teach_skill.compiler.parser import parse_recording, Recording
from teach_skill.compiler.prompt import build_system_prompt, build_user_message
from teach_skill.runtime_log import get_logger


logger = get_logger("compiler.agent")


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
    def __init__(self, recording_path: Path):
        self.recording_path = recording_path
        self.recording: Recording | None = None

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
        if not self.recording:
            return []

        base_dir = self.recording_path.parent.resolve()
        images = []
        for event in self.recording.events:
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

            images.append((
                path,
                media_type,
                _screenshot_frame_id(raw_path, event),
                str(normalized_path),
            ))

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
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            },
        }

    async def iter_prompt_messages(self):
        if not self.recording:
            raise RuntimeError("Call load() before building prompt messages")

        content = [{"type": "text", "text": build_user_message(self.recording)}]
        for path, media_type, frame_id, raw_path in self.collect_screenshot_image_details():
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
            return "".join(skill_text_blocks)

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
