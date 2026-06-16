"""Формы приложения users.

Содержит формы регистрации, авторизации и редактирования профиля.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm

from users.models import User

BS_INPUT = "form-control"


class UserRegisterForm(UserCreationForm):
    """Форма регистрации нового пользователя."""

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", BS_INPUT)


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля пользователя."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "country", "avatar")
        widgets = {
            "email": forms.EmailInput(attrs={"class": BS_INPUT}),
            "first_name": forms.TextInput(attrs={"class": BS_INPUT}),
            "last_name": forms.TextInput(attrs={"class": BS_INPUT}),
            "phone": forms.TextInput(attrs={"class": BS_INPUT, "placeholder": "+7 (999) 123-45-67"}),
            "country": forms.TextInput(attrs={"class": BS_INPUT, "placeholder": "Россия"}),
            "avatar": forms.ClearableFileInput(attrs={"class": BS_INPUT}),
        }


class UserLoginForm(AuthenticationForm):
    """Форма входа пользователя с Bootstrap-стилями."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", BS_INPUT)


class UserPasswordResetForm(PasswordResetForm):
    """Форма запроса сброса пароля с Bootstrap-стилями."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", BS_INPUT)


class UserSetPasswordForm(SetPasswordForm):
    """Форма установки нового пароля с Bootstrap-стилями."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", BS_INPUT)
