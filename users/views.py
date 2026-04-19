"""Представления приложения users.

Содержит views для регистрации, входа, выхода,
подтверждения email и профиля пользователя.
"""

import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import CreateView, TemplateView, View

from users.forms import UserLoginForm, UserRegisterForm
from users.models import User

ENCODING = "utf-8"
FILE_WRITE_MODE = "a"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _setup_logger() -> logging.Logger:
    """Настраивает и возвращает логгер для модуля users.views."""
    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.DEBUG)

    if _logger.handlers:
        return _logger

    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "users.log"
    file_handler = logging.FileHandler(log_file, mode=FILE_WRITE_MODE, encoding=ENCODING)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=TIMESTAMP_FORMAT,
    )
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)

    return _logger


logger = _setup_logger()


class UserRegisterView(CreateView):
    """Регистрация нового пользователя с отправкой письма-подтверждения."""

    model = User
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")

    def form_valid(self, form: UserRegisterForm) -> HttpResponseRedirect:
        user = form.save(commit=False)
        user.is_active = True
        user.is_verified = False
        user.save()

        self._send_verification_email(user)
        messages.success(
            self.request,
            "Регистрация прошла успешно. Проверьте вашу почту для подтверждения email.",
        )
        return redirect(self.success_url)

    def _send_verification_email(self, user: User) -> None:
        from django.conf import settings
        from django.core.mail import send_mail

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verify_url = self.request.build_absolute_uri(f"/users/verify/{uid}/{token}/")

        try:
            send_mail(
                subject="Подтверждение email — Mailing Service",
                message=f"Перейдите по ссылке для подтверждения: {verify_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Ошибка отправки письма подтверждения на {user.email}: {type(e).__name__} - {e}")


class EmailVerifyView(View):
    """Подтверждение email по ссылке из письма."""

    def get(self, request, uidb64: str, token: str) -> HttpResponse:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except TypeError, ValueError, OverflowError, User.DoesNotExist:
            messages.error(request, "Неверная ссылка подтверждения.")
            return redirect("users:login")

        if default_token_generator.check_token(user, token):
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            messages.success(request, "Email успешно подтверждён.")
            login(request, user)
            return redirect("mailing:home")

        messages.error(request, "Ссылка подтверждения недействительна или устарела.")
        return redirect("users:login")


class UserLoginView(LoginView):
    """Вход пользователя в систему."""

    template_name = "users/login.html"
    authentication_form = UserLoginForm


class UserLogoutView(LogoutView):
    """Выход пользователя из системы."""

    pass


class ProfileView(LoginRequiredMixin, TemplateView):
    """Профиль текущего пользователя."""

    template_name = "users/profile.html"
