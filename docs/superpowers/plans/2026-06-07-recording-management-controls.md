# Recording Management Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe rename, delete, pause, and resume controls to the PySide6 recording shell.

**Architecture:** Store friendly recording names in per-recording metadata while leaving folder names stable. Use root-level recorder control files for pause/resume, matching the existing stop-request pattern. Keep destructive operations in `QtAppServices` so the GUI remains a thin caller and tests can cover behavior without PySide6.

**Tech Stack:** Python, PySide6, pytest, existing recorder controller/tray/lock patterns.

---

## File Structure

- Create `src/teach_skill/recording_metadata.py`
  - Owns `recording-info.json` read/write and display-name validation.
- Modify `src/teach_skill/launcher_state.py`
  - Add `display_name` to `RecordingSummary`; list uses metadata when present.
- Modify `src/teach_skill/recorder/control.py`
  - Add pause/resume request files and paused-state helpers.
- Modify `src/teach_skill/recorder/controller.py`
  - Add pause/resume state and ignore all capture callbacks while paused.
- Modify `src/teach_skill/recorder/tray.py`
  - Poll pause/resume controls and apply them to the controller.
- Modify `src/teach_skill/qt_app/services.py`
  - Add rename/delete/pause/resume service methods.
- Modify `src/teach_skill/qt_app/app.py`
  - Add Pause, Resume, Rename, and Delete buttons.
- Test with:
  - `tests/test_recording_metadata.py`
  - `tests/test_launcher_state.py`
  - `tests/test_recorder_control.py`
  - `tests/test_recorder_controller.py`
  - `tests/test_tray.py`
  - `tests/test_qt_services.py`
  - `tests/test_qt_app.py`

## Task 1: Friendly Recording Metadata

**Files:**
- Create: `src/teach_skill/recording_metadata.py`
- Modify: `src/teach_skill/launcher_state.py`
- Test: `tests/test_recording_metadata.py`
- Test: `tests/test_launcher_state.py`

- [ ] **Step 1: Write failing metadata tests**

Add `tests/test_recording_metadata.py`:

```python
from teach_skill.recording_metadata import (
    RecordingInfo,
    load_recording_info,
    save_recording_title,
)


def test_save_and_load_recording_title(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    info = save_recording_title(recording_dir, "Excel pricing cleanup")

    assert info == RecordingInfo(title="Excel pricing cleanup")
    assert load_recording_info(recording_dir).title == "Excel pricing cleanup"


def test_load_recording_info_ignores_missing_or_malformed_file(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    assert load_recording_info(recording_dir).title is None

    (recording_dir / "recording-info.json").write_text("{bad json", encoding="utf-8")

    assert load_recording_info(recording_dir).title is None


def test_save_recording_title_rejects_empty_or_multiline_titles(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    for title in ["", "   ", "first\nsecond"]:
        try:
            save_recording_title(recording_dir, title)
        except ValueError as exc:
            assert "Recording title" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
```

Extend `tests/test_launcher_state.py`:

```python
def test_list_recordings_uses_friendly_display_name(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    (recording_dir / "recording-info.json").write_text(
        '{"title": "Excel pricing cleanup"}\n',
        encoding="utf-8",
    )

    recordings = list_recordings(tmp_path)

    assert recordings[0].name == "recording_20260607_120000"
    assert recordings[0].display_name == "Excel pricing cleanup"
```

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
.venv/bin/python -m pytest tests/test_recording_metadata.py tests/test_launcher_state.py -q
```

Expected: fail because `teach_skill.recording_metadata` and `display_name` do not exist.

- [ ] **Step 3: Implement metadata module and summary field**

Create `src/teach_skill/recording_metadata.py`:

```python
from dataclasses import dataclass
import json
from pathlib import Path


INFO_FILE = "recording-info.json"
MAX_TITLE_LENGTH = 120


@dataclass(frozen=True)
class RecordingInfo:
    title: str | None = None


