# Teach Skill Claude

Teach Skill Claude is a Windows tool that records a desktop workflow and turns it into a reusable Claude Code skill.

Use it when you want to teach Claude Code how to repeat a process you normally do by hand: opening apps, moving through screens, copying text, saving files, or using internal tools.

## Who This Is For

This project is for Windows users who are comfortable following PowerShell instructions but do not want to write Python code.

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
- PowerShell

When installing Python, check the box that says **Add Python.exe to PATH**.

## Install

Open PowerShell in the project folder and run:

```powershell
.\install.ps1
```

The installer creates:

- A local Python environment in `.venv`
- A default config file at `$env:USERPROFILE\.teach-skill\config.json`
- A desktop launcher named `Start Teach Skill Claude.bat`

## Record A Workflow

1. Double-click `Start Teach Skill Claude.bat` on your Desktop.
2. Do the task you want Claude Code to learn.
3. Right-click the red Teach Skill Claude tray icon.
4. Choose **Stop Recording**.

Recordings are saved here:

```text
$env:USERPROFILE\.teach-skill\recordings
```

Each recording folder contains:

- `recording.jsonl` - the event timeline
- `frames\` - screenshots captured during the workflow

## Compile A Skill

Open PowerShell in the project folder and run:

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

Run this once in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run the installer again.

### Python Is Not Found

Install Python from:

```text
https://www.python.org/downloads/
```

During installation, check **Add Python.exe to PATH**.

### Claude Code Is Not Found

Install and sign in to Claude Code, then open a new PowerShell window and try again.

## Developer Checks

For contributors:

```powershell
.\scripts\setup-windows.ps1
pytest tests -q
```

## License

MIT
