import hashlib
import sys
import time
from PIL import Image
import socket

from teach_skill.recorder.writer import EventWriter
from teach_skill.recorder.window import WindowTracker
from teach_skill.recorder.input import InputCounter
from teach_skill.recorder.clipboard import ClipboardMonitor
from teach_skill.recorder.privacy import PrivacyFilter
from teach_skill.recorder.ui_context import UIContextProvider
from teach_skill.recorder.compat import get_active_window_info, capture_screenshot
from teach_skill.runtime_log import get_logger


logger = get_logger("recorder.controller")


GENERIC_UI_CONTEXT_TYPES = {
    "",
    "Pane",
    "Window",
    "Document",
    "Group",
    "Custom",
    "Image",
}
SCREENSHOT_CAPTURE_MODES = {"adaptive", "all", "minimal"}


class RecorderController:
    def __init__(self, writer: EventWriter, config: dict):
        self.writer = writer
        self.config = config
        self.privacy = PrivacyFilter(enabled=config.get("privacy_filter", True))
        
        self.window_tracker = WindowTracker()
        self.input_counter = InputCounter(capture_raw=config.get("capture_raw_keystrokes", False))
        self.clipboard_monitor = ClipboardMonitor(self.privacy)
        self.ui_context = UIContextProvider(enabled=config.get("capture_ui_context", True))
        
        self.is_recording = True
        self.is_paused = False
        self.start_time = time.time()
        self.last_screenshot_time = 0
        self.last_screenshot_frame_id = None
        self.last_screenshot_frame_path = None
        self.last_frame_hash = None
        self.screenshot_capture_mode = self._screenshot_capture_mode(
            config.get("screenshot_capture_mode", "adaptive")
        )
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
        ui_context = self._ui_context_at_point(x, y)
        if ui_context:
            event["ui_context"] = ui_context
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
        ui_context: dict | None = None,
    ):
        if not self.is_recording or self.is_paused:
            return

        # Apply privacy filter guards
        title = window_info.get("title", "")
        if self.privacy.is_sensitive_title(title):
            self._clear_last_screenshot_frame()
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

        if self.screenshot_capture_mode == "minimal" and event_type != "window_switch":
            self._write_capture_event(
                window_info,
                event_type=event_type,
                trigger=trigger,
                ui_context=ui_context,
            )
            self.last_screenshot_time = time.time()
            return

        try:
            img = capture_screenshot()
            frame_hash = self._image_hash(img)
        except Exception:
            logger.exception("screenshot capture failed")
            self._clear_last_screenshot_frame()
            self._write_capture_event(
                window_info,
                event_type=event_type,
                trigger=trigger,
                ui_context=ui_context,
                screenshot="suppressed:capture_failed",
            )
            self.last_screenshot_time = time.time()
            return
        if (
            event_type == "post_action_capture"
            and frame_hash == self.last_frame_hash
            and self.last_screenshot_frame_id
            and self.last_screenshot_frame_path
        ):
            self._write_capture_event(
                window_info,
                event_type=event_type,
                trigger=trigger,
                ui_context=ui_context,
                screenshot=self.last_screenshot_frame_path,
                frame_id=self.last_screenshot_frame_id,
                deduped_from_frame_id=self.last_screenshot_frame_id,
            )
            self.last_screenshot_time = time.time()
            return

        frame_path = self.writer.next_frame_path()
        try:
            img.save(frame_path)
        except Exception:
            logger.exception("screenshot save failed path=%s", frame_path)
            self._clear_last_screenshot_frame()
            self._write_capture_event(
                window_info,
                event_type=event_type,
                trigger=trigger,
                ui_context=ui_context,
                screenshot="suppressed:capture_failed",
            )
            self.last_screenshot_time = time.time()
            return
        frame_id = frame_path.stem
        relative_frame_path = str(frame_path.relative_to(self.writer.session_dir))
        self.last_screenshot_frame_id = frame_id
        self.last_screenshot_frame_path = relative_frame_path
        self.last_frame_hash = frame_hash

        self._write_capture_event(
            window_info,
            event_type=event_type,
            trigger=trigger,
            ui_context=ui_context,
            screenshot=relative_frame_path,
            frame_id=frame_id,
        )
        self.last_screenshot_time = time.time()

    def capture_post_action(self, trigger: str):
        if not self.window_tracker.last_process:
            return
        current_info = get_active_window_info()
        window_info = {
            "process": current_info.get("process") or self.window_tracker.last_process,
            "title": current_info.get("title") or self.window_tracker.last_title,
        }
        ui_context = None
        if not self.privacy.is_sensitive_title(current_info.get("title", "")):
            ui_context = self._focused_ui_context()
        if (
            self.screenshot_capture_mode == "adaptive"
            and self._post_action_context_is_descriptive(ui_context)
        ):
            self._write_capture_event(
                window_info,
                event_type="post_action_capture",
                trigger=trigger,
                ui_context=ui_context,
            )
            return
        self.capture_screenshot(
            window_info,
            event_type="post_action_capture",
            trigger=trigger,
            ui_context=ui_context,
        )

    def write_keyboard_shortcut_event(self, shortcut: str):
        if not self.window_tracker.last_process:
            self.on_window_switch(get_active_window_info())
        if not self.window_tracker.last_process:
            return
        event = {
            "type": "keyboard_shortcut",
            "process": self.window_tracker.last_process,
            "title": self.privacy.redact_title(self.window_tracker.last_title),
            "shortcut": shortcut,
        }
        if not self.privacy.is_sensitive_title(self.window_tracker.last_title):
            ui_context = self._focused_ui_context()
            if ui_context:
                event["ui_context"] = ui_context
        self.writer.write_event(event)

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
            self._with_ui_context_pair(
                {
                    "type": "drag_select",
                    "process": process,
                    "title": self.privacy.redact_title(title),
                    "start": [start_x, start_y],
                    "end": [end_x, end_y],
                    "button": str(button) if button is not None else drag_button,
                },
                start_x,
                start_y,
                end_x,
                end_y,
            )
        )
        self.capture_post_action("drag_select")

    def _ui_context_at_point(self, x: int, y: int) -> dict | None:
        try:
            context = self.ui_context.context_at_point(x, y)
        except Exception:
            return None
        return self._sanitize_ui_context(context)

    def _focused_ui_context(self) -> dict | None:
        try:
            context = self.ui_context.focused_context()
        except Exception:
            return None
        return self._sanitize_ui_context(context)

    def _with_ui_context_pair(
        self,
        event: dict,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> dict:
        start_context = self._ui_context_at_point(start_x, start_y)
        end_context = self._ui_context_at_point(end_x, end_y)
        if start_context:
            event["ui_context_start"] = start_context
        if end_context:
            event["ui_context_end"] = end_context
        return event

    def _write_capture_event(
        self,
        window_info: dict,
        event_type: str,
        trigger: str | None = None,
        ui_context: dict | None = None,
        screenshot: str | None = None,
        frame_id: str | None = None,
        deduped_from_frame_id: str | None = None,
    ) -> None:
        event = {
            "type": event_type,
            "process": window_info.get("process"),
            "title": window_info.get("title", ""),
        }
        if screenshot:
            event["screenshot"] = screenshot
        if frame_id:
            event["frame_id"] = frame_id
        if deduped_from_frame_id:
            event["deduped_from_frame_id"] = deduped_from_frame_id
        if trigger:
            event["trigger"] = trigger
        if ui_context:
            event["ui_context"] = ui_context
        self.writer.write_event(event)

    def _post_action_context_is_descriptive(self, ui_context) -> bool:
        if not isinstance(ui_context, dict):
            return False
        name = str(ui_context.get("name") or "").strip()
        control_type = str(ui_context.get("control_type") or "").strip()
        return bool(name) and control_type not in GENERIC_UI_CONTEXT_TYPES

    def _image_hash(self, img: Image.Image) -> str:
        digest = hashlib.sha1()
        digest.update(str(img.mode).encode("utf-8"))
        digest.update(str(img.size).encode("utf-8"))
        digest.update(img.tobytes())
        return digest.hexdigest()

    def _screenshot_capture_mode(self, raw_mode) -> str:
        mode = str(raw_mode or "adaptive").strip().lower()
        if mode not in SCREENSHOT_CAPTURE_MODES:
            logger.warning("invalid screenshot_capture_mode=%s; using adaptive", raw_mode)
            return "adaptive"
        return mode

    def _clear_last_screenshot_frame(self) -> None:
        self.last_screenshot_frame_id = None
        self.last_screenshot_frame_path = None
        self.last_frame_hash = None

    def _sanitize_ui_context(self, context):
        if not context:
            return None
        if isinstance(context, dict):
            sanitized = {}
            for key, value in context.items():
                cleaned = self._sanitize_ui_context(value)
                if cleaned not in (None, "", [], {}):
                    sanitized[key] = cleaned
            return sanitized
        if isinstance(context, list):
            cleaned_items = [
                self._sanitize_ui_context(item)
                for item in context[:8]
            ]
            return [item for item in cleaned_items if item not in (None, "", [], {})]
        if isinstance(context, str):
            return self.privacy.redact_ui_text(context)
        if isinstance(context, (int, float, bool)):
            return context
        return self.privacy.redact_ui_text(str(context))

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
        self._clear_last_screenshot_frame()
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
