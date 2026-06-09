import sys
from types import SimpleNamespace
from teach_skill.recorder.compat import (
    get_active_window_info,
    capture_screenshot,
    capture_screenshot_stub,
)


def test_active_window_info_returns_dict():
    info = get_active_window_info()
    assert isinstance(info, dict)
    assert "process" in info
    assert "title" in info


def test_active_window_info_returns_test_fallback_when_win32_is_unavailable():
    if sys.platform != "win32":
        info = get_active_window_info()
        assert info["process"] == "mock_process.exe"
        assert "Mock Title" in info["title"]


def test_capture_screenshot_returns_image():
    from PIL import Image
    img = capture_screenshot()
    assert isinstance(img, Image.Image)


def test_capture_screenshot_stub_alias_is_kept_for_compatibility():
    assert capture_screenshot_stub is capture_screenshot


def test_get_clipboard_text_returns_string():
    from teach_skill.recorder.compat import get_clipboard_text
    txt = get_clipboard_text()
    assert isinstance(txt, str)
    if sys.platform != "win32":
        assert txt == "mock_clipboard_text"


def test_active_window_info_uses_real_process_name_on_windows(monkeypatch):
    from teach_skill.recorder import compat

    monkeypatch.setattr(compat.sys, "platform", "win32")
    monkeypatch.setattr(compat.win32gui, "GetForegroundWindow", lambda: 100)
    monkeypatch.setattr(
        compat.win32process,
        "GetWindowThreadProcessId",
        lambda hwnd: (1, 1234),
    )
    monkeypatch.setattr(compat.win32gui, "GetWindowText", lambda hwnd: "Quarterly Report")
    monkeypatch.setattr(
        compat,
        "psutil",
        SimpleNamespace(Process=lambda pid: SimpleNamespace(name=lambda: "EXCEL.EXE")),
    )

    assert get_active_window_info() == {
        "process": "EXCEL.EXE",
        "title": "Quarterly Report",
    }


def test_active_window_info_falls_back_when_process_name_lookup_fails(monkeypatch):
    from teach_skill.recorder import compat

    def raise_lookup_error(pid):
        raise RuntimeError("process exited")

    monkeypatch.setattr(compat.sys, "platform", "win32")
    monkeypatch.setattr(compat.win32gui, "GetForegroundWindow", lambda: 100)
    monkeypatch.setattr(
        compat.win32process,
        "GetWindowThreadProcessId",
        lambda hwnd: (1, 1234),
    )
    monkeypatch.setattr(compat.win32gui, "GetWindowText", lambda hwnd: "Quarterly Report")
    monkeypatch.setattr(compat, "psutil", SimpleNamespace(Process=raise_lookup_error))

    assert get_active_window_info() == {
        "process": "pid_1234.exe",
        "title": "Quarterly Report",
    }


def test_active_window_info_uses_pid_fallback_when_psutil_missing(monkeypatch):
    from teach_skill.recorder import compat

    monkeypatch.setattr(compat.sys, "platform", "win32")
    monkeypatch.setattr(compat.win32gui, "GetForegroundWindow", lambda: 100)
    monkeypatch.setattr(
        compat.win32process,
        "GetWindowThreadProcessId",
        lambda hwnd: (1, 1234),
    )
    monkeypatch.setattr(compat.win32gui, "GetWindowText", lambda hwnd: "Quarterly Report")
    monkeypatch.setattr(compat, "psutil", None)

    assert get_active_window_info() == {
        "process": "pid_1234.exe",
        "title": "Quarterly Report",
    }
