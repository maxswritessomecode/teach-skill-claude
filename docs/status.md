# Teach Skill Claude Status

## Current State

Teach Skill Claude is a Windows-first recorder and compiler for Claude Code skills.

Implemented:

- Windows tray recorder
- JSONL event stream
- Screenshot capture and image attachment
- Structured click telemetry with frame references
- Clipboard capture with privacy filtering
- Sensitive-window screenshot and click-detail redaction
- Claude Agent SDK compiler
- Windows installer and recorder launcher
- Automated test suite

## Current Quality Gates

- Run tests with `pytest tests -q`
- Run whitespace checks with `git diff --check`
- Review generated skills before saving them

## Next Product Work

- Add optional UI Automation metadata for clicked controls
- Add a narration or step-label channel during recording
- Add a replay/evaluation step before installing generated skills
- Build a packaged `.exe` installer for non-developer users

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Entry-level Windows setup and usage guide |
| `install.ps1` | Simple Windows installer |
| `run-recorder.ps1` | Recorder launcher |
| `scripts\setup-windows.ps1` | Contributor setup |
| `src\teach_skill\recorder\` | Recorder implementation |
| `src\teach_skill\compiler\` | Compiler implementation |
| `tests\` | Automated test suite |
