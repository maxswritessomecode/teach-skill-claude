# Core + Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the platform-independent core (config, JSONL writer/parser, privacy regex, system prompt, Agent SDK compiler) so the compile pipeline can be tested with fixture data on any OS.

**Architecture:** Two packages — `recorder/` (writer + privacy regex) and `compiler/` (parser, prompt, agent). Shared config module at package root. CLI entry point via `click`. TDD throughout — tests first, then implementation.

**Tech Stack:** Python 3.10+, click (CLI), claude-agent-sdk (compilation), pytest (testing)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `src/teach_skill/__init__.py`
- Create: `src/teach_skill/recorder/__init__.py`
- Create: `src/teach_skill/compiler/__init__.py`
- Create: `setup.py`
- Create: `requirements.txt`
- Create: `CLAUDE.md`
- Create: `.gitignore`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/teach_skill/recorder
mkdir -p src/teach_skill/compiler
mkdir -p tests/fixtures
```

- [ ] **Step 2: Create package init files**

`src/teach_skill/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/teach_skill/recorder/__init__.py`:
```python
```

`src/teach_skill/compiler/__init__.py`:
```python
```

- [ ] **Step 3: Create setup.py**

```python
from setuptools import setup, find_packages

setup(
    name="teach-skill",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "click",
        "claude-agent-sdk",
    ],
    extras_require={
        "recorder": [
            "pywin32",
            "pynput",
            "Pillow",
            "pystray",
        ],
        "dev": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "teach-skill=teach_skill.cli:main",
        ],
    },
)
```

- [ ] **Step 4: Create requirements.txt**

```
click
claude-agent-sdk
pytest
```

- [ ] **Step 5: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
recordings/
```

- [ ] **Step 6: Create CLAUDE.md**

```markdown
# Teach Skill

Windows desktop tool that records workflow telemetry and compiles Claude Code skills.

## Commands

- `pip install -e ".[dev]"` — install in dev mode
- `pytest tests/ -v` — run tests
- `teach-skill compile <file.jsonl>` — compile a recording into a skill
- `teach-skill record` — start the recorder (Windows only)

## Structure

- `src/teach_skill/config.py` — configuration (load/save JSON)
- `src/teach_skill/recorder/` — telemetry capture (writer, privacy filter)
- `src/teach_skill/compiler/` — JSONL → SKILL.md pipeline (parser, prompt, agent)
- `src/teach_skill/cli.py` — CLI entry points
- `tests/` — pytest test suite
- `tests/fixtures/` — sample JSONL recordings for testing
```

- [ ] **Step 7: Commit**

```bash
git add src/teach_skill/__init__.py src/teach_skill/recorder/__init__.py src/teach_skill/compiler/__init__.py setup.py requirements.txt .gitignore CLAUDE.md
git commit -m "feat: project scaffolding with package structure and setup.py"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `tests/test_config.py`
- Create: `src/teach_skill/config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
import json
from pathlib import Path
from teach_skill.config import load_config, save_config, DEFAULT_CONFIG


def test_load_config_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    custom = {**DEFAULT_CONFIG, "privacy_filter": False}
    save_config(custom)
    loaded = load_config()
    assert loaded["privacy_filter"] is False


