# Teach Skill Claude Development Guide

This guide is for people changing the project, not for basic recorder users.

For normal use, start with the root `README.md`.

## Project Goal

Teach Skill Claude records a Windows desktop workflow and compiles the recording into a Claude Code `SKILL.md` file.

The intended user flow is:

1. Install on Windows.
2. Record a task from the tray app.
3. Stop recording.
4. Compile the generated `recording.jsonl`.
5. Review and save the generated skill.

## Main Components

- `install.ps1` - simple installer for users
- `run-recorder.ps1` - PowerShell launcher for the recorder
- `scripts\setup-windows.ps1` - contributor setup and dependency checks
- `src\teach_skill\recorder\` - recorder controller, tray app, screenshots, input events, privacy filters
- `src\teach_skill\compiler\` - parser, prompt builder, image attachment handling, Claude Agent SDK compiler
- `tests\` - automated coverage for recorder, compiler, CLI, and installer behavior

## Contributor Setup

Run PowerShell from the project root:

```powershell
.\scripts\setup-windows.ps1
```

This creates `.venv`, installs the package in editable mode, installs recorder dependencies, and verifies required imports.

## Run Tests

After setup:

```powershell
pytest tests -q
```

## Manual Smoke Test

Use this before handing a build to someone else:

1. Run `.\install.ps1`.
2. Double-click `Start Teach Skill Claude.bat` on the Desktop.
3. Open Notepad, type a short sentence, and save a test file.
4. Stop the recorder from the tray icon.
5. Confirm a new folder exists under `$env:USERPROFILE\.teach-skill\recordings`.
6. Compile the new `recording.jsonl`:

```powershell
.\.venv\Scripts\Activate.ps1
teach-skill compile "$env:USERPROFILE\.teach-skill\recordings\<recording-folder>\recording.jsonl"
```

## Privacy Checklist

Before testing with real work systems:

- Confirm the user has permission to record the workflow.
- Avoid passwords, MFA prompts, client data, bank portals, and production secrets.
- Keep `privacy_filter` enabled unless the recording is known to be safe.
- Delete recordings when they are no longer needed.

## Release Checklist

Before committing:

```powershell
pytest tests -q
git diff --check
```

Before sharing with users:

- Confirm README install steps still match `install.ps1`.
- Confirm the Desktop launcher starts the recorder.
- Confirm compile output is reviewed before saving.
