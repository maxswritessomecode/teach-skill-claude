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
