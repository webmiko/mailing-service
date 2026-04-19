"""Модели приложения users.

Содержит кастомную модель пользователя с авторизацией по email.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from users.managers import UserManager


class User(AbstractUser):
    """Пользователь сервиса рассылок.

    Расширяет стандартную модель пользователя Django,
    используя email как основной идентификатор для входа.
    """

    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    is_verified = models.BooleanField(default=False, verbose_name="Email подтверждён")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.email
