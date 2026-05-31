# Windows Packaging

Teach Skill Claude has two Windows install paths.

## Full Installer

The recommended user-facing release artifact is `TeachSkillClaudeSetup.exe`.
It bundles the Python application and dependencies into a Windows app folder,
then installs launcher shortcuts for nontechnical users.

This path is for normal users who should not need to install Python packages or
run PowerShell commands by hand.

The current package keeps a console available because skill compilation still
uses command-line review prompts. Once compile review moves fully into the
launcher UI, the build can switch to a windowed executable.

Build on Windows:

```powershell
.\packaging\windows\build-full-installer.ps1
```

The build expects:

- Python 3.10 or newer
- PyInstaller available in the build environment
- Inno Setup with `ISCC.exe` available
- Claude Code installed separately on the user's machine for skill compilation

## Advanced Installer

The advanced path is `install.bat` from the repository root. It uses the user's
existing Python installation and creates a local editable environment.

Use this path for contributors, technical users, or managed environments that
prefer to control Python and package installation themselves.
