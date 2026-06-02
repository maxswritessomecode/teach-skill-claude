# PySide6 Record Review Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first PySide6/Qt Record And Review shell slice while keeping existing CLI, recorder, compiler, logging, and diagnostics flows working.

**Architecture:** Add shell-neutral review and service modules first, then put a thin PySide6 UI on top. The Qt app launches through the existing `teach-skill launch` command behind an explicit `--qt` flag for the spike, while the existing Tkinter launcher remains available. Packaging fixes are included because the shell choice is not viable until a clean Windows bundle can be tested.

**Tech Stack:** Python 3.10+, Click, PySide6, pytest, PyInstaller, Inno Setup.

**Repository rule:** Do not commit during execution unless the user explicitly asks. The checkpoint steps below use `git status` only.

---

## File Structure

- Create `src/teach_skill/review.py`: review data model, JSONL parsing, review persistence, include/exclude filtering.
- Create `tests/test_review.py`: unit tests for review model behavior.
- Create `src/teach_skill/qt_app/__init__.py`: Qt app package marker.
- Create `src/teach_skill/qt_app/services.py`: shell-neutral setup, recordings, recorder, compile, logs, and support-bundle service helpers.
- Create `tests/test_qt_services.py`: tests for service helpers without importing PySide6.
- Create `src/teach_skill/qt_app/app.py`: PySide6 app shell and widgets.
- Create `tests/test_qt_app.py`: import-guard and launch-factory tests using fake PySide6 modules where needed.
- Modify `src/teach_skill/cli.py`: add `teach-skill launch --qt` and `--check-only` behavior for the Qt spike.
- Modify `setup.py`: add `ui` extra with `PySide6`.
- Modify `packaging/windows/TeachSkillClaude.spec`: use `src` import path and account for PySide6 packaging.
- Modify `packaging/windows/build-full-installer.ps1`: delete only known generated outputs.
- Modify `tests/test_packaging_windows.py`: assert packaging fixes.
- Modify `packaging/windows/README.md`: document `teach-skill launch --qt` as the modern shell spike.

---

## Task 1: Add Review Model

**Files:**
- Create: `src/teach_skill/review.py`
- Create: `tests/test_review.py`

- [ ] **Step 1: Write failing tests for loading review state**

Create `tests/test_review.py`:

```python
import json
from pathlib import Path

from teach_skill.review import (
    CompileSelection,
    load_recording_review,
)


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )


def test_load_recording_review_lists_events_and_frames(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    jsonl_path = recording_dir / "recording.jsonl"
    write_jsonl(
        jsonl_path,
        [
            {"type": "recording_meta", "machine": "PC"},
            {"type": "window_switch", "title": "Excel", "screenshot": "frames/0001.png"},
            {"type": "click", "title": "Excel", "screenshot_frame_path": "frames/0001.png"},
        ],
    )

    review = load_recording_review(recording_dir)

    assert review.recording_dir == recording_dir
    assert len(review.events) == 3
    assert review.frames[0].relative_path == "frames/0001.png"
    assert review.events[1].included is True
    assert review.frames[0].included is True


def test_review_state_persists_event_and_frame_exclusions(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
        ],
    )

    review = load_recording_review(recording_dir)
    review.events[1].included = False
    review.frames[0].included = False
    review.save()

    reloaded = load_recording_review(recording_dir)

    assert reloaded.events[1].included is False
    assert reloaded.frames[0].included is False


def test_compile_selection_excludes_events_and_frames(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    (frames_dir / "0002.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
            {"type": "window_switch", "screenshot": "frames/0002.png"},
        ],
    )

    review = load_recording_review(recording_dir)
    review.events[2].included = False
    review.frames[1].included = False

    selection = CompileSelection.from_review(review)

    assert [event["type"] for event in selection.events] == ["recording_meta", "window_switch"]
    assert selection.frame_paths == [recording_dir / "frames" / "0001.png"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_review.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'teach_skill.review'`.

- [ ] **Step 3: Implement review model**

