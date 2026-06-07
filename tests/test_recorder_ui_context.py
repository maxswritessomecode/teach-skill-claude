import sys
import types

from teach_skill.recorder.ui_context import UIContextProvider


def test_ui_context_provider_is_disabled_outside_windows(monkeypatch):
    monkeypatch.setattr("teach_skill.recorder.ui_context.sys.platform", "darwin")

    provider = UIContextProvider(enabled=True)

    assert provider.context_at_point(1, 2) is None
    assert provider.focused_context() is None


def test_ui_context_provider_extracts_control_summary(monkeypatch):
    monkeypatch.setattr("teach_skill.recorder.ui_context.sys.platform", "win32")

    parent = FakeControl(name="Home", control_type="TabItem")
    control = FakeControl(
        name="Conditional Formatting",
        control_type="MenuItem",
        automation_id="ConditionalFormattingGallery",
        class_name="NetUIRibbonButton",
        rect=types.SimpleNamespace(left=10, top=20, right=110, bottom=60),
        parent=parent,
    )
    automation = types.SimpleNamespace(
        ControlFromPoint=lambda x, y: control,
        GetFocusedControl=lambda: control,
    )
    monkeypatch.setitem(sys.modules, "uiautomation", automation)

    provider = UIContextProvider(enabled=True)

    context = provider.context_at_point(42, 84)

    assert context == {
        "name": "Conditional Formatting",
        "control_type": "MenuItem",
        "automation_id": "ConditionalFormattingGallery",
        "class_name": "NetUIRibbonButton",
        "bounds": [10, 20, 110, 60],
        "parent_path": [
            {
                "name": "Home",
                "control_type": "TabItem",
            }
        ],
    }
    assert provider.focused_context()["name"] == "Conditional Formatting"


class FakeControl:
    def __init__(
        self,
        name="",
        control_type="",
        automation_id="",
        class_name="",
        rect=None,
        parent=None,
    ):
        self.Name = name
        self.ControlTypeName = control_type
        self.AutomationId = automation_id
        self.ClassName = class_name
        self.BoundingRectangle = rect
        self._parent = parent

    def GetParentControl(self):
        return self._parent
