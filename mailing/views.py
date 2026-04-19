"""Представления приложения mailing.

Содержит CBV для CRUD-операций, главной страницы,
просмотра попыток и ручной отправки рассылок.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import QuerySet
from django.forms import Form
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from config.rate_limit import rate_limit
from mailing.forms import MailingForm, MessageForm, RecipientForm
from mailing.models import (
    ATTEMPT_STATUS_FAILURE,
    ATTEMPT_STATUS_SUCCESS,
    MAILING_STATUS_COMPLETED,
    MAILING_STATUS_STARTED,
    Mailing,
    MailingAttempt,
    Message,
    Recipient,
)

HOME_CACHE_TIMEOUT = 60


class OwnerRequiredMixin(UserPassesTestMixin):
    """Миксин проверки владельца объекта.

    Разрешает доступ только владельцу объекта или менеджеру (для просмотра).
    """

    def test_func(self) -> bool:
        obj = self.get_object()
        if hasattr(obj, "owner"):
            return obj.owner == self.request.user or self.request.user.is_staff
        return True


class MailingStatusMixin:
    """Миксин для пересчёта статуса рассылки при обращении к объекту."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()
        return obj


@method_decorator(cache_page(HOME_CACHE_TIMEOUT), name="dispatch")
class HomeView(TemplateView):
    """Главная страница со статистикой рассылок."""

    template_name = "mailing/home.html"

    def get_context_data(self, **kwargs: object) -> dict:
        context = super().get_context_data(**kwargs)
        context["total_mailings"] = Mailing.objects.count()
        context["active_mailings"] = Mailing.objects.filter(status=MAILING_STATUS_STARTED).count()
        context["total_recipients"] = Recipient.objects.count()
        return context


# --- Получатели ---


class RecipientListView(LoginRequiredMixin, ListView):
    """Список получателей рассылки текущего пользователя."""

    model = Recipient
    template_name = "mailing/recipient_list.html"
    context_object_name = "recipients"

    def get_queryset(self) -> QuerySet[Recipient]:
        if self.request.user.is_staff:
            return Recipient.objects.all()
        return Recipient.objects.filter(owner=self.request.user)


class RecipientDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Детальная страница получателя."""

    model = Recipient
    template_name = "mailing/recipient_detail.html"
    context_object_name = "recipient"


class RecipientCreateView(LoginRequiredMixin, CreateView):
    """Создание нового получателя."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailing/recipient_form.html"
    success_url = reverse_lazy("mailing:recipient_list")

    def form_valid(self, form: RecipientForm) -> HttpResponse:
        form.instance.owner = self.request.user
        messages.success(self.request, "Получатель успешно создан.")
        return super().form_valid(form)


class RecipientUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование получателя."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailing/recipient_form.html"
    success_url = reverse_lazy("mailing:recipient_list")

    def form_valid(self, form: RecipientForm) -> HttpResponse:
        messages.success(self.request, "Получатель успешно обновлён.")
        return super().form_valid(form)


class RecipientDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление получателя."""

    model = Recipient
    template_name = "mailing/recipient_confirm_delete.html"
    success_url = reverse_lazy("mailing:recipient_list")
    context_object_name = "recipient"

    def form_valid(self, form: Form) -> HttpResponse:
        messages.success(self.request, "Получатель удалён.")
        return super().form_valid(form)


# --- Сообщения ---


class MessageListView(LoginRequiredMixin, ListView):
    """Список сообщений текущего пользователя."""

    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "messages_list"

    def get_queryset(self) -> QuerySet[Message]:
        if self.request.user.is_staff:
            return Message.objects.all()
        return Message.objects.filter(owner=self.request.user)


class MessageDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Детальная страница сообщения."""

    model = Message
    template_name = "mailing/message_detail.html"
    context_object_name = "msg"


class MessageCreateView(LoginRequiredMixin, CreateView):
    """Создание нового сообщения."""

    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form: MessageForm) -> HttpResponse:
        form.instance.owner = self.request.user
        messages.success(self.request, "Сообщение успешно создано.")
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование сообщения."""

    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form: MessageForm) -> HttpResponse:
        messages.success(self.request, "Сообщение успешно обновлено.")
        return super().form_valid(form)


class MessageDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление сообщения."""

    model = Message
    template_name = "mailing/message_confirm_delete.html"
    success_url = reverse_lazy("mailing:message_list")
    context_object_name = "msg"

    def form_valid(self, form: Form) -> HttpResponse:
        messages.success(self.request, "Сообщение удалено.")
        return super().form_valid(form)


