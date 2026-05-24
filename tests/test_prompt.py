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
