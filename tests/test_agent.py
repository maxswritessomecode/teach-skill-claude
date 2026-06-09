import asyncio
import base64
import json
import random
import sys
from io import BytesIO
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk, save_skill


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


def test_compiler_rejects_nonpositive_max_image_edge():
    compiler = SkillCompiler(FIXTURE, compile_max_image_edge=0)
    assert compiler.compile_max_image_edge == 1568


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


def test_compiler_prompt_stream_labels_screenshot_image_blocks():
    compiler = SkillCompiler(FIXTURE)
    compiler.load()

    messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))
    content = messages[0]["message"]["content"]

    labels = [
        block["text"]
        for block in content
        if block["type"] == "text" and block["text"].startswith("Screen ")
    ]
    assert labels == [
        "Screen 0001: frames/0001.png",
        "Screen 0002: frames/0002.png",
        "Screen 0003: frames/0003.png",
        "Screen 0004: frames/0004.png",
    ]


def test_build_image_block_downscales_images_before_encoding(tmp_path):
    frame_path = tmp_path / "large.png"
    rng = random.Random(0)
    pixels = bytes(rng.randrange(256) for _ in range(300 * 200 * 3))
    Image.frombytes("RGB", (300, 200), pixels).save(frame_path)
    original_bytes = frame_path.read_bytes()

    compiler = SkillCompiler(FIXTURE, compile_max_image_edge=64)
    block = compiler.build_image_block(frame_path, "image/png")
    decoded = base64.b64decode(block["source"]["data"])
    image = Image.open(BytesIO(decoded))

    assert max(image.size) <= 64
    assert len(decoded) < len(original_bytes)
    assert frame_path.read_bytes() == original_bytes


def test_compiler_prompt_stream_skips_unsafe_missing_and_non_image_screenshots(tmp_path):
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

    labels = [
        block["text"]
        for block in messages[0]["message"]["content"]
        if block["type"] == "text" and block["text"].startswith("Screen ")
    ]
    assert labels == ["Screen safe: frames/safe.png"]


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


def test_compile_returns_streamed_text_when_sdk_raises_success_result():
    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        yield AssistantMessage([SimpleNamespace(text="compiled skill")])
        raise Exception("Claude Code returned an error result: success")

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


def test_compile_rejects_request_too_large_as_skill_text():
    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        yield AssistantMessage([SimpleNamespace(text="Request too large (max 32MB). Try with a smaller file.")])

    fake_sdk = SimpleNamespace(
        AssistantMessage=AssistantMessage,
        ClaudeAgentOptions=ClaudeAgentOptions,
        query=fake_query,
    )

    compiler = SkillCompiler(FIXTURE)
    with patch.dict(sys.modules, {"claude_agent_sdk": fake_sdk}), \
            patch("teach_skill.compiler.agent.check_agent_sdk", return_value=True):
        try:
            asyncio.run(compiler.compile())
        except RuntimeError as exc:
            assert "Request too large" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError")


def test_compile_rejects_api_error_as_skill_text():
    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        yield AssistantMessage(
            [
                SimpleNamespace(
                    text=(
                        "API Error: 500 Internal server error. "
                        "This is a server-side issue, usually temporary."
                    )
                )
            ]
        )

    fake_sdk = SimpleNamespace(
        AssistantMessage=AssistantMessage,
        ClaudeAgentOptions=ClaudeAgentOptions,
        query=fake_query,
    )

    compiler = SkillCompiler(FIXTURE)
    with patch.dict(sys.modules, {"claude_agent_sdk": fake_sdk}), \
            patch("teach_skill.compiler.agent.check_agent_sdk", return_value=True):
        try:
            asyncio.run(compiler.compile())
        except RuntimeError as exc:
            assert "API Error: 500" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError")


def test_prompt_stream_limits_attached_screenshot_payload(tmp_path):
    recording_dir = tmp_path / "recording_20260606_230930"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"x" * 120
    events = [{"type": "recording_meta", "machine": "X"}]
    for index in range(1, 7):
        frame_name = f"{index:04d}.png"
        (frames_dir / frame_name).write_bytes(image_bytes)
        events.append(
            {
                "type": "window_switch",
                "process": "EXCEL.EXE",
                "title": "Workbook.xlsx - Excel",
                "screenshot": f"frames/{frame_name}",
                "frame_id": f"{index:04d}",
            }
        )
    recording_path = recording_dir / "recording.jsonl"
    recording_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    compiler = SkillCompiler(recording_path)
    compiler.load()

    with patch("teach_skill.compiler.agent.MAX_SCREENSHOT_PAYLOAD_BYTES", 500):
        messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    image_blocks = [
        block
        for block in messages[0]["message"]["content"]
        if block["type"] == "image"
    ]
    text_blocks = [
        block["text"]
        for block in messages[0]["message"]["content"]
        if block["type"] == "text"
    ]

    assert len(image_blocks) < 6
    assert any("Screenshots omitted" in text for text in text_blocks)


