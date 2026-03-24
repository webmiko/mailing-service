"""Management-команда для ручной отправки рассылки через CLI.

Использование:
    python manage.py send_mailing <mailing_id>
"""

from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError

from mailing.services import send_mailing


class Command(BaseCommand):
    """Отправляет рассылку по указанному ID."""

    help = "Отправляет рассылку по указанному ID"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("mailing_id", type=int, help="ID рассылки для отправки")

    def handle(self, *args: object, **options: object) -> None:
        mailing_id = options["mailing_id"]
        self.stdout.write(f"Отправка рассылки #{mailing_id}...")

        try:
            success_count, failure_count = send_mailing(mailing_id)
        except Exception as e:
            raise CommandError(f"Ошибка при отправке рассылки: {type(e).__name__} - {e}") from e

        self.stdout.write(
            self.style.SUCCESS(
                f"Рассылка #{mailing_id} обработана. Успешно: {success_count}, ошибок: {failure_count}."
            )
        )
