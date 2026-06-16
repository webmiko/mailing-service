"""Бизнес-логика отправки рассылок.

Содержит функции для отправки email-сообщений получателям
и фиксации результатов в модели MailingAttempt.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from config.logging_config import setup_logger

logger = setup_logger(__name__, "services.log")


def send_mailing(mailing_id: int) -> tuple[int, int]:
    """Отправляет рассылку всем её получателям.

    Для каждого получателя вызывает send_mail() и создаёт запись
    MailingAttempt с результатом отправки.

    Args:
        mailing_id: ID рассылки для отправки

    Returns:
        Кортеж (количество_успешных, количество_неуспешных) отправок
    """
    from mailing.models import (
        ATTEMPT_STATUS_FAILURE,
        ATTEMPT_STATUS_SUCCESS,
        MAILING_STATUS_COMPLETED,
        MAILING_STATUS_STARTED,
        Mailing,
        MailingAttempt,
    )

    logger.info(f"Начало отправки рассылки #{mailing_id}")

    try:
        mailing_obj = Mailing.objects.get(pk=mailing_id)
    except Mailing.DoesNotExist:
        logger.error(f"Рассылка #{mailing_id} не найдена")
        return (0, 0)

    now = timezone.now()
    if now < mailing_obj.start_time:
        logger.warning(f"Рассылка #{mailing_id} ещё не началась — время начала не наступило")
        return (0, 0)

    if mailing_obj.end_time < now:
        mailing_obj.status = MAILING_STATUS_COMPLETED
        mailing_obj.save(update_fields=["status"])
        logger.warning(f"Рассылка #{mailing_id} завершена — время окончания прошло")
        return (0, 0)

    recipients = mailing_obj.recipients.all()
    if not recipients.exists():
        logger.warning(f"Рассылка #{mailing_id} не имеет получателей")
        return (0, 0)

    success_count = 0
    failure_count = 0

    for recipient in recipients:
        try:
            send_mail(
                subject=mailing_obj.message.subject,
                message=mailing_obj.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
            MailingAttempt.objects.create(
                mailing=mailing_obj,
                status=ATTEMPT_STATUS_SUCCESS,
                server_response="Письмо успешно отправлено",
            )
            success_count += 1
            logger.info(f"Письмо отправлено: {recipient.email}")

        except Exception as e:
            MailingAttempt.objects.create(
                mailing=mailing_obj,
                status=ATTEMPT_STATUS_FAILURE,
                server_response=f"{type(e).__name__}: {e}",
            )
            failure_count += 1
            logger.error(f"Ошибка отправки на {recipient.email}: {type(e).__name__} - {e}")

    mailing_obj.status = MAILING_STATUS_STARTED
    mailing_obj.save(update_fields=["status"])

    logger.info(f"Рассылка #{mailing_id} завершена: успешно={success_count}, ошибок={failure_count}")
    return (success_count, failure_count)
