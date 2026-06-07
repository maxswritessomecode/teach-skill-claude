import json
from pathlib import Path

DEFAULT_CONFIG = {
    "hotkey_toggle": "ctrl+shift+t",
    "hotkey_pause": "ctrl+shift+p",
    "storage_path": str(Path.home() / ".teach-skill" / "recordings"),
    "screenshot_resolution": "native",
    "privacy_filter": True,
    "capture_ui_context": True,
}


def config_dir() -> Path:
    return Path.home() / ".teach-skill"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if path.exists():
        with open(path) as f:
            stored = json.load(f)
        return {**DEFAULT_CONFIG, **stored}
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
