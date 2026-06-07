from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner
from teach_skill.cli import main
from teach_skill.recorder.lock import RecorderLock


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


async def fake_compile(self):
    return MOCK_SKILL


def test_compile_loads_and_shows_recording():
    runner = CliRunner()
    with patch("teach_skill.cli.check_agent_sdk", return_value=True), \
            patch("teach_skill.cli.SkillCompiler.compile", new=fake_compile):
        result = runner.invoke(main, ["compile", str(FIXTURE)], input="n\n")

    assert "Events: 8" in result.output
    assert "Screenshots: 4" in result.output
    assert "GENERATED SKILL" in result.output
    assert "Skill discarded" in result.output


def test_compile_full_flow_with_mock_sdk(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    with patch("teach_skill.cli.check_agent_sdk", return_value=True), \
            patch("teach_skill.cli.SkillCompiler.compile", new=fake_compile):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["compile", str(FIXTURE)],
            input="y\nupdate-q2-report\ny\n",
        )
        assert "GENERATED SKILL" in result.output
        assert "update-q2-report" in result.output.lower()
        assert (
            tmp_path
            / ".claude"
            / "skills"
            / "update-q2-report"
            / "SKILL.md"
        ).exists()


def test_compile_blocks_recording_under_active_recordings_root(tmp_path):
    recording_dir = tmp_path / "recording_20260531_120000"
    recording_dir.mkdir()
    recording_path = recording_dir / "recording.jsonl"
    recording_path.write_text('{"type": "recording_meta"}\n', encoding="utf-8")

    runner = CliRunner()
    with (
        RecorderLock(tmp_path),
        patch("teach_skill.cli.load_config", return_value={"storage_path": str(tmp_path)}),
        patch("teach_skill.cli.check_agent_sdk", return_value=True),
    ):
        result = runner.invoke(main, ["compile", str(recording_path)])

    assert result.exit_code == 1
    assert "Stop the active recording before compiling a skill" in result.output


async def fake_failed_compile(self):
    raise RuntimeError("Agent SDK compile failed: Claude Code returned an error result: success")


async def fake_transcript_compile(self):
    return """---
name: test-ustrates
description: Compile this recording into a skill
---

# test_ustrates

The test_ustrates skill ran and verified clean:

- Artifact exists: C:\\Users\\mshin\\.claude\\skills\\archive-forward-rates-heatmap\\SKILL.md
- Registered: it shows up in the active skills list.

Nothing further to run.
"""


def test_compile_shows_agent_sdk_errors_without_traceback():
    runner = CliRunner()
    with patch("teach_skill.cli.check_agent_sdk", return_value=True), \
            patch("teach_skill.cli.SkillCompiler.compile", new=fake_failed_compile):
        result = runner.invoke(main, ["compile", str(FIXTURE)])

    assert result.exit_code == 1
    assert "Agent SDK compile failed" in result.output
    assert "Traceback" not in result.output


def test_compile_rejects_run_report_transcript_without_traceback():
    runner = CliRunner()
    with patch("teach_skill.cli.check_agent_sdk", return_value=True), \
            patch("teach_skill.cli.SkillCompiler.compile", new=fake_transcript_compile):
        result = runner.invoke(
            main,
            ["compile", str(FIXTURE)],
            input="y\ntest-ustrates\ny\n",
        )

    assert result.exit_code == 1
    assert "not an executable skill" in result.output
    assert "Traceback" not in result.output
