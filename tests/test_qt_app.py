import builtins
import json
import types

from click.testing import CliRunner

from teach_skill.cli import main


def test_launch_qt_check_only_runs_doctor_without_importing_qt(monkeypatch):
    calls = []
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "teach_skill.qt_app.app":
            raise AssertionError("Qt app should not be imported for --check-only")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    monkeypatch.setattr(
        "teach_skill.cli.run_doctor",
        lambda: calls.append("doctor") or type(
            "DoctorResult",
            (),
            {"status": "Ready", "can_record": True, "can_compile": True},
        )(),
    )
    monkeypatch.setattr(
        "teach_skill.cli.format_doctor_result",
        lambda result: [f"Setup status: {result.status}"],
    )

    result = CliRunner().invoke(main, ["launch", "--qt", "--check-only"])

    assert result.exit_code == 0
    assert "Setup status: Ready" in result.output
    assert calls == ["doctor"]


def test_launch_qt_invokes_qt_app(monkeypatch):
    launched = []
    fake_qt_app = types.ModuleType("teach_skill.qt_app.app")
    fake_qt_app.launch_qt_app = lambda: launched.append(True)
    monkeypatch.setattr(
        "teach_skill.cli.run_doctor",
        lambda: type(
            "DoctorResult",
            (),
            {"status": "Ready", "can_record": True, "can_compile": True},
        )(),
    )
    monkeypatch.setattr("teach_skill.cli.format_doctor_result", lambda result: [])
    monkeypatch.setitem(
        __import__("sys").modules,
        "teach_skill.qt_app.app",
        fake_qt_app,
    )

    result = CliRunner().invoke(main, ["launch", "--qt"])

    assert result.exit_code == 0
    assert launched == [True]


def test_qt_app_import_error_message_is_actionable(monkeypatch):
    import importlib
    import sys

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name.startswith("PySide6"):
            raise ModuleNotFoundError("No module named 'PySide6'")
        return original_import(name, *args, **kwargs)

    sys.modules.pop("teach_skill.qt_app.app", None)
    monkeypatch.setattr(builtins, "__import__", blocked_import)

    module = importlib.import_module("teach_skill.qt_app.app")

    try:
        module.launch_qt_app()
    except RuntimeError as exc:
        assert "Install the UI extra" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_launch_qt_app_reuses_existing_qapplication(monkeypatch):
    import importlib
    import sys

    sys.modules.pop("teach_skill.qt_app.app", None)
    module = importlib.import_module("teach_skill.qt_app.app")
    existing_app = types.SimpleNamespace(exec=lambda: 0)
    constructed = []
    shown = []

    class FakeApplication:
        @staticmethod
        def instance():
            return existing_app

        def __init__(self, argv):
            constructed.append(argv)

    class FakeWindow:
        def __init__(self, qt, services):
            pass

        def show(self):
            shown.append(True)

    monkeypatch.setattr(module, "_import_qt", lambda: {"QApplication": FakeApplication})
    monkeypatch.setattr(module, "QtAppServices", lambda: object())
    monkeypatch.setattr(module, "TeachSkillQtWindow", FakeWindow)

    assert module.launch_qt_app() == 0
    assert constructed == []
    assert shown == [True]


class _FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class _FakeWindow:
    def __init__(self):
        self.status_bar = _FakeStatusBar()

    def statusBar(self):
        return self.status_bar


class _FakeWidget:
    def __init__(self):
        self.text = None
        self.enabled = None
        self.cleared = False
        self.pixmap = None

    def setText(self, text):
        self.text = text

    def setPlainText(self, text):
        self.text = text

    def setEnabled(self, enabled):
        self.enabled = enabled

    def clear(self):
        self.cleared = True

    def setPixmap(self, pixmap):
        self.pixmap = pixmap


class _FakeList:
    def __init__(self, row):
        self.row = row

    def currentRow(self):
        return self.row


def _write_recording_with_frame(recording_dir):
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    (recording_dir / "recording.jsonl").write_text(
        json.dumps({"type": "window_switch", "screenshot": "frames/0001.png"}) + "\n",
        encoding="utf-8",
    )


def test_qt_window_blocks_compile_when_setup_is_not_ready():
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    window = object.__new__(module.TeachSkillQtWindow)
    compiled = []
    window.selected_recording = object()
    window.current_status = types.SimpleNamespace(can_compile=False, recording_active=False)
    window.services = types.SimpleNamespace(compile_recording=lambda recording: compiled.append(recording))
    window.window = _FakeWindow()

    window.compile_selected()

    assert compiled == []
    assert window.window.status_bar.messages == [
        "Compile is not ready. Check setup and recording state."
    ]


