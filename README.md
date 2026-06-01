# Teach Skill Claude

Teach Skill Claude is a Windows tool that records a desktop workflow and turns it into a reusable Claude Code skill.

Use it when you want to teach Claude Code how to repeat a process you normally do by hand: opening apps, moving through screens, copying text, saving files, or using internal tools.

## Who This Is For

This project is for Windows users who want to teach Claude Code a desktop workflow without writing Python code or working from a terminal after setup.

You will:

1. Install the recorder.
2. Start recording.
3. Do the task once.
4. Stop recording from the Windows tray icon.
5. Compile the recording into a `SKILL.md` file for Claude Code.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Claude Code installed and signed in
- PowerShell, only needed for optional command-line use

When installing Python, check the box that says **Add Python.exe to PATH**.

## Install

### Recommended: Full Installer

For normal Windows users, the recommended release artifact is:

```text
TeachSkillClaudeSetup.exe
```

The full installer bundles the Python app and creates shortcuts. Claude Code is
still required for compiling recordings into skills, and the launcher will check
whether Claude Code is installed and available.

### Advanced: Existing Python Environment

Use this path if you are contributing, testing from the repository, or need to
use an existing Python environment.

Double-click this file in the project folder:

```text
install.bat
```

The installer creates:

- A local Python environment in `.venv`
- A default config file at `$env:USERPROFILE\.teach-skill\config.json`
- A desktop launcher named `Start Teach Skill Claude.bat`

Logs are written to:

```text
$env:USERPROFILE\.teach-skill\logs\teach-skill.log
```

To find the log path from the command line:

```powershell
teach-skill logs
```

To create a troubleshooting zip with diagnostics and logs:

```powershell
teach-skill support-bundle
```

If Windows asks whether to allow the script, choose yes only if this folder came from a source you trust.

## Use The Launcher

1. Double-click `Start Teach Skill Claude.bat` on your Desktop.
2. Choose **Check Setup** if the app says setup needs attention.
3. Choose **Start Recording**.
4. Do the task you want Claude Code to learn.
5. Right-click the red Teach Skill Claude tray icon.
6. Choose **Stop Recording**.
7. Return to the launcher and choose **Compile Latest**.

The launcher also lets you open the recordings folder or export the latest recording as a zip file for review or handoff.

Recordings are saved here:

```text
$env:USERPROFILE\.teach-skill\recordings
```

Each recording folder contains:

- `recording.jsonl` - the event timeline
- `frames\` - screenshots captured during the workflow

## Compile From PowerShell

The launcher is the recommended path. If you need the command-line path, open PowerShell in the project folder and run:

```powershell
.\.venv\Scripts\Activate.ps1
teach-skill compile "$env:USERPROFILE\.teach-skill\recordings\<recording-folder>\recording.jsonl"
```

Replace `<recording-folder>` with the folder created by your recording.

The compiler shows the generated skill before saving it. Read it carefully. If it looks wrong, reject it and record the task again with slower, clearer steps.

To save without prompts:

```powershell
teach-skill compile "$env:USERPROFILE\.teach-skill\recordings\<recording-folder>\recording.jsonl" --yes --name my-workflow
```

## Privacy Notes

Teach Skill Claude records workflow metadata and screenshots. Treat recording folders as sensitive data.

By default, the recorder:

- Redacts common login, password, SSO, MFA, and banking screens
- Suppresses screenshots for sensitive windows
- Does not store raw typed characters

For workplace use, get approval before recording internal systems or client data.

## Common Problems

### PowerShell Says Scripts Are Disabled

Use `install.bat` instead of running `install.ps1` directly. The batch installer uses `cmd.exe` and Python directly, so it does not change your user PowerShell settings.

```text
install.bat
```

### Python Is Not Found

Install Python from:

```text
https://www.python.org/downloads/
```

During installation, check **Add Python.exe to PATH**.

### Claude Code Is Not Found

Install and sign in to Claude Code, then open a new PowerShell window and try again.

### Something Goes Wrong

Open the launcher and choose **Check Setup**, then create a support bundle:

```powershell
teach-skill support-bundle
```

The support bundle includes diagnostics and Teach Skill Claude logs. It does not
include recording screenshots or workflow event files.

## Developer Checks

For contributors:

```powershell
.\scripts\setup-windows.ps1
pytest tests -q
```

## License

MIT
