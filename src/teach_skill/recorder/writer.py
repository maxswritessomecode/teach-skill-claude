import json
import threading
from pathlib import Path
from datetime import datetime, timezone


class EventWriter:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.jsonl_path = session_dir / "recording.jsonl"
        self.frames_dir = session_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._frame_counter = 0

    def write_event(self, event: dict) -> None:
        if "ts" not in event:
            event["ts"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with open(self.jsonl_path, "a") as f:
                f.write(json.dumps(event) + "\n")

    def next_frame_path(self) -> Path:
        with self._lock:
            self._frame_counter += 1
            return self.frames_dir / f"{self._frame_counter:04d}.png"
