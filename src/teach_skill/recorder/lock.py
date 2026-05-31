import os
import uuid
from pathlib import Path


class RecordingAlreadyRunning(RuntimeError):
    pass


def _try_lock_fd(fd: int) -> bool:
    if os.name == "nt":
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock_fd(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return

    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


def is_recording_active(recordings_root: Path) -> bool:
    lock_path = recordings_root / ".recording.lock"
    if not lock_path.exists():
        return False

    fd = os.open(lock_path, os.O_RDWR)
    try:
        if not _try_lock_fd(fd):
            return True
        _unlock_fd(fd)
        return False
    finally:
        os.close(fd)


class RecorderLock:
    def __init__(self, recordings_root: Path):
        self.lock_path = recordings_root / ".recording.lock"
        self._fd: int | None = None
        self.token = f"{os.getpid()}:{uuid.uuid4().hex}"

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        if not _try_lock_fd(self._fd):
            os.close(self._fd)
            self._fd = None
            raise RecordingAlreadyRunning

        os.ftruncate(self._fd, 0)
        os.write(self._fd, self.token.encode("ascii"))
        os.fsync(self._fd)
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self._fd is None:
            return

        try:
            _unlock_fd(self._fd)
        finally:
            os.close(self._fd)
            self._fd = None
