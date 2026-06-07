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


def test_recorder_controller_ignores_capture_while_paused(tmp_path):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    controller.pause_recording()
    controller.on_window_switch({"process": "chrome.exe", "title": "Ignore me"})
    controller.on_click(10, 20, None, True)
    controller.on_clipboard_change("secret")
    controller.resume_recording()

    events = [
        json.loads(line)
        for line in (tmp_path / "recording.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["type"] for event in events] == [
        "recording_meta",
        "recording_paused",
        "recording_resumed",
    ]


def test_pause_recording_closes_active_session_before_pause_gap(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    now = [1000.0]
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Workflow"},
    )
    controller = RecorderController(writer, DEFAULT_CONFIG)

    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    controller.on_click(10, 20, None, True)
    now[0] += 2
    controller.pause_recording()
    now[0] += 30
    controller.stop_recording()

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    session_ends = [event for event in events if event["type"] == "session_end"]

    assert [event["type"] for event in events] == [
        "recording_meta",
        "window_switch",
        "click",
        "session_end",
        "recording_paused",
    ]
    assert len(session_ends) == 1
    assert session_ends[0]["duration_s"] == 2
    assert session_ends[0]["click_count"] == 1


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


def test_recorder_controller_writes_structured_click_event(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    now = [1000.0]
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Workflow"},
    )

    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    now[0] += 1
    controller.on_click(42, 84, "Button.left", True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]
    clicks = [event for event in events if event["type"] == "click"]

    assert len(clicks) == 1
    click = clicks[0]
    assert click["process"] == "chrome.exe"
    assert click["title"] == "Workflow"
    assert click["x"] == 42
    assert click["y"] == 84
    assert click["button"] == "Button.left"
    assert click["screenshot_frame_id"] == "0001"
    assert click["screenshot_frame_path"] == "frames/0001.png"
    assert "ts" in click


def test_first_click_samples_active_window_and_records_click(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Workflow"},
    )

    controller.on_click(42, 84, "Button.left", True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events] == [
        "recording_meta",
        "window_switch",
        "click",
    ]
    assert events[-1]["process"] == "chrome.exe"
    assert events[-1]["title"] == "Workflow"
    assert events[-1]["x"] == 42
    assert events[-1]["y"] == 84


def test_click_event_omits_frame_after_sensitive_screenshot_is_suppressed(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)

    now = [1000.0]
    active_window = {"process": "chrome.exe", "title": "Workflow"}
    monkeypatch.setattr("teach_skill.recorder.controller.time.time", lambda: now[0])
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: active_window,
    )

    controller.on_window_switch(active_window)
    active_window = {"process": "chrome.exe", "title": "Okta sign in"}
    now[0] += 6
    controller.on_click(42, 84, "Button.left", True)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]
    click = [event for event in events if event["type"] == "click"][0]

    assert click["title"] == "[auth/login - redacted]"
    assert click["details_redacted"] == "sensitive_title"
    assert "x" not in click
    assert "y" not in click
    assert "button" not in click
    assert "screenshot_frame_id" not in click
    assert "screenshot_frame_path" not in click


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
    clicks = [event for event in events if event["type"] == "click"]
    assert len(clicks) == 2
    assert clicks[0]["screenshot_frame_id"] == "0002"
    assert clicks[1]["screenshot_frame_id"] == "0002"


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
    assert events[-2]["type"] == "window_switch"
    assert events[-2]["process"] == "outlook.exe"
    assert events[-2]["title"] == "Inbox"
    assert events[-1]["type"] == "click"
    assert events[-1]["process"] == "outlook.exe"
    assert events[-1]["title"] == "Inbox"
    assert events[-1]["x"] == 10
    assert events[-1]["y"] == 20
    assert events[-1]["screenshot_frame_id"] == "0002"
