"""Общая конфигурация логирования для всех модулей проекта."""

import logging
from pathlib import Path

ENCODING = "utf-8"
FILE_WRITE_MODE = "a"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def setup_logger(name: str, log_filename: str) -> logging.Logger:
    """Создаёт и настраивает логгер с записью в файл.

    Args:
        name: имя логгера (обычно __name__ вызывающего модуля).
        log_filename: имя файла лога (например, 'services.log').

    Returns:
        Настроенный экземпляр logging.Logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    _LOGS_DIR.mkdir(exist_ok=True)

    log_file = _LOGS_DIR / log_filename
    file_handler = logging.FileHandler(log_file, mode=FILE_WRITE_MODE, encoding=ENCODING)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=TIMESTAMP_FORMAT,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
