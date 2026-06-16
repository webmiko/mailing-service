"""Регистрация моделей приложения mailing в админ-панели Django."""

from django.contrib import admin

from mailing.models import Mailing, MailingAttempt, Message, Recipient


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    """Настройка отображения получателей в админ-панели."""

    list_display = ("full_name", "email", "comment")
    search_fields = ("full_name", "email")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Настройка отображения сообщений в админ-панели."""

    list_display = ("subject",)
    search_fields = ("subject", "body")


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    """Настройка отображения рассылок в админ-панели."""

    list_display = ("pk", "message", "status", "start_time", "end_time")
    list_filter = ("status",)
    filter_horizontal = ("recipients",)


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    """Настройка отображения попыток рассылок в админ-панели."""

    list_display = ("mailing", "attempt_time", "status")
    list_filter = ("status",)
    readonly_fields = ("attempt_time",)