Create `src/teach_skill/review.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REVIEW_FILE = "review.json"


@dataclass
class ReviewEvent:
    index: int
    data: dict[str, Any]
    included: bool = True


@dataclass
class ReviewFrame:
    relative_path: str
    path: Path
    included: bool = True
    sensitive: bool = False


@dataclass
class RecordingReview:
    recording_dir: Path
    jsonl_path: Path
    events: list[ReviewEvent]
    frames: list[ReviewFrame]

    @property
    def review_path(self) -> Path:
        return self.recording_dir / REVIEW_FILE

    def save(self) -> None:
        payload = {
            "excluded_events": [
                event.index for event in self.events if not event.included
            ],
            "frames": {
                frame.relative_path: {
                    "included": frame.included,
                    "sensitive": frame.sensitive,
                }
                for frame in self.frames
            },
        }
        self.review_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


@dataclass(frozen=True)
class CompileSelection:
    events: list[dict[str, Any]]
    frame_paths: list[Path]

    @classmethod
    def from_review(cls, review: RecordingReview) -> "CompileSelection":
        included_frame_paths = {
            frame.relative_path for frame in review.frames if frame.included
        }
        events = []
        for event in review.events:
            if not event.included:
                continue
            event_frame = _event_frame_path(event.data)
            if event_frame and event_frame not in included_frame_paths:
                continue
            events.append(event.data)

        frame_paths = [
            frame.path for frame in review.frames if frame.included and frame.path.is_file()
        ]
        return cls(events=events, frame_paths=frame_paths)


def load_recording_review(recording_dir: Path) -> RecordingReview:
    jsonl_path = recording_dir / "recording.jsonl"
    events = _load_events(jsonl_path)
    frames = _discover_frames(recording_dir, events)
    review = RecordingReview(
        recording_dir=recording_dir,
        jsonl_path=jsonl_path,
        events=[ReviewEvent(index=index, data=event) for index, event in enumerate(events)],
        frames=frames,
    )
    _apply_saved_review(review)
    return review


def _load_events(jsonl_path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _discover_frames(recording_dir: Path, events: list[dict[str, Any]]) -> list[ReviewFrame]:
    paths: list[str] = []
    seen: set[str] = set()
    for event in events:
        relative_path = _event_frame_path(event)
        if relative_path and relative_path not in seen:
            seen.add(relative_path)
            paths.append(relative_path)

    return [
        ReviewFrame(
            relative_path=relative_path,
            path=recording_dir / relative_path,
        )
        for relative_path in paths
    ]


def _event_frame_path(event: dict[str, Any]) -> str | None:
    value = event.get("screenshot_frame_path") or event.get("screenshot")
    if not isinstance(value, str):
        return None
    if value.startswith("suppressed:"):
        return None
    return value.replace("\\", "/")


def _apply_saved_review(review: RecordingReview) -> None:
    if not review.review_path.is_file():
        return

    payload = json.loads(review.review_path.read_text(encoding="utf-8"))
    excluded_events = set(payload.get("excluded_events", []))
    frame_state = payload.get("frames", {})

    for event in review.events:
        event.included = event.index not in excluded_events

    for frame in review.frames:
        state = frame_state.get(frame.relative_path, {})
        frame.included = bool(state.get("included", True))
        frame.sensitive = bool(state.get("sensitive", False))
```

- [ ] **Step 4: Run review tests**

Run: `pytest tests/test_review.py -q`

Expected: PASS.

- [ ] **Step 5: Checkpoint status**

Run: `git status --short`

Expected: new `src/teach_skill/review.py` and `tests/test_review.py`.

---

## Task 2: Add Shell-Neutral Qt Services

**Files:**
- Create: `src/teach_skill/qt_app/__init__.py`
- Create: `src/teach_skill/qt_app/services.py`
- Create: `tests/test_qt_services.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_qt_services.py`:

```python
import types
from pathlib import Path
from unittest.mock import patch

from teach_skill.qt_app.services import (
    AppStatus,
    QtAppServices,
    build_app_status,
)


def test_build_app_status_maps_doctor_and_recording_state():
    doctor = types.SimpleNamespace(status="Ready", can_record=True, can_compile=False)

    status = build_app_status(doctor, recording_active=True)

    assert status == AppStatus(
        setup_status="Ready",
        can_record=True,
        can_compile=False,
        recording_active=True,
        state_label="Recording",
    )


def test_services_load_recent_recordings(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")

    services = QtAppServices(recordings_root=tmp_path)

    recordings = services.recent_recordings(limit=3)

    assert recordings[0].name == "recording_20260602_120000"


def test_services_start_recorder_delegates_to_launcher_runner(tmp_path):
    starts = []
    services = QtAppServices(recordings_root=tmp_path)
    services.recorder_runner = types.SimpleNamespace(
        start=lambda callback: starts.append(callback()) or True
    )

    with patch("teach_skill.qt_app.services._run_cli_command", lambda *args: args):
        started = services.start_recording()

    assert started is True
    assert starts == [("record",)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_qt_services.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'teach_skill.qt_app'`.