def info_path(recording_dir: Path) -> Path:
    return Path(recording_dir) / INFO_FILE


def normalize_recording_title(title: str) -> str:
    normalized = " ".join(title.strip().split())
    if not normalized:
        raise ValueError("Recording title cannot be empty.")
    if len(normalized) > MAX_TITLE_LENGTH:
        raise ValueError(f"Recording title cannot exceed {MAX_TITLE_LENGTH} characters.")
    return normalized


def load_recording_info(recording_dir: Path) -> RecordingInfo:
    path = info_path(recording_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return RecordingInfo()
    if not isinstance(payload, dict):
        return RecordingInfo()
    title = payload.get("title")
    if not isinstance(title, str):
        return RecordingInfo()
    try:
        return RecordingInfo(title=normalize_recording_title(title))
    except ValueError:
        return RecordingInfo()


def save_recording_title(recording_dir: Path, title: str) -> RecordingInfo:
    info = RecordingInfo(title=normalize_recording_title(title))
    path = info_path(recording_dir)
    path.write_text(json.dumps({"title": info.title}, indent=2) + "\n", encoding="utf-8")
    return info
```

Modify `RecordingSummary` in `src/teach_skill/launcher_state.py`:

```python
@dataclass(frozen=True)
class RecordingSummary:
    name: str
    display_name: str
    path: Path
    jsonl_path: Path
    frame_count: int
    modified_at: float
```

Inside `list_recordings()`, load metadata and pass `display_name`:

```python
from teach_skill.recording_metadata import load_recording_info

# inside the loop before recordings.append(...)
info = load_recording_info(folder)
display_name = info.title or folder.name

recordings.append(
    RecordingSummary(
        name=folder.name,
        display_name=display_name,
        path=folder,
        jsonl_path=jsonl_path,
        frame_count=frame_count,
        modified_at=folder.stat().st_mtime,
    )
)
```

Update existing tests that manually construct `RecordingSummary` to include `display_name=...`.

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_recording_metadata.py tests/test_launcher_state.py tests/test_launcher.py tests/test_qt_services.py -q
```

Expected: pass.

## Task 2: Safe Rename And Delete Services

**Files:**
- Modify: `src/teach_skill/qt_app/services.py`
- Test: `tests/test_qt_services.py`

- [ ] **Step 1: Write failing service tests**

Add to `tests/test_qt_services.py`:

```python
def test_rename_recording_saves_friendly_title(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=recording_dir)

    QtAppServices(recordings_root=tmp_path).rename_recording(recording, "Excel demo")

    assert (recording_dir / "recording-info.json").read_text(encoding="utf-8").count("Excel demo") == 1


def test_delete_recording_removes_folder_when_no_recording_is_active(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=recording_dir)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: False)

    QtAppServices(recordings_root=tmp_path).delete_recording(recording)

    assert not recording_dir.exists()


def test_delete_recording_blocks_when_recording_is_active(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=recording_dir)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: True)

    try:
        QtAppServices(recordings_root=tmp_path).delete_recording(recording)
    except RuntimeError as exc:
        assert "Stop the active recording" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert recording_dir.exists()


def test_delete_recording_rejects_recording_outside_root(tmp_path):
    recordings_root = tmp_path / "recordings"
    outside = tmp_path / "outside"
    recordings_root.mkdir()
    outside.mkdir()
    (outside / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=outside)

    try:
        QtAppServices(recordings_root=recordings_root).delete_recording(recording)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert outside.exists()
```

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_services.py -q
```

Expected: fail because `rename_recording()` and `delete_recording()` do not exist.

- [ ] **Step 3: Implement service methods**

In `src/teach_skill/qt_app/services.py`, import:

```python
import shutil
from teach_skill.recording_metadata import save_recording_title
```

Add helper:

```python
    def _recording_path_under_root(self, recording: RecordingSummary) -> Path:
        recording_path = recording.path.resolve()
        recording_path.relative_to(self.recordings_root.resolve())
        return recording_path
```

Use the helper in `compile_recording()` and add:

```python
    def rename_recording(self, recording: RecordingSummary, title: str) -> None:
        recording_path = self._recording_path_under_root(recording)
        save_recording_title(recording_path, title)

    def delete_recording(self, recording: RecordingSummary) -> None:
        recording_path = self._recording_path_under_root(recording)
        if is_recording_active(self.recordings_root):
            raise RuntimeError("Stop the active recording before deleting recordings.")
        shutil.rmtree(recording_path)
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_services.py tests/test_recording_metadata.py -q
```

Expected: pass.

## Task 3: Pause And Resume Recorder Controls

**Files:**
- Modify: `src/teach_skill/recorder/control.py`
- Modify: `src/teach_skill/recorder/controller.py`
- Modify: `src/teach_skill/recorder/tray.py`
- Test: `tests/test_recorder_control.py`
- Test: `tests/test_recorder_controller.py`
- Test: `tests/test_tray.py`

- [ ] **Step 1: Write failing control/controller/tray tests**

Add to `tests/test_recorder_control.py`:

```python
from teach_skill.recorder.control import (
    clear_pause_request,
    clear_resume_request,
    is_pause_requested,
    is_resume_requested,
    is_recording_paused,
    mark_recording_paused,
    mark_recording_resumed,
    request_pause,
    request_resume,
)


def test_pause_resume_request_and_state_files(tmp_path):
    request_pause(tmp_path)
    assert is_pause_requested(tmp_path) is True

    clear_pause_request(tmp_path)
    assert is_pause_requested(tmp_path) is False

    mark_recording_paused(tmp_path)
    assert is_recording_paused(tmp_path) is True

    request_resume(tmp_path)
    assert is_resume_requested(tmp_path) is True

    clear_resume_request(tmp_path)
    mark_recording_resumed(tmp_path)
    assert is_resume_requested(tmp_path) is False
    assert is_recording_paused(tmp_path) is False
```

Add to `tests/test_recorder_controller.py`:

```python
def test_recorder_controller_ignores_capture_while_paused(tmp_path):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    controller.pause_recording()
    controller.on_window_switch({"process": "chrome.exe", "title": "Ignore me"})
    controller.on_click(10, 20, None, True)
    controller.on_clipboard_change("secret")
    controller.resume_recording()

    events = [
        json.loads(line)
        for line in (tmp_path / "recording.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["type"] for event in events] == [
        "recording_meta",
        "recording_paused",
        "recording_resumed",
    ]
```

Add to `tests/test_tray.py`:

```python
def test_tray_app_applies_pause_and_resume_requests(tmp_path):
    controller = MagicMock()
    app = RecorderTrayApp(controller, recordings_root=tmp_path)

    request_pause(tmp_path)
    assert app.apply_recording_controls() is True
    controller.pause_recording.assert_called_once()

    request_resume(tmp_path)
    assert app.apply_recording_controls() is True
    controller.resume_recording.assert_called_once()
```

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
.venv/bin/python -m pytest tests/test_recorder_control.py tests/test_recorder_controller.py tests/test_tray.py -q
```

Expected: fail because pause/resume helpers and methods do not exist.

- [ ] **Step 3: Implement pause/resume controls**

Extend `src/teach_skill/recorder/control.py`:

```python
PAUSE_REQUEST_FILE = ".recording.pause"
RESUME_REQUEST_FILE = ".recording.resume"
PAUSED_STATE_FILE = ".recording.paused"


def pause_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / PAUSE_REQUEST_FILE


def resume_request_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / RESUME_REQUEST_FILE


def paused_state_path(recordings_root: Path) -> Path:
    return Path(recordings_root) / PAUSED_STATE_FILE


def _write_control_file(path: Path, action: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    requested_at = datetime.now(timezone.utc).isoformat()
    path.write_text(f"{action} at {requested_at}\n", encoding="utf-8")
    return path


def request_pause(recordings_root: Path) -> Path:
    return _write_control_file(pause_request_path(recordings_root), "pause requested")


def request_resume(recordings_root: Path) -> Path:
    return _write_control_file(resume_request_path(recordings_root), "resume requested")


def is_pause_requested(recordings_root: Path) -> bool:
    return pause_request_path(recordings_root).exists()


def is_resume_requested(recordings_root: Path) -> bool:
    return resume_request_path(recordings_root).exists()


def clear_pause_request(recordings_root: Path) -> None:
    _clear_file(pause_request_path(recordings_root))


def clear_resume_request(recordings_root: Path) -> None:
    _clear_file(resume_request_path(recordings_root))


def mark_recording_paused(recordings_root: Path) -> None:
    _write_control_file(paused_state_path(recordings_root), "paused")


def mark_recording_resumed(recordings_root: Path) -> None:
    _clear_file(paused_state_path(recordings_root))


def is_recording_paused(recordings_root: Path) -> bool:
    return paused_state_path(recordings_root).exists()
```

Refactor `clear_stop_request()` to use:

```python
def _clear_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
```

In `src/teach_skill/recorder/controller.py`, add `self.is_paused = False` and methods:

```python
    def pause_recording(self):
        if self.is_paused:
            return
        self.is_paused = True
        self.writer.write_event({"type": "recording_paused"})

    def resume_recording(self):
        if not self.is_paused:
            return
        self.is_paused = False
        self.start_time = time.time()
        self.writer.write_event({"type": "recording_resumed"})
```

Change callback guards from:

```python
if not self.is_recording:
    return
```

to:

```python
if not self.is_recording or self.is_paused:
    return
```

Apply that to `on_window_switch()`, `on_click()`, `on_clipboard_change()`, and `capture_screenshot()`. Keep `on_press()` ignored while paused by adding:

```python
    def on_press(self, key):
        if self.is_paused:
            return
        self.input_counter.on_press(key)
```

In `src/teach_skill/recorder/tray.py`, import pause helpers and add:

```python
    def apply_recording_controls(self) -> bool:
        if self.recordings_root is None:
            return False
        applied = False
        if is_pause_requested(self.recordings_root):
            clear_pause_request(self.recordings_root)
            self.controller.pause_recording()
            mark_recording_paused(self.recordings_root)
            applied = True
        if is_resume_requested(self.recordings_root):
            clear_resume_request(self.recordings_root)
            self.controller.resume_recording()
            mark_recording_resumed(self.recordings_root)
            applied = True
        return applied
```

Call it in `poll_stop_request()` before checking stop:

```python
self.apply_recording_controls()
```

In CLI `record`, clear pause/resume/paused files at start and after `app.start()` returns.

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_recorder_control.py tests/test_recorder_controller.py tests/test_tray.py tests/test_cli_record.py -q
```

Expected: pass.

## Task 4: Qt Services For Pause And Resume

**Files:**
- Modify: `src/teach_skill/qt_app/services.py`
- Test: `tests/test_qt_services.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_qt_services.py`:

```python
def test_services_pause_and_resume_recording_request_controls(tmp_path, monkeypatch):
    states = {"active": True, "paused": False}
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: states["active"])
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_paused", lambda root: states["paused"])
    services = QtAppServices(recordings_root=tmp_path)

    assert services.pause_recording() is True
    assert (tmp_path / ".recording.pause").exists()

    states["paused"] = True
    assert services.resume_recording() is True
    assert (tmp_path / ".recording.resume").exists()


def test_services_pause_resume_report_when_not_available(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: False)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_paused", lambda root: False)
    services = QtAppServices(recordings_root=tmp_path)

    assert services.pause_recording() is False
    assert services.resume_recording() is False
```

Also assert `status.paused` once `AppStatus` gains the field:

```python
def test_status_reports_paused_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "teach_skill.qt_app.services.run_doctor",
        lambda config: types.SimpleNamespace(status="Ready", can_record=True, can_compile=True),
    )
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: True)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_paused", lambda root: True)

    status = QtAppServices(recordings_root=tmp_path).status()

    assert status.recording_paused is True
    assert status.state_label == "Paused"
