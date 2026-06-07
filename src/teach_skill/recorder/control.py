from datetime import datetime, timezone
from pathlib import Path


STOP_REQUEST_FILE = ".recording.stop"


def stop_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / STOP_REQUEST_FILE


def request_stop(recordings_root: Path) -> Path:
    path = stop_request_path(recordings_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    requested_at = datetime.now(timezone.utc).isoformat()
    path.write_text(f"stop requested at {requested_at}\n", encoding="utf-8")
    return path


def is_stop_requested(recordings_root: Path) -> bool:
    return stop_request_path(recordings_root).exists()


def clear_stop_request(recordings_root: Path) -> None:
    try:
        stop_request_path(recordings_root).unlink()
    except FileNotFoundError:
        pass