def test_prompt_stream_trims_by_frame_value_and_preserves_chronological_order(tmp_path):
    recording_dir = tmp_path / "recording_20260609_090000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    frame_names = ["0001.png", "0002.png", "0003.png"]
    colors = ["red", "green", "blue"]
    for frame_name, color in zip(frame_names, colors):
        Image.new("RGB", (2, 2), color).save(frames_dir / frame_name)

    events = [
        {"type": "recording_meta", "machine": "X"},
        {
            "type": "window_switch",
            "process": "EXCEL.EXE",
            "title": "Workbook.xlsx - Excel",
            "screenshot": "frames/0001.png",
            "frame_id": "0001",
        },
        {
            "type": "post_action_capture",
            "process": "EXCEL.EXE",
            "title": "Workbook.xlsx - Excel",
            "screenshot": "frames/0002.png",
            "frame_id": "0002",
            "ui_context": {"name": "Bold", "control_type": "Button"},
        },
        {
            "type": "click",
            "process": "EXCEL.EXE",
            "title": "Workbook.xlsx - Excel",
            "screenshot": "frames/0003.png",
            "frame_id": "0003",
        },
    ]
    recording_path = recording_dir / "recording.jsonl"
    recording_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    keep_budget = sum(
        ((frames_dir / frame_name).stat().st_size + 2) // 3 * 4
        for frame_name in ("0001.png", "0003.png")
    )

    compiler = SkillCompiler(recording_path)
    compiler.load()

    with patch("teach_skill.compiler.agent.MAX_SCREENSHOT_PAYLOAD_BYTES", keep_budget):
        messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    labels = [
        block["text"]
        for block in messages[0]["message"]["content"]
        if block["type"] == "text" and block["text"].startswith("Screen ")
    ]

    assert labels == [
        "Screen 0001: frames/0001.png",
        "Screen 0003: frames/0003.png",
    ]
    assert any(
        block["type"] == "text" and "Screenshots omitted: 1" in block["text"]
        for block in messages[0]["message"]["content"]
    )


def test_prompt_stream_does_not_force_last_frame_over_payload_budget(tmp_path):
    recording_dir = tmp_path / "recording_20260609_100000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    rng = random.Random(1)
    for frame_name in ("0001.png", "0002.png"):
        pixels = bytes(rng.randrange(256) for _ in range(200 * 200 * 3))
        Image.frombytes("RGB", (200, 200), pixels).save(frames_dir / frame_name)

    events = [
        {"type": "recording_meta", "machine": "X"},
        {
            "type": "window_switch",
            "process": "EXCEL.EXE",
            "title": "Workbook.xlsx - Excel",
            "screenshot": "frames/0001.png",
            "frame_id": "0001",
        },
        {
            "type": "post_action_capture",
            "process": "EXCEL.EXE",
            "title": "Workbook.xlsx - Excel",
            "screenshot": "frames/0002.png",
            "frame_id": "0002",
        },
    ]
    recording_path = recording_dir / "recording.jsonl"
    recording_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    first_budget = ((frames_dir / "0001.png").stat().st_size + 2) // 3 * 4

    compiler = SkillCompiler(recording_path)
    compiler.load()

    with patch("teach_skill.compiler.agent.MAX_SCREENSHOT_PAYLOAD_BYTES", first_budget):
        messages = asyncio.run(collect_async(compiler.iter_prompt_messages()))

    image_blocks = [
        block
        for block in messages[0]["message"]["content"]
        if block["type"] == "image"
    ]
    labels = [
        block["text"]
        for block in messages[0]["message"]["content"]
        if block["type"] == "text" and block["text"].startswith("Screen ")
    ]
    total_encoded_bytes = sum(
        len(block["source"]["data"].encode("ascii"))
        for block in image_blocks
    )

    assert labels == ["Screen 0001: frames/0001.png"]
    assert total_encoded_bytes <= first_budget


def test_compile_wraps_sdk_exception_without_traceback():
    class AssistantMessage:
        pass

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        raise Exception("Claude Code returned an error result: success")
        yield

    fake_sdk = SimpleNamespace(
        AssistantMessage=AssistantMessage,
        ClaudeAgentOptions=ClaudeAgentOptions,
        query=fake_query,
    )

    compiler = SkillCompiler(FIXTURE)
    with patch.dict(sys.modules, {"claude_agent_sdk": fake_sdk}), \
            patch("teach_skill.compiler.agent.check_agent_sdk", return_value=True):
        try:
            asyncio.run(compiler.compile())
        except RuntimeError as exc:
            assert "Agent SDK compile failed" in str(exc)
            assert "Claude Code returned an error result: success" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError")


def test_save_skill_writes_utf8_markdown_on_windows_default_encoding(
    tmp_path,
    monkeypatch,
):
    original_write_text = Path.write_text

    def write_text_with_windows_default_encoding(
        self,
        data,
        encoding=None,
        errors=None,
        newline=None,
    ):
        if encoding is None:
            data.encode("cp1252")
        return original_write_text(
            self,
            data,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "write_text", write_text_with_windows_default_encoding)

    skill_text = "# Download Rates\n\nOpen the report → verify the saved file.\n"
    skill_path = save_skill(skill_text, "downloadrates", global_save=False)

    assert skill_path.read_text(encoding="utf-8") == skill_text