```

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_services.py -q
```

Expected: fail because service methods and status field do not exist.

- [ ] **Step 3: Implement service pause/resume**

In `AppStatus`, add:

```python
recording_paused: bool
```

Change `build_app_status()` signature:

```python
def build_app_status(doctor_result: DoctorResult, recording_active: bool, recording_paused: bool = False) -> AppStatus:
```

State label logic:

```python
if recording_active and recording_paused:
    state_label = "Paused"
elif recording_active:
    state_label = "Recording"
```

In `status()`:

```python
recording_paused = is_recording_paused(self.recordings_root)
return build_app_status(doctor_result, recording_active, recording_paused)
```

Add imports:

```python
from teach_skill.recorder.control import (
    is_recording_paused,
    request_pause,
    request_resume,
    request_stop,
)
```

Add methods:

```python
    def pause_recording(self) -> bool:
        if not is_recording_active(self.recordings_root) or is_recording_paused(self.recordings_root):
            return False
        request_pause(self.recordings_root)
        return True

    def resume_recording(self) -> bool:
        if not is_recording_active(self.recordings_root) or not is_recording_paused(self.recordings_root):
            return False
        request_resume(self.recordings_root)
        return True
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_services.py -q
```

Expected: pass.

## Task 5: Qt Window Controls

