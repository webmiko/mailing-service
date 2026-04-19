"""Конфигурация приложения mailing."""

import os

from django.apps import AppConfig


class MailingConfig(AppConfig):
    """Конфигурация Django-приложения для управления рассылками."""

    name = "mailing"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Рассылки"

    def ready(self) -> None:
        if os.environ.get("RUN_MAIN") == "true":
            from mailing.scheduler import start_scheduler

            start_scheduler()
