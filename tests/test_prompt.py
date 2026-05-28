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


def test_system_prompt_mentions_click_coordinates():
    prompt = build_system_prompt()
    assert "click coordinates" in prompt.lower()
    assert "frame" in prompt.lower()


def test_system_prompt_requires_execution_oriented_skill_sections():
    prompt = build_system_prompt()

    assert "## Preconditions" in prompt
    assert "## Verification" in prompt
    assert "## If Something Goes Wrong" in prompt


def test_system_prompt_requires_agent_executable_steps():
    prompt = build_system_prompt()
    lower_prompt = prompt.lower()

    assert "generate a skill that claude code can execute" in lower_prompt
    assert "prefer commands, file paths, urls, scripts, apis" in lower_prompt
    assert "do not write vague gui instructions" in lower_prompt
    assert "requires a human-only gui action" in lower_prompt


def test_system_prompt_requires_verification_and_failure_handling():
    prompt = build_system_prompt()
    lower_prompt = prompt.lower()

    assert "every skill must include at least one verification step" in lower_prompt
    assert "verify file type, size, and expected content" in lower_prompt
    assert "if the workflow cannot be automated" in lower_prompt


def test_user_message_contains_timeline():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "chrome.exe" in msg
    assert "Google Sheets" in msg


def test_user_message_contains_meta():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "DESKTOP-TEST" in msg
