"""Модели приложения mailing.

Содержит модели для управления рассылками: получатели, сообщения,
рассылки и попытки отправки.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

MAILING_STATUS_CREATED = "Создана"
MAILING_STATUS_STARTED = "Запущена"
MAILING_STATUS_COMPLETED = "Завершена"

MAILING_STATUS_CHOICES = [
    (MAILING_STATUS_CREATED, "Создана"),
    (MAILING_STATUS_STARTED, "Запущена"),
    (MAILING_STATUS_COMPLETED, "Завершена"),
]

ATTEMPT_STATUS_SUCCESS = "Успешно"
ATTEMPT_STATUS_FAILURE = "Не успешно"

ATTEMPT_STATUS_CHOICES = [
    (ATTEMPT_STATUS_SUCCESS, "Успешно"),
    (ATTEMPT_STATUS_FAILURE, "Не успешно"),
]

SUBJECT_MAX_LENGTH = 255
FULL_NAME_MAX_LENGTH = 255
STATUS_MAX_LENGTH = 50


class Recipient(models.Model):
    """Получатель рассылки.

    Хранит контактную информацию клиента для отправки сообщений.
    """

    email = models.EmailField(unique=True, verbose_name="Email")
    full_name = models.CharField(max_length=FULL_NAME_MAX_LENGTH, verbose_name="Ф. И. О.")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name="Владелец",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"
        ordering = ["full_name"]
        permissions = [
            ("can_view_all_recipients", "Может просматривать всех получателей"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"


class Message(models.Model):
    """Сообщение для рассылки.

    Хранит тему и тело письма, используемого в рассылках.
    """

    subject = models.CharField(max_length=SUBJECT_MAX_LENGTH, verbose_name="Тема письма")
    body = models.TextField(verbose_name="Тело письма")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Владелец",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["-pk"]
        permissions = [
            ("can_view_all_messages", "Может просматривать все сообщения"),
        ]

    def __str__(self) -> str:
        return self.subject


class Mailing(models.Model):
    """Рассылка сообщений.

    Объединяет сообщение и получателей, определяет расписание
    и текущий статус рассылки.
    """

    start_time = models.DateTimeField(verbose_name="Дата и время начала отправки")
    end_time = models.DateTimeField(verbose_name="Дата и время окончания отправки")
    status = models.CharField(
        max_length=STATUS_MAX_LENGTH,
        choices=MAILING_STATUS_CHOICES,
        default=MAILING_STATUS_CREATED,
        verbose_name="Статус",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Сообщение",
    )
    recipients = models.ManyToManyField(
        Recipient,
        related_name="mailings",
        verbose_name="Получатели",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Владелец",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ["-start_time"]
        permissions = [
            ("can_view_all_mailings", "Может просматривать все рассылки"),
            ("can_disable_mailing", "Может отключать рассылки"),
        ]

    def __str__(self) -> str:
        return f"Рассылка #{self.pk} — {self.message.subject} ({self.status})"

    def update_status(self) -> None:
        """Динамически пересчитывает статус на основе текущего времени."""
        now = timezone.now()
        if now < self.start_time:
            new_status = MAILING_STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            new_status = MAILING_STATUS_STARTED
        else:
            new_status = MAILING_STATUS_COMPLETED
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status"])


class MailingAttempt(models.Model):
    """Попытка отправки рассылки.

    Фиксирует результат каждой попытки отправки сообщения,
    включая статус и ответ почтового сервера.
    """

    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время попытки")
    status = models.CharField(
        max_length=STATUS_MAX_LENGTH,
        choices=ATTEMPT_STATUS_CHOICES,
        verbose_name="Статус",
    )
    server_response = models.TextField(blank=True, verbose_name="Ответ почтового сервера")
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Рассылка",
    )

    class Meta:
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылок"
        ordering = ["-attempt_time"]

    def __str__(self) -> str:
        return f"Попытка {self.attempt_time:%Y-%m-%d %H:%M} — {self.status}"
