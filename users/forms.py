"""Формы приложения users.

Содержит формы регистрации и авторизации пользователей.
"""

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
