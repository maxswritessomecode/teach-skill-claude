import sys
import time
from pathlib import Path
from PIL import Image
import socket

from teach_skill.recorder.writer import EventWriter
from teach_skill.recorder.window import WindowTracker
from teach_skill.recorder.input import InputCounter
from teach_skill.recorder.clipboard import ClipboardMonitor
from teach_skill.recorder.privacy import PrivacyFilter
from teach_skill.recorder.compat import get_active_window_info, capture_screenshot_stub


class RecorderController:
    def __init__(self, writer: EventWriter, config: dict):
        self.writer = writer
        self.config = config
        self.privacy = PrivacyFilter(enabled=config.get("privacy_filter", True))
        
        self.window_tracker = WindowTracker()
        self.input_counter = InputCounter(capture_raw=config.get("capture_raw_keystrokes", False))
        self.clipboard_monitor = ClipboardMonitor(self.privacy)
        
        self.is_recording = True
        self.is_paused = False
        self.start_time = time.time()
        self.last_screenshot_time = 0
        self.last_screenshot_frame_id = None
        self.last_screenshot_frame_path = None
        self.in_app_capture_interval_s = 5.0
        self.drag_start = None
        self.drag_last = None
        self.drag_button = None
        
        # Write initial metadata event
        try:
            machine_name = socket.gethostname()
        except Exception:
            machine_name = "LOCAL-PC"
            
        self.writer.write_event({
            "type": "recording_meta",
            "machine": machine_name,
            "os": sys.platform,
            "version": "0.1.0"
        })

    def on_window_switch(self, window_info: dict):
        if not self.is_recording or self.is_paused:
            return
            
        # Keep a reference to the previous state before updating
        prev_process = self.window_tracker.last_process
        prev_title = self.window_tracker.last_title
        
        if self.window_tracker.update_active_window(window_info):
            # End previous window session
            if prev_process:
                self._write_session_end(prev_process, prev_title)
            
            # Snap screenshot for the new window switch
            self.capture_screenshot(window_info)
            self.start_time = time.time()

    def on_click(self, x, y, button, pressed):
        if not self.is_recording or self.is_paused:
            return
        if not pressed:
            self._finish_pointer_action(x, y, button)
            return
        if not self.window_tracker.last_process:
            self.on_window_switch(get_active_window_info())
        if not self.window_tracker.last_process:
            return

        current_info = get_active_window_info()
        if (
            current_info.get("process") != self.window_tracker.last_process
            or current_info.get("title") != self.window_tracker.last_title
        ):
            self.on_window_switch(current_info)

        self.input_counter.on_click(x, y, button, pressed)
        self.drag_start = (x, y)
        self.drag_last = (x, y)
        self.drag_button = str(button) if button is not None else None

    def write_click_event(self, x, y, button):
        if self.privacy.is_sensitive_title(self.window_tracker.last_title):
            self.writer.write_event({
                "type": "click",
                "process": self.window_tracker.last_process,
                "title": "[auth/login - redacted]",
                "details_redacted": "sensitive_title",
            })
            return

        event = {
            "type": "click",
            "process": self.window_tracker.last_process,
            "title": self.privacy.redact_title(self.window_tracker.last_title),
            "x": x,
            "y": y,
            "button": str(button) if button is not None else None,
        }
        if self.last_screenshot_frame_id:
            event["screenshot_frame_id"] = self.last_screenshot_frame_id
        if self.last_screenshot_frame_path:
            event["screenshot_frame_path"] = self.last_screenshot_frame_path
        self.writer.write_event(event)

    def on_press(self, key):
        if self.is_paused:
            return
        shortcut = self.input_counter.on_press(key)
        if shortcut:
            self.write_keyboard_shortcut_event(shortcut)
            self.capture_post_action(f"shortcut:{shortcut}")

    def on_release(self, key):
        self.input_counter.on_release(key)

    def on_move(self, x, y):
        if not self.is_recording or self.is_paused or self.drag_start is None:
            return
        self.drag_last = (x, y)

    def on_clipboard_change(self, text: str):
        if not self.is_recording or self.is_paused:
            return
            
        filtered = self.clipboard_monitor.update_content(text)
        if filtered:
            self.writer.write_event({
                "type": "clipboard_text",
                "content": filtered,
                "source_process": self.window_tracker.last_process or "unknown"
            })

    def capture_screenshot(
        self,
        window_info: dict,
        event_type: str = "window_switch",
        trigger: str | None = None,
    ):
        if not self.is_recording or self.is_paused:
            return

        # Apply privacy filter guards
        title = window_info.get("title", "")
        if self.privacy.is_sensitive_title(title):
            self.last_screenshot_frame_id = None
            self.last_screenshot_frame_path = None
            event = {
                "type": event_type,
                "process": window_info.get("process"),
                "title": "[auth/login - redacted]",
                "screenshot": "suppressed:auth_detected"
            }
            if trigger:
                event["trigger"] = trigger
            self.writer.write_event(event)
            self.last_screenshot_time = time.time()
            return

        frame_path = self.writer.next_frame_path()
        img = capture_screenshot_stub()
        img.save(frame_path)
        frame_id = frame_path.stem
        relative_frame_path = str(frame_path.relative_to(self.writer.session_dir))
        self.last_screenshot_frame_id = frame_id
        self.last_screenshot_frame_path = relative_frame_path

        event = {
            "type": event_type,
            "process": window_info.get("process"),
            "title": title,
            "screenshot": relative_frame_path,
            "frame_id": frame_id
        }
        if trigger:
            event["trigger"] = trigger
        self.writer.write_event(event)
        self.last_screenshot_time = time.time()

    def capture_post_action(self, trigger: str):
        if not self.window_tracker.last_process:
            return
        current_info = get_active_window_info()
        self.capture_screenshot(
            {
                "process": current_info.get("process") or self.window_tracker.last_process,
                "title": current_info.get("title") or self.window_tracker.last_title,
            },
            event_type="post_action_capture",
            trigger=trigger,
        )

    def write_keyboard_shortcut_event(self, shortcut: str):
        if not self.window_tracker.last_process:
            self.on_window_switch(get_active_window_info())
        if not self.window_tracker.last_process:
            return
        self.writer.write_event(
            {
                "type": "keyboard_shortcut",
                "process": self.window_tracker.last_process,
                "title": self.privacy.redact_title(self.window_tracker.last_title),
                "shortcut": shortcut,
            }
        )

    def _finish_pointer_action(self, x, y, button):
        if self.drag_start is None:
            return
        start_x, start_y = self.drag_start
        end_x, end_y = x, y
        self.drag_start = None
        self.drag_last = None
        drag_button = self.drag_button
        self.drag_button = None
        if abs(end_x - start_x) < 5 and abs(end_y - start_y) < 5:
            if time.time() - self.last_screenshot_time >= self.in_app_capture_interval_s:
                self.capture_screenshot(
                    {
                        "process": self.window_tracker.last_process,
                        "title": self.window_tracker.last_title,
                    },
                    event_type="in_app_capture",
                    trigger="click_after_5s",
                )
            self.write_click_event(start_x, start_y, button)
            self.capture_post_action("click")
            return
        if not self.window_tracker.last_process:
            return
        current_info = get_active_window_info()
        process = current_info.get("process") or self.window_tracker.last_process
        title = current_info.get("title") or self.window_tracker.last_title
        if self.privacy.is_sensitive_title(title):
            self.writer.write_event(
                {
                    "type": "drag_select",
                    "process": process,
                    "title": "[auth/login - redacted]",
                    "details_redacted": "sensitive_title",
                }
            )
            self.capture_post_action("drag_select")
            return
        if self.privacy.is_sensitive_title(self.window_tracker.last_title):
            self.writer.write_event(
                {
                    "type": "drag_select",
                    "process": process,
                    "title": "[auth/login - redacted]",
                    "details_redacted": "sensitive_title",
                }
            )
            self.capture_post_action("drag_select")
            return
        self.writer.write_event(
            {
                "type": "drag_select",
                "process": process,
                "title": self.privacy.redact_title(title),
                "start": [start_x, start_y],
                "end": [end_x, end_y],
                "button": str(button) if button is not None else drag_button,
            }
        )
        self.capture_post_action("drag_select")

    def _write_session_end(self, process, title) -> bool:
        if not process:
            return False
        clicks, keys, typed_text = self.input_counter.reset()
        event = {
            "type": "session_end",
            "process": process,
            "title": self.privacy.redact_title(title),
            "duration_s": round(time.time() - self.start_time, 1),
            "click_count": clicks,
            "keystroke_count": keys
        }
        if self.config.get("capture_raw_keystrokes", False) and typed_text:
            event["keys_typed"] = typed_text
        self.writer.write_event(event)
        return True

    def _clear_active_session(self):
        self.window_tracker.last_process = None
        self.window_tracker.last_title = None
        self.last_screenshot_frame_id = None
        self.last_screenshot_frame_path = None
        self.drag_start = None
        self.drag_last = None
        self.drag_button = None

    def pause_recording(self):
        if self.is_paused:
            return
        if self._write_session_end(
            self.window_tracker.last_process,
            self.window_tracker.last_title,
        ):
            self._clear_active_session()
        self.is_paused = True
        self.writer.write_event({"type": "recording_paused"})

    def resume_recording(self):
        if not self.is_paused:
            return
        self.is_paused = False
        self.start_time = time.time()
        self.writer.write_event({"type": "recording_resumed"})

    def stop_recording(self):
        self.is_recording = False
        if self.window_tracker.last_process:
            self._write_session_end(
                self.window_tracker.last_process,
                self.window_tracker.last_title,
            )
            self._clear_active_session()
