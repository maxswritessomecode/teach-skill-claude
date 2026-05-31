import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from teach_skill.config import config_dir, load_config


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    message: str
    required_for: tuple[str, ...]
    fix: str = ""


@dataclass(frozen=True)
class DoctorResult:
    status: str
    checks: list[Check]
    can_record: bool
    can_compile: bool


def evaluate_checks(checks: Iterable[Check]) -> DoctorResult:
    check_list = list(checks)
    can_record = all(
        check.ok for check in check_list if "record" in check.required_for
    )
    can_compile = can_record and all(
        check.ok for check in check_list if "compile" in check.required_for
    )

    if not can_record:
        status = "Needs setup"
    elif not can_compile:
        status = "Can record, but cannot compile yet"
    else:
        status = "Ready"

    return DoctorResult(
        status=status,
        checks=check_list,
        can_record=can_record,
        can_compile=can_compile,
    )


def _default_command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _default_import_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _folder_check(name: str, path: Path, required_for: tuple[str, ...]) -> Check:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return Check(
            name,
            False,
            f"Cannot create {path}: {exc}",
            required_for=required_for,
            fix="Choose a writable folder or run setup again.",
        )

    if not path.is_dir():
        return Check(
            name,
            False,
            f"{path} is not a folder",
            required_for=required_for,
            fix="Choose a writable folder or run setup again.",
        )

    return Check(name, True, str(path), required_for=required_for)


def run_doctor(
    *,
    config: dict | None = None,
    python_version: tuple[int, int] | None = None,
    platform: str | None = None,
    command_exists: Callable[[str], bool] | None = None,
    import_exists: Callable[[str], bool] | None = None,
) -> DoctorResult:
    config = load_config() if config is None else config
    version = python_version or (sys.version_info.major, sys.version_info.minor)
    current_platform = platform or sys.platform
    has_command = command_exists or _default_command_exists
    has_import = import_exists or _default_import_exists

    claude_found = has_command("claude")
    agent_sdk_found = has_import("claude_agent_sdk")

    checks = [
        Check(
            "Operating system",
            current_platform == "win32",
            "Windows" if current_platform == "win32" else "Recording is Windows-only",
            required_for=("record",),
            fix="Run recording on Windows 10 or Windows 11.",
        ),
        Check(
            "Python",
            version >= (3, 10),
            f"Python {version[0]}.{version[1]}",
            required_for=("record",),
            fix="Install Python 3.10 or newer.",
        ),
        _folder_check("Config folder", config_dir(), required_for=("record",)),
        _folder_check(
            "Recordings folder",
            Path(config.get("storage_path", Path.home() / ".teach-skill" / "recordings")),
            required_for=("record",),
        ),
        Check(
            "Claude Code",
            claude_found,
            "Found" if claude_found else "Not found",
            required_for=("compile",),
            fix="Install Claude Code, sign in, then reopen Teach Skill Claude.",
        ),
        Check(
            "Agent SDK",
            agent_sdk_found,
            "Installed" if agent_sdk_found else "Not installed",
            required_for=("compile",),
            fix="Run the installer again to install Python dependencies.",
        ),
    ]
    return evaluate_checks(checks)


def format_doctor_result(result: DoctorResult) -> list[str]:
    lines = [f"Setup status: {result.status}"]
    for check in result.checks:
        marker = "OK" if check.ok else "NEEDS ATTENTION"
        lines.append(f"[{marker}] {check.name}: {check.message}")
        if not check.ok and check.fix:
            lines.append(f"  Fix: {check.fix}")
    return lines
