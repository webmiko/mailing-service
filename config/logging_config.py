"""Общая конфигурация логирования для всех модулей проекта."""

import logging
import textwrap
from pathlib import Path

ENCODING = "utf-8"
FILE_WRITE_MODE = "a"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_LINE_LENGTH = 119

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def _wrap_log_text(text: str, width: int) -> str:
    """Переносит длинные строки записи лога, чтобы ни одна строка не превышала width символов."""
    lines: list[str] = []
    for line in text.splitlines():
        if len(line) <= width:
            lines.append(line)
            continue
        lines.extend(
            textwrap.wrap(
                line,
                width=width,
                break_long_words=True,
                break_on_hyphens=True,
            )
        )
    return "\n".join(lines)


class LineLimitedFormatter(logging.Formatter):
    """Formatter, ограничивающий длину каждой выходной строки (как в EditorConfig / Ruff)."""

    def __init__(self, *args: object, max_line_length: int = MAX_LOG_LINE_LENGTH, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._max_line_length = max_line_length

    def format(self, record: logging.LogRecord) -> str:
        return _wrap_log_text(super().format(record), self._max_line_length)


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

    formatter = LineLimitedFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=TIMESTAMP_FORMAT,
        max_line_length=MAX_LOG_LINE_LENGTH,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