def test_qt_window_stop_recording_requests_stop_and_refreshes():
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    window = object.__new__(module.TeachSkillQtWindow)
    stopped = []
    refreshed = []
    window.services = types.SimpleNamespace(stop_recording=lambda: stopped.append(True) or True)
    window.refresh = lambda: refreshed.append(True)
    window.window = _FakeWindow()

    window.stop_recording()

    assert stopped == [True]
    assert refreshed == [True]
    assert window.window.status_bar.messages == ["Recording stop requested"]


def test_qt_window_clears_selection_when_review_load_fails(monkeypatch):
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    recording = types.SimpleNamespace(path="missing", name="recording")
    window = object.__new__(module.TeachSkillQtWindow)
    window.recordings = [recording]
    window.selected_recording = recording
    window.review = object()
    window.review_title = _FakeWidget()
    window.frame_preview = _FakeWidget()
    window.events_text = _FakeWidget()
    window.compile_button = _FakeWidget()
    window.exclude_first_frame_button = _FakeWidget()
    window.mark_sensitive_button = _FakeWidget()
    window.window = _FakeWindow()
    monkeypatch.setattr(module, "load_recording_review", lambda path: (_ for _ in ()).throw(OSError("gone")))

    window.select_recording(0)

    assert window.selected_recording is None
    assert window.review is None
    assert window.review_title.text == "Select a recording"
    assert window.frame_preview.text == "Review unavailable"
    assert window.events_text.text == ""
    assert window.compile_button.enabled is False
    assert window.window.status_bar.messages == ["Could not load recording: gone"]


def test_qt_window_excludes_first_frame(tmp_path):
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    recording_dir = tmp_path / "recording_20260602_120000"
    _write_recording_with_frame(recording_dir)
    recording = types.SimpleNamespace(path=recording_dir)
    selected_rows = []
    window = object.__new__(module.TeachSkillQtWindow)
    window.selected_recording = recording
    window.recordings_list = _FakeList(0)
    window.window = _FakeWindow()
    window.select_recording = lambda row: selected_rows.append(row)

    window.exclude_first_frame()

    review = module.load_recording_review(recording_dir)
    assert review.frames[0].included is False
    assert review.frames[0].sensitive is False
    assert window.window.status_bar.messages == ["First screenshot excluded from compile."]
    assert selected_rows == [0]


def test_qt_window_marks_first_frame_sensitive(tmp_path):
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    recording_dir = tmp_path / "recording_20260602_120000"
    _write_recording_with_frame(recording_dir)
    recording = types.SimpleNamespace(path=recording_dir)
    selected_rows = []
    window = object.__new__(module.TeachSkillQtWindow)
    window.selected_recording = recording
    window.recordings_list = _FakeList(0)
    window.window = _FakeWindow()
    window.select_recording = lambda row: selected_rows.append(row)

    window.mark_first_frame_sensitive()

    review = module.load_recording_review(recording_dir)
    assert review.frames[0].included is False
    assert review.frames[0].sensitive is True
    assert window.window.status_bar.messages == [
        "First screenshot marked sensitive and excluded."
    ]
    assert selected_rows == [0]


def test_qt_window_does_not_preview_sensitive_first_frame():
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    window = object.__new__(module.TeachSkillQtWindow)
    window.frame_preview = _FakeWidget()
    window.qt = {"QPixmap": lambda path: (_ for _ in ()).throw(AssertionError("QPixmap should not load"))}
    review = types.SimpleNamespace(
        frames=[
            types.SimpleNamespace(
                path="sensitive.png",
                sensitive=True,
            )
        ]
    )

    window._show_first_frame(review)

    assert window.frame_preview.text == "First screenshot marked sensitive"
    assert window.frame_preview.pixmap is None


def test_qt_window_review_action_handles_missing_recording(monkeypatch):
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    window = object.__new__(module.TeachSkillQtWindow)
    window.selected_recording = types.SimpleNamespace(path="missing")
    window.review = object()
    window.review_title = _FakeWidget()
    window.frame_preview = _FakeWidget()
    window.events_text = _FakeWidget()
    window.compile_button = _FakeWidget()
    window.exclude_first_frame_button = _FakeWidget()
    window.mark_sensitive_button = _FakeWidget()
    window.window = _FakeWindow()
    monkeypatch.setattr(module, "load_recording_review", lambda path: (_ for _ in ()).throw(OSError("gone")))

    window.exclude_first_frame()

    assert window.selected_recording is None
    assert window.review is None
    assert window.frame_preview.text == "Review unavailable"
    assert window.exclude_first_frame_button.enabled is False
    assert window.window.status_bar.messages == ["Could not load recording: gone"]
