import json
from pathlib import Path
from teach_skill.config import load_config, save_config, DEFAULT_CONFIG


def test_load_config_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    custom = {**DEFAULT_CONFIG, "privacy_filter": False}
    save_config(custom)
    loaded = load_config()
    assert loaded["privacy_filter"] is False


def test_load_config_fills_missing_keys(tmp_path, monkeypatch):
    monkeypatch.setattr("teach_skill.config.config_dir", lambda: tmp_path)
    partial = {"hotkey_toggle": "ctrl+alt+r"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(partial))
    loaded = load_config()
    assert loaded["hotkey_toggle"] == "ctrl+alt+r"
    assert loaded["privacy_filter"] == DEFAULT_CONFIG["privacy_filter"]


def test_default_config_has_required_keys():
    required = ["hotkey_toggle", "hotkey_pause", "storage_path",
                 "screenshot_resolution", "screenshot_capture_mode",
                 "compile_max_image_edge", "privacy_filter"]
    for key in required:
        assert key in DEFAULT_CONFIG

    assert DEFAULT_CONFIG["screenshot_capture_mode"] == "adaptive"
    assert DEFAULT_CONFIG["compile_max_image_edge"] == 1568
