"""Планировщик автоматической отправки рассылок.

Использует django-apscheduler для периодической проверки
и отправки рассылок по расписанию.
"""

import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

ENCODING = "utf-8"
FILE_WRITE_MODE = "w"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SCHEDULER_INTERVAL_SECONDS = 60


def _setup_logger() -> logging.Logger:
    """Настраивает и возвращает логгер для модуля scheduler."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "scheduler.log"
    file_handler = logging.FileHandler(log_file, mode=FILE_WRITE_MODE, encoding=ENCODING)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=TIMESTAMP_FORMAT,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = _setup_logger()


def check_and_send_mailings() -> None:
    """Проверяет рассылки и отправляет те, время которых наступило.

    Находит рассылки со статусом 'Создана' и start_datetime <= now,
    отправляет их. Также завершает рассылки с истёкшим end_datetime.
    """
    from mailing.models import MAILING_STATUS_COMPLETED, MAILING_STATUS_CREATED, Mailing
    from mailing.services import send_mailing

    now = timezone.now()
    logger.info(f"Проверка рассылок по расписанию: {now}")

    expired_mailings = Mailing.objects.exclude(status=MAILING_STATUS_COMPLETED).filter(end_datetime__lt=now)
    expired_count = expired_mailings.update(status=MAILING_STATUS_COMPLETED)
    if expired_count:
        logger.info(f"Завершено рассылок с истёкшим сроком: {expired_count}")

    pending_mailings = Mailing.objects.filter(
        status=MAILING_STATUS_CREATED,
        start_datetime__lte=now,
        end_datetime__gt=now,
    )

    for mailing_obj in pending_mailings:
        logger.info(f"Автоотправка рассылки #{mailing_obj.pk}")
        try:
            success, failure = send_mailing(mailing_obj.pk)
            logger.info(f"Рассылка #{mailing_obj.pk}: успешно={success}, ошибок={failure}")
        except Exception as e:
            logger.error(f"Ошибка автоотправки рассылки #{mailing_obj.pk}: {type(e).__name__} - {e}")


def start_scheduler() -> None:
    """Запускает фоновый планировщик для автоматической отправки рассылок."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_and_send_mailings,
        "interval",
        seconds=SCHEDULER_INTERVAL_SECONDS,
        id="check_and_send_mailings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Планировщик запущен с интервалом {SCHEDULER_INTERVAL_SECONDS} секунд")