- [ ] **Step 3: Implement service package**

Create `src/teach_skill/qt_app/__init__.py`:

```python
"""PySide6 application shell for Teach Skill Claude."""
```

Create `src/teach_skill/qt_app/services.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from teach_skill.config import load_config
from teach_skill.diagnostics import create_support_bundle
from teach_skill.doctor import run_doctor
from teach_skill.launcher import SingleProcessRunner, _open_folder, _run_cli_command
from teach_skill.launcher_state import RecordingSummary, list_recordings
from teach_skill.recorder.lock import is_recording_active
from teach_skill.runtime_log import log_path


@dataclass(frozen=True)
class AppStatus:
    setup_status: str
    can_record: bool
    can_compile: bool
    recording_active: bool
    state_label: str


def build_app_status(doctor_result, recording_active: bool) -> AppStatus:
    if recording_active:
        state_label = "Recording"
    elif doctor_result.can_record:
        state_label = "Can record"
    else:
        state_label = "Needs setup"

    return AppStatus(
        setup_status=doctor_result.status,
        can_record=doctor_result.can_record,
        can_compile=doctor_result.can_compile,
        recording_active=recording_active,
        state_label=state_label,
    )


class QtAppServices:
    def __init__(self, recordings_root: Path | None = None) -> None:
        self.config = load_config()
        self.recordings_root = recordings_root or Path(self.config["storage_path"])
        self.recorder_runner = SingleProcessRunner()

    def status(self) -> AppStatus:
        doctor_result = run_doctor(config=self.config)
        active = is_recording_active(self.recordings_root)
        return build_app_status(doctor_result, active)

    def recent_recordings(self, limit: int = 10) -> list[RecordingSummary]:
        return list_recordings(self.recordings_root, limit=limit)

    def start_recording(self) -> bool:
        return self.recorder_runner.start(lambda: _run_cli_command("record"))

    def compile_recording(self, recording: RecordingSummary) -> None:
        _run_cli_command("compile", str(recording.jsonl_path), new_console=True)

    def open_recordings_folder(self) -> None:
        self.recordings_root.mkdir(parents=True, exist_ok=True)
        _open_folder(self.recordings_root)

    def open_logs_folder(self) -> None:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _open_folder(path.parent)

    def create_support_bundle(self) -> Path:
        return create_support_bundle()
```

- [ ] **Step 4: Run service tests**

Run: `pytest tests/test_qt_services.py -q`

Expected: PASS.

- [ ] **Step 5: Checkpoint status**

Run: `git status --short`

Expected: new `src/teach_skill/qt_app/` files and `tests/test_qt_services.py`.

---

## Task 3: Add Qt Launch Entry Point

**Files:**
- Modify: `src/teach_skill/cli.py`
- Modify: `setup.py`
- Create: `tests/test_qt_app.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_qt_app.py`:

```python
from click.testing import CliRunner

from teach_skill.cli import main


def test_launch_qt_check_only_runs_doctor_without_importing_qt(monkeypatch):
    calls = []

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
        type("FakeQtAppModule", (), {"launch_qt_app": lambda: launched.append(True)})(),
    )

    result = CliRunner().invoke(main, ["launch", "--qt"])

    assert result.exit_code == 0
    assert launched == [True]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_qt_app.py -q`

Expected: FAIL because `--qt` does not exist.

- [ ] **Step 3: Add `--qt` launch flag**

Modify the `launch` command in `src/teach_skill/cli.py`:

```python
@main.command()
@click.option("--check-only", is_flag=True, help="Run setup checks without opening the launcher window.")
@click.option("--qt", "use_qt", is_flag=True, help="Open the PySide6 Record And Review shell.")
def launch(check_only: bool, use_qt: bool):
    """Open the guided Teach Skill Claude launcher."""
    logger = get_logger("cli")
    result = run_doctor()
    logger.info("launch requested check_only=%s qt=%s status=%s", check_only, use_qt, result.status)
    for line in format_doctor_result(result):
        click.echo(line)

    if check_only:
        return

    if use_qt:
        from teach_skill.qt_app.app import launch_qt_app

        launch_qt_app()
        return

    from teach_skill.launcher import launch_app

    launch_app()
```

