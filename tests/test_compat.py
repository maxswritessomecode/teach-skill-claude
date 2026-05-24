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


def test_get_clipboard_text_returns_string():
    from teach_skill.recorder.compat import get_clipboard_text
    txt = get_clipboard_text()
    assert isinstance(txt, str)
    if sys.platform != "win32":
        assert txt == "mock_clipboard_text"

