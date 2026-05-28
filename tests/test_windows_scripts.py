from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_windows_uses_current_checkout_instead_of_cloning_antigravity():
    text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    assert "teach-skill-antigravity" not in text
    assert "git clone" not in text
    assert "$projectDir = Split-Path -Parent $PSScriptRoot" in text


def test_install_fails_when_recorder_import_verification_fails():
    text = (ROOT / "install.ps1").read_text()

    assert "$pipUpgradeOutput = & .\\.venv\\Scripts\\python.exe -m pip install --upgrade pip" in text
    assert "$installOutput = & .\\.venv\\Scripts\\python.exe -m pip install -e" in text
    assert "$verifyOutput = & .\\.venv\\Scripts\\python.exe -c" in text
    assert "from PIL import Image" in text
    assert "import pynput, pystray" in text
    assert text.count("if ($LASTEXITCODE -ne 0)") >= 3


def test_setup_windows_fails_when_dependency_install_or_checks_fail():
    text = (ROOT / "scripts" / "setup-windows.ps1").read_text()

    assert "$uvInstallOutput = uv pip install -e" in text
    assert "$pipInstallOutput = pip install -e" in text
    assert "exit 1" in text[text.index("if ($allPassed)"):]
