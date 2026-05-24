from unittest.mock import MagicMock
from teach_skill.recorder.tray import RecorderTrayApp


def test_tray_app_initialization():
    controller = MagicMock()
    app = RecorderTrayApp(controller)
    assert app.controller == controller
    assert app.icon is None
