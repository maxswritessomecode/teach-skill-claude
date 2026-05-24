import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Recording:
    meta: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    screenshot_paths: list[str] = field(default_factory=list)
    source_path: Path | None = None

    def workflow_steps(self) -> list[dict]:
        return [e for e in self.events if e["type"] == "session_end"]

    def timeline_text(self) -> str:
        lines = []
        if self.meta:
            lines.append(f"Recording from {self.meta.get('machine', 'unknown')} "
                         f"({self.meta.get('os', 'unknown')})")
            lines.append("")

        for event in self.events:
            ts = event.get("ts", "")
            etype = event["type"]

            if etype == "window_switch":
                lines.append(f"[{ts}] Switched to: {event['process']} — \"{event.get('title', '')}\"")
            elif etype == "in_app_capture":
                lines.append(f"[{ts}] In-app action in: {event['process']} — \"{event.get('title', '')}\"")
            elif etype == "clipboard_text":
                lines.append(f"[{ts}] Clipboard copied: \"{event.get('content', '')}\"")
            elif etype == "session_end":
                lines.append(f"[{ts}] Left: {event['process']} — \"{event.get('title', '')}\" "
                             f"(duration: {event.get('duration_s', 0)}s, "
                             f"clicks: {event.get('click_count', 0)}, "
                             f"keystrokes: {event.get('keystroke_count', 0)})")
            lines.append("")

        return "\n".join(lines)


def parse_recording(jsonl_path: Path) -> Recording:
    recording = Recording(source_path=jsonl_path)
    text = jsonl_path.read_text().strip()

    if not text:
        return recording

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "recording_meta":
            recording.meta = event
            continue

        recording.events.append(event)

        screenshot = event.get("screenshot")
        if screenshot:
            recording.screenshot_paths.append(screenshot)

    return recording
