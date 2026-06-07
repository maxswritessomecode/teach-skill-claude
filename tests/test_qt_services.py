import types
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
        recording_paused=False,
        state_label="Recording",
    )


def test_build_app_status_maps_non_recording_states():
    ready = types.SimpleNamespace(status="Can record", can_record=True, can_compile=True)
    needs_setup = types.SimpleNamespace(status="Needs setup", can_record=False, can_compile=False)

    assert build_app_status(ready, recording_active=False).state_label == "Can record"
    assert build_app_status(needs_setup, recording_active=False).state_label == "Needs setup"


def test_status_uses_injected_recordings_root_in_config(tmp_path, monkeypatch):
    captured = {}

    def fake_run_doctor(config):
        captured["storage_path"] = config["storage_path"]
        return types.SimpleNamespace(status="Ready", can_record=True, can_compile=True)

    monkeypatch.setattr("teach_skill.qt_app.services.run_doctor", fake_run_doctor)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: False)

    status = QtAppServices(recordings_root=tmp_path).status()

    assert captured["storage_path"] == str(tmp_path)
    assert status.state_label == "Can record"


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


def test_services_stop_recording_requests_stop_when_recording_is_active(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: True)

    stopped = QtAppServices(recordings_root=tmp_path).stop_recording()

    assert stopped is True
    assert (tmp_path / ".recording.stop").exists()


def test_services_stop_recording_reports_when_no_recording_is_active(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: False)

    stopped = QtAppServices(recordings_root=tmp_path).stop_recording()

    assert stopped is False
    assert not (tmp_path / ".recording.stop").exists()


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


def test_rename_recording_saves_friendly_title(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=recording_dir)

    QtAppServices(recordings_root=tmp_path).rename_recording(recording, "Excel demo")

    assert (recording_dir / "recording-info.json").read_text(encoding="utf-8").count("Excel demo") == 1


def test_rename_recording_blocks_when_recording_is_active(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    recording = types.SimpleNamespace(path=recording_dir)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: True)

    try:
        QtAppServices(recordings_root=tmp_path).rename_recording(recording, "Excel demo")
    except RuntimeError as exc:
        assert "Stop the active recording" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert not (recording_dir / "recording-info.json").exists()


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


def test_delete_recording_rejects_symlinked_recording_folder(tmp_path, monkeypatch):
    target = tmp_path / "target_recording"
    target.mkdir()
    (target / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    link = tmp_path / "recording_20260607_120000"
    link.symlink_to(target, target_is_directory=True)
    recording = types.SimpleNamespace(path=link)
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: False)

    try:
        QtAppServices(recordings_root=tmp_path).delete_recording(recording)
    except ValueError as exc:
        assert "symlinked" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert link.exists()
    assert target.exists()


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


def test_compile_recording_uses_reviewed_jsonl(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (recording_dir / "recording.jsonl").write_text(
        '{"type": "recording_meta"}\n{"type": "clipboard_text", "content": "secret"}\n',
        encoding="utf-8",
    )
    (recording_dir / "review.json").write_text(
        '{"excluded_events": [1], "frames": []}\n',
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
    assert commands[0][1] == {"new_console": True, "keep_console_open": True}
    filtered_path = recording_dir / "reviewed-recording.jsonl"
    assert filtered_path.read_text(encoding="utf-8") == '{"type": "recording_meta"}\n'


def test_compile_recording_blocks_active_recording_before_writing(tmp_path, monkeypatch):
    recording_dir = tmp_path / "recording_20260602_120000"
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text(
        '{"type": "recording_meta"}\n',
        encoding="utf-8",
    )
    recording = types.SimpleNamespace(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )
    commands = []
    monkeypatch.setattr("teach_skill.qt_app.services.is_recording_active", lambda root: True)
    monkeypatch.setattr(
        "teach_skill.qt_app.services._run_cli_command",
        lambda *args, **kwargs: commands.append((args, kwargs)),
    )

    try:
        QtAppServices(recordings_root=tmp_path).compile_recording(recording)
    except RuntimeError as exc:
        assert "Stop the active recording" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert commands == []
    assert not (recording_dir / "reviewed-recording.jsonl").exists()


def test_compile_recording_rejects_recording_outside_root(tmp_path):
    recordings_root = tmp_path / "recordings"
    recording_dir = tmp_path / "outside"
    recordings_root.mkdir()
    recording_dir.mkdir()
    (recording_dir / "recording.jsonl").write_text(
        '{"type": "recording_meta"}\n',
        encoding="utf-8",
    )
    recording = types.SimpleNamespace(
        name=recording_dir.name,
        path=recording_dir,
        jsonl_path=recording_dir / "recording.jsonl",
        frame_count=0,
        modified_at=1,
    )

    try:
        QtAppServices(recordings_root=recordings_root).compile_recording(recording)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert not (recording_dir / "reviewed-recording.jsonl").exists()
