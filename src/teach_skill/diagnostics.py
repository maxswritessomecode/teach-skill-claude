import platform
import stat
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from teach_skill import __version__
from teach_skill.config import config_path
from teach_skill.runtime_log import log_dir


def _is_known_log_name(name: str) -> bool:
    if name == "teach-skill.log":
        return True
    prefix = "teach-skill.log."
    if not name.startswith(prefix):
        return False
    suffix = name.removeprefix(prefix)
    return suffix.isdigit() and 1 <= int(suffix) <= 5


def _safe_log_files() -> list[Path]:
    logs = log_dir()
    if not logs.is_dir():
        return []

    safe_files = []
    for path in logs.iterdir():
        if not _is_known_log_name(path.name):
            continue
        try:
            stat_result = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(stat_result.st_mode):
            safe_files.append(path)
    return safe_files


def diagnostics_text() -> str:
    lines = [
        "Teach Skill Claude diagnostics",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"version: {__version__}",
        f"python: {sys.version.split()[0]}",
        f"platform: {platform.platform()}",
        f"executable: {sys.executable}",
        f"config_path: {config_path()}",
        f"log_dir: {log_dir()}",
    ]
    return "\n".join(lines) + "\n"


def create_support_bundle(destination_dir: Path | None = None) -> Path:
    destination = destination_dir or (log_dir().parent / "support")
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_path = destination / f"teach-skill-support-{timestamp}.zip"

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("diagnostics.txt", diagnostics_text())
        for path in _safe_log_files():
            bundle.write(path, f"logs/{path.name}")

    return bundle_path