**Files:**
- Modify: `src/teach_skill/qt_app/app.py`
- Test: `tests/test_qt_app.py`

- [ ] **Step 1: Write failing window-handler tests**

Add to `tests/test_qt_app.py`:

```python
def test_qt_window_pause_and_resume_recording_refresh_status():
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    window = object.__new__(module.TeachSkillQtWindow)
    messages = []
    window.window = _FakeWindow()
    window.services = types.SimpleNamespace(
        pause_recording=lambda: messages.append("pause") or True,
        resume_recording=lambda: messages.append("resume") or True,
    )
    window.refresh_status = lambda: messages.append("refresh")

    window.pause_recording()
    window.resume_recording()

    assert messages == ["pause", "refresh", "resume", "refresh"]
    assert window.window.status_bar.messages == [
        "Recording pause requested",
        "Recording resume requested",
    ]


def test_qt_window_rename_and_delete_selected_recording_refreshes():
    import importlib

    module = importlib.import_module("teach_skill.qt_app.app")
    recording = types.SimpleNamespace(display_name="Old name")
    calls = []
    window = object.__new__(module.TeachSkillQtWindow)
    window.selected_recording = recording
    window.services = types.SimpleNamespace(
        rename_recording=lambda selected, title: calls.append(("rename", selected, title)),
        delete_recording=lambda selected: calls.append(("delete", selected)),
    )
    window.refresh = lambda: calls.append(("refresh",))
    window.window = _FakeWindow()

    window.rename_selected_recording("New name")
    window.delete_selected_recording(confirm=True)

    assert calls == [
        ("rename", recording, "New name"),
        ("refresh",),
        ("delete", recording),
        ("refresh",),
    ]
```

