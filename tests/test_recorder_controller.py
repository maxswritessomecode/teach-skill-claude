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
    controller.on_press("Key.ctrl_l")
    controller.on_press("b")
    controller.on_release("Key.ctrl_l")
    controller.on_click(10, 20, None, False)
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


def test_recorder_controller_records_keyboard_shortcut_and_post_action_capture(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "EXCEL.EXE", "title": "Workbook.xlsx - Excel"},
    )

    controller.on_press("Key.ctrl_l")
    controller.on_press("b")
    controller.on_release("Key.ctrl_l")

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    shortcuts = [event for event in events if event["type"] == "keyboard_shortcut"]
    captures = [event for event in events if event["type"] == "post_action_capture"]

    assert shortcuts[0]["shortcut"] == "ctrl+b"
    assert shortcuts[0]["process"] == "EXCEL.EXE"
    assert captures[0]["trigger"] == "shortcut:ctrl+b"
    assert captures[0]["screenshot"].startswith("frames/")


def test_recorder_controller_does_not_record_shift_typing_as_shortcut(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, {**DEFAULT_CONFIG, "capture_raw_keystrokes": True})
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "WINWORD.EXE", "title": "Document.docx - Word"},
    )

    controller.on_window_switch({"process": "WINWORD.EXE", "title": "Document.docx - Word"})
    controller.on_press("Key.shift")
    controller.on_press("h")
    controller.on_release("Key.shift")
    controller.stop_recording()

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]

    assert [event for event in events if event["type"] == "keyboard_shortcut"] == []
    assert [event for event in events if event["type"] == "post_action_capture"] == []
    assert events[-1]["keys_typed"] == "h"


def test_post_action_capture_resamples_sensitive_active_window(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    active_windows = iter(
        [
            {"process": "chrome.exe", "title": "Workflow"},
            {"process": "chrome.exe", "title": "Okta sign in"},
        ]
    )
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: next(active_windows),
    )

    controller.on_click(42, 84, "Button.left", True)
    controller.on_click(42, 84, "Button.left", False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    captures = [event for event in events if event["type"] == "post_action_capture"]

    assert captures[0]["title"] == "[auth/login - redacted]"
    assert captures[0]["screenshot"] == "suppressed:auth_detected"
    assert "frame_id" not in captures[0]


def test_recorder_controller_records_post_click_capture(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "powerpnt.exe", "title": "Deck.pptx - PowerPoint"},
    )

    controller.on_click(42, 84, "Button.left", True)
    controller.on_click(42, 84, "Button.left", False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    captures = [event for event in events if event["type"] == "post_action_capture"]

    assert captures[0]["trigger"] == "click"
    assert captures[0]["process"] == "powerpnt.exe"
    assert captures[0]["screenshot"].startswith("frames/")


def test_recorder_controller_records_drag_selection_and_post_action_capture(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Web app"},
    )

    controller.on_click(10, 20, "Button.left", True)
    controller.on_move(80, 120)
    controller.on_click(100, 140, "Button.left", False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    drags = [event for event in events if event["type"] == "drag_select"]
    captures = [event for event in events if event["type"] == "post_action_capture"]

    assert drags[0]["start"] == [10, 20]
    assert drags[0]["end"] == [100, 140]
    assert captures[-1]["trigger"] == "drag_select"


def test_drag_selection_redacts_sensitive_window_details(tmp_path, monkeypatch):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Okta sign in"},
    )
    controller.on_window_switch({"process": "chrome.exe", "title": "Okta sign in"})

    controller.on_click(10, 20, "Button.left", True)
    controller.on_move(80, 120)
    controller.on_click(100, 140, "Button.left", False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    drag = [event for event in events if event["type"] == "drag_select"][0]

    assert drag["title"] == "[auth/login - redacted]"
    assert drag["details_redacted"] == "sensitive_title"
    assert "start" not in drag
    assert "end" not in drag
    assert "button" not in drag


def test_shortcut_post_action_capture_resamples_sensitive_active_window(
    tmp_path,
    monkeypatch,
):
    writer = EventWriter(tmp_path)
    controller = RecorderController(writer, DEFAULT_CONFIG)
    controller.on_window_switch({"process": "chrome.exe", "title": "Workflow"})
    monkeypatch.setattr(
        "teach_skill.recorder.controller.get_active_window_info",
        lambda: {"process": "chrome.exe", "title": "Okta sign in"},
    )

    controller.on_press("Key.ctrl_l")
    controller.on_press("b")

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    captures = [event for event in events if event["type"] == "post_action_capture"]

    assert captures[0]["title"] == "[auth/login - redacted]"
    assert captures[0]["screenshot"] == "suppressed:auth_detected"


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
    controller.on_click(10, 20, None, False)
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
        "post_action_capture",
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
    controller.on_click(10, 20, None, False)

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
    controller.on_click(42, 84, "Button.left", False)

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
    controller.on_click(42, 84, "Button.left", False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events] == [
        "recording_meta",
        "window_switch",
        "click",
        "post_action_capture",
    ]
    assert events[-1]["process"] == "chrome.exe"
    assert events[-1]["title"] == "Workflow"
    assert events[-2]["x"] == 42
    assert events[-2]["y"] == 84


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
    controller.on_click(42, 84, "Button.left", False)

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
    controller.on_click(10, 20, None, False)
    now[0] += 1
    controller.on_click(30, 40, None, True)
    controller.on_click(30, 40, None, False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events].count("in_app_capture") == 1
    clicks = [event for event in events if event["type"] == "click"]
    assert len(clicks) == 2
    assert clicks[0]["screenshot_frame_id"] == "0002"
    assert clicks[1]["screenshot_frame_id"] == "0003"


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
    controller.on_click(10, 20, None, False)

    events = [
        json.loads(line)
        for line in writer.jsonl_path.read_text().strip().split("\n")
    ]

    assert [event["type"] for event in events].count("in_app_capture") == 0
    assert events[-3]["type"] == "window_switch"
    assert events[-3]["process"] == "outlook.exe"
    assert events[-3]["title"] == "Inbox"
    assert events[-2]["type"] == "click"
    assert events[-2]["process"] == "outlook.exe"
    assert events[-2]["title"] == "Inbox"
    assert events[-2]["x"] == 10
    assert events[-2]["y"] == 20
    assert events[-2]["screenshot_frame_id"] == "0002"
    assert events[-1]["type"] == "post_action_capture"
