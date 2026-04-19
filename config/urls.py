"""Главная конфигурация URL-маршрутов проекта."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls", namespace="users")),
    path("", include("mailing.urls", namespace="mailing")),
]
