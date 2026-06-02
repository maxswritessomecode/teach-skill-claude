import json
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any


REVIEW_FILE = "review.json"
RECORDING_FILE = "recording.jsonl"


@dataclass
class ReviewEvent:
    index: int
    data: dict
    included: bool = True


@dataclass
class ReviewFrame:
    relative_path: str
    path: Path
    included: bool = True
    sensitive: bool = False


@dataclass(frozen=True)
class FrameReference:
    relative_path: str | None
    invalid: bool = False


@dataclass
class RecordingReview:
    recording_dir: Path
    jsonl_path: Path
    events: list[ReviewEvent] = field(default_factory=list)
    frames: list[ReviewFrame] = field(default_factory=list)

    def save(self) -> None:
        review_path = self.jsonl_path.with_name(REVIEW_FILE)
        excluded_events = [
            event.index for event in self.events
            if not event.included
        ]
        frames = [
            {
                "relative_path": frame.relative_path,
                "included": frame.included,
                "sensitive": frame.sensitive,
            }
            for frame in self.frames
        ]
        review_path.write_text(
            json.dumps(
                {
                    "excluded_events": excluded_events,
                    "frames": frames,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


@dataclass
class CompileSelection:
    events: list[dict] = field(default_factory=list)
    frame_paths: list[Path] = field(default_factory=list)

    @classmethod
    def from_review(cls, review: RecordingReview) -> "CompileSelection":
        excluded_frames = {
            frame.relative_path for frame in review.frames
            if not frame.included or frame.sensitive
        }
        included_events = [
            event.data for event in review.events
            if event.included
            and _event_is_allowed_for_compile(event.data, excluded_frames)
        ]
        included_frame_paths = [
            frame.path for frame in review.frames
            if frame.included and not frame.sensitive
        ]
        return cls(events=included_events, frame_paths=included_frame_paths)

    def write_filtered_jsonl(self, destination: Path) -> Path:
        destination.write_text(
            "".join(json.dumps(event) + "\n" for event in self.events),
            encoding="utf-8",
        )
        return destination


def load_recording_review(recording_dir: Path) -> RecordingReview:
    jsonl_path = recording_dir / RECORDING_FILE
    events = _load_events(jsonl_path)
    frames = _discover_frames(recording_dir, events)
    review = RecordingReview(
        recording_dir=recording_dir,
        jsonl_path=jsonl_path,
        events=events,
        frames=frames,
    )
    _apply_saved_review(review)
    return review


def _load_events(jsonl_path: Path) -> list[ReviewEvent]:
    events = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        events.append(ReviewEvent(index=len(events), data=data))
    return events


def _discover_frames(recording_dir: Path, events: list[ReviewEvent]) -> list[ReviewFrame]:
    frames = []
    seen = set()
    base_dir = recording_dir.resolve()
    for event in events:
        for frame_reference in _event_frame_references(event.data):
            relative_path = frame_reference.relative_path
            if relative_path is None or relative_path in seen:
                continue

            path = (base_dir / relative_path).resolve()
            try:
                path.relative_to(base_dir)
            except ValueError:
                continue

            if not path.is_file():
                continue

            seen.add(relative_path)
            frames.append(
                ReviewFrame(
                    relative_path=relative_path,
                    path=path,
                )
            )
    return frames


def _event_is_allowed_for_compile(event: dict, excluded_frames: set[str]) -> bool:
    for frame_reference in _event_frame_references(event):
        if frame_reference.invalid:
            return False
        if frame_reference.relative_path in excluded_frames:
            return False
    return True


def _event_frame_references(event: dict) -> list[FrameReference]:
    references = []
    for key in ("screenshot", "screenshot_frame_path"):
        value = event.get(key)
        if not isinstance(value, str):
            continue
        if not value:
            continue
        if value.startswith("suppressed:"):
            references.append(FrameReference(relative_path=None))
            continue

        windows_path = PureWindowsPath(value)
        if (
            Path(value).is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or value.startswith("\\")
        ):
            references.append(FrameReference(relative_path=None, invalid=True))
            continue

        normalized_path = Path(*windows_path.parts)
        if ".." in normalized_path.parts:
            references.append(FrameReference(relative_path=None, invalid=True))
            continue

        references.append(FrameReference(relative_path=normalized_path.as_posix()))
    return references


def _apply_saved_review(review: RecordingReview) -> None:
    review_path = review.jsonl_path.with_name(REVIEW_FILE)
    if not review_path.exists():
        return

    try:
        saved = json.loads(review_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(saved, dict):
        return
    saved_excluded_events = saved.get("excluded_events", [])
    if isinstance(saved_excluded_events, (list, tuple, set)):
        excluded_events = {
            value
            for value in saved_excluded_events
            if isinstance(value, int) and not isinstance(value, bool)
        }
    else:
        excluded_events = set()
    for event in review.events:
        if event.index in excluded_events:
            event.included = False

    frame_states = _saved_frame_states(saved.get("frames", []))
    for frame in review.frames:
        state = frame_states.get(frame.relative_path)
        if state is None:
            continue
        included = state.get("included")
        if isinstance(included, bool):
            frame.included = included
        sensitive = state.get("sensitive")
        if isinstance(sensitive, bool):
            frame.sensitive = sensitive


def _saved_frame_states(frames: Any) -> dict[str, dict]:
    if not isinstance(frames, list):
        return {}

    states = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        relative_path = frame.get("relative_path")
        if not isinstance(relative_path, str):
            continue
        states[relative_path.replace("\\", "/")] = frame
    return states