- [ ] **Step 4: Add UI extra**

Modify `setup.py` so `extras_require` includes `ui`:

```python
    extras_require={
        "recorder": [
            "pywin32",
            "pynput",
            "Pillow",
            "pystray",
            "psutil",
        ],
        "ui": [
            "PySide6",
        ],
        "dev": [
            "pytest",
        ],
    },
```

- [ ] **Step 5: Run CLI tests**

Run: `pytest tests/test_qt_app.py -q`

Expected: PASS.

- [ ] **Step 6: Run existing launcher tests**

Run: `pytest tests/test_launcher.py -q`

Expected: PASS.

---

## Task 4: Build Minimal PySide6 Shell

**Files:**
- Create: `src/teach_skill/qt_app/app.py`
- Modify: `tests/test_qt_app.py`

- [ ] **Step 1: Add import-guard test**

Append to `tests/test_qt_app.py`:

```python
def test_qt_app_import_error_message_is_actionable(monkeypatch):
    import builtins
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_qt_app.py::test_qt_app_import_error_message_is_actionable -q`

Expected: FAIL because `teach_skill.qt_app.app` does not exist.

- [ ] **Step 3: Implement Qt shell**

Create `src/teach_skill/qt_app/app.py`:

```python
from __future__ import annotations

import sys

from teach_skill.qt_app.services import QtAppServices
from teach_skill.review import load_recording_review


def _import_qt():
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QPushButton,
            QSplitter,
            QStatusBar,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PySide6 is not installed. Install the UI extra with: pip install -e .[ui,recorder]"
        ) from exc

    return {
        "Qt": Qt,
        "QPixmap": QPixmap,
        "QApplication": QApplication,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QListWidget": QListWidget,
        "QListWidgetItem": QListWidgetItem,
        "QMainWindow": QMainWindow,
        "QPushButton": QPushButton,
        "QSplitter": QSplitter,
        "QStatusBar": QStatusBar,
        "QTextEdit": QTextEdit,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
    }


def launch_qt_app() -> None:
    qt = _import_qt()
    app = qt["QApplication"](sys.argv)
    window = TeachSkillQtWindow(qt, QtAppServices())
    window.show()
    app.exec()


class TeachSkillQtWindow:
    def __init__(self, qt, services: QtAppServices) -> None:
        self.qt = qt
        self.services = services
        self.recordings = []
        self.selected_recording = None

        QMainWindow = qt["QMainWindow"]
        self.window = QMainWindow()
        self.window.setWindowTitle("Teach Skill Claude")
        self.window.resize(1040, 680)
        self._build_ui()
        self.refresh()

    def __getattr__(self, name):
        return getattr(self.window, name)

    def _build_ui(self) -> None:
        qt = self.qt
        root = qt["QWidget"]()
        layout = qt["QHBoxLayout"](root)
        splitter = qt["QSplitter"]()
        splitter.setOrientation(qt["Qt"].Horizontal)

        sidebar = qt["QWidget"]()
        sidebar_layout = qt["QVBoxLayout"](sidebar)
        self.status_label = qt["QLabel"]("Checking setup...")
        self.record_button = qt["QPushButton"]("Start Recording")
        self.refresh_button = qt["QPushButton"]("Refresh")
        self.recordings_list = qt["QListWidget"]()
        sidebar_layout.addWidget(self.status_label)
        sidebar_layout.addWidget(self.record_button)
        sidebar_layout.addWidget(self.refresh_button)
        sidebar_layout.addWidget(qt["QLabel"]("Recent recordings"))
        sidebar_layout.addWidget(self.recordings_list)

        review = qt["QWidget"]()
        review_layout = qt["QVBoxLayout"](review)
        self.review_title = qt["QLabel"]("Select a recording to review")
        self.frame_preview = qt["QLabel"]("No screenshot selected")
        self.frame_preview.setMinimumHeight(320)
        self.frame_preview.setAlignment(qt["Qt"].AlignCenter)
        self.events_text = qt["QTextEdit"]()
        self.events_text.setReadOnly(True)
        self.compile_button = qt["QPushButton"]("Send to Agent SDK")
        review_layout.addWidget(self.review_title)
        review_layout.addWidget(self.frame_preview)
        review_layout.addWidget(self.events_text)
        review_layout.addWidget(self.compile_button)

        splitter.addWidget(sidebar)
        splitter.addWidget(review)
        layout.addWidget(splitter)
        self.window.setCentralWidget(root)
        self.window.setStatusBar(qt["QStatusBar"]())

        self.record_button.clicked.connect(self.start_recording)
        self.refresh_button.clicked.connect(self.refresh)
        self.recordings_list.currentRowChanged.connect(self.select_recording)
        self.compile_button.clicked.connect(self.compile_selected)

    def refresh(self) -> None:
        status = self.services.status()
        self.status_label.setText(f"{status.state_label} - setup: {status.setup_status}")
        self.record_button.setEnabled(status.can_record and not status.recording_active)
        self.compile_button.setEnabled(False)
        self.recordings = self.services.recent_recordings()
        self.recordings_list.clear()
        for recording in self.recordings:
            self.recordings_list.addItem(f"{recording.name} ({recording.frame_count} screenshots)")

    def start_recording(self) -> None:
        started = self.services.start_recording()
        message = "Recording started. Stop from the tray, then refresh." if started else "Recording is already active."
        self.window.statusBar().showMessage(message)
        self.refresh()

    def select_recording(self, index: int) -> None:
        if index < 0 or index >= len(self.recordings):
            return
        self.selected_recording = self.recordings[index]
        review = load_recording_review(self.selected_recording.path)
        self.review_title.setText(f"Review: {self.selected_recording.name}")
        self.events_text.setPlainText(
            "\n".join(
                f"{event.index}: {event.data.get('type', 'unknown')} - {event.data.get('title', '')}"
                for event in review.events
            )
        )
        if review.frames:
            pixmap = self.qt["QPixmap"](str(review.frames[0].path))
            self.frame_preview.setPixmap(
                pixmap.scaled(
                    self.frame_preview.width(),
                    self.frame_preview.height(),
                    self.qt["Qt"].KeepAspectRatio,
                )
            )
        else:
            self.frame_preview.setText("No screenshot frames found")
        self.compile_button.setEnabled(True)

    def compile_selected(self) -> None:
        if self.selected_recording is None:
            return
        self.services.compile_recording(self.selected_recording)
        self.window.statusBar().showMessage("Compiling. Follow the Agent SDK prompt/output.")
```

