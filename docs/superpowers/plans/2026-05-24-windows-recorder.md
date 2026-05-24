# Windows Recorder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the telemetry recorder component (Process A — `teach-skill record`) as a Windows system tray app that captures active window changes, clipboard updates, input metrics (keystrokes and mouse clicks), and screenshots, streaming them crash-resiliently to a JSONL file. 

**Architecture:** A set of modules under `teach_skill/recorder/` controlled by a main recording controller. Utilizes a platform compatibility stubbing layer so all modules import and test successfully on Mac/Linux while calling native Win32/pynput hooks on Windows.

**Tech Stack:** Python 3.10+, click (CLI), pywin32 (Windows GUI/process hooks), pynput (input/hotkeys), Pillow (screenshots), pystray (system tray), pytest (testing).

---

### Task 1: Platform Compatibility & Stubs

**Files:**
- Create: `src/teach_skill/recorder/compat.py`
- Create: `tests/test_compat.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_compat.py`:
```python
import sys
from teach_skill.recorder.compat import get_active_window_info, capture_screenshot_stub


def test_active_window_info_returns_dict():
    info = get_active_window_info()
    assert isinstance(info, dict)
    assert "process" in info
    assert "title" in info


def test_active_window_stub_returns_mock_on_non_windows():
    if sys.platform != "win32":
        info = get_active_window_info()
        assert info["process"] == "mock_process.exe"
        assert "Mock Title" in info["title"]


def test_capture_screenshot_stub_returns_image():
    from PIL import Image
    img = capture_screenshot_stub()
    assert isinstance(img, Image.Image)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/test_compat.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/recorder/compat.py`:
```python
import sys
from PIL import Image

# Dynamic import helper to mock Win32 modules on Mac/Linux
if sys.platform == "win32":
    import win32gui
    import win32process
    import win32clipboard
    import win32con
else:
    # Stubs for non-Windows platforms
    class MockWin32:
        def __getattr__(self, name):
            return lambda *args, **kwargs: 0
    
    win32gui = MockWin32()
    win32process = MockWin32()
    win32clipboard = MockWin32()
    win32con = MockWin32()


def get_active_window_info() -> dict:
    if sys.platform == "win32":
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            # Fetch window title
            title = win32gui.GetWindowText(hwnd)
            # For simplicity, fallback if title empty
            if not title:
                title = "Unknown Window"
            
            # Simple process name lookup (native process listing left to recorder/window.py)
            return {"process": f"pid_{pid}.exe", "title": title}
        except Exception:
            return {"process": "unknown.exe", "title": "Unknown Window"}
    
    return {"process": "mock_process.exe", "title": "Mock Title - Chrome"}


def capture_screenshot_stub() -> Image.Image:
    # Fallback capture creating a colored box on Mac/Linux
    if sys.platform == "win32":
        from PIL import ImageGrab
        return ImageGrab.grab()
    
    return Image.new("RGB", (800, 600), color="blue")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_compat.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_compat.py src/teach_skill/recorder/compat.py
git commit -m "feat: platform compatibility layer for cross-platform test execution"
```

---

### Task 2: Active Window Tracker

**Files:**
- Create: `src/teach_skill/recorder/window.py`
- Create: `tests/test_window.py`

- [ ] **Step 1: Write tests**

`tests/test_window.py`:
```python
from teach_skill.recorder.window import WindowTracker


def test_window_tracker_initial_state():
    tracker = WindowTracker()
    assert tracker.last_process is None
    assert tracker.last_title is None


def test_window_tracker_detects_switch():
    tracker = WindowTracker()
    switched = tracker.update_active_window({"process": "chrome.exe", "title": "Google Docs"})
    assert switched is True
    assert tracker.last_process == "chrome.exe"
    
    # Switch title only
    switched_title = tracker.update_active_window({"process": "chrome.exe", "title": "YouTube"})
    assert switched_title is True
    assert tracker.last_title == "YouTube"
    
    # Same window = no switch
    switched_same = tracker.update_active_window({"process": "chrome.exe", "title": "YouTube"})
    assert switched_same is False
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/test_window.py -v`

- [ ] **Step 3: Write implementation**

`src/teach_skill/recorder/window.py`:
```python
class WindowTracker:
    def __init__(self):
        self.last_process = None
        self.last_title = None

    def update_active_window(self, current_info: dict) -> bool:
        process = current_info.get("process")
        title = current_info.get("title")

        if process != self.last_process or title != self.last_title:
            self.last_process = process
            self.last_title = title
            return True
        
        return False
```

- [ ] **Step 4: Run tests to pass**

Run: `.venv/bin/pytest tests/test_window.py -v`

- [ ] **Step 5: Commit**

```bash
git add tests/test_window.py src/teach_skill/recorder/window.py
git commit -m "feat: WindowTracker module detecting process and title shifts"
```

---

### Task 3: Input Metric Counter

**Files:**
- Create: `src/teach_skill/recorder/input.py`
- Create: `tests/test_input.py`

