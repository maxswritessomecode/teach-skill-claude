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


def test_recording_timeline_text_includes_structured_clicks(tmp_path):
    recording = tmp_path / "recording.jsonl"
    recording.write_text(
        "\n".join(
            [
                json.dumps({"type": "recording_meta", "machine": "X"}),
                json.dumps(
                    {
                        "ts": "2026-05-28T15:00:00Z",
                        "type": "window_switch",
                        "process": "chrome.exe",
                        "title": "Workflow",
                        "screenshot": "frames/0001.png",
                        "frame_id": "0001",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-05-28T15:00:01Z",
                        "type": "click",
                        "process": "chrome.exe",
                        "title": "Workflow",
                        "x": 42,
                        "y": 84,
                        "button": "Button.left",
                        "screenshot_frame_id": "0001",
                    }
                ),
            ]
        )
    )

    text = parse_recording(recording).timeline_text()

    assert "[2026-05-28T15:00:01Z] Clicked Button.left at (42, 84)" in text
    assert "chrome.exe" in text
    assert "screen: 0001" in text


def test_recording_timeline_text_describes_missing_click_button(tmp_path):
    recording = tmp_path / "recording.jsonl"
    recording.write_text(
        json.dumps(
            {
                "ts": "2026-05-28T15:00:01Z",
                "type": "click",
                "process": "chrome.exe",
                "title": "Workflow",
                "x": 42,
                "y": 84,
                "button": None,
            }
        )
    )

    text = parse_recording(recording).timeline_text()

    assert "Clicked unknown button at (42, 84)" in text
    assert "Clicked None" not in text


def test_recording_timeline_text_includes_generic_action_events(tmp_path):
    recording = tmp_path / "recording.jsonl"
    recording.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-06-07T15:00:00Z",
                        "type": "keyboard_shortcut",
                        "process": "EXCEL.EXE",
                        "title": "Workbook.xlsx - Excel",
                        "shortcut": "ctrl+b",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-06-07T15:00:01Z",
                        "type": "drag_select",
                        "process": "EXCEL.EXE",
                        "title": "Workbook.xlsx - Excel",
                        "start": [10, 20],
                        "end": [100, 140],
                        "button": "Button.left",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-06-07T15:00:02Z",
                        "type": "post_action_capture",
                        "process": "EXCEL.EXE",
                        "title": "Workbook.xlsx - Excel",
                        "trigger": "shortcut:ctrl+b",
                        "screenshot": "frames/0002.png",
                        "frame_id": "0002",
                    }
                ),
            ]
        )
    )

    text = parse_recording(recording).timeline_text()

    assert "Pressed shortcut ctrl+b" in text
    assert "Dragged Button.left from (10, 20) to (100, 140)" in text
    assert "Post-action screen after shortcut:ctrl+b" in text
    assert "screen: 0002" in text
