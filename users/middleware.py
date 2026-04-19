"""Middleware приложения users.

Содержит промежуточные обработчики для проверки статуса пользователя.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

EXEMPT_URL_PREFIXES = (
    "/users/login/",
    "/users/register/",
    "/users/logout/",
    "/users/verify/",
    "/users/password-reset/",
    "/users/profile/",
    "/admin/",
)

EXEMPT_EXACT_URLS = ("/",)


class EmailVerificationMiddleware:
    """Ограничивает доступ неподтверждённым пользователям.

    Перенаправляет на страницу профиля, если email не подтверждён.
    Пропускает публичные URL и страницы авторизации.
    """

    def __init__(self, get_response: object) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated and not request.user.is_verified:
            path = request.path
            if path in EXEMPT_EXACT_URLS:
                return self.get_response(request)
            if not any(path.startswith(prefix) for prefix in EXEMPT_URL_PREFIXES):
                return redirect("users:profile")
        return self.get_response(request)
