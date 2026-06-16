"""Представления приложения users.

Содержит views для регистрации, входа, выхода,
подтверждения email, профиля и управления пользователями.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from config.logging_config import setup_logger
from config.rate_limit import rate_limit
from users.forms import UserLoginForm, UserProfileForm, UserRegisterForm
from users.models import User

logger = setup_logger(__name__, "users.log")


@method_decorator(rate_limit(max_requests=5, period_seconds=300, key_prefix="register"), name="post")
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
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
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


@method_decorator(rate_limit(max_requests=10, period_seconds=300, key_prefix="login"), name="post")
class UserLoginView(LoginView):
    """Вход пользователя в систему."""

    template_name = "users/login.html"
    authentication_form = UserLoginForm


class UserLogoutView(LogoutView):
    """Выход пользователя из системы."""

    pass


class ProfileView(LoginRequiredMixin, TemplateView):
    """Профиль текущего пользователя (просмотр)."""

    template_name = "users/profile.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование профиля текущего пользователя."""

    model = User
    form_class = UserProfileForm
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form: UserProfileForm) -> HttpResponse:
        messages.success(self.request, "Профиль успешно обновлён.")
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Список пользователей сервиса (только для менеджеров/staff)."""

    model = User
    template_name = "users/user_list.html"
    context_object_name = "users_list"

    def test_func(self) -> bool:
        return self.request.user.is_staff


class UserBlockView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Блокировка/разблокировка пользователя менеджером."""

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def post(self, request, pk: int) -> HttpResponse:
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Нельзя заблокировать самого себя.")
            return redirect("users:user_list")

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        action = "разблокирован" if user.is_active else "заблокирован"
        messages.success(request, f"Пользователь {user.email} {action}.")
        return redirect("users:user_list")
