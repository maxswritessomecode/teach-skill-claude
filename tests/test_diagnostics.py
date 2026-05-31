import zipfile

from teach_skill.diagnostics import create_support_bundle


def test_create_support_bundle_includes_logs_and_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    logs_dir = tmp_path / ".teach-skill" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "teach-skill.log").write_text("log line\n", encoding="utf-8")

    bundle_path = create_support_bundle(destination_dir=tmp_path / "bundles")

    assert bundle_path.is_file()
    with zipfile.ZipFile(bundle_path) as bundle:
        names = set(bundle.namelist())
        assert "diagnostics.txt" in names
        assert "logs/teach-skill.log" in names
        diagnostics = bundle.read("diagnostics.txt").decode("utf-8")
        assert "Teach Skill Claude diagnostics" in diagnostics
        assert "python:" in diagnostics


def test_create_support_bundle_does_not_follow_log_symlinks(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    logs_dir = tmp_path / ".teach-skill" / "logs"
    logs_dir.mkdir(parents=True)
    secret = tmp_path / "recording.jsonl"
    secret.write_text("private recording data\n", encoding="utf-8")
    (logs_dir / "teach-skill.log").write_text("safe log\n", encoding="utf-8")
    (logs_dir / "teach-skill.log.1").symlink_to(secret)

    bundle_path = create_support_bundle(destination_dir=tmp_path / "bundles")

    with zipfile.ZipFile(bundle_path) as bundle:
        names = set(bundle.namelist())
        assert "logs/teach-skill.log" in names
        assert "logs/teach-skill.log.1" not in names
        assert "private recording data" not in " ".join(
            bundle.read(name).decode("utf-8") for name in names
        )
