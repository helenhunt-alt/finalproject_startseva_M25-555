# logging_config.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    settings = SettingsLoader()

    log_path = settings.get("LOG_PATH")
    log_level = settings.get("LOG_LEVEL", "INFO")

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,   # ~1 MB
        backupCount=3
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    return logger