# --- Рассылки ---


class MailingListView(LoginRequiredMixin, ListView):
    """Список рассылок текущего пользователя."""

    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self) -> QuerySet[Mailing]:
        if self.request.user.is_staff:
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=self.request.user)


class MailingDetailView(MailingStatusMixin, LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Детальная страница рассылки с историей попыток."""

    model = Mailing
    template_name = "mailing/mailing_detail.html"
    context_object_name = "mailing_obj"

    def get_context_data(self, **kwargs: object) -> dict:
        context = super().get_context_data(**kwargs)
        context["attempts"] = self.object.attempts.all()
        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    """Создание новой рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: MailingForm) -> HttpResponse:
        form.instance.owner = self.request.user
        messages.success(self.request, "Рассылка успешно создана.")
        return super().form_valid(form)


class MailingUpdateView(MailingStatusMixin, LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: MailingForm) -> HttpResponse:
        messages.success(self.request, "Рассылка успешно обновлена.")
        return super().form_valid(form)


class MailingDeleteView(MailingStatusMixin, LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление рассылки."""

    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing:mailing_list")
    context_object_name = "mailing_obj"

    def form_valid(self, form: Form) -> HttpResponse:
        messages.success(self.request, "Рассылка удалена.")
        return super().form_valid(form)


@method_decorator(rate_limit(max_requests=10, period_seconds=60, key_prefix="mailing_send"), name="post")
class MailingSendView(LoginRequiredMixin, View):
    """Ручная отправка рассылки по POST-запросу.

    Отправку может выполнить только владелец рассылки или менеджер (is_staff).
    Отправка разрешена только если текущее время между start_time и end_time.
    """

    def post(self, request, pk: int) -> HttpResponse:
        from django.core.exceptions import PermissionDenied

        from mailing.services import send_mailing

        mailing_obj = get_object_or_404(Mailing, pk=pk)

        if mailing_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied

        now = timezone.now()
        if not (mailing_obj.start_time <= now <= mailing_obj.end_time):
            messages.error(
                request,
                "Отправка невозможна: текущее время вне диапазона рассылки.",
            )
            return redirect("mailing:mailing_detail", pk=pk)

        success_count, failure_count = send_mailing(mailing_obj.pk)
        messages.success(
            request,
            f"Рассылка отправлена. Успешно: {success_count}, ошибок: {failure_count}.",
        )
        return redirect("mailing:mailing_detail", pk=pk)


class MailingDisableView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Отключение рассылки менеджером."""

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def post(self, request, pk: int) -> HttpResponse:
        mailing_obj = get_object_or_404(Mailing, pk=pk)
        mailing_obj.status = MAILING_STATUS_COMPLETED
        mailing_obj.save(update_fields=["status"])
        messages.success(request, f"Рассылка #{pk} отключена.")
        return redirect("mailing:mailing_list")


# --- Попытки рассылок ---


class AttemptListView(LoginRequiredMixin, ListView):
    """Список попыток рассылок с фильтрацией по рассылке."""

    model = MailingAttempt
    template_name = "mailing/attempt_list.html"
    context_object_name = "attempts"

    def get_queryset(self) -> QuerySet[MailingAttempt]:
        queryset = super().get_queryset()
        mailing_id = self.request.GET.get("mailing_id")
        if mailing_id:
            queryset = queryset.filter(mailing_id=mailing_id)
        if not self.request.user.is_staff:
            queryset = queryset.filter(mailing__owner=self.request.user)
        return queryset


# --- Статистика ---


class StatisticsView(LoginRequiredMixin, TemplateView):
    """Страница статистики рассылок текущего пользователя."""

    template_name = "mailing/statistics.html"

    def get_context_data(self, **kwargs: object) -> dict:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_staff:
            user_attempts = MailingAttempt.objects.all()
            user_mailings = Mailing.objects.all()
        else:
            user_attempts = MailingAttempt.objects.filter(mailing__owner=user)
            user_mailings = Mailing.objects.filter(owner=user)

        context["total_attempts"] = user_attempts.count()
        context["success_attempts"] = user_attempts.filter(status=ATTEMPT_STATUS_SUCCESS).count()
        context["failure_attempts"] = user_attempts.filter(status=ATTEMPT_STATUS_FAILURE).count()
        context["total_mailings"] = user_mailings.count()
        return context
