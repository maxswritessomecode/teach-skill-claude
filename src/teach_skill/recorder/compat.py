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
            
            # Simple process name lookup
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


def get_clipboard_text() -> str:
    if sys.platform == "win32":
        try:
            win32clipboard.OpenClipboard()
            text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return text or ""
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass
            return ""
    return "mock_clipboard_text"

