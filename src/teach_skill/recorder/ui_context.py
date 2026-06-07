import sys
from typing import Any


class UIContextProvider:
    def __init__(self, enabled: bool = True, max_parent_depth: int = 4):
        self.enabled = enabled and sys.platform == "win32"
        self.max_parent_depth = max_parent_depth
        self._automation = None
        if not self.enabled:
            return
        try:
            import uiautomation as automation
        except Exception:
            return
        self._automation = automation

    def context_at_point(self, x: int, y: int) -> dict[str, Any] | None:
        if self._automation is None:
            return None
        try:
            control = self._automation.ControlFromPoint(int(x), int(y))
        except Exception:
            return None
        return self._context_from_control(control)

    def focused_context(self) -> dict[str, Any] | None:
        if self._automation is None:
            return None
        try:
            control = self._automation.GetFocusedControl()
        except Exception:
            return None
        return self._context_from_control(control)

    def _context_from_control(self, control: Any) -> dict[str, Any] | None:
        if control is None:
            return None

        context = _control_summary(control)
        parent_path = []
        current = control
        for _ in range(self.max_parent_depth):
            try:
                current = current.GetParentControl()
            except Exception:
                break
            if current is None:
                break
            parent = _control_summary(current)
            if parent:
                parent_path.append(parent)

        if parent_path:
            context["parent_path"] = parent_path
        return context or None


def _control_summary(control: Any) -> dict[str, Any]:
    summary = {}
    for output_key, attr_name in (
        ("name", "Name"),
        ("control_type", "ControlTypeName"),
        ("automation_id", "AutomationId"),
        ("class_name", "ClassName"),
    ):
        value = _read_attr(control, attr_name)
        if value:
            summary[output_key] = str(value)

    rect = _read_attr(control, "BoundingRectangle")
    bounds = _rect_to_list(rect)
    if bounds:
        summary["bounds"] = bounds
    return summary


def _read_attr(control: Any, attr_name: str) -> Any:
    try:
        value = getattr(control, attr_name)
    except Exception:
        return None
    if callable(value):
        try:
            value = value()
        except Exception:
            return None
    return value


def _rect_to_list(rect: Any) -> list[int] | None:
    if rect is None:
        return None
    try:
        return [
            int(rect.left),
            int(rect.top),
            int(rect.right),
            int(rect.bottom),
        ]
    except Exception:
        return None
