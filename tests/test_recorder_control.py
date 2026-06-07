from teach_skill.recorder.control import (
    clear_pause_request,
    clear_resume_request,
    clear_stop_request,
    is_pause_requested,
    is_recording_paused,
    is_resume_requested,
    is_stop_requested,
    mark_recording_paused,
    mark_recording_resumed,
    request_pause,
    request_resume,
    request_stop,
    stop_request_path,
)


def test_request_stop_creates_recording_stop_signal(tmp_path):
    path = request_stop(tmp_path)

    assert path == stop_request_path(tmp_path)
    assert is_stop_requested(tmp_path) is True
    assert "stop requested" in path.read_text(encoding="utf-8")


def test_clear_stop_request_removes_signal_idempotently(tmp_path):
    request_stop(tmp_path)

    clear_stop_request(tmp_path)
    clear_stop_request(tmp_path)

    assert is_stop_requested(tmp_path) is False


def test_pause_resume_request_and_state_files(tmp_path):
    request_pause(tmp_path)
    assert is_pause_requested(tmp_path) is True

    clear_pause_request(tmp_path)
    assert is_pause_requested(tmp_path) is False

    mark_recording_paused(tmp_path)
    assert is_recording_paused(tmp_path) is True

    request_resume(tmp_path)
    assert is_resume_requested(tmp_path) is True

    clear_resume_request(tmp_path)
    mark_recording_resumed(tmp_path)
    assert is_resume_requested(tmp_path) is False
    assert is_recording_paused(tmp_path) is False
