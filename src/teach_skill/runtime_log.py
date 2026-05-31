import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from teach_skill.config import config_dir


LOG_NAME = "teach_skill"


class CommandFilter(logging.Filter):
    def __init__(self, command: str):
        super().__init__()
        self.command = command

    def filter(self, record: logging.LogRecord) -> bool:
        record.command = self.command
        return True


def log_dir() -> Path:
    return config_dir() / "logs"


def log_path() -> Path:
    return log_dir() / "teach-skill.log"


def configure_logging(command: str = "unknown") -> logging.Logger:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        path,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.addFilter(CommandFilter(command))
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s command=%(command)s %(name)s: %(message)s"
    ))
    logger.addHandler(handler)
    logger.info("logging configured")
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOG_NAME}.{name}")
