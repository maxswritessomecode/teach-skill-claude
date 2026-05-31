import os
from unittest.mock import patch

import pytest

from teach_skill.recorder.lock import RecorderLock, RecordingAlreadyRunning, is_recording_active


def test_recorder_lock_writes_owner_token_and_leaves_lock_file(tmp_path):
    lock_path = tmp_path / ".recording.lock"

    with RecorderLock(tmp_path):
        assert lock_path.read_text(encoding="utf-8").startswith(f"{os.getpid()}:")

    assert lock_path.exists()


def test_recorder_lock_blocks_when_exclusive_lock_is_unavailable(tmp_path):
    lock_path = tmp_path / ".recording.lock"
    lock_path.write_text("other", encoding="utf-8")

    with (
        patch("teach_skill.recorder.lock._try_lock_fd", return_value=False),
        pytest.raises(RecordingAlreadyRunning),
    ):
        with RecorderLock(tmp_path):
            pass

    assert lock_path.read_text(encoding="utf-8") == "other"


def test_is_recording_active_reports_held_lock(tmp_path):
    assert is_recording_active(tmp_path) is False

    with RecorderLock(tmp_path):
        assert is_recording_active(tmp_path) is True

    assert is_recording_active(tmp_path) is False


def test_recorder_lock_reuses_leftover_file_when_exclusive_lock_is_available(tmp_path):
    lock_path = tmp_path / ".recording.lock"
    lock_path.write_text("leftover", encoding="utf-8")

    with RecorderLock(tmp_path):
        assert lock_path.read_text(encoding="utf-8").startswith(f"{os.getpid()}:")

    assert lock_path.exists()


def test_recorder_lock_only_removes_lock_it_owns(tmp_path):
    lock_path = tmp_path / ".recording.lock"

    with RecorderLock(tmp_path):
        lock_path.write_text("other-process-token", encoding="utf-8")

    assert lock_path.read_text(encoding="utf-8") == "other-process-token"
