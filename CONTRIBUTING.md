# Contributing

Teach Skill Claude is a Windows-first recorder and compiler for Claude Code skills.

## Useful Commands

Install for development:

```powershell
.\scripts\setup-windows.ps1
```

Run tests:

```powershell
pytest tests -q
```

Start the recorder:

```powershell
teach-skill record
```

Compile a recording:

```powershell
teach-skill compile path\to\recording.jsonl
```

## Project Structure

- `src\teach_skill\recorder\` - Windows recording, privacy filtering, screenshots, input events
- `src\teach_skill\compiler\` - JSONL parser, Claude prompt, Agent SDK integration
- `src\teach_skill\cli.py` - command line interface
- `scripts\setup-windows.ps1` - contributor setup
- `install.ps1` - simple Windows installer for users
- `tests\` - automated tests

Keep user-facing instructions simple and Windows-focused.
