"""Менеджеры моделей приложения users.

Содержит кастомный менеджер для создания пользователей по email.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from users.models import User


class UserManager(BaseUserManager):
    """Менеджер пользователей с авторизацией по email вместо username."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: object) -> User:
        """Создаёт и сохраняет пользователя с указанным email и паролем.

        Args:
            email: Email-адрес нового пользователя.
            password: Пароль (будет хеширован).
            **extra_fields: Дополнительные поля модели.

        Returns:
            Созданный экземпляр пользователя.

        Raises:
            ValueError: Если email не указан.
        """
        if not email:
            raise ValueError("Email обязателен для создания пользователя")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> User:
        """Создаёт обычного пользователя.

        Args:
            email: Email-адрес нового пользователя.
            password: Пароль (будет хеширован).
            **extra_fields: Дополнительные поля модели.

        Returns:
            Созданный экземпляр пользователя.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> User:
        """Создаёт суперпользователя с полными правами.

        Args:
            email: Email-адрес суперпользователя.
            password: Пароль (будет хеширован).
            **extra_fields: Дополнительные поля модели.

        Returns:
            Созданный экземпляр суперпользователя.

        Raises:
            ValueError: Если is_staff или is_superuser не равны True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True")
        return self._create_user(email, password, **extra_fields)