- [ ] **Step 1: Write tests**

`tests/test_input.py`:
```python
from teach_skill.recorder.input import InputCounter


def test_input_counter_accumulates_clicks():
    counter = InputCounter()
    assert counter.click_count == 0
    counter.on_click(0, 0, None, True)
    counter.on_click(10, 10, None, True)
    assert counter.click_count == 2


def test_input_counter_accumulates_keys():
    counter = InputCounter()
    assert counter.keystroke_count == 0
    counter.on_press(None)
    counter.on_press(None)
    assert counter.keystroke_count == 2


def test_input_counter_reset():
    counter = InputCounter()
    counter.click_count = 5
    counter.keystroke_count = 10
    clicks, keys = counter.reset()
    assert clicks == 5
    assert keys == 10
    assert counter.click_count == 0
    assert counter.keystroke_count == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/test_input.py -v`

- [ ] **Step 3: Write implementation**

`src/teach_skill/recorder/input.py`:
```python
class InputCounter:
    def __init__(self):
        self.click_count = 0
        self.keystroke_count = 0

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.click_count += 1

    def on_press(self, key):
        self.keystroke_count += 1

    def reset(self) -> tuple[int, int]:
        clicks = self.click_count
        keys = self.keystroke_count
        self.click_count = 0
        self.keystroke_count = 0
        return clicks, keys
```

- [ ] **Step 4: Run tests to pass**

Run: `.venv/bin/pytest tests/test_input.py -v`

- [ ] **Step 5: Commit**

```bash
git add tests/test_input.py src/teach_skill/recorder/input.py
git commit -m "feat: InputCounter compiling mouse clicks and keystroke frequency"
```

---

### Task 4: Clipboard Monitor

**Files:**
- Create: `src/teach_skill/recorder/clipboard.py`
- Create: `tests/test_clipboard.py`

- [ ] **Step 1: Write tests**

`tests/test_clipboard.py`:
```python
from teach_skill.recorder.clipboard import ClipboardMonitor
from teach_skill.recorder.privacy import PrivacyFilter


def test_clipboard_monitor_detects_changes():
    monitor = ClipboardMonitor(privacy_filter=PrivacyFilter(enabled=True))
    assert monitor.update_content("test") == "test"
    # Same content = no change detected
    assert monitor.update_content("test") is None
    # Sensitive content = redacted
    assert monitor.update_content("password = secret123") is None
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/test_clipboard.py -v`

- [ ] **Step 3: Write implementation**

`src/teach_skill/recorder/clipboard.py`:
```python
from teach_skill.recorder.privacy import PrivacyFilter


class ClipboardMonitor:
    def __init__(self, privacy_filter: PrivacyFilter):
        self.privacy_filter = privacy_filter
        self.last_text = ""

    def update_content(self, text: str) -> str | None:
        if not text or text == self.last_text:
            return None
        
        self.last_text = text
        if self.privacy_filter.is_sensitive_clipboard(text):
            return None
            
        return text
```

- [ ] **Step 4: Run tests to pass**

Run: `.venv/bin/pytest tests/test_clipboard.py -v`

- [ ] **Step 5: Commit**

```bash
git add tests/test_clipboard.py src/teach_skill/recorder/clipboard.py
git commit -m "feat: ClipboardMonitor detecting clipboard shifts and filtering secrets"
```

---

### Task 5: Recorder Controller & E2E Integration

**Files:**
- Create: `src/teach_skill/recorder/controller.py`
- Create: `tests/test_recorder_controller.py`

- [ ] **Step 1: Write integration tests**

`tests/test_recorder_controller.py`:
```python
from pathlib import Path
from teach_skill.recorder.controller import RecorderController
from teach_skill.recorder.writer import EventWriter
from teach_skill.config import DEFAULT_CONFIG


def test_recorder_controller_streams_events(tmp_path):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    
    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    controller.on_clipboard_change("some payload")
    controller.stop_recording()
    
    lines = writer.jsonl_path.read_text().strip().split("\n")
    assert len(lines) == 3  # meta, window_switch, session_end
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/test_recorder_controller.py -v`

- [ ] **Step 3: Write implementation**

`src/teach_skill/recorder/controller.py`:
```python
import sys
import time
from pathlib import Path
from PIL import Image

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
        self.writer.write_event({
            "type": "recording_meta",
            "machine": "LOCAL-PC",
            "os": sys.platform,
            "version": "0.1.0"
        })

    def on_window_switch(self, window_info: dict):
        if not self.is_recording:
            return
            
        if self.window_tracker.update_active_window(window_info):
            # End previous window session
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
```

- [ ] **Step 4: Run tests to pass**

Run: `.venv/bin/pytest tests/test_recorder_controller.py -v`
Expected: Passes cleanly on all platforms (Mac, Linux, Windows)

- [ ] **Step 5: Commit**

```bash
git add tests/test_recorder_controller.py src/teach_skill/recorder/controller.py
git commit -m "feat: complete RecorderController integrating window, input, clipboard, and screenshots"
```
