"""Планировщик автоматической отправки рассылок.

Использует django-apscheduler для периодической проверки
и отправки рассылок по расписанию.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from config.logging_config import setup_logger

SCHEDULER_INTERVAL_SECONDS = 60

logger = setup_logger(__name__, "scheduler.log")


def check_and_send_mailings() -> None:
    """Проверяет рассылки и отправляет те, время которых наступило.

    Находит рассылки со статусом 'Создана' и start_time <= now,
    отправляет их. Также завершает рассылки с истёкшим end_time.
    """
    from mailing.models import MAILING_STATUS_COMPLETED, MAILING_STATUS_CREATED, Mailing
    from mailing.services import send_mailing

    now = timezone.now()
    logger.info(f"Проверка рассылок по расписанию: {now}")

    expired_mailings = Mailing.objects.exclude(status=MAILING_STATUS_COMPLETED).filter(end_time__lt=now)
    expired_count = expired_mailings.update(status=MAILING_STATUS_COMPLETED)
    if expired_count:
        logger.info(f"Завершено рассылок с истёкшим сроком: {expired_count}")

    pending_mailings = Mailing.objects.filter(
        status=MAILING_STATUS_CREATED,
        start_time__lte=now,
        end_time__gt=now,
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
