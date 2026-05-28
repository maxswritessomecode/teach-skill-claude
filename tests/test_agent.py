import asyncio
import base64
import json
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk


FIXTURE = Path("tests/fixtures/sample_recording.jsonl")


async def collect_async(async_iterable):
    return [item async for item in async_iterable]


def test_check_agent_sdk_returns_true_when_installed():
    result = check_agent_sdk()
    assert isinstance(result, bool)


def test_compiler_init_with_recording_path():
    compiler = SkillCompiler(FIXTURE)
    assert compiler.recording_path == FIXTURE


def test_compiler_load_recording():
    compiler = SkillCompiler(FIXTURE)
    compiler.load()
    assert compiler.recording is not None
    assert compiler.recording.meta["machine"] == "DESKTOP-TEST"


def test_compiler_collect_screenshots_resolves_paths():
    compiler = SkillCompiler(FIXTURE)
    compiler.load()
    paths = compiler.collect_screenshot_paths()
    assert len(paths) == 4
    for p in paths:
        assert p.name.endswith(".png")


def test_compiler_prompt_stream_attaches_screenshot_image_blocks():
    compiler = SkillCompiler(FIXTURE)
    compiler.load()

    messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    assert len(messages) == 1
    user_message = messages[0]
    assert user_message["type"] == "user"
    content = user_message["message"]["content"]
    assert content[0]["type"] == "text"

    image_blocks = [block for block in content if block["type"] == "image"]
    assert len(image_blocks) == 4
    assert image_blocks[0]["source"]["type"] == "base64"
    assert image_blocks[0]["source"]["media_type"] == "image/png"
    assert image_blocks[0]["source"]["data"]


def test_compiler_prompt_stream_skips_unsafe_missing_and_non_image_screenshots(tmp_path):
    from PIL import Image

    recording_dir = tmp_path / "recording"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    safe_frame = frames_dir / "safe.png"
    Image.new("RGB", (1, 1), "white").save(safe_frame)

    outside_frame = tmp_path / "outside.png"
    Image.new("RGB", (1, 1), "black").save(outside_frame)

    non_image = frames_dir / "note.txt"
    non_image.write_text("not an image")
    fake_png = frames_dir / "fake.png"
    fake_png.write_text("not an image either")

    recording_path = recording_dir / "recording.jsonl"
    events = [
        {"type": "recording_meta", "machine": "TEST", "os": "test"},
        {
            "type": "window_switch",
            "process": "safe.exe",
            "title": "Safe",
            "screenshot": "frames/safe.png",
        },
        {
            "type": "window_switch",
            "process": "escape.exe",
            "title": "Traversal",
            "screenshot": "../outside.png",
        },
        {
            "type": "window_switch",
            "process": "absolute.exe",
            "title": "Absolute",
            "screenshot": str(outside_frame),
        },
        {
            "type": "window_switch",
            "process": "missing.exe",
            "title": "Missing",
            "screenshot": "frames/missing.png",
        },
        {
            "type": "window_switch",
            "process": "text.exe",
            "title": "Text",
            "screenshot": "frames/note.txt",
        },
        {
            "type": "window_switch",
            "process": "fake.exe",
            "title": "Fake",
            "screenshot": "frames/fake.png",
        },
        {
            "type": "window_switch",
            "process": "auth.exe",
            "title": "Auth",
            "screenshot": "suppressed:auth_detected",
        },
    ]
    recording_path.write_text("\n".join(json.dumps(event) for event in events))

    compiler = SkillCompiler(recording_path)
    compiler.load()
    messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    image_blocks = [
        block
        for block in messages[0]["message"]["content"]
        if block["type"] == "image"
    ]
    assert len(image_blocks) == 1
    assert base64.b64decode(image_blocks[0]["source"]["data"]) == safe_frame.read_bytes()


def test_compiler_prompt_stream_rejects_windows_absolute_and_backslash_traversal(tmp_path):
    from PIL import Image

    recording_dir = tmp_path / "recording"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    safe_frame = frames_dir / "safe.png"
    Image.new("RGB", (1, 1), "white").save(safe_frame)

    outside_frame = tmp_path / "outside.png"
    Image.new("RGB", (1, 1), "black").save(outside_frame)

    recording_path = recording_dir / "recording.jsonl"
    events = [
        {"type": "recording_meta", "machine": "TEST", "os": "test"},
        {
            "type": "window_switch",
            "process": "safe.exe",
            "title": "Safe",
            "screenshot": "frames\\safe.png",
        },
        {
            "type": "window_switch",
            "process": "drive.exe",
            "title": "Drive",
            "screenshot": "C:\\Users\\martinshin\\secret.png",
        },
        {
            "type": "window_switch",
            "process": "unc.exe",
            "title": "UNC",
            "screenshot": "\\\\server\\share\\secret.png",
        },
        {
            "type": "window_switch",
            "process": "root.exe",
            "title": "Root",
            "screenshot": "\\Users\\martinshin\\secret.png",
        },
        {
            "type": "window_switch",
            "process": "escape.exe",
            "title": "Escape",
            "screenshot": "..\\outside.png",
        },
    ]
    recording_path.write_text("\n".join(json.dumps(event) for event in events))

    compiler = SkillCompiler(recording_path)
    compiler.load()
    messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    image_blocks = [
        block
        for block in messages[0]["message"]["content"]
        if block["type"] == "image"
    ]
    assert len(image_blocks) == 1
    assert base64.b64decode(image_blocks[0]["source"]["data"]) == safe_frame.read_bytes()


def test_compile_sends_prompt_stream_to_agent_sdk():
    captured = {}

    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        captured["prompt"] = prompt
        captured["options"] = options
        yield AssistantMessage([SimpleNamespace(text="compiled skill")])

    fake_sdk = SimpleNamespace(
        AssistantMessage=AssistantMessage,
        ClaudeAgentOptions=ClaudeAgentOptions,
        query=fake_query,
    )

    compiler = SkillCompiler(FIXTURE)
    with patch.dict(sys.modules, {"claude_agent_sdk": fake_sdk}), \
            patch("teach_skill.compiler.agent.check_agent_sdk", return_value=True):
        result = asyncio.run(compiler.compile())

    assert result == "compiled skill"
    assert not isinstance(captured["prompt"], str)
    messages = asyncio.run(collect_async(captured["prompt"]))
    assert any(block["type"] == "image" for block in messages[0]["message"]["content"])
