"""Rate-limiting на основе Django cache.

Декоратор для ограничения количества запросов к view
без внешних зависимостей.
"""

import functools

from django.core.cache import cache
from django.http import HttpRequest, HttpResponseForbidden


def rate_limit(max_requests: int = 5, period_seconds: int = 60, key_prefix: str = "rl"):
    """Декоратор для ограничения частоты запросов.

    Args:
        max_requests: максимум запросов за период.
        period_seconds: длина периода в секундах.
        key_prefix: префикс ключа в кэше.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request_or_self, *args, **kwargs):
            request = request_or_self
            if not isinstance(request, HttpRequest):
                request = args[0] if args else kwargs.get("request")

            ip = _get_client_ip(request)
            cache_key = f"{key_prefix}:{ip}"

            request_count = cache.get(cache_key, 0)
            if request_count >= max_requests:
                return HttpResponseForbidden(
                    "Слишком много запросов. Попробуйте позже.",
                    content_type="text/plain; charset=utf-8",
                )

            cache.set(cache_key, request_count + 1, period_seconds)
            return view_func(request_or_self, *args, **kwargs)

        return wrapper

    return decorator


def _get_client_ip(request: HttpRequest) -> str:
    """Извлекает IP-адрес клиента из запроса."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
