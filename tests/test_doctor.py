from pathlib import Path

from teach_skill.doctor import Check, evaluate_checks, run_doctor


def test_evaluate_checks_ready_when_record_and_compile_checks_pass():
    result = evaluate_checks([
        Check("Python", True, "Python 3.11", required_for=("record",)),
        Check("Recordings folder", True, "Writable", required_for=("record",)),
        Check("Claude Code", True, "Found", required_for=("compile",)),
        Check("Agent SDK", True, "Installed", required_for=("compile",)),
    ])

    assert result.status == "Ready"
    assert result.can_record is True
    assert result.can_compile is True


def test_evaluate_checks_allows_recording_when_only_compile_checks_fail():
    result = evaluate_checks([
        Check("Python", True, "Python 3.11", required_for=("record",)),
        Check("Recordings folder", True, "Writable", required_for=("record",)),
        Check("Claude Code", False, "Not found", required_for=("compile",)),
    ])

    assert result.status == "Can record, but cannot compile yet"
    assert result.can_record is True
    assert result.can_compile is False


def test_evaluate_checks_needs_setup_when_recording_check_fails():
    result = evaluate_checks([
        Check("Python", False, "Python 3.10+ is required", required_for=("record",)),
        Check("Claude Code", True, "Found", required_for=("compile",)),
    ])

    assert result.status == "Needs setup"
    assert result.can_record is False
    assert result.can_compile is False


def test_run_doctor_uses_injected_probes_and_creates_recordings_folder(tmp_path):
    recordings_dir = tmp_path / "recordings"

    result = run_doctor(
        config={"storage_path": str(recordings_dir)},
        python_version=(3, 11),
        platform="win32",
        command_exists=lambda name: name == "claude",
        import_exists=lambda name: name == "claude_agent_sdk",
    )

    assert result.status == "Ready"
    assert recordings_dir.is_dir()
    assert {check.name: check.ok for check in result.checks}["Claude Code"] is True


def test_run_doctor_reports_missing_claude_as_compile_only_issue(tmp_path):
    result = run_doctor(
        config={"storage_path": str(tmp_path / "recordings")},
        python_version=(3, 11),
        platform="win32",
        command_exists=lambda name: False,
        import_exists=lambda name: True,
    )

    assert result.status == "Can record, but cannot compile yet"
    assert result.can_record is True
    assert result.can_compile is False


def test_run_doctor_calls_external_probes_once(tmp_path):
    calls = {"command": 0, "import": 0}

    def command_exists(name):
        calls["command"] += 1
        return True

    def import_exists(name):
        calls["import"] += 1
        return True

    run_doctor(
        config={"storage_path": str(tmp_path / "recordings")},
        python_version=(3, 11),
        platform="win32",
        command_exists=command_exists,
        import_exists=import_exists,
    )

    assert calls == {"command": 1, "import": 1}


def test_run_doctor_reports_recording_unsupported_on_non_windows(tmp_path):
    result = run_doctor(
        config={"storage_path": str(tmp_path / "recordings")},
        python_version=(3, 11),
        platform="darwin",
        command_exists=lambda name: True,
        import_exists=lambda name: True,
    )

    assert result.status == "Needs setup"
    assert result.can_record is False
    assert {check.name: check.ok for check in result.checks}["Operating system"] is False
