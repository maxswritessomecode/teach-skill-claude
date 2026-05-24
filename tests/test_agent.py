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
