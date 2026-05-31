from unittest.mock import patch

import types

from teach_skill.launcher import (
    SingleProcessRunner,
    _run_cli_command,
    export_recording,
    try_export_recording,
)
from teach_skill.launcher_state import RecordingSummary


def test_run_cli_command_can_open_new_console_on_windows(tmp_path):
    with (
        patch("teach_skill.launcher.sys.platform", "win32"),
        patch("teach_skill.launcher.subprocess.CREATE_NEW_CONSOLE", 16, create=True),
        patch("teach_skill.launcher.subprocess.Popen") as mock_popen,
    ):
        _run_cli_command("compile", str(tmp_path / "recording.jsonl"), new_console=True)

    assert mock_popen.call_args.kwargs["creationflags"] == 16


def test_run_cli_command_uses_frozen_executable_without_module_flag(tmp_path):
    with (
        patch("teach_skill.launcher.sys.executable", "TeachSkillClaude.exe"),
        patch("teach_skill.launcher.sys.frozen", True, create=True),
        patch("teach_skill.launcher.subprocess.Popen") as mock_popen,
    ):
        _run_cli_command("record")

    assert mock_popen.call_args.args[0] == ["TeachSkillClaude.exe", "record"]


def test_export_recording_creates_zip_archive(tmp_path):
    recording_dir = tmp_path / "recording_20260531_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = RecordingSummary(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )

    archive_path = export_recording(recording, tmp_path / "exports")

    assert archive_path.is_file()
    assert archive_path.suffix == ".zip"


def test_export_recording_rejects_destination_inside_recording_folder(tmp_path):
    recording_dir = tmp_path / "recording_20260531_120000"
    nested_export_dir = recording_dir / "exports"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = RecordingSummary(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )

    try:
        export_recording(recording, nested_export_dir)
    except ValueError as exc:
        assert "inside the recording folder" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_export_recording_generates_unique_archive_when_zip_exists(tmp_path):
    recording_dir = tmp_path / "recording_20260531_120000"
    export_dir = tmp_path / "exports"
    recording_dir.mkdir()
    export_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    (export_dir / "recording_20260531_120000.zip").write_text("existing", encoding="utf-8")
    recording = RecordingSummary(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )

    archive_path = export_recording(recording, export_dir)

    assert archive_path.name == "recording_20260531_120000-1.zip"


def test_single_process_runner_does_not_start_second_live_process():
    class Process:
        def __init__(self, returncode):
            self.returncode = returncode

        def poll(self):
            return self.returncode

    starts = []
    runner = SingleProcessRunner()

    assert runner.start(lambda: starts.append("first") or Process(None)) is True
    assert runner.start(lambda: starts.append("second") or Process(None)) is False

    assert starts == ["first"]


def test_try_export_recording_reports_export_errors(tmp_path):
    recording_dir = tmp_path / "recording_20260531_120000"
    nested_export_dir = recording_dir / "exports"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = RecordingSummary(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )
    errors = []

    archive_path = try_export_recording(recording, nested_export_dir, errors.append)

    assert archive_path is None
    assert "inside the recording folder" in errors[0]


def test_compile_is_blocked_while_recording_is_active(monkeypatch):
    import teach_skill.launcher as launcher

    messages = []
    app = types.SimpleNamespace(
        config={"storage_path": "recordings"},
        recordings_root="recordings",
        logger=types.SimpleNamespace(warning=lambda *args, **kwargs: None),
        latest_recording=lambda: RecordingSummary(
            name="recording_20260531_120000",
            path="recordings/recording_20260531_120000",
            jsonl_path="recordings/recording_20260531_120000/recording.jsonl",
            frame_count=1,
            modified_at=1,
        ),
    )
    monkeypatch.setattr(
        launcher,
        "run_doctor",
        lambda config: types.SimpleNamespace(can_compile=True),
    )
    monkeypatch.setattr(launcher, "is_recording_active", lambda recordings_root: True)
    monkeypatch.setattr(launcher, "_run_cli_command", lambda *args, **kwargs: messages.append("compiled"))
    monkeypatch.setitem(
        __import__("sys").modules,
        "tkinter",
        types.SimpleNamespace(
            messagebox=types.SimpleNamespace(
                showerror=lambda title, message: messages.append(message),
                showinfo=lambda title, message: messages.append(message),
            )
        ),
    )

    launcher.TeachSkillLauncher.compile_latest(app)

    assert messages == ["Stop the active recording before compiling a skill."]


def test_export_is_blocked_while_recording_is_active(monkeypatch):
    import teach_skill.launcher as launcher

    messages = []
    app = types.SimpleNamespace(
        recordings_root="recordings",
        logger=types.SimpleNamespace(warning=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(launcher, "is_recording_active", lambda recordings_root: True)
    monkeypatch.setitem(
        __import__("sys").modules,
        "tkinter",
        types.SimpleNamespace(
            filedialog=types.SimpleNamespace(askdirectory=lambda title: "exports"),
            messagebox=types.SimpleNamespace(
                showerror=lambda title, message: messages.append(message),
                showinfo=lambda title, message: messages.append(message),
            ),
        ),
    )

    launcher.TeachSkillLauncher.export_latest(app)

    assert messages == ["Stop the active recording before exporting it."]