- [ ] **Step 4: Run import-guard tests**

Run: `pytest tests/test_qt_app.py -q`

Expected: PASS.

- [ ] **Step 5: Manual Qt smoke on a machine with PySide6**

Run: `teach-skill launch --qt --check-only`

Expected: doctor output prints and no GUI opens.

Run: `teach-skill launch --qt`

Expected: Qt window opens with setup state and recent recordings.

---

## Task 5: Add Review Exclusion Controls

**Files:**
- Modify: `src/teach_skill/qt_app/app.py`
- Modify: `tests/test_review.py`

- [ ] **Step 1: Add review filtering persistence test**

Append to `tests/test_review.py`:

```python
def test_mark_frame_sensitive_persists(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [{"type": "window_switch", "screenshot": "frames/0001.png"}],
    )

    review = load_recording_review(recording_dir)
    review.frames[0].sensitive = True
    review.frames[0].included = False
    review.save()

    reloaded = load_recording_review(recording_dir)

    assert reloaded.frames[0].sensitive is True
    assert reloaded.frames[0].included is False
```

- [ ] **Step 2: Run review tests**

Run: `pytest tests/test_review.py -q`

Expected: PASS because the model already persists frame sensitivity.

- [ ] **Step 3: Add UI controls in Qt shell**

Modify `src/teach_skill/qt_app/app.py`:

```python
# Add these widgets in _build_ui after self.events_text:
self.exclude_first_frame_button = qt["QPushButton"]("Exclude first screenshot")
self.mark_sensitive_button = qt["QPushButton"]("Mark first screenshot sensitive")
review_layout.addWidget(self.exclude_first_frame_button)
review_layout.addWidget(self.mark_sensitive_button)

# Add these signal connections:
self.exclude_first_frame_button.clicked.connect(self.exclude_first_frame)
self.mark_sensitive_button.clicked.connect(self.mark_first_frame_sensitive)
```

