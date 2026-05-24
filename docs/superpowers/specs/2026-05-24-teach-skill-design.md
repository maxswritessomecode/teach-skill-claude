# Teach Skill — Design Specification

**Date:** 2026-05-24
**Status:** POC
**Repo:** https://github.com/maxswritessomecode/teach-skill
**Platform:** Windows

## Overview

Teach Skill is a Windows desktop tool that records user workflow telemetry and compiles it into Claude Code skills (SKILL.md). Two target audiences:

1. **Everyday Claude Code users** who want to create skills by demonstration — do the task once, get a reusable skill.
2. **Advanced AI consultants** who go into organizations, observe workflows, auto-generate skills, and leave behind automation.

## Architecture

Two-process split:

- **Process A — Recorder** (`teach-skill record`): Windows system tray app that captures desktop telemetry and streams events to a JSONL file.
- **Process B — Compiler** (`teach-skill compile <file.jsonl>`): Reads a JSONL telemetry file, invokes the Claude Agent SDK to generate a SKILL.md, presents it for user review, and saves to the chosen directory.

```
User performs task
    -> Recorder captures events -> JSONL file
        -> Compiler reads JSONL -> Agent SDK generates SKILL.md
            -> User reviews -> saves to skills directory
```

The compiler can run independently on any existing JSONL file, enabling consultants to replay and recompile recordings.

## Recorder

### Telemetry Captured

| Signal | Detail |
|--------|--------|
| Active window | Process name (e.g., `chrome.exe`) + window title |
| Mouse clicks | Count per window session (no coordinates) |
| Keystrokes | Frequency count per window session (no raw keys logged) |
| Screenshots | PNG on window switch + on click if 5s+ since last capture. Native resolution. |
| Clipboard | Text-only clipboard changes, routed through privacy filter |

### Components

| Component | Module | Library |
|-----------|--------|---------|
| Window tracker | `recorder/window.py` | `pywin32` (win32gui, win32process) |
| Input counter | `recorder/input.py` | `pynput` |
| Screenshot grabber | `recorder/screenshot.py` | `Pillow` |
| Event writer | `recorder/writer.py` | stdlib |
| Tray icon + menu | `recorder/tray.py` | `pystray` |
| Hotkey listener | `recorder/hotkey.py` | `pynput` (GlobalHotKeys) |
| Privacy filter | `recorder/privacy.py` | `pywin32` + regex |
| Clipboard monitor | `recorder/clipboard.py` | `pywin32` (win32clipboard) |

### JSONL Event Schema

Five event types per recording:

```jsonl
{"ts": "2026-05-24T10:30:00.000Z", "type": "recording_meta", "machine": "DESKTOP-ABC", "os": "Windows 11", "version": "0.1.0"}
{"ts": "2026-05-24T10:30:01.123Z", "type": "window_switch", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "screenshot": "frames/001.png"}
{"ts": "2026-05-24T10:30:15.789Z", "type": "in_app_capture", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "screenshot": "frames/002.png", "trigger": "click_after_5s"}
{"ts": "2026-05-24T10:30:20.456Z", "type": "clipboard_text", "content": "=SUM(B2:B15)", "source_process": "chrome.exe"}
{"ts": "2026-05-24T10:30:45.456Z", "type": "session_end", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "duration_s": 44.3, "click_count": 12, "keystroke_count": 87}
```

- **`recording_meta`** — first line. Start time, machine name, OS version.
- **`window_switch`** — emitted when foreground app changes. Includes screenshot path.
- **`in_app_capture`** — screenshot taken within the same window, triggered by a click 5+ seconds after the last capture. Covers single-app workflows.
- **`clipboard_text`** — text-only clipboard change. Routed through privacy filter. Captures high-signal context (copied errors, config values, URLs).
- **`session_end`** — emitted for the previous window when user switches away. Aggregated click/keystroke counts and duration.

### Trigger Model

- **Tray menu**: right-click → Start Recording / Stop Recording
- **Global hotkey**: Ctrl+Shift+T toggles recording
- **Double-click tray icon**: toggles recording (quick shortcut)

### Tray Menu

| Menu Item | Description |
|-----------|-------------|
| Start Recording / Stop Recording | Toggles state, label changes accordingly |
| Compile Last Recording | Runs compiler on most recent JSONL file |
| --- | separator |
| Recordings → | Submenu of past sessions (by date/time), click to open folder |
| View Captured Files | Opens current/latest session folder in Explorer |
| View Logs | Opens app log file in default text editor |
| --- | separator |
| Settings → | |
| &nbsp;&nbsp;Change Hotkey | Configure start/stop keyboard shortcut |
| &nbsp;&nbsp;Screenshot Quality | PNG resolution (1280px / 1920px / native) |
| &nbsp;&nbsp;Storage Location | Where recordings are saved |
| &nbsp;&nbsp;Privacy Filter | On (default) / Off — disables all sensitive input filtering |
| --- | separator |
| About | Version, GitHub link |
| Quit | Exit tray app |

**Tray icon states:** idle (gray), recording (red/pulsing).

### Privacy Filter

Three automated detection layers, plus a manual override. All bypass-able via Settings → Privacy Filter → Off:

1. **Win32 password field detection** — detect `ES_PASSWORD` styled input fields in native Windows apps. Suppress screenshot when detected.
2. **Title regex filtering** — redact window titles matching sensitive patterns: "password", "login", "credentials", "sign in", "bank", etc.
3. **SSO/auth provider detection** — detect known auth windows: Okta, Azure AD, Duo Security, OneLogin, Auth0, "Multi-Factor", "Verify your identity", etc.

