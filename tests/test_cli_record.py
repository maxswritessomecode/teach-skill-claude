import sys
import ast
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from teach_skill.cli import main


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
    with patch("teach_skill.recorder.tray.RecorderTrayApp") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        
        result = runner.invoke(main, ["record", "--test-mode"])
        assert result.exit_code == 0
        assert "Starting recorder session..." in result.output
        mock_app.start.assert_called_once()
