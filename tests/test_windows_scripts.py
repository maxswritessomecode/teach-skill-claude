from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_windows_uses_current_checkout_instead_of_cloning_remote_repo():
    text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    assert "git clone" not in text
    assert "$projectDir = Split-Path -Parent $PSScriptRoot" in text


def test_install_scripts_accept_future_python_majors():
    install_text = (ROOT / "install.ps1").read_text()
    setup_text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    expected = "$major -gt 3 -or ($major -eq 3 -and $minor -ge 10)"
    assert expected in install_text
    assert expected in setup_text


def test_install_bat_does_not_depend_on_powershell_execution_policy():
    text = (ROOT / "install.bat").read_text()

    assert "powershell" not in text.lower()
    assert "ExecutionPolicy" not in text
    assert "Invoke-Expression" not in text
    assert " -File " not in text
    assert "python -m venv .venv" in text
    assert "-m pip install -e \".[recorder]\"" in text
    assert "-m teach_skill.cli launch" in text


def test_setup_windows_does_not_pipe_remote_installers_to_shell_or_require_admin():
    text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    assert "irm " not in text
    assert "| iex" not in text
    assert "Administrator" not in text


def test_install_fails_when_recorder_import_verification_fails():
    text = (ROOT / "install.ps1").read_text()

    assert "pip uninstall -y teach-skill" in text
    assert "$pipUpgradeOutput = & .\\.venv\\Scripts\\python.exe -m pip install --upgrade pip" in text
    assert "$installOutput = & .\\.venv\\Scripts\\python.exe -m pip install -e" in text
    assert "$verifyOutput = & .\\.venv\\Scripts\\python.exe -c" in text
    assert "from PIL import Image" in text
    assert "import pynput, pystray" in text
    assert text.count("if ($LASTEXITCODE -ne 0)") >= 3


def test_install_desktop_launcher_opens_guided_launcher_not_direct_recording():
    text = (ROOT / "install.ps1").read_text()

    assert "-m teach_skill.cli launch" in text
    assert "-m teach_skill.cli record" not in text


def test_install_uses_windows_known_desktop_folder():
    text = (ROOT / "install.ps1").read_text()

    assert '[Environment]::GetFolderPath("Desktop")' in text
    assert '$env:USERPROFILE, "Desktop"' not in text


def test_install_mentions_log_folder():
    text = (ROOT / "install.ps1").read_text()

    assert "$configDir\\logs" in text


def test_setup_windows_fails_when_dependency_install_or_checks_fail():
    text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    assert "uv pip uninstall teach-skill" in text
    assert "pip uninstall -y teach-skill" in text
    assert "$uvInstallOutput = uv pip install -e" in text
    assert "$pipInstallOutput = pip install -e" in text
    assert "exit 1" in text[text.index("if ($allPassed)"):]
