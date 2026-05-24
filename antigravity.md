# Teach Skill

Windows desktop tool that records workflow telemetry and compiles Claude Code skills.

## Commands

- `uv pip install -e ".[dev]"` — install in dev mode

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
