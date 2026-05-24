import sys
import threading
import time
from PIL import Image, ImageDraw
import pystray
from teach_skill.recorder.controller import RecorderController


def create_tray_icon_image():
    # Generate a simple 64x64 dynamic icon image
    # Red circle with a white border to indicate active recording
    img = Image.new("RGB", (64, 64), color="black")
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="red", outline="white", width=4)
    return img


class RecorderTrayApp:
    def __init__(self, controller: RecorderController):
        self.controller = controller
        self.icon = None
        self.polling_thread = None
        self.clipboard_thread = None
        self.keyboard_listener = None
        self.mouse_listener = None

    def start(self):
        # Create system tray icon
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Teach Skill (Recording...)", lambda: None, enabled=False),
            pystray.MenuItem("Stop Recording & Compile", self.on_stop),
        )
        self.icon = pystray.Icon("teach-skill", image, "Teach Skill Recorder", menu)

        # Start input listeners in background threads
        self.start_listeners()

        # Start window & clipboard polling in background daemon threads
        self.polling_thread = threading.Thread(target=self.poll_active_window, daemon=True)
        self.polling_thread.start()

        self.clipboard_thread = threading.Thread(target=self.poll_clipboard, daemon=True)
        self.clipboard_thread.start()

        # Run system tray icon on the main thread (blocking loop)
        self.icon.run()

    def start_listeners(self):
        # Dynamically import pynput listeners
        try:
            from pynput import keyboard, mouse
            
            # Hook the controller's callback handlers
            self.keyboard_listener = keyboard.Listener(on_press=self.controller.input_counter.on_press)
            self.mouse_listener = mouse.Listener(on_click=self.controller.input_counter.on_click)

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
        icon.stop()
        print("Recording saved successfully. Run `teach-skill compile` to build your skill!")
