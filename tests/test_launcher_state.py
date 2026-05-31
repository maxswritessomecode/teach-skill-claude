import os
from pathlib import Path

from teach_skill.launcher_state import list_recordings


def test_list_recordings_returns_recording_folders_newest_first(tmp_path):
    older = tmp_path / "recording_20260531_090000"
    newer = tmp_path / "recording_20260531_100000"
    ignored = tmp_path / "notes"

    for folder in (older, newer, ignored):
        folder.mkdir()
    (older / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    (newer / "recording.jsonl").write_text("{}\n", encoding="utf-8")
    (newer / "frames").mkdir()
    (newer / "frames" / "0001.png").write_bytes(b"fake")
    (newer / "frames" / "notes.txt").write_text("not a screenshot", encoding="utf-8")

    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))

    recordings = list_recordings(tmp_path)

    assert [recording.name for recording in recordings] == [
        "recording_20260531_100000",
        "recording_20260531_090000",
    ]
    assert recordings[0].frame_count == 1
    assert recordings[0].jsonl_path == newer / "recording.jsonl"


def test_list_recordings_returns_empty_list_when_root_missing(tmp_path):
    assert list_recordings(tmp_path / "missing") == []


def test_list_recordings_returns_empty_list_when_root_is_file(tmp_path):
    recordings_root = tmp_path / "recordings"
    recordings_root.write_text("not a folder", encoding="utf-8")

    assert list_recordings(recordings_root) == []
