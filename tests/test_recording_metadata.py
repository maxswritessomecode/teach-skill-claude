from teach_skill.recording_metadata import (
    RecordingInfo,
    load_recording_info,
    save_recording_title,
)


def test_save_and_load_recording_title(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    info = save_recording_title(recording_dir, "Excel pricing cleanup")

    assert info == RecordingInfo(title="Excel pricing cleanup")
    assert load_recording_info(recording_dir).title == "Excel pricing cleanup"


def test_load_recording_info_ignores_missing_or_malformed_file(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    assert load_recording_info(recording_dir).title is None

    (recording_dir / "recording-info.json").write_text("{bad json", encoding="utf-8")

    assert load_recording_info(recording_dir).title is None


def test_save_recording_title_rejects_empty_or_multiline_titles(tmp_path):
    recording_dir = tmp_path / "recording_20260607_120000"
    recording_dir.mkdir()

    for title in ["", "   ", "first\nsecond"]:
        try:
            save_recording_title(recording_dir, title)
        except ValueError as exc:
            assert "Recording title" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
