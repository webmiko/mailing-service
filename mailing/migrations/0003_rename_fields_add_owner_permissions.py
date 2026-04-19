"""Rename datetime fields per ТЗ, add owner to Message, add custom permissions."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mailing", "0002_mailing_owner_recipient_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name="mailing",
            old_name="start_datetime",
            new_name="start_time",
        ),
        migrations.RenameField(
            model_name="mailing",
            old_name="end_datetime",
            new_name="end_time",
        ),
        migrations.RenameField(
            model_name="mailingattempt",
            old_name="attempted_at",
            new_name="attempt_time",
        ),
        migrations.AddField(
            model_name="message",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
        migrations.AlterModelOptions(
            name="mailing",
            options={
                "ordering": ["-start_time"],
                "permissions": [
                    ("can_view_all_mailings", "Может просматривать все рассылки"),
                    ("can_disable_mailing", "Может отключать рассылки"),
                ],
                "verbose_name": "Рассылка",
                "verbose_name_plural": "Рассылки",
            },
        ),
        migrations.AlterModelOptions(
            name="mailingattempt",
            options={
                "ordering": ["-attempt_time"],
                "verbose_name": "Попытка рассылки",
                "verbose_name_plural": "Попытки рассылок",
            },
        ),
        migrations.AlterModelOptions(
            name="message",
            options={
                "ordering": ["-pk"],
                "permissions": [
                    ("can_view_all_messages", "Может просматривать все сообщения"),
                ],
                "verbose_name": "Сообщение",
                "verbose_name_plural": "Сообщения",
            },
        ),
        migrations.AlterModelOptions(
            name="recipient",
            options={
                "ordering": ["full_name"],
                "permissions": [
                    ("can_view_all_recipients", "Может просматривать всех получателей"),
                ],
                "verbose_name": "Получатель",
                "verbose_name_plural": "Получатели",
            },
        ),
        migrations.AlterField(
            model_name="mailing",
            name="start_time",
            field=models.DateTimeField(verbose_name="Дата и время начала отправки"),
        ),
        migrations.AlterField(
            model_name="mailing",
            name="end_time",
            field=models.DateTimeField(verbose_name="Дата и время окончания отправки"),
        ),
    ]
