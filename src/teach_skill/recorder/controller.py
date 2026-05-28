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
        self.start_time = time.time()
        self.last_screenshot_time = 0
        self.in_app_capture_interval_s = 5.0
        
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
        if not self.is_recording:
            return
            
        # Keep a reference to the previous state before updating
        prev_process = self.window_tracker.last_process
        prev_title = self.window_tracker.last_title
        
        if self.window_tracker.update_active_window(window_info):
            # End previous window session
            if prev_process:
                clicks, keys, typed_text = self.input_counter.reset()
                event = {
                    "type": "session_end",
                    "process": prev_process,
                    "title": self.privacy.redact_title(prev_title),
                    "duration_s": round(time.time() - self.start_time, 1),
                    "click_count": clicks,
                    "keystroke_count": keys
                }
                if self.config.get("capture_raw_keystrokes", False) and typed_text:
                    event["keys_typed"] = typed_text
                self.writer.write_event(event)
            
            # Snap screenshot for the new window switch
            self.capture_screenshot(window_info)
            self.start_time = time.time()

    def on_click(self, x, y, button, pressed):
        self.input_counter.on_click(x, y, button, pressed)
        if not self.is_recording or not pressed:
            return
        if not self.window_tracker.last_process:
            return
        if time.time() - self.last_screenshot_time < self.in_app_capture_interval_s:
            return

        current_info = get_active_window_info()
        if (
            current_info.get("process") != self.window_tracker.last_process
            or current_info.get("title") != self.window_tracker.last_title
        ):
            self.on_window_switch(current_info)
            return

        self.capture_screenshot(
            {
                "process": self.window_tracker.last_process,
                "title": self.window_tracker.last_title,
            },
            event_type="in_app_capture",
            trigger="click_after_5s",
        )

    def on_press(self, key):
        self.input_counter.on_press(key)

    def on_clipboard_change(self, text: str):
        if not self.is_recording:
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
        # Apply privacy filter guards
        title = window_info.get("title", "")
        if self.privacy.is_sensitive_title(title):
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
        
        event = {
            "type": event_type,
            "process": window_info.get("process"),
            "title": title,
            "screenshot": str(frame_path.relative_to(self.writer.session_dir))
        }
        if trigger:
            event["trigger"] = trigger
        self.writer.write_event(event)
        self.last_screenshot_time = time.time()

    def stop_recording(self):
        self.is_recording = False
        if self.window_tracker.last_process:
            clicks, keys, typed_text = self.input_counter.reset()
            event = {
                "type": "session_end",
                "process": self.window_tracker.last_process,
                "title": self.privacy.redact_title(self.window_tracker.last_title),
                "duration_s": round(time.time() - self.start_time, 1),
                "click_count": clicks,
                "keystroke_count": keys
            }
            if self.config.get("capture_raw_keystrokes", False) and typed_text:
                event["keys_typed"] = typed_text
            self.writer.write_event(event)
