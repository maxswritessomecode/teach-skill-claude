import sys
import ast
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from teach_skill.cli import main
from teach_skill.recorder.lock import RecorderLock


ROOT = Path(__file__).resolve().parents[1]


def test_cli_has_no_top_level_recorder_imports():
    tree = ast.parse((ROOT / "src" / "teach_skill" / "cli.py").read_text())
    top_level_recorder_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("teach_skill.recorder")
    ]

    assert top_level_recorder_imports == []


def test_record_fails_on_non_windows_by_default():
    if sys.platform != "win32":
        runner = CliRunner()
        result = runner.invoke(main, ["record"])
        assert result.exit_code == 1
        assert "Recording is only supported on Windows" in result.output


def test_record_runs_in_test_mode():
    runner = CliRunner()
    with (
        patch("teach_skill.cli.load_config", return_value={"storage_path": "recordings"}),
        patch("teach_skill.recorder.tray.RecorderTrayApp") as mock_app_class,
    ):
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["record", "--test-mode"])
        assert result.exit_code == 0
        assert "Starting recorder session..." in result.output
        mock_app.start.assert_called_once()


def test_record_fails_when_another_recording_lock_exists(tmp_path):
    runner = CliRunner()
    with RecorderLock(tmp_path), patch("teach_skill.cli.load_config", return_value={"storage_path": str(tmp_path)}):
        result = runner.invoke(main, ["record", "--test-mode"])

    assert result.exit_code == 1
    assert "Another recording appears to be running" in result.output


def test_launch_check_only_prints_doctor_status():
    runner = CliRunner()
    with patch("teach_skill.cli.run_doctor") as mock_run_doctor:
        mock_result = MagicMock()
        mock_result.status = "Ready"
        mock_result.checks = []
        mock_run_doctor.return_value = mock_result

        result = runner.invoke(main, ["launch", "--check-only"])

    assert result.exit_code == 0
    assert "Setup status: Ready" in result.output


def test_logs_command_prints_log_file_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    runner = CliRunner()
    result = runner.invoke(main, ["logs"])

    assert result.exit_code == 0
    assert str(tmp_path / ".teach-skill" / "logs" / "teach-skill.log") in result.output


def test_support_bundle_command_creates_zip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    runner = CliRunner()
    result = runner.invoke(main, ["support-bundle"])

    assert result.exit_code == 0
    assert "Support bundle saved to:" in result.output
    assert list((tmp_path / ".teach-skill" / "support").glob("teach-skill-support-*.zip"))
