from dataclasses import dataclass
import json
from pathlib import Path


INFO_FILE = "recording-info.json"
MAX_TITLE_LENGTH = 120


@dataclass(frozen=True)
class RecordingInfo:
    title: str | None = None


def info_path(recording_dir: Path) -> Path:
    return Path(recording_dir) / INFO_FILE


def normalize_recording_title(title: str) -> str:
    if "\n" in title or "\r" in title:
        raise ValueError("Recording title cannot contain line breaks.")
    normalized = " ".join(title.strip().split())
    if not normalized:
        raise ValueError("Recording title cannot be empty.")
    if len(normalized) > MAX_TITLE_LENGTH:
        raise ValueError(f"Recording title cannot exceed {MAX_TITLE_LENGTH} characters.")
    return normalized


def load_recording_info(recording_dir: Path) -> RecordingInfo:
    path = info_path(recording_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return RecordingInfo()
    if not isinstance(payload, dict):
        return RecordingInfo()
    title = payload.get("title")
    if not isinstance(title, str):
        return RecordingInfo()
    try:
        return RecordingInfo(title=normalize_recording_title(title))
    except ValueError:
        return RecordingInfo()


def save_recording_title(recording_dir: Path, title: str) -> RecordingInfo:
    info = RecordingInfo(title=normalize_recording_title(title))
    path = info_path(recording_dir)
    path.write_text(json.dumps({"title": info.title}, indent=2) + "\n", encoding="utf-8")
    return info