Add methods to `TeachSkillQtWindow`:

```python
    def _selected_review(self):
        if self.selected_recording is None:
            return None
        return load_recording_review(self.selected_recording.path)

    def exclude_first_frame(self) -> None:
        review = self._selected_review()
        if review is None or not review.frames:
            return
        review.frames[0].included = False
        review.save()
        self.window.statusBar().showMessage("First screenshot excluded from compile.")
        self.select_recording(self.recordings_list.currentRow())

    def mark_first_frame_sensitive(self) -> None:
        review = self._selected_review()
        if review is None or not review.frames:
            return
        review.frames[0].sensitive = True
        review.frames[0].included = False
        review.save()
        self.window.statusBar().showMessage("First screenshot marked sensitive and excluded.")
        self.select_recording(self.recordings_list.currentRow())
```

- [ ] **Step 4: Run review and Qt tests**

Run: `pytest tests/test_review.py tests/test_qt_app.py -q`

Expected: PASS.

---

## Task 6: Wire Compile Selection To Compiler Boundary

**Files:**
- Modify: `src/teach_skill/review.py`
- Modify: `src/teach_skill/qt_app/services.py`
- Modify: `tests/test_review.py`
- Modify: `tests/test_qt_services.py`

- [ ] **Step 1: Add reviewed JSONL export test**

Append to `tests/test_review.py`:

```python
def test_compile_selection_writes_filtered_jsonl(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
            {"type": "clipboard_text", "content": "secret"},
        ],
    )
    review = load_recording_review(recording_dir)
    review.events[2].included = False
    selection = CompileSelection.from_review(review)

    filtered_path = selection.write_filtered_jsonl(recording_dir / "reviewed-recording.jsonl")

    assert filtered_path.read_text(encoding="utf-8").count("\n") == 2
    assert "secret" not in filtered_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_review.py::test_compile_selection_writes_filtered_jsonl -q`

Expected: FAIL because `write_filtered_jsonl` does not exist.

- [ ] **Step 3: Implement filtered JSONL writer**

Add method to `CompileSelection` in `src/teach_skill/review.py`:

```python
    def write_filtered_jsonl(self, destination: Path) -> Path:
        destination.write_text(
            "".join(json.dumps(event) + "\n" for event in self.events),
            encoding="utf-8",
        )
        return destination
```

- [ ] **Step 4: Update compile service to use review state**

Modify `compile_recording` in `src/teach_skill/qt_app/services.py`:

```python
    def compile_recording(self, recording: RecordingSummary) -> None:
        from teach_skill.review import CompileSelection, load_recording_review

        review = load_recording_review(recording.path)
        filtered_path = CompileSelection.from_review(review).write_filtered_jsonl(
            recording.path / "reviewed-recording.jsonl"
        )
        _run_cli_command("compile", str(filtered_path), new_console=True)
```

- [ ] **Step 5: Add service test for reviewed compile path**

Append to `tests/test_qt_services.py`:

```python
def test_compile_recording_uses_reviewed_jsonl(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (recording_dir / "recording.jsonl").write_text(
        '{"type": "recording_meta"}\n{"type": "clipboard_text", "content": "secret"}\n',
        encoding="utf-8",
    )
    recording = type(
        "Recording",
        (),
        {
            "name": recording_dir.name,
            "path": recording_dir,
            "jsonl_path": recording_dir / "recording.jsonl",
            "frame_count": 0,
            "modified_at": 1,
        },
    )()
    commands = []
    monkeypatch.setattr(
        "teach_skill.qt_app.services._run_cli_command",
        lambda *args, **kwargs: commands.append((args, kwargs)),
    )

    QtAppServices(recordings_root=tmp_path).compile_recording(recording)

    assert commands[0][0][0] == "compile"
    assert commands[0][0][1].endswith("reviewed-recording.jsonl")
```

- [ ] **Step 6: Run review and service tests**

Run: `pytest tests/test_review.py tests/test_qt_services.py -q`

Expected: PASS.

---

## Task 7: Fix Packaging Spike Risks

**Files:**
- Modify: `packaging/windows/TeachSkillClaude.spec`
- Modify: `packaging/windows/build-full-installer.ps1`
- Modify: `tests/test_packaging_windows.py`
- Modify: `packaging/windows/README.md`

- [ ] **Step 1: Add packaging assertions**

