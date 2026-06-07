import sys
from contextlib import nullcontext
from typing import Any

from teach_skill.runtime_log import get_logger


logger = get_logger("recorder.ui_context")


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
            logger.info("uiautomation package unavailable")
            return
        self._automation = automation
        logger.info("uiautomation provider enabled")

    def context_at_point(self, x: int, y: int) -> dict[str, Any] | None:
        if self._automation is None:
            return None
        try:
            with self._thread_initializer():
                control = self._automation.ControlFromPoint(int(x), int(y))
                return self._context_from_control(control)
        except Exception as exc:
            logger.info("uiautomation point lookup failed error=%r", exc)
            return None

    def focused_context(self) -> dict[str, Any] | None:
        if self._automation is None:
            return None
        try:
            with self._thread_initializer():
                control = self._automation.GetFocusedControl()
                return self._context_from_control(control)
        except Exception as exc:
            logger.info("uiautomation focused lookup failed error=%r", exc)
            return None

    def _thread_initializer(self):
        initializer = getattr(
            self._automation,
            "UIAutomationInitializerInThread",
            None,
        )
        if initializer is None:
            return nullcontext()
        return initializer(debug=False)

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