- [ ] **Step 2: Run tests and verify red**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_app.py -q
```

Expected: fail because handlers and UI buttons do not exist.

- [ ] **Step 3: Implement UI**

In `_import_qt()`, import and return:

```python
QInputDialog,
QMessageBox,
```

In `_build_ui()`, create:

```python
self.pause_button = qt["QPushButton"]("Pause")
self.resume_button = qt["QPushButton"]("Resume")
self.rename_button = qt["QPushButton"]("Rename")
self.delete_button = qt["QPushButton"]("Delete")
```

Add Pause/Resume near Stop, and Rename/Delete near the recordings list.

Connect:

```python
self.pause_button.clicked.connect(self.pause_recording)
self.resume_button.clicked.connect(self.resume_recording)
self.rename_button.clicked.connect(self.prompt_rename_selected_recording)
self.delete_button.clicked.connect(self.confirm_delete_selected_recording)
```

In `refresh_status()`:

```python
self.pause_button.setEnabled(status.recording_active and not status.recording_paused)
self.resume_button.setEnabled(status.recording_active and status.recording_paused)
```

In `select_recording()`, enable rename/delete when a recording is selected and no recording is active:

```python
self.rename_button.setEnabled(not self.current_status.recording_active)
self.delete_button.setEnabled(not self.current_status.recording_active)
```

Add methods:

```python
    def pause_recording(self) -> None:
        if self.services.pause_recording():
            self.window.statusBar().showMessage("Recording pause requested")
        else:
            self.window.statusBar().showMessage("Recording is not available to pause")
        self.refresh_status()

    def resume_recording(self) -> None:
        if self.services.resume_recording():
            self.window.statusBar().showMessage("Recording resume requested")
        else:
            self.window.statusBar().showMessage("Recording is not available to resume")
        self.refresh_status()

    def prompt_rename_selected_recording(self) -> None:
        if self.selected_recording is None:
            return
        title, accepted = self.qt["QInputDialog"].getText(
            self.window,
            "Rename recording",
            "Recording name",
            text=self.selected_recording.display_name,
        )
        if accepted:
            self.rename_selected_recording(title)

    def rename_selected_recording(self, title: str) -> None:
        if self.selected_recording is None:
            return
        try:
            self.services.rename_recording(self.selected_recording, title)
        except (OSError, ValueError) as exc:
            self.window.statusBar().showMessage(f"Could not rename recording: {exc}")
            return
        self.window.statusBar().showMessage("Recording renamed")
        self.refresh()

    def confirm_delete_selected_recording(self) -> None:
        if self.selected_recording is None:
            return
        answer = self.qt["QMessageBox"].question(
            self.window,
            "Delete recording",
            f"Delete {self.selected_recording.display_name}?",
        )
        if answer == self.qt["QMessageBox"].Yes:
            self.delete_selected_recording(confirm=True)

    def delete_selected_recording(self, confirm: bool = False) -> None:
        if self.selected_recording is None or not confirm:
            return
        try:
            self.services.delete_recording(self.selected_recording)
        except (OSError, RuntimeError, ValueError) as exc:
            self.window.statusBar().showMessage(f"Could not delete recording: {exc}")
            return
        self.window.statusBar().showMessage("Recording deleted")
        self.refresh()
