from datetime import datetime, timezone
from pathlib import Path


STOP_REQUEST_FILE = ".recording.stop"
PAUSE_REQUEST_FILE = ".recording.pause"
RESUME_REQUEST_FILE = ".recording.resume"
PAUSED_STATE_FILE = ".recording.paused"


def stop_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / STOP_REQUEST_FILE


def pause_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / PAUSE_REQUEST_FILE


def resume_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / RESUME_REQUEST_FILE


def paused_state_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / PAUSED_STATE_FILE


def _write_control_file(path: Path, action: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    requested_at = datetime.now(timezone.utc).isoformat()
    path.write_text(f"{action} at {requested_at}\n", encoding="utf-8")
    return path


def _clear_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def request_stop(recordings_root: Path) -> Path:
    return _write_control_file(stop_request_path(recordings_root), "stop requested")


def request_pause(recordings_root: Path) -> Path:
    return _write_control_file(pause_request_path(recordings_root), "pause requested")


def request_resume(recordings_root: Path) -> Path:
    return _write_control_file(resume_request_path(recordings_root), "resume requested")


def is_stop_requested(recordings_root: Path) -> bool:
    return stop_request_path(recordings_root).exists()


def is_pause_requested(recordings_root: Path) -> bool:
    return pause_request_path(recordings_root).exists()


def is_resume_requested(recordings_root: Path) -> bool:
    return resume_request_path(recordings_root).exists()


def is_recording_paused(recordings_root: Path) -> bool:
    return paused_state_path(recordings_root).exists()


def clear_stop_request(recordings_root: Path) -> None:
    _clear_file(stop_request_path(recordings_root))


def clear_pause_request(recordings_root: Path) -> None:
    _clear_file(pause_request_path(recordings_root))


def clear_resume_request(recordings_root: Path) -> None:
    _clear_file(resume_request_path(recordings_root))


def mark_recording_paused(recordings_root: Path) -> None:
    _write_control_file(paused_state_path(recordings_root), "paused")


def mark_recording_resumed(recordings_root: Path) -> None:
    _clear_file(paused_state_path(recordings_root))
