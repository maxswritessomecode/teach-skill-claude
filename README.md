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
