import json
from pathlib import Path
from teach_skill.recorder.controller import RecorderController
from teach_skill.recorder.writer import EventWriter
from teach_skill.config import DEFAULT_CONFIG


def test_recorder_controller_streams_events(tmp_path):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    
    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    controller.on_clipboard_change("some payload")
    controller.stop_recording()
    
    lines = writer.jsonl_path.read_text().strip().split("\n")
    assert len(lines) == 4  # meta, window_switch, clipboard_text, session_end


def test_recorder_controller_emits_in_app_capture_after_stable_click(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    now = [1000.0]
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Workflow"},
    )

    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    now[0] += 6
    controller.on_click(10, 20, None, True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]
    captures = [event for event in events if event["type"] == "in_app_capture"]

    assert len(captures) == 1
    assert captures[0]["process"] == "chrome.exe"
    assert captures[0]["title"] == "Workflow"
    assert captures[0]["trigger"] == "click_after_5s"
    assert captures[0]["screenshot"].startswith("frames/")


def test_recorder_controller_rate_limits_in_app_capture(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    now = [1000.0]
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Workflow"},
    )

    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    now[0] += 6
    controller.on_click(10, 20, None, True)
    now[0] += 1
    controller.on_click(30, 40, None, True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events].count("in_app_capture") == 1


def test_click_after_unpolled_window_switch_records_window_switch_not_in_app_capture(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    now = [1000.0]
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "outlook.exe", "title": "Inbox"},
    )

    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    now[0] += 6
    controller.on_click(10, 20, None, True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events].count("in_app_capture") == 0
    assert events[-1]["type"] == "window_switch"
    assert events[-1]["process"] == "outlook.exe"
    assert events[-1]["title"] == "Inbox"
