import json
from pathlib import Path
from teach_skill.compiler.parser import parse_recording, Recording


FIXTURE = Path(__file__).parent / "fixtures" / "sample_recording.jsonl"


def test_parse_recording_returns_recording():
    rec = parse_recording(FIXTURE)
    assert isinstance(rec, Recording)


def test_parse_recording_extracts_meta():
    rec = parse_recording(FIXTURE)
    assert rec.meta["machine"] == "DESKTOP-TEST"
    assert rec.meta["os"] == "Windows 11"


def test_parse_recording_collects_events():
    rec = parse_recording(FIXTURE)
    assert len(rec.events) == 8  # all events except recording_meta


def test_parse_recording_collects_screenshot_paths():
    rec = parse_recording(FIXTURE)
    assert len(rec.screenshot_paths) == 4
    assert all(p.endswith(".png") for p in rec.screenshot_paths)


def test_parse_recording_extracts_workflow_steps():
    rec = parse_recording(FIXTURE)
    steps = rec.workflow_steps()
    assert len(steps) == 3  # 3 session_end events = 3 workflow steps
    assert steps[0]["process"] == "chrome.exe"
    assert steps[0]["click_count"] == 12


def test_parse_recording_handles_empty_file(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    rec = parse_recording(empty)
    assert rec.meta == {}
    assert rec.events == []


def test_parse_recording_skips_malformed_lines(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"type": "recording_meta", "machine": "X"}\nnot json\n{"type": "window_switch"}\n')
    rec = parse_recording(bad)
    assert rec.meta["machine"] == "X"
    assert len(rec.events) == 1


def test_recording_timeline_text():
    rec = parse_recording(FIXTURE)
    text = rec.timeline_text()
    assert "chrome.exe" in text
    assert "outlook.exe" in text
    assert "Google Sheets" in text
