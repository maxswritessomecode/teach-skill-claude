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
        self.input_counter = InputCounter()
        self.clipboard_monitor = ClipboardMonitor(self.privacy)
        
        self.is_recording = True
        self.start_time = time.time()
        self.last_screenshot_time = 0
        
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
                clicks, keys = self.input_counter.reset()
                self.writer.write_event({
                    "type": "session_end",
                    "process": prev_process,
                    "title": self.privacy.redact_title(prev_title),
                    "duration_s": round(time.time() - self.start_time, 1),
                    "click_count": clicks,
                    "keystroke_count": keys
                })
            
            # Snap screenshot for the new window switch
            self.capture_screenshot(window_info)
            self.start_time = time.time()

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

    def capture_screenshot(self, window_info: dict):
        # Apply privacy filter guards
        title = window_info.get("title", "")
        if self.privacy.is_sensitive_title(title):
            self.writer.write_event({
                "type": "window_switch",
                "process": window_info.get("process"),
                "title": "[auth/login - redacted]",
                "screenshot": "suppressed:auth_detected"
            })
            return
            
        frame_path = self.writer.next_frame_path()
        img = capture_screenshot_stub()
        img.save(frame_path)
        
        self.writer.write_event({
            "type": "window_switch",
            "process": window_info.get("process"),
            "title": title,
            "screenshot": str(frame_path.relative_to(self.writer.session_dir))
        })
        self.last_screenshot_time = time.time()

    def stop_recording(self):
        self.is_recording = False
        if self.window_tracker.last_process:
            clicks, keys = self.input_counter.reset()
            self.writer.write_event({
                "type": "session_end",
                "process": self.window_tracker.last_process,
                "title": self.privacy.redact_title(self.window_tracker.last_title),
                "duration_s": round(time.time() - self.start_time, 1),
                "click_count": clicks,
                "keystroke_count": keys
            })
