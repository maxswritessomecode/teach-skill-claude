from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecordingSummary:
    name: str
    path: Path
    jsonl_path: Path
    frame_count: int
    modified_at: float


def list_recordings(recordings_root: Path, *, limit: int | None = None) -> list[RecordingSummary]:
    if not recordings_root.is_dir():
        return []

    recordings = []
    for folder in recordings_root.iterdir():
        jsonl_path = folder / "recording.jsonl"
        if not folder.is_dir() or not jsonl_path.is_file():
            continue

        frames_dir = folder / "frames"
        frame_count = 0
        if frames_dir.is_dir():
            frame_count = sum(
                1
                for item in frames_dir.iterdir()
                if item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            )

        recordings.append(
            RecordingSummary(
                name=folder.name,
                path=folder,
                jsonl_path=jsonl_path,
                frame_count=frame_count,
                modified_at=folder.stat().st_mtime,
            )
        )

    recordings.sort(key=lambda recording: recording.modified_at, reverse=True)
    if limit is not None:
        return recordings[:limit]
    return recordings
