from dataclasses import dataclass
from pathlib import Path
import subprocess

from teach_skill.config import load_config
from teach_skill.diagnostics import create_support_bundle
from teach_skill.doctor import DoctorResult, run_doctor
from teach_skill.launcher import SingleProcessRunner, _open_folder, _run_cli_command
from teach_skill.launcher_state import RecordingSummary, list_recordings
from teach_skill.recorder.control import request_stop
from teach_skill.recorder.lock import is_recording_active
from teach_skill.review import CompileSelection, load_recording_review
from teach_skill.runtime_log import log_path


@dataclass(frozen=True)
class AppStatus:
    setup_status: str
    can_record: bool
    can_compile: bool
    recording_active: bool
    state_label: str


def build_app_status(doctor_result: DoctorResult, recording_active: bool) -> AppStatus:
    if recording_active:
        state_label = "Recording"
    elif doctor_result.can_record:
        state_label = "Can record"
    else:
        state_label = "Needs setup"

    return AppStatus(
        setup_status=doctor_result.status,
        can_record=doctor_result.can_record,
        can_compile=doctor_result.can_compile,
        recording_active=recording_active,
        state_label=state_label,
    )


class QtAppServices:
    def __init__(self, recordings_root: Path | None = None):
        self.config = dict(load_config())
        self.recordings_root = Path(recordings_root or self.config["storage_path"])
        self.config["storage_path"] = str(self.recordings_root)
        self.recorder_runner = SingleProcessRunner()

    def status(self) -> AppStatus:
        doctor_result = run_doctor(config=self.config)
        recording_active = is_recording_active(self.recordings_root)
        return build_app_status(doctor_result, recording_active)

    def recent_recordings(self, limit: int = 10) -> list[RecordingSummary]:
        return list_recordings(self.recordings_root, limit=limit)

    def start_recording(self) -> bool:
        return self.recorder_runner.start(lambda: _run_cli_command("record"))

    def stop_recording(self) -> bool:
        if not is_recording_active(self.recordings_root):
            return False
        request_stop(self.recordings_root)
        return True

    def compile_recording(self, recording: RecordingSummary) -> subprocess.Popen:
        recording_path = recording.path.resolve()
        recordings_root = self.recordings_root.resolve()
        recording_path.relative_to(recordings_root)
        if is_recording_active(recordings_root):
            raise RuntimeError("Stop the active recording before compiling.")

        review = load_recording_review(recording.path)
        filtered_path = CompileSelection.from_review(review).write_filtered_jsonl(
            recording.path / "reviewed-recording.jsonl"
        )
        return _run_cli_command("compile", str(filtered_path), new_console=True)

    def open_recordings_folder(self) -> None:
        self.recordings_root.mkdir(parents=True, exist_ok=True)
        _open_folder(self.recordings_root)

    def open_logs_folder(self) -> None:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _open_folder(path.parent)

    def create_support_bundle(self) -> Path:
        return create_support_bundle()
