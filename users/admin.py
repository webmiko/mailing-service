"""Регистрация модели User в админ-панели Django."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Настройка отображения пользователей в админ-панели."""

    list_display = ("email", "is_verified", "is_staff", "is_active")
    list_filter = ("is_verified", "is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Статус", {"fields": ("is_verified", "is_active", "is_staff", "is_superuser")}),
        ("Группы и права", {"fields": ("groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
