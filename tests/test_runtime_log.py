import logging

from teach_skill.runtime_log import configure_logging, log_path


def test_configure_logging_writes_to_default_log_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    logger = configure_logging("doctor")
    logger.info("diagnostic message")
    logging.shutdown()

    path = log_path()
    assert path == tmp_path / ".teach-skill" / "logs" / "teach-skill.log"
    assert "diagnostic message" in path.read_text(encoding="utf-8")
    assert "command=doctor" in path.read_text(encoding="utf-8")