```

Use `recording.display_name` in the recent recordings list label.

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_qt_app.py tests/test_qt_services.py -q
```

Expected: pass.

## Task 6: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run focused regression suite**

Run:

```bash
.venv/bin/python -m pytest tests/test_recording_metadata.py tests/test_launcher_state.py tests/test_recorder_control.py tests/test_recorder_controller.py tests/test_tray.py tests/test_qt_services.py tests/test_qt_app.py -q
```

Expected: pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: pass.

- [ ] **Step 3: Run whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run Qt preflight**

Run:

```bash
.venv/bin/teach-skill launch --qt --check-only
```

Expected on macOS: exit code 0 with "Needs setup" because recording is Windows-only, plus OK checks for Python/config folders.

- [ ] **Step 5: Quality gates**

Run code review and QA gates after code changes. They should check:

- pause captures no user activity
- resume keeps using the same recording folder
- delete cannot remove an active recording root
- friendly names do not rename folders
- no duplicate stop/pause/resume races

## Self-Review

- Spec coverage: friendly names are Task 1/2/5; delete is Task 2/5; pause/resume are Task 3/4/5; safety checks are Task 2/4/5; testing/manual Windows smoke is Task 6.
- Placeholder scan: no TBD/TODO/fill-in placeholders remain.
- Type consistency: `RecordingSummary.display_name`, `AppStatus.recording_paused`, `QtAppServices.rename_recording/delete_recording/pause_recording/resume_recording`, and recorder control helper names are consistent across tasks.
