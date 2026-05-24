import json
from pathlib import Path
from teach_skill.recorder.writer import EventWriter


def test_write_event_creates_jsonl_file(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "recording_meta", "machine": "TEST-PC"})
    assert writer.jsonl_path.exists()


def test_write_event_appends_valid_json_lines(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "recording_meta", "machine": "TEST-PC"})
    writer.write_event({"type": "window_switch", "process": "chrome.exe", "title": "Test"})
    lines = writer.jsonl_path.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert "ts" in parsed
        assert "type" in parsed


def test_write_event_adds_timestamp_if_missing(tmp_path):
    writer = EventWriter(tmp_path)
    writer.write_event({"type": "window_switch", "process": "test.exe", "title": "Test"})
    line = json.loads(writer.jsonl_path.read_text().strip())
    assert "ts" in line
    assert "T" in line["ts"]


def test_write_event_preserves_existing_timestamp(tmp_path):
    writer = EventWriter(tmp_path)
    ts = "2026-05-24T10:30:00.000Z"
    writer.write_event({"type": "window_switch", "ts": ts, "process": "test.exe", "title": "Test"})
    line = json.loads(writer.jsonl_path.read_text().strip())
    assert line["ts"] == ts


def test_next_frame_path_increments(tmp_path):
    writer = EventWriter(tmp_path)
    p1 = writer.next_frame_path()
    p2 = writer.next_frame_path()
    assert p1.name == "0001.png"
    assert p2.name == "0002.png"
    assert p1.parent == writer.frames_dir


def test_frames_directory_created(tmp_path):
    writer = EventWriter(tmp_path)
    assert writer.frames_dir.exists()
    assert writer.frames_dir.is_dir()
