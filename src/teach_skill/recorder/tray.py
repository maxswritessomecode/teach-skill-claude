import sys
import threading
import time
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from teach_skill.recorder.controller import RecorderController
from teach_skill.recorder.control import (
    clear_pause_request,
    clear_resume_request,
    clear_stop_request,
    is_pause_requested,
    is_resume_requested,
    is_stop_requested,
    mark_recording_paused,
    mark_recording_resumed,
)


def create_tray_icon_image():
    # Generate a simple 64x64 dynamic icon image
    # Red circle with a white border to indicate active recording
    img = Image.new("RGB", (64, 64), color="black")
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="red", outline="white", width=4)
    return img


class RecorderTrayApp:
    def __init__(self, controller: RecorderController, recordings_root: Path | None = None):
        self.controller = controller
        self.recordings_root = recordings_root
        self.icon = None
        self.polling_thread = None
        self.clipboard_thread = None
        self.stop_request_thread = None
        self.keyboard_listener = None
        self.mouse_listener = None
        self._stop_lock = threading.Lock()
        self._stopping = False

    def start(self):
        # Create system tray icon
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Teach Skill Claude (Recording...)", lambda: None, enabled=False),
            pystray.MenuItem("Stop Recording & Compile", self.on_stop),
        )
        self.icon = pystray.Icon("teach-skill-claude", image, "Teach Skill Claude Recorder", menu)

        # Start input listeners in background threads
        self.start_listeners()

        # Start window & clipboard polling in background daemon threads
        self.polling_thread = threading.Thread(target=self.poll_active_window, daemon=True)
        self.polling_thread.start()

        self.clipboard_thread = threading.Thread(target=self.poll_clipboard, daemon=True)
        self.clipboard_thread.start()

        self.stop_request_thread = threading.Thread(target=self.poll_stop_request, daemon=True)
        self.stop_request_thread.start()

        # Run system tray icon on the main thread (blocking loop)
        self.icon.run()

    def start_listeners(self):
        # Dynamically import pynput listeners
        try:
            from pynput import keyboard, mouse
            
            # Hook the controller's callback handlers
            self.keyboard_listener = keyboard.Listener(on_press=self.controller.on_press)
            self.mouse_listener = mouse.Listener(on_click=self.controller.on_click)

            self.keyboard_listener.start()
            self.mouse_listener.start()
        except Exception as e:
            # Graceful fallback if OS permissions are missing
            print(f"Warning: Failed to start input listeners (usually due to Accessibility permissions): {e}", file=sys.stderr)

    def poll_active_window(self):
        from teach_skill.recorder.compat import get_active_window_info
        while self.controller.is_recording:
            try:
                info = get_active_window_info()
                self.controller.on_window_switch(info)
            except Exception:
                pass
            time.sleep(0.5)

    def poll_clipboard(self):
        from teach_skill.recorder.compat import get_clipboard_text
        while self.controller.is_recording:
            try:
                text = get_clipboard_text()
                if text:
                    self.controller.on_clipboard_change(text)
            except Exception:
                pass
            time.sleep(0.5)

    def on_stop(self, icon, item):
        self.stop(icon)

    def poll_stop_request(self):
        while self.controller.is_recording:
            self.apply_recording_controls()
            if self.stop_if_requested():
                return
            time.sleep(0.5)

    def apply_recording_controls(self) -> bool:
        if self.recordings_root is None:
            return False
        applied = False
        if is_pause_requested(self.recordings_root):
            clear_pause_request(self.recordings_root)
            self.controller.pause_recording()
            mark_recording_paused(self.recordings_root)
            applied = True
        if is_resume_requested(self.recordings_root):
            clear_resume_request(self.recordings_root)
            self.controller.resume_recording()
            mark_recording_resumed(self.recordings_root)
            applied = True
        return applied

    def stop_if_requested(self) -> bool:
        if self.recordings_root is None or not is_stop_requested(self.recordings_root):
            return False
        clear_stop_request(self.recordings_root)
        self.stop(self.icon)
        return True

    def stop(self, icon) -> bool:
        with self._stop_lock:
            if self._stopping:
                return False
            self._stopping = True

        # Stop recording loop and flush metadata
        self.controller.stop_recording()

        # Stop pynput listeners
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass

        # Stop system tray icon loop and quit
        if icon is not None:
            icon.stop()
        print("Recording saved successfully. Run `teach-skill compile` to build your skill!")
        return True
