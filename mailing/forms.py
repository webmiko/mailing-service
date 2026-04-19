"""Формы приложения mailing.

Содержит Django-формы для CRUD-операций над получателями,
сообщениями и рассылками.
"""

from django import forms

from mailing.models import Mailing, Message, Recipient

DATETIME_INPUT_FORMAT = "%Y-%m-%dT%H:%M"
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
        fields = ("start_datetime", "end_datetime", "message", "recipients")
        widgets = {
            "start_datetime": forms.DateTimeInput(
                attrs={"class": BS_INPUT, "type": "datetime-local"},
                format=DATETIME_INPUT_FORMAT,
            ),
            "end_datetime": forms.DateTimeInput(
                attrs={"class": BS_INPUT, "type": "datetime-local"},
                format=DATETIME_INPUT_FORMAT,
            ),
            "message": forms.Select(attrs={"class": BS_SELECT}),
            "recipients": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["start_datetime"].input_formats = [DATETIME_INPUT_FORMAT]
        self.fields["end_datetime"].input_formats = [DATETIME_INPUT_FORMAT]
