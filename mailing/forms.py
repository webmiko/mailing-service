"""Формы приложения mailing.

Содержит Django-формы для CRUD-операций над получателями,
сообщениями и рассылками.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from mailing.models import Mailing, Message, Recipient

DATETIME_INPUT_FORMAT = "%Y-%m-%dT%H:%M"
DATETIME_TOLERANCE_SECONDS = 60
COMMENT_TEXTAREA_ROWS = 3
BODY_TEXTAREA_ROWS = 8

BS_INPUT = "form-control"
BS_SELECT = "form-select"


class RecipientForm(forms.ModelForm):
    """Форма создания и редактирования получателя рассылки."""

    class Meta:
        model = Recipient
        fields = ("email", "full_name", "comment")
        widgets = {
            "email": forms.EmailInput(attrs={"class": BS_INPUT, "placeholder": "example@mail.ru"}),
            "full_name": forms.TextInput(attrs={"class": BS_INPUT, "placeholder": "Иванов Иван Иванович"}),
            "comment": forms.Textarea(
                attrs={
                    "class": BS_INPUT,
                    "rows": COMMENT_TEXTAREA_ROWS,
                    "placeholder": "Комментарий (необязательно)",
                },
            ),
        }


class MessageForm(forms.ModelForm):
    """Форма создания и редактирования сообщения."""

    class Meta:
        model = Message
        fields = ("subject", "body")
        widgets = {
            "subject": forms.TextInput(attrs={"class": BS_INPUT, "placeholder": "Тема письма"}),
            "body": forms.Textarea(
                attrs={"class": BS_INPUT, "rows": BODY_TEXTAREA_ROWS, "placeholder": "Текст сообщения"},
            ),
        }


class MailingForm(forms.ModelForm):
    """Форма создания и редактирования рассылки."""

    class Meta:
        model = Mailing
        fields = ("start_time", "end_time", "message", "recipients")
        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={"class": BS_INPUT, "type": "datetime-local"},
                format=DATETIME_INPUT_FORMAT,
            ),
            "end_time": forms.DateTimeInput(
                attrs={"class": BS_INPUT, "type": "datetime-local"},
                format=DATETIME_INPUT_FORMAT,
            ),
            "message": forms.Select(attrs={"class": BS_SELECT}),
            "recipients": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = [DATETIME_INPUT_FORMAT]
        self.fields["end_time"].input_formats = [DATETIME_INPUT_FORMAT]
        if self.user:
            self.fields["message"].queryset = Message.objects.filter(owner=self.user)
            self.fields["recipients"].queryset = Recipient.objects.filter(owner=self.user)

    def _is_start_time_changed(self, new_start) -> bool:
        if self.instance.pk is None:
            return True
        original = self.instance.start_time
        if original is None:
            return True
        return abs((new_start - original).total_seconds()) > DATETIME_TOLERANCE_SECONDS

    def clean(self) -> dict:
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and start < timezone.now() and self._is_start_time_changed(start):
            raise ValidationError({"start_time": "Дата начала не может быть в прошлом."})
        if start and end and start >= end:
            raise ValidationError({"end_time": "Дата окончания должна быть позже даты начала."})
        return cleaned
