"""Тесты приложения users.

Покрывает кастомную модель пользователя, менеджер,
регистрацию, верификацию email и разграничение доступа.
"""

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from users.models import User

# ========== Менеджер пользователей ==========


class TestUserManager(TestCase):
    """Тесты кастомного UserManager."""

    def test_create_user_with_email(self) -> None:
        user = User.objects.create_user(email="test@mail.ru", password="TestPass123!")
        assert user.email == "test@mail.ru"
        assert user.check_password("TestPass123!")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_normalizes_email(self) -> None:
        user = User.objects.create_user(email="test@MAIL.RU", password="TestPass123!")
        assert user.email == "test@mail.ru"

    def test_create_user_without_email_raises(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="TestPass123!")

    def test_create_superuser(self) -> None:
        user = User.objects.create_superuser(email="admin@mail.ru", password="AdminPass123!")
        assert user.is_staff
        assert user.is_superuser

    def test_create_superuser_without_is_staff_raises(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@mail.ru", password="pass", is_staff=False)

    def test_create_superuser_without_is_superuser_raises(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@mail.ru", password="pass", is_superuser=False)


# ========== Модель пользователя ==========


class TestUserModel(TestCase):
    """Тесты модели User."""

    def test_str_returns_email(self) -> None:
        user = User.objects.create_user(email="show@mail.ru", password="TestPass123!")
        assert str(user) == "show@mail.ru"

    def test_username_field_is_email(self) -> None:
        assert User.USERNAME_FIELD == "email"

    def test_default_is_verified_false(self) -> None:
        user = User.objects.create_user(email="new@mail.ru", password="TestPass123!")
        assert not user.is_verified

    def test_email_unique_constraint(self) -> None:
        User.objects.create_user(email="dup@mail.ru", password="pass1")
        with self.assertRaises(Exception):
            User.objects.create_user(email="dup@mail.ru", password="pass2")


# ========== Регистрация ==========


class TestUserRegistration(TestCase):
    """Тесты процесса регистрации."""

    def test_register_page_accessible(self) -> None:
        response = self.client.get(reverse("users:register"))
        assert response.status_code == 200

    def test_register_creates_user(self) -> None:
        response = self.client.post(
            reverse("users:register"),
            data={
                "email": "newuser@test.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        assert response.status_code == 302
        assert User.objects.filter(email="newuser@test.com").exists()

    def test_register_user_is_not_verified(self) -> None:
        self.client.post(
            reverse("users:register"),
            data={
                "email": "unverified@test.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        user = User.objects.get(email="unverified@test.com")
        assert not user.is_verified

    def test_register_password_mismatch(self) -> None:
        response = self.client.post(
            reverse("users:register"),
            data={
                "email": "fail@test.com",
                "password1": "ComplexPass123!",
                "password2": "DifferentPass456!",
            },
        )
        assert response.status_code == 200
        assert not User.objects.filter(email="fail@test.com").exists()

    def test_register_duplicate_email(self) -> None:
        User.objects.create_user(email="exists@test.com", password="TestPass123!")
        response = self.client.post(
            reverse("users:register"),
            data={
                "email": "exists@test.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
        )
        assert response.status_code == 200
        assert User.objects.filter(email="exists@test.com").count() == 1


# ========== Верификация email ==========


class TestEmailVerification(TestCase):
    """Тесты подтверждения email."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="verify@test.com", password="TestPass123!")
        self.user.is_verified = False
        self.user.save()

    def test_valid_token_verifies_user(self) -> None:
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(reverse("users:email_verify", args=[uid, token]))

        assert response.status_code == 302
        self.user.refresh_from_db()
        assert self.user.is_verified

    def test_invalid_token_rejects(self) -> None:
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.get(reverse("users:email_verify", args=[uid, "invalid-token"]))

        assert response.status_code == 302
        self.user.refresh_from_db()
        assert not self.user.is_verified

    def test_invalid_uid_rejects(self) -> None:
        token = default_token_generator.make_token(self.user)

        response = self.client.get(reverse("users:email_verify", args=["invalid-uid", token]))

        assert response.status_code == 302
        self.user.refresh_from_db()
        assert not self.user.is_verified


# ========== Авторизация ==========


class TestLoginLogout(TestCase):
    """Тесты входа и выхода."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="login@test.com", password="TestPass123!")

    def test_login_page_accessible(self) -> None:
        response = self.client.get(reverse("users:login"))
        assert response.status_code == 200

    def test_login_with_valid_credentials(self) -> None:
        response = self.client.post(
            reverse("users:login"),
            data={"username": "login@test.com", "password": "TestPass123!"},
        )
        assert response.status_code == 302

    def test_login_with_invalid_password(self) -> None:
        response = self.client.post(
            reverse("users:login"),
            data={"username": "login@test.com", "password": "WrongPass"},
        )
        assert response.status_code == 200

    def test_logout(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(reverse("users:logout"))
        assert response.status_code == 302


class TestPasswordReset(TestCase):
    """Тесты сброса пароля по email."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(email="reset@test.com", password="OldPass123!")

    def test_password_reset_form_accessible(self) -> None:
        response = self.client.get(reverse("users:password_reset"))
        assert response.status_code == 200

    def test_password_reset_sends_email_with_valid_link(self) -> None:
        response = self.client.post(
            reverse("users:password_reset"),
            data={"email": "reset@test.com"},
        )
        assert response.status_code == 302
        assert response.url == reverse("users:password_reset_done")
        assert len(mail.outbox) == 1
        body = mail.outbox[0].body
        assert "/users/password-reset/" in body
        assert "reset@test.com" in mail.outbox[0].to

    def test_password_reset_unknown_email_still_redirects(self) -> None:
        response = self.client.post(
            reverse("users:password_reset"),
            data={"email": "nobody@example.com"},
        )
        assert response.status_code == 302
        assert len(mail.outbox) == 0


# ========== Профиль ==========


class TestProfileView(TestCase):
    """Тесты страницы профиля."""

    def test_profile_requires_login(self) -> None:
        response = self.client.get(reverse("users:profile"))
        assert response.status_code == 302

    def test_authenticated_user_sees_profile(self) -> None:
        user = User.objects.create_user(email="profile@test.com", password="TestPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("users:profile"))
        assert response.status_code == 200
