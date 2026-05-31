import shutil
import subprocess
import sys
from pathlib import Path

from teach_skill.config import load_config
from teach_skill.doctor import format_doctor_result, run_doctor
from teach_skill.launcher_state import RecordingSummary, list_recordings
from teach_skill.recorder.lock import is_recording_active
from teach_skill.runtime_log import configure_logging, get_logger


def _run_cli_command(*args: str, new_console: bool = False) -> subprocess.Popen:
    kwargs = {}
    if new_console and sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    if getattr(sys, "frozen", False):
        command = [sys.executable, *args]
    else:
        command = [sys.executable, "-m", "teach_skill.cli", *args]
    get_logger("launcher").info("starting subprocess args=%s", args)
    return subprocess.Popen(command, **kwargs)


class SingleProcessRunner:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None

    def start(self, start_process) -> bool:
        if self.process is not None and self.process.poll() is None:
            return False
        self.process = start_process()
        return True


def _open_folder(path: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def export_recording(recording: RecordingSummary, destination_dir: Path | None = None) -> Path:
    destination = destination_dir or recording.path.parent
    recording_path = recording.path.resolve()
    destination_path = destination.resolve()
    if destination_path == recording_path or recording_path in destination_path.parents:
        raise ValueError("Export destination cannot be inside the recording folder.")

    destination.mkdir(parents=True, exist_ok=True)
    archive_base = destination / recording.name
    suffix = 1
    while archive_base.with_suffix(".zip").exists():
        archive_base = destination / f"{recording.name}-{suffix}"
        suffix += 1

    archive_path = shutil.make_archive(str(archive_base), "zip", recording.path)
    return Path(archive_path)


def try_export_recording(
    recording: RecordingSummary,
    destination_dir: Path,
    on_error,
) -> Path | None:
    try:
        return export_recording(recording, destination_dir)
    except (OSError, ValueError) as exc:
        on_error(str(exc))
        return None


class TeachSkillLauncher:
    def __init__(self) -> None:
        import tkinter as tk

        configure_logging("launch")
        self.logger = get_logger("launcher")
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Teach Skill Claude")
        self.root.geometry("620x460")

        self.config = load_config()
        self.recordings_root = Path(self.config["storage_path"])
        self.recordings: list[RecordingSummary] = []
        self.recorder_runner = SingleProcessRunner()

        self.status_var = tk.StringVar(value="Checking setup...")
        self.recordings_var = tk.StringVar(value="No recordings found.")

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        tk = self.tk
        frame = tk.Frame(self.root, padx=18, pady=18)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Teach Skill Claude", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=self.status_var, wraplength=560, justify="left").pack(
            anchor="w", pady=(8, 14)
        )

        button_row = tk.Frame(frame)
        button_row.pack(anchor="w", pady=(0, 14))
        tk.Button(button_row, text="Start Recording", command=self.start_recording).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(button_row, text="Compile Latest", command=self.compile_latest).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(button_row, text="Check Setup", command=self.show_doctor).pack(side=tk.LEFT, padx=(0, 8))

        file_row = tk.Frame(frame)
        file_row.pack(anchor="w", pady=(0, 14))
        tk.Button(file_row, text="Open Recordings", command=self.open_recordings).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(file_row, text="Export Latest", command=self.export_latest).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(file_row, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(frame, text="Recent recordings", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=self.recordings_var, justify="left", anchor="nw").pack(
            fill=tk.BOTH, expand=True, anchor="w", pady=(6, 0)
        )

    def refresh(self) -> None:
        doctor_result = run_doctor(config=self.config)
        self.logger.info("refresh status=%s", doctor_result.status)
        self.status_var.set(f"Setup status: {doctor_result.status}")
        self.recordings = list_recordings(self.recordings_root, limit=5)
        if not self.recordings:
            self.recordings_var.set("No recordings found yet.")
            return

        lines = [
            f"{recording.name} - {recording.frame_count} screenshot(s)"
            for recording in self.recordings
        ]
        self.recordings_var.set("\n".join(lines))

    def latest_recording(self) -> RecordingSummary | None:
        self.refresh()
        return self.recordings[0] if self.recordings else None

    def start_recording(self) -> None:
        from tkinter import messagebox

        result = run_doctor(config=self.config)
        if not result.can_record:
            self.logger.warning("start recording blocked status=%s", result.status)
            messagebox.showerror("Setup needed", "\n".join(format_doctor_result(result)))
            return
        started = self.recorder_runner.start(lambda: _run_cli_command("record"))
        if started:
            self.logger.info("recording process started")
            self.status_var.set("Recording started. Stop it from the tray icon, then refresh.")
        else:
            self.logger.warning("recording process already active")
            self.status_var.set("Recording is already running. Stop it from the tray icon first.")

    def compile_latest(self) -> None:
        from tkinter import messagebox

        result = run_doctor(config=self.config)
        if not result.can_compile:
            self.logger.warning("compile blocked status=%s", result.status)
            messagebox.showerror("Compile setup needed", "\n".join(format_doctor_result(result)))
            return
        if is_recording_active(self.recordings_root):
            self.logger.warning("compile blocked active_recording")
            messagebox.showinfo(
                "Recording in progress",
                "Stop the active recording before compiling a skill.",
            )
            return

        recording = self.latest_recording()
        if recording is None:
            messagebox.showinfo("No recording", "Record a workflow before compiling a skill.")
            return

        _run_cli_command("compile", str(recording.jsonl_path), new_console=True)
        self.logger.info("compile process started recording=%s", recording.jsonl_path)
        self.status_var.set(f"Compiling {recording.name}. Follow the prompts in the opened window.")

    def open_recordings(self) -> None:
        self.recordings_root.mkdir(parents=True, exist_ok=True)
        _open_folder(self.recordings_root)

    def export_latest(self) -> None:
        from tkinter import filedialog, messagebox

        if is_recording_active(self.recordings_root):
            self.logger.warning("export blocked active_recording")
            messagebox.showinfo(
                "Recording in progress",
                "Stop the active recording before exporting it.",
            )
            return

        recording = self.latest_recording()
        if recording is None:
            messagebox.showinfo("No recording", "Record a workflow before exporting.")
            return

        destination = filedialog.askdirectory(title="Choose export folder")
        if not destination:
            return

        archive_path = try_export_recording(
            recording,
            Path(destination),
            lambda message: messagebox.showerror("Export failed", message),
        )
        if archive_path is None:
            self.logger.warning("export failed recording=%s", recording.path)
            return
        self.logger.info("exported recording=%s archive=%s", recording.path, archive_path)
        messagebox.showinfo("Recording exported", f"Saved export to:\n{archive_path}")

    def show_doctor(self) -> None:
        from tkinter import messagebox

        result = run_doctor(config=self.config)
        messagebox.showinfo("Setup check", "\n".join(format_doctor_result(result)))
        self.refresh()

    def run(self) -> None:
        self.root.mainloop()


def launch_app() -> None:
    configure_logging("launch")
    TeachSkillLauncher().run()