**Manual override:** Ctrl+Shift+P hotkey to pause/resume recording for sensitive moments the automated layers don't catch.

When triggered, screenshots are suppressed and the JSONL event records:
```jsonl
{"type": "window_switch", "process": "chrome.exe", "title": "[auth/login - redacted]", "screenshot": "suppressed:auth_detected"}
```

## Compiler

### Flow

1. Read the JSONL file, parse into structured timeline
2. Collect referenced PNG screenshots from `frames\` directory
3. Invoke Claude Agent SDK programmatically — pass the system prompt, telemetry timeline, and screenshots as image inputs. The SDK authenticates via the user's existing Claude Code subscription (no API key needed).
4. Display generated SKILL.md for user review
5. User can request revisions via the agent session (Agent SDK supports session continuity)
6. On approval, prompt: "Save globally or to this project?"
   - Global: `%USERPROFILE%\.claude\skills\<task_name>\SKILL.md`
   - Project: `.claude\skills\<task_name>\SKILL.md`
7. Write file and confirm

### System Prompt

Instructs Claude to:
- Treat screenshots as the primary source of truth for the workflow sequence
- Use the JSONL timeline as timestamps and structural markers to stitch the story together
- Identify the workflow pattern from telemetry (apps, sequence, goal)
- Name the skill based on the observed task
- Write trigger conditions (when this skill should activate)
- Write step-by-step instructions Claude Code can follow to reproduce the workflow
- Keep the skill concise — actionable steps, not telemetry narration

### Auth Checks

Before compiling:
1. Is `claude-agent-sdk` installed? If no → "Run `pip install claude-agent-sdk`"
2. Is the Claude Code session valid? If no → "Re-authenticate Claude Code in your terminal"

Check at both startup (disable Compile menu items) and compile time (session could expire between recording and compiling).

## Storage

### Configuration

Location: `%USERPROFILE%\.teach-skill\config.json`
Created with defaults on first run.

```json
{
  "hotkey_toggle": "ctrl+shift+t",
  "hotkey_pause": "ctrl+shift+p",
  "storage_path": "%USERPROFILE%\\.teach-skill\\recordings",
  "screenshot_resolution": "native",
  "privacy_filter": true
}
```

### Recordings

Each session creates a timestamped subfolder:
```
%USERPROFILE%\.teach-skill\recordings\
    2026-05-24_103001\
        recording.jsonl
        frames/
            001.png
            002.png
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Agent SDK not installed | Tray notification, disable Compile menu items |
| Claude Code auth expired (including SSO/Okta) | Tray notification: "Re-authenticate Claude Code in your terminal" |
| Double-start recording | Ignored. Menu shows Stop — can't double-start. |
| Crash mid-recording | JSONL preserved (append-streamed). Next launch offers to compile partial session. |
| Admin/UAC window | Log as `"title": "[elevated process]"`, skip screenshot. |
| Disk full | Warn if < 500MB before recording. Stop gracefully if write fails. |
| Agent SDK timeout/failure | Show error. JSONL on disk — user retries with `teach-skill compile`. |
| SSO prompt during recording | Privacy filter detects and suppresses screenshot. Logs redacted event. |

## Project Structure

```
teach-skill/
├── .claude/
│   └── settings.json
├── docs/
│   ├── decisions.md
│   └── superpowers/
│       └── specs/
│           └── 2026-05-24-teach-skill-design.md
├── src/
│   └── teach_skill/
│       ├── __init__.py
│       ├── cli.py
│       ├── recorder/
│       │   ├── __init__.py
│       │   ├── tray.py
│       │   ├── window.py
│       │   ├── input.py
│       │   ├── screenshot.py
│       │   ├── hotkey.py
│       │   ├── writer.py
│       │   ├── privacy.py
│       │   └── clipboard.py
│       ├── compiler/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   ├── prompt.py
│       │   └── agent.py
│       └── config.py
├── tests/
│   ├── test_writer.py
│   ├── test_parser.py
│   ├── test_privacy.py
│   └── fixtures/
│       └── sample_recording.jsonl
├── requirements.txt
├── setup.py
├── CLAUDE.md
└── README.md
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `pywin32` | Window tracking (win32gui, win32process) |
| `pynput` | Mouse clicks, keystroke frequency, global hotkeys |
| `Pillow` | PNG screenshot capture |
| `pystray` | System tray icon and menu |
| `click` | CLI subcommands (record, compile) |
| `claude-agent-sdk` | Skill compilation — invokes Claude programmatically via Agent SDK |
| `pytest` | Testing |

No separate API key required — Agent SDK authenticates via existing Claude Code subscription.

## Testing Strategy

| Layer | Method |
|-------|--------|
| Event writer | Unit tests — mock events, validate JSONL output |
| JSONL parser | Unit tests — fixture files (valid, empty, corrupt) |
| Privacy filter | Unit tests — sensitive/safe titles, assert redaction |
| Config | Unit tests — defaults, load/save roundtrip |
| Compiler prompt | Manual integration test (requires Claude CLI) |
| Window tracker | Manual on Windows |
| Screenshot grabber | Manual on Windows |
| End-to-end | Manual — record workflow, compile, validate SKILL.md |

`tests/fixtures/sample_recording.jsonl` enables testing the compile pipeline on any platform without Windows.

## Installation (POC)

```bash
git clone https://github.com/maxswritessomecode/teach-skill.git
cd teach-skill
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Requires: Python 3.10+, Windows 10/11, Claude Code CLI installed and authenticated.

## Future Enhancements (Not in POC)

- Audio narration capture
- Post-recording scrub for sensitive content
- PyInstaller `.exe` bundling for non-technical distribution
- Plugin architecture for extensible telemetry sources
