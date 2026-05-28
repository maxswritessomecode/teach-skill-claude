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


def test_system_prompt_includes_gated_after_running_script_promotion():
    prompt = build_system_prompt()
    lower_prompt = prompt.lower()
    required_structure = prompt.split("Optionally append this section only")[0]

    assert "## After Running" in prompt
    assert "## After Running" not in required_structure
    assert "offer to create a reusable script" in lower_prompt
    assert "only make this offer when" in lower_prompt
    assert "recording shows repeated manual ui work" in lower_prompt
    assert "stable input/output pattern" in lower_prompt
    assert "structured data parsing" in lower_prompt
    assert "same artifact or result with less manual ui work" in lower_prompt
    assert "omit the \"after running\" section if no clear speedup exists" in lower_prompt
    assert "artifact-producing path already uses a script" in lower_prompt
    assert "large speedup" in lower_prompt
    assert "ask before creating or modifying scripts" in lower_prompt


def test_user_message_contains_timeline():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "chrome.exe" in msg
    assert "Google Sheets" in msg


def test_user_message_contains_meta():
    rec = parse_recording(FIXTURE)
    msg = build_user_message(rec)
    assert "DESKTOP-TEST" in msg
