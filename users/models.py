"""Модели приложения users.

Содержит кастомную модель пользователя с авторизацией по email.
"""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from users.managers import UserManager

PHONE_MAX_LENGTH = 35
COUNTRY_MAX_LENGTH = 100
AVATAR_MAX_SIZE_MB = 5
AVATAR_MAX_SIZE_BYTES = AVATAR_MAX_SIZE_MB * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def validate_avatar(value: object) -> None:
    """Проверяет тип и размер загружаемого аватара."""
    import os

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        allowed = ", ".join(ALLOWED_AVATAR_EXTENSIONS)
        raise ValidationError(f"Допустимые форматы: {allowed}. Загружен: {ext}")
    if value.size > AVATAR_MAX_SIZE_BYTES:
        raise ValidationError(f"Максимальный размер файла — {AVATAR_MAX_SIZE_MB} МБ.")


class User(AbstractUser):
    """Пользователь сервиса рассылок.

    Расширяет стандартную модель пользователя Django,
    используя email как основной идентификатор для входа.
    """

    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="Аватар", validators=[validate_avatar]
    )
    phone = models.CharField(max_length=PHONE_MAX_LENGTH, blank=True, verbose_name="Номер телефона")
    country = models.CharField(max_length=COUNTRY_MAX_LENGTH, blank=True, verbose_name="Страна")
    is_verified = models.BooleanField(default=False, verbose_name="Email подтверждён")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.email
