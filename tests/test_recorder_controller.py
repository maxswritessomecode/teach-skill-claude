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
