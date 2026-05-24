import sys
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from teach_skill.cli import main


def test_record_fails_on_non_windows_by_default():
    if sys.platform != "win32":
        runner = CliRunner()
        result = runner.invoke(main, ["record"])
        assert result.exit_code == 1
        assert "Recording is only supported on Windows" in result.output


def test_record_runs_in_simulation_mode():
    runner = CliRunner()
    with patch("teach_skill.cli.RecorderTrayApp") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        
        result = runner.invoke(main, ["record", "--simulate"])
        assert result.exit_code == 0
        assert "Starting recorder session..." in result.output
        mock_app.start.assert_called_once()
