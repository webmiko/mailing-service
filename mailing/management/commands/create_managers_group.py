"""Management-команда для создания группы «Менеджеры» с необходимыми правами.

Использование:
    python manage.py create_managers_group
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Создаёт группу «Менеджеры» и назначает ей пользовательские права."""

    help = "Создаёт группу «Менеджеры» с правами просмотра и отключения рассылок"

    def handle(self, *args: object, **options: object) -> None:
        group, created = Group.objects.get_or_create(name="Менеджеры")

        permission_codenames = [
            "can_view_all_mailings",
            "can_disable_mailing",
            "can_view_all_messages",
            "can_view_all_recipients",
        ]

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.set(permissions)

        action = "Создана" if created else "Обновлена"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} группа «Менеджеры» с {permissions.count()} правами: "
                f"{', '.join(p.codename for p in permissions)}"
            )
        )
