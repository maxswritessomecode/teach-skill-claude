from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_packaging_documents_full_and_advanced_installs():
    text = (ROOT / "packaging" / "windows" / "README.md").read_text()

    assert "Full Installer" in text
    assert "Advanced Installer" in text
    assert "TeachSkillClaudeSetup.exe" in text
    assert "install.bat" in text


def test_full_installer_build_script_uses_pyinstaller_and_inno_setup():
    text = (ROOT / "packaging" / "windows" / "build-full-installer.ps1").read_text()

    assert "pyinstaller" in text
    assert "TeachSkillClaude.spec" in text
    assert "ISCC.exe" in text
    assert "Python 3.10 or higher is required" in text
    assert "$major -gt 3 -or ($major -eq 3 -and $minor -ge 10)" in text
    assert "irm " not in text
    assert "| iex" not in text


def test_inno_setup_script_creates_launcher_shortcuts():
    text = (ROOT / "packaging" / "windows" / "TeachSkillClaude.iss").read_text()

    assert "TeachSkillClaudeSetup" in text
    assert "Teach Skill Claude" in text
    assert "{autodesktop}" in text


def test_pyinstaller_spec_keeps_console_for_compile_prompts():
    text = (ROOT / "packaging" / "windows" / "TeachSkillClaude.spec").read_text()

    assert "console=True" in text