Modify `tests/test_packaging_windows.py`:

```python
def test_pyinstaller_spec_uses_src_import_path():
    text = (ROOT / "packaging" / "windows" / "TeachSkillClaude.spec").read_text()

    assert 'pathex=["src"]' in text


def test_full_installer_build_script_deletes_only_known_outputs():
    text = (ROOT / "packaging" / "windows" / "build-full-installer.ps1").read_text()

    assert 'Remove-Item "$projectDir\\dist"' not in text
    assert "TeachSkillClaude" in text
    assert "TeachSkillClaudeSetup.exe" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_packaging_windows.py -q`

Expected: FAIL because the current spec uses `pathex=["."]` and the build script deletes the whole `dist`.

- [ ] **Step 3: Fix PyInstaller import path**

In `packaging/windows/TeachSkillClaude.spec`, change:

```python
pathex=["."],
```

to:

```python
pathex=["src"],
```

- [ ] **Step 4: Narrow build cleanup**

In `packaging/windows/build-full-installer.ps1`, replace broad `dist` deletion with known outputs:

```powershell
$knownOutputs = @(
    "$projectDir\dist\TeachSkillClaude",
    "$projectDir\dist\installer\TeachSkillClaudeSetup.exe",
    "$projectDir\build\TeachSkillClaude"
)

foreach ($output in $knownOutputs) {
    if (Test-Path $output) {
        Remove-Item $output -Recurse -Force
    }
}
```

- [ ] **Step 5: Document Qt spike install**

Add to `packaging/windows/README.md`:

```markdown
## Modern Qt Shell Spike

During the PySide6 spike, run the modern shell from a Git checkout with:

```powershell
.\install.bat
.\.venv\Scripts\teach-skill.exe launch --qt
```

The classic launcher remains available with:

```powershell
.\.venv\Scripts\teach-skill.exe launch
```

The full installer should not be treated as release-ready until the PySide6
bundle has been smoke-tested on Windows 10 and Windows 11.
```
```

- [ ] **Step 6: Run packaging tests**

Run: `pytest tests/test_packaging_windows.py -q`

Expected: PASS.

---

## Task 8: Full Local Verification

**Files:**
- No expected source edits.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest tests/test_review.py tests/test_qt_services.py tests/test_qt_app.py tests/test_packaging_windows.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Check whitespace**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Inspect workspace**

Run:

```bash
git status --short
```

Expected: only intended files are modified or untracked. `.superpowers/` may still appear from the visual companion and should not be staged unless the user asks to preserve it.

---

## Task 9: Windows Manual Smoke Test

**Files:**
- No expected source edits.

- [ ] **Step 1: Pull branch on Windows**

Run:

```powershell
git pull
```

Expected: branch updates successfully.

- [ ] **Step 2: Install checkout**

Run:

```powershell
.\install.bat
```

Expected: Python environment installs and launcher shortcut is created.

- [ ] **Step 3: Install UI extra if needed**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,recorder]"
```

Expected: PySide6 installs successfully.

- [ ] **Step 4: Launch Qt check-only**

Run:

```powershell
.\.venv\Scripts\teach-skill.exe launch --qt --check-only
```

Expected: setup checks print without opening a GUI.

- [ ] **Step 5: Launch Qt shell**

Run:

```powershell
.\.venv\Scripts\teach-skill.exe launch --qt
```

Expected: Qt shell opens, shows setup state, and lists recent recordings.

- [ ] **Step 6: Record and review**

Use the Qt shell to start recording. Stop recording from the tray. Refresh the Qt shell.

Expected: new recording appears, screenshot/event preview loads, and review actions can save `review.json`.

- [ ] **Step 7: Compile reviewed recording**

Click `Send to Agent SDK`.

Expected: compile command starts using `reviewed-recording.jsonl`. If Agent SDK is missing, the failure is visible and logs capture the issue.

---

## Self-Review

- Spec coverage: shell choice, review model, app states, tray ownership, compile boundary, packaging spike, and testing are covered.
- Red-flag scan: no unresolved markers or unspecified implementation steps should remain.
- Type consistency: `RecordingReview`, `ReviewEvent`, `ReviewFrame`, `CompileSelection`, `AppStatus`, and `QtAppServices` names are introduced before use.
- Scope control: voice narration, skill chains, full redaction drawing, and full in-app generated-skill editing are intentionally deferred.