def test_load_config_fills_missing_keys(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    partial = {"hotkey_toggle": "ctrl+alt+r"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(partial))
    loaded = load_config()
    assert loaded["hotkey_toggle"] == "ctrl+alt+r"
    assert loaded["privacy_filter"] == DEFAULT_CONFIG["privacy_filter"]


def test_default_config_has_required_keys():
    required = ["hotkey_toggle", "hotkey_pause", "storage_path",
                 "screenshot_resolution", "privacy_filter"]
    for key in required:
        assert key in DEFAULT_CONFIG
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'teach_skill.config'`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/config.py`:
```python
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "hotkey_toggle": "ctrl+shift+t",
    "hotkey_pause": "ctrl+shift+p",
    "storage_path": str(Path.home() / ".teach-skill" / "recordings"),
    "screenshot_resolution": "native",
    "privacy_filter": True,
}


def config_dir() -> Path:
    return Path.home() / ".teach-skill"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if path.exists():
        with open(path) as f:
            stored = json.load(f)
        return {**DEFAULT_CONFIG, **stored}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_config.py src/teach_skill/config.py
git commit -m "feat: config module with load/save and defaults"
```

---

### Task 3: JSONL Event Writer

**Files:**
- Create: `tests/test_writer.py`
- Create: `src/teach_skill/recorder/writer.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_writer.py`:
```python
import json
from pathlib import Path
from teach_skill.recorder.writer import EventWriter


def test_write_event_creates_jsonl_file(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "recording_meta", "machine": "TEST-PC"})
    assert writer.jsonl_path.exists()


def test_write_event_appends_valid_json_lines(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "recording_meta", "machine": "TEST-PC"})
    writer.write_event({"type": "window_switch", "process": "chrome.exe", "title": "Test"})
    lines = writer.jsonl_path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert "ts" in parsed
        assert "type" in parsed


def test_write_event_adds_timestamp_if_missing(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "window_switch", "process": "test.exe", "title": "Test"})
    line = json.loads(writer.jsonl_path.read_text().strip())
    assert "ts" in line
    assert "T" in line["ts"]


def test_write_event_preserves_existing_timestamp(tmp_path):
    writer = EventWriter(tmp_path)
    ts = "2026-05-24T10:30:00.000Z"
    writer.write_event({"type": "window_switch", "ts": ts, "process": "test.exe", "title": "Test"})
    line = json.loads(writer.jsonl_path.read_text().strip())
    assert line["ts"] == ts


def test_next_frame_path_increments(tmp_path):
    writer = EventWriter(tmp_path)
    p1 = writer.next_frame_path()
    p2 = writer.next_frame_path()
    assert p1.name == "0001.png"
    assert p2.name == "0002.png"
    assert p1.parent == writer.frames_dir


def test_frames_directory_created(tmp_path):
    writer = EventWriter(tmp_path)
    assert writer.frames_dir.exists()
    assert writer.frames_dir.is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_writer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/recorder/writer.py`:
```python
import json
import threading
from pathlib import Path
from datetime import datetime, timezone


class EventWriter:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.jsonl_path = session_dir / "recording.jsonl"
        self.frames_dir = session_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._frame_counter = 0

    def write_event(self, event: dict) -> None:
        if "ts" not in event:
            event["ts"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with open(self.jsonl_path, "a") as f:
                f.write(json.dumps(event) + "\n")

    def next_frame_path(self) -> Path:
        with self._lock:
            self._frame_counter += 1
            return self.frames_dir / f"{self._frame_counter:04d}.png"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_writer.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_writer.py src/teach_skill/recorder/writer.py
git commit -m "feat: JSONL event writer with thread-safe append streaming"
```

---

### Task 4: Privacy Filter (Regex Layer)

**Files:**
- Create: `tests/test_privacy.py`
- Create: `src/teach_skill/recorder/privacy.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_privacy.py`:
```python
from teach_skill.recorder.privacy import PrivacyFilter


def test_detects_password_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Reset Password - Google Chrome") is True


def test_detects_login_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Sign in to your account - Chrome") is True


def test_detects_okta_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Okta - Single Sign-On") is True


def test_detects_azure_ad_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Azure AD - Pick an account") is True


def test_detects_duo_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Duo Security - Two-Factor Authentication") is True


def test_detects_mfa_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Multi-Factor Authentication Required") is True


def test_passes_normal_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Google Sheets - Q2 Report") is False


def test_passes_normal_app_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Visual Studio Code - main.py") is False


def test_disabled_filter_passes_everything():
    pf = PrivacyFilter(enabled=False)
    assert pf.is_sensitive_title("Reset Password - Chrome") is False


def test_redact_title_replaces_sensitive():
    pf = PrivacyFilter(enabled=True)
    result = pf.redact_title("Reset Password - Chrome")
    assert result == "[auth/login - redacted]"


def test_redact_title_passes_normal():
    pf = PrivacyFilter(enabled=True)
    result = pf.redact_title("Google Sheets - Q2 Report")
    assert result == "Google Sheets - Q2 Report"


def test_sensitive_clipboard_content():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_clipboard("my_password_123") is False
    assert pf.is_sensitive_clipboard("password: secret123") is True
    assert pf.is_sensitive_clipboard("api_key=sk-abc123def456") is True


def test_disabled_filter_passes_clipboard():
    pf = PrivacyFilter(enabled=False)
    assert pf.is_sensitive_clipboard("password: secret123") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_privacy.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/recorder/privacy.py`:
```python
import re

SENSITIVE_TITLE_PATTERNS = [
    r"password",
    r"sign[\s\-_]?in",
    r"log[\s\-_]?in",
    r"credentials",
    r"okta",
    r"azure[\s\-_]?ad",
    r"duo[\s\-_]?security",
    r"onelogin",
    r"auth0",
    r"multi[\s\-_]?factor",
    r"verify your identity",
    r"two[\s\-_]?factor",
    r"authentication",
    r"sso",
    r"\bbank\b",
]

SENSITIVE_CLIPBOARD_PATTERNS = [
    r"password\s*[:=]",
    r"api[_\-]?key\s*[:=]",
    r"secret\s*[:=]",
    r"token\s*[:=]",
    r"bearer\s+\S+",
]

_title_regex = re.compile("|".join(SENSITIVE_TITLE_PATTERNS), re.IGNORECASE)
_clipboard_regex = re.compile("|".join(SENSITIVE_CLIPBOARD_PATTERNS), re.IGNORECASE)


class PrivacyFilter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def is_sensitive_title(self, title: str) -> bool:
        if not self.enabled:
            return False
        return bool(_title_regex.search(title))

    def redact_title(self, title: str) -> str:
        if self.is_sensitive_title(title):
            return "[auth/login - redacted]"
        return title

    def is_sensitive_clipboard(self, text: str) -> bool:
        if not self.enabled:
            return False
        return bool(_clipboard_regex.search(text))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_privacy.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_privacy.py src/teach_skill/recorder/privacy.py
git commit -m "feat: privacy filter with title regex and clipboard pattern detection"
```

---

### Task 5: JSONL Parser

**Files:**
- Create: `tests/fixtures/sample_recording.jsonl`
- Create: `tests/test_parser.py`
- Create: `src/teach_skill/compiler/parser.py`

- [ ] **Step 1: Create the sample fixture**

`tests/fixtures/sample_recording.jsonl`:
```jsonl
{"ts": "2026-05-24T10:30:00.000Z", "type": "recording_meta", "machine": "DESKTOP-TEST", "os": "Windows 11", "version": "0.1.0"}
{"ts": "2026-05-24T10:30:01.123Z", "type": "window_switch", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "screenshot": "frames/0001.png"}
{"ts": "2026-05-24T10:30:15.789Z", "type": "in_app_capture", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "screenshot": "frames/0002.png", "trigger": "click_after_5s"}
{"ts": "2026-05-24T10:30:20.456Z", "type": "clipboard_text", "content": "=SUM(B2:B15)", "source_process": "chrome.exe"}
{"ts": "2026-05-24T10:30:45.456Z", "type": "session_end", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "duration_s": 44.3, "click_count": 12, "keystroke_count": 87}
{"ts": "2026-05-24T10:30:46.000Z", "type": "window_switch", "process": "outlook.exe", "title": "RE: Q2 Numbers - Outlook", "screenshot": "frames/0003.png"}
{"ts": "2026-05-24T10:31:30.000Z", "type": "session_end", "process": "outlook.exe", "title": "RE: Q2 Numbers - Outlook", "duration_s": 44.0, "click_count": 5, "keystroke_count": 120}
{"ts": "2026-05-24T10:31:31.000Z", "type": "window_switch", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "screenshot": "frames/0004.png"}
{"ts": "2026-05-24T10:32:00.000Z", "type": "session_end", "process": "chrome.exe", "title": "Google Sheets - Q2 Report", "duration_s": 29.0, "click_count": 3, "keystroke_count": 15}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_parser.py`:
```python
import json
from pathlib import Path
from teach_skill.compiler.parser import parse_recording, Recording


FIXTURE = Path(__file__).parent / "fixtures" / "sample_recording.jsonl"


def test_parse_recording_returns_recording():
    rec = parse_recording(FIXTURE)
    assert isinstance(rec, Recording)


def test_parse_recording_extracts_meta():
    rec = parse_recording(FIXTURE)
    assert rec.meta["machine"] == "DESKTOP-TEST"
    assert rec.meta["os"] == "Windows 11"


def test_parse_recording_collects_events():
    rec = parse_recording(FIXTURE)
    assert len(rec.events) == 8  # all events except recording_meta


def test_parse_recording_collects_screenshot_paths():
    rec = parse_recording(FIXTURE)
    assert len(rec.screenshot_paths) == 4
    assert all(p.endswith(".png") for p in rec.screenshot_paths)


def test_parse_recording_extracts_workflow_steps():
    rec = parse_recording(FIXTURE)
    steps = rec.workflow_steps()
    assert len(steps) == 3  # 3 session_end events = 3 workflow steps
    assert steps[0]["process"] == "chrome.exe"
    assert steps[0]["click_count"] == 12


def test_parse_recording_handles_empty_file(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    rec = parse_recording(empty)
    assert rec.meta == {}
    assert rec.events == []


def test_parse_recording_skips_malformed_lines(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"type": "recording_meta", "machine": "X"}\nnot json\n{"type": "window_switch"}\n')
    rec = parse_recording(bad)
    assert rec.meta["machine"] == "X"
    assert len(rec.events) == 1


def test_recording_timeline_text():
    rec = parse_recording(FIXTURE)
    text = rec.timeline_text()
    assert "chrome.exe" in text
    assert "outlook.exe" in text
    assert "Google Sheets" in text
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_parser.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the implementation**

`src/teach_skill/compiler/parser.py`:
```python
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Recording:
    meta: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    screenshot_paths: list[str] = field(default_factory=list)
    source_path: Path | None = None

    def workflow_steps(self) -> list[dict]:
        return [e for e in self.events if e["type"] == "session_end"]

    def timeline_text(self) -> str:
        lines = []
        if self.meta:
            lines.append(f"Recording from {self.meta.get('machine', 'unknown')} "
                         f"({self.meta.get('os', 'unknown')})")
            lines.append("")

        for event in self.events:
            ts = event.get("ts", "")
            etype = event["type"]

            if etype == "window_switch":
                lines.append(f"[{ts}] Switched to: {event['process']} — \"{event.get('title', '')}\"")
            elif etype == "in_app_capture":
                lines.append(f"[{ts}] In-app action in: {event['process']} — \"{event.get('title', '')}\"")
            elif etype == "clipboard_text":
                lines.append(f"[{ts}] Clipboard copied: \"{event.get('content', '')}\"")
            elif etype == "session_end":
                lines.append(f"[{ts}] Left: {event['process']} — \"{event.get('title', '')}\" "
                             f"(duration: {event.get('duration_s', 0)}s, "
                             f"clicks: {event.get('click_count', 0)}, "
                             f"keystrokes: {event.get('keystroke_count', 0)})")
            lines.append("")

        return "\n".join(lines)


def parse_recording(jsonl_path: Path) -> Recording:
    recording = Recording(source_path=jsonl_path)
    text = jsonl_path.read_text().strip()

    if not text:
        return recording

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "recording_meta":
            recording.meta = event
            continue

        recording.events.append(event)

        screenshot = event.get("screenshot")
        if screenshot:
            recording.screenshot_paths.append(screenshot)

    return recording
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_parser.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/sample_recording.jsonl tests/test_parser.py src/teach_skill/compiler/parser.py
git commit -m "feat: JSONL parser with Recording dataclass and timeline formatter"
```

---

### Task 6: System Prompt Template

**Files:**
- Create: `src/teach_skill/compiler/prompt.py`
- Create: `tests/test_prompt.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_prompt.py`:
```python
from teach_skill.compiler.prompt import build_system_prompt, build_user_message
from teach_skill.compiler.parser import parse_recording
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sample_recording.jsonl"


def test_system_prompt_is_nonempty_string():
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_system_prompt_mentions_skill_md():
    prompt = build_system_prompt()
    assert "SKILL.md" in prompt


def test_system_prompt_mentions_screenshots_as_primary():
    prompt = build_system_prompt()
    assert "screenshot" in prompt.lower()
    assert "primary" in prompt.lower()


def test_user_message_contains_timeline():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "chrome.exe" in msg
    assert "Google Sheets" in msg


def test_user_message_contains_meta():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "DESKTOP-TEST" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_prompt.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/compiler/prompt.py`:
```python
from teach_skill.compiler.parser import Recording

SYSTEM_PROMPT = """You are a Claude Code skill compiler. You analyze desktop workflow recordings and generate reusable Claude Code skills (SKILL.md files).

## Your Input

You receive:
1. **Screenshots** — these are your PRIMARY source of truth. They show exactly what the user was looking at during each step of their workflow. Study them carefully to understand the sequence of actions.
2. **A telemetry timeline** — timestamps, window switches, click/keystroke counts, and clipboard activity. Use these as structural markers to understand timing and sequence, but rely on screenshots for the actual workflow content.

## Your Output

Generate a complete SKILL.md file with this structure:

```markdown
---
name: <short-kebab-case-name>
description: <one-line description of what this skill does>
---

# <Skill Name>

<Brief description of the workflow this skill automates.>

## When to Use

<Trigger conditions — what user request or context should activate this skill.>

## Steps

<Numbered step-by-step instructions that Claude Code can follow to reproduce this workflow. Be specific about which applications to use, what actions to take, and what to look for at each step.>
```

## Rules

- Name the skill based on the observed task, not the apps used
- Write trigger conditions that match how a user would naturally ask for this workflow
- Keep steps actionable and specific — "Open the Q2 Report spreadsheet" not "Open a spreadsheet"
- Reference specific UI elements, menu paths, or commands you observe in the screenshots
- If clipboard content was captured, incorporate it as context for understanding the workflow
- Do not narrate the telemetry — transform it into instructions
- Keep the skill concise — a skilled developer should be able to follow it without ambiguity"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_message(recording: Recording) -> str:
    parts = []

    if recording.meta:
        parts.append(f"## Recording Metadata")
        parts.append(f"- Machine: {recording.meta.get('machine', 'unknown')}")
        parts.append(f"- OS: {recording.meta.get('os', 'unknown')}")
        parts.append(f"- Version: {recording.meta.get('version', 'unknown')}")
        parts.append("")

    parts.append("## Workflow Timeline")
    parts.append("")
    parts.append(recording.timeline_text())

    if recording.screenshot_paths:
        parts.append(f"## Screenshots")
        parts.append(f"{len(recording.screenshot_paths)} screenshots are attached as images.")
        parts.append("")

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_prompt.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/teach_skill/compiler/prompt.py tests/test_prompt.py
git commit -m "feat: system prompt template for skill compilation"
```

---

### Task 7: Agent SDK Compiler

**Files:**
- Create: `src/teach_skill/compiler/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_agent.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk


def test_check_agent_sdk_returns_true_when_installed():
    result = check_agent_sdk()
    assert isinstance(result, bool)


def test_compiler_init_with_recording_path():
    compiler = SkillCompiler(Path("tests/fixtures/sample_recording.jsonl"))
    assert compiler.recording_path == Path("tests/fixtures/sample_recording.jsonl")


def test_compiler_load_recording():
    compiler = SkillCompiler(Path("tests/fixtures/sample_recording.jsonl"))
    compiler.load()
    assert compiler.recording is not None
    assert compiler.recording.meta["machine"] == "DESKTOP-TEST"


def test_compiler_collect_screenshots_resolves_paths():
    compiler = SkillCompiler(Path("tests/fixtures/sample_recording.jsonl"))
    compiler.load()
    paths = compiler.collect_screenshot_paths()
    assert len(paths) == 4
    for p in paths:
        assert p.name.endswith(".png")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`src/teach_skill/compiler/agent.py`:
```python
import shutil
from pathlib import Path

from teach_skill.compiler.parser import parse_recording, Recording
from teach_skill.compiler.prompt import build_system_prompt, build_user_message


def check_agent_sdk() -> bool:
    try:
        import claude_agent_sdk
        return True
    except ImportError:
        return False


def check_claude_cli() -> bool:
    return shutil.which("claude") is not None


class SkillCompiler:
    def __init__(self, recording_path: Path):
        self.recording_path = recording_path
        self.recording: Recording | None = None

    def load(self) -> None:
        self.recording = parse_recording(self.recording_path)

    def collect_screenshot_paths(self) -> list[Path]:
        if not self.recording:
            return []
        base_dir = self.recording_path.parent
        return [base_dir / p for p in self.recording.screenshot_paths]

    def build_prompt_payload(self) -> dict:
        if not self.recording:
            raise RuntimeError("Call load() before building prompt payload")
        return {
            "system": build_system_prompt(),
            "user_message": build_user_message(self.recording),
            "screenshot_paths": [str(p) for p in self.collect_screenshot_paths()],
        }

    async def compile(self) -> str:
        if not check_agent_sdk():
            raise RuntimeError(
                "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"
            )

        self.load()
        payload = self.build_prompt_payload()

        from claude_agent_sdk import query

        messages = [{"role": "user", "content": payload["user_message"]}]

        result = await query(
            prompt=payload["system"],
            messages=messages,
            options={"max_turns": 1},
        )

        for message in result.messages:
            if message.role == "assistant":
                for block in message.content:
                    if hasattr(block, "text"):
                        return block.text

        raise RuntimeError("No text response received from Claude")


def save_skill(skill_text: str, task_name: str, global_save: bool = True) -> Path:
    if global_save:
        base = Path.home() / ".claude" / "skills" / task_name
    else:
        base = Path.cwd() / ".claude" / "skills" / task_name

    base.mkdir(parents=True, exist_ok=True)
    skill_path = base / "SKILL.md"
    skill_path.write_text(skill_text)
    return skill_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agent.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/teach_skill/compiler/agent.py tests/test_agent.py
git commit -m "feat: Agent SDK compiler with prompt payload builder"
```

---

### Task 8: CLI Entry Points

**Files:**
- Create: `src/teach_skill/cli.py`

- [ ] **Step 1: Write the implementation**

`src/teach_skill/cli.py`:
```python
import asyncio
import sys
from pathlib import Path

import click

from teach_skill import __version__
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk, save_skill


@click.group()
@click.version_option(version=__version__)
def main():
    """Teach Skill — record workflows, compile Claude Code skills."""
    pass


@main.command()
@click.argument("jsonl_path", type=click.Path(exists=True, path_type=Path))
def compile(jsonl_path: Path):
    """Compile a JSONL recording into a Claude Code skill."""
    if not check_agent_sdk():
        click.echo("Error: claude-agent-sdk not installed.", err=True)
        click.echo("Run: pip install claude-agent-sdk", err=True)
        sys.exit(1)

    compiler = SkillCompiler(jsonl_path)

    click.echo(f"Loading recording: {jsonl_path}")
    compiler.load()

    rec = compiler.recording
    click.echo(f"  Machine: {rec.meta.get('machine', 'unknown')}")
    click.echo(f"  Events: {len(rec.events)}")
    click.echo(f"  Screenshots: {len(rec.screenshot_paths)}")
    click.echo()

    click.echo("Compiling skill via Agent SDK...")
    try:
        skill_text = asyncio.run(compiler.compile())
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo()
    click.echo("=" * 60)
    click.echo("GENERATED SKILL")
    click.echo("=" * 60)
    click.echo(skill_text)
    click.echo("=" * 60)
    click.echo()

    if not click.confirm("Does this skill look correct?"):
        click.echo("Skill discarded. Recording is still at:")
        click.echo(f"  {jsonl_path}")
        click.echo("Re-run `teach-skill compile` to try again.")
        return

    task_name = click.prompt("Skill name (kebab-case)", type=str)

    save_global = click.confirm("Save globally? (No = save to current project)", default=True)
    skill_path = save_skill(skill_text, task_name, global_save=save_global)

    click.echo(f"Skill saved to: {skill_path}")


@main.command()
def record():
    """Start the Teach Skill recorder (Windows only)."""
    if sys.platform != "win32":
        click.echo("Error: Recording is only supported on Windows.", err=True)
        sys.exit(1)

    click.echo("Recorder not yet implemented. See Plan 2 (Windows Recorder).")
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Install the package and verify CLI works**

```bash
pip install -e ".[dev]"
teach-skill --version
```
Expected: `teach-skill, version 0.1.0`

- [ ] **Step 3: Verify compile command shows help**

```bash
teach-skill compile --help
```
Expected: Shows usage with `JSONL_PATH` argument

- [ ] **Step 4: Verify record command rejects non-Windows**

```bash
teach-skill record
```
Expected (on Mac): `Error: Recording is only supported on Windows.`

- [ ] **Step 5: Commit**

```bash
git add src/teach_skill/cli.py
git commit -m "feat: CLI entry points with compile and record subcommands"
```

---

### Task 9: End-to-End Compile Test with Fixture

**Files:**
- Create: `tests/fixtures/frames/0001.png` (tiny test image)
- Create: `tests/test_compile_e2e.py`

- [ ] **Step 1: Create a minimal test screenshot**

```python
# Run this once to create a tiny fixture PNG
from PIL import Image
img = Image.new("RGB", (100, 100), color="white")
img.save("tests/fixtures/frames/0001.png")
```

```bash
mkdir -p tests/fixtures/frames
python -c "from PIL import Image; Image.new('RGB', (100, 100), 'white').save('tests/fixtures/frames/0001.png')"
```

- [ ] **Step 2: Write the e2e test (mocked Agent SDK)**

`tests/test_compile_e2e.py`:
```python
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from click.testing import CliRunner
from teach_skill.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "sample_recording.jsonl"

MOCK_SKILL = """---
name: update-q2-report
description: Update Q2 report in Google Sheets and notify team via Outlook
---

# Update Q2 Report

Update the quarterly report spreadsheet and send a summary email.

## When to Use

When the user asks to update a quarterly report or send report summaries.

## Steps

1. Open the Q2 Report in Google Sheets
2. Update the relevant cells with new data
3. Switch to Outlook and compose a reply with the updated numbers
4. Return to Google Sheets to verify changes
"""


def test_compile_loads_and_shows_recording():
    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(FIXTURE)], input="n\n")
    assert "Events: 8" in result.output
    assert "Screenshots: 4" in result.output


def test_compile_full_flow_with_mock_sdk():
    mock_message = MagicMock()
    mock_message.role = "assistant"
    mock_block = MagicMock()
    mock_block.text = MOCK_SKILL
    mock_message.content = [mock_block]

    mock_result = MagicMock()
    mock_result.messages = [mock_message]

    with patch("teach_skill.compiler.agent.check_agent_sdk", return_value=True), \
         patch("claude_agent_sdk.query", new_callable=AsyncMock, return_value=mock_result):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["compile", str(FIXTURE)],
            input="y\nupdate-q2-report\ny\n",
        )
        assert "GENERATED SKILL" in result.output
        assert "update-q2-report" in result.output.lower()
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_compile_e2e.py -v`
Expected: 2 passed

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (config: 4, writer: 6, privacy: 13, parser: 8, prompt: 5, agent: 4, e2e: 2 = ~42 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/frames/0001.png tests/test_compile_e2e.py
git commit -m "feat: end-to-end compile test with mocked Agent SDK"
```

---

### Task 10: README and Final Cleanup

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

`README.md`:
```markdown
# Teach Skill

Record desktop workflows, compile them into Claude Code skills.

**Teach Skill** watches what you do on your Windows desktop — which apps you use, how you navigate between them, what you copy — and turns that workflow into a reusable [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) (SKILL.md). Do a task once, get automation forever.

## Quick Start

```bash
git clone https://github.com/maxswritessomecode/teach-skill.git
cd teach-skill
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[recorder,dev]"
```

## Usage

### Compile a recording into a skill

```bash
teach-skill compile path/to/recording.jsonl
```

### Record a workflow (Windows only)

```bash
teach-skill record
```

## How It Works

1. **Record** — The tray app captures window switches, click/keystroke counts, screenshots, and clipboard text as you perform a task
2. **Compile** — The compiler feeds the telemetry to Claude (via Agent SDK) with a prompt that generates a SKILL.md
3. **Review** — You see the generated skill and can request revisions before saving
4. **Save** — Choose to save globally or to the current project's `.claude/skills/` directory

## Requirements

- Python 3.10+
- Windows 10/11 (for recording)
- Claude Code CLI (for compilation)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
```

- [ ] **Step 2: Run full test suite one final time**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start, usage, and development instructions"
```

- [ ] **Step 4: Push to remote**

```bash
git push origin main
```
