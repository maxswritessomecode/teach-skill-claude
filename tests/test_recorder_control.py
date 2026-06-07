from teach_skill.recorder.control import (
    clear_stop_request,
    is_stop_requested,
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
