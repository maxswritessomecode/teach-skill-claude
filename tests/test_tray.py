from unittest.mock import MagicMock
from teach_skill.recorder.control import request_pause, request_resume, request_stop
from teach_skill.recorder.tray import RecorderTrayApp


def test_tray_app_initialization():
    controller = MagicMock()
    app = RecorderTrayApp(controller)
    assert app.controller == controller
    assert app.icon is None


def test_tray_app_stops_when_stop_request_exists(tmp_path):
    request_stop(tmp_path)
    controller = MagicMock()
    icon = MagicMock()
    app = RecorderTrayApp(controller, recordings_root=tmp_path)
    app.icon = icon

    assert app.stop_if_requested() is True

    controller.stop_recording.assert_called_once()
    icon.stop.assert_called_once()
    assert not (tmp_path / ".recording.stop").exists()


def test_tray_app_stop_is_idempotent_when_tray_and_gui_both_stop(tmp_path):
    request_stop(tmp_path)
    controller = MagicMock()
    icon = MagicMock()
    app = RecorderTrayApp(controller, recordings_root=tmp_path)
    app.icon = icon

    app.on_stop(icon, None)
    assert app.stop_if_requested() is True
    assert app.stop(icon) is False

    controller.stop_recording.assert_called_once()
    icon.stop.assert_called_once()
    assert not (tmp_path / ".recording.stop").exists()


def test_tray_app_applies_pause_and_resume_requests(tmp_path):
    controller = MagicMock()
    app = RecorderTrayApp(controller, recordings_root=tmp_path)

    request_pause(tmp_path)
    assert app.apply_recording_controls() is True
    controller.pause_recording.assert_called_once()

    request_resume(tmp_path)
    assert app.apply_recording_controls() is True
    controller.resume_recording.assert_called_once()
