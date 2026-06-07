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
                screen = _screen_suffix(event.get("frame_id"))
                lines.append(
                    f"[{ts}] Switched to: {event['process']} — "
                    f"\"{event.get('title', '')}\"{screen}"
                )
            elif etype == "in_app_capture":
                screen = _screen_suffix(event.get("frame_id"))
                lines.append(
                    f"[{ts}] In-app action in: {event['process']} — "
                    f"\"{event.get('title', '')}\"{screen}"
                )
            elif etype == "post_action_capture":
                screen = _screen_suffix(event.get("frame_id"))
                target = _target_suffix(event.get("ui_context"), prefix=" targeting")
                lines.append(
                    f"[{ts}] Post-action screen after {event.get('trigger', 'action')} "
                    f"in: {event['process']} — \"{event.get('title', '')}\""
                    f"{target}{screen}"
                )
            elif etype == "keyboard_shortcut":
                target = _target_suffix(event.get("ui_context"), prefix=" targeting")
                lines.append(
                    f"[{ts}] Pressed shortcut {event.get('shortcut', '')} "
                    f"in: {event['process']} — \"{event.get('title', '')}\"{target}"
                )
            elif etype == "drag_select":
                button = event.get("button") or "unknown button"
                start = event.get("start") or ["?", "?"]
                end = event.get("end") or ["?", "?"]
                target = _drag_target_suffix(
                    event.get("ui_context_start"),
                    event.get("ui_context_end"),
                )
                lines.append(
                    f"[{ts}] Dragged {button} from ({start[0]}, {start[1]}) "
                    f"to ({end[0]}, {end[1]}) "
                    f"in: {event['process']} — \"{event.get('title', '')}\"{target}"
                )
            elif etype == "click":
                screen = _screen_suffix(event.get("screenshot_frame_id"))
                button = event.get("button") or "unknown button"
                if event.get("details_redacted"):
                    lines.append(
                        f"[{ts}] Click details redacted "
                        f"in: {event['process']} — \"{event.get('title', '')}\""
                    )
                    lines.append("")
                    continue
                target = _target_suffix(event.get("ui_context"), prefix=" on")
                lines.append(
                    f"[{ts}] Clicked {button} "
                    f"at ({event.get('x', '?')}, {event.get('y', '?')}) "
                    f"in: {event['process']} — \"{event.get('title', '')}\""
                    f"{target}{screen}"
                )
            elif etype == "clipboard_text":
                lines.append(f"[{ts}] Clipboard copied: \"{event.get('content', '')}\"")
            elif etype == "session_end":
                lines.append(f"[{ts}] Left: {event['process']} — \"{event.get('title', '')}\" "
                             f"(duration: {event.get('duration_s', 0)}s, "
                             f"clicks: {event.get('click_count', 0)}, "
                             f"keystrokes: {event.get('keystroke_count', 0)})")
            lines.append("")

        return "\n".join(lines)


def _screen_suffix(frame_id: str | None) -> str:
    if not frame_id:
        return ""
    return f" (screen: {frame_id})"


def _target_suffix(context: dict | None, prefix: str) -> str:
    label = _context_label(context)
    if not label:
        return ""
    return f"{prefix} {label}"


def _drag_target_suffix(start_context: dict | None, end_context: dict | None) -> str:
    start_label = _context_label(start_context)
    end_label = _context_label(end_context)
    if start_label and end_label:
        return f" from {start_label} to {end_label}"
    if start_label:
        return f" from {start_label}"
    if end_label:
        return f" to {end_label}"
    return ""


def _context_label(context: dict | None) -> str:
    if not context:
        return ""
    control_type = context.get("control_type") or context.get("class_name")
    name = context.get("name")
    if control_type and name:
        return f"{control_type} \"{name}\""
    if name:
        return f"\"{name}\""
    if control_type:
        return str(control_type)
    return ""


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
