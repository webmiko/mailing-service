"""Тесты приложения mailing.

Покрывает бизнес-логику отправки, модели, формы,
разграничение доступа и CRUD-операции.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailing.forms import MailingForm, MessageForm, RecipientForm
from mailing.models import (
    ATTEMPT_STATUS_FAILURE,
    ATTEMPT_STATUS_SUCCESS,
    MAILING_STATUS_COMPLETED,
    MAILING_STATUS_CREATED,
    MAILING_STATUS_STARTED,
    Mailing,
    MailingAttempt,
    Message,
    Recipient,
)
from mailing.services import send_mailing
from users.models import User


class _TestDataMixin:
    """Миксин для создания тестовых данных."""

    def _create_user(self, email: str = "user@test.com", password: str = "TestPass123!") -> User:
        return User.objects.create_user(email=email, password=password)

    def _create_staff(self, email: str = "staff@test.com", password: str = "TestPass123!") -> User:
        return User.objects.create_user(email=email, password=password, is_staff=True)

    def _create_message(self, subject: str = "Тема", body: str = "Текст") -> Message:
        return Message.objects.create(subject=subject, body=body)

    def _create_recipient(self, email: str = "client@test.com", owner: User | None = None) -> Recipient:
        return Recipient.objects.create(email=email, full_name="Иванов Иван", owner=owner)

    def _create_mailing(
        self,
        owner: User | None = None,
        message: Message | None = None,
        status: str = MAILING_STATUS_CREATED,
        delta_start: timedelta = timedelta(hours=-1),
        delta_end: timedelta = timedelta(hours=1),
    ) -> Mailing:
        now = timezone.now()
        msg = message or self._create_message()
        return Mailing.objects.create(
            start_datetime=now + delta_start,
            end_datetime=now + delta_end,
            status=status,
            message=msg,
            owner=owner,
        )


# ========== Модели ==========


class TestRecipientModel(TestCase, _TestDataMixin):
    """Тесты модели Recipient."""

    def test_str_representation(self) -> None:
        recipient = self._create_recipient(email="ivan@mail.ru")
        assert "ivan@mail.ru" in str(recipient)
        assert "Иванов Иван" in str(recipient)

    def test_email_unique_constraint(self) -> None:
        self._create_recipient(email="dup@test.com")
        with self.assertRaises(Exception):
            self._create_recipient(email="dup@test.com")


class TestMessageModel(TestCase, _TestDataMixin):
    """Тесты модели Message."""

    def test_str_representation(self) -> None:
        msg = self._create_message(subject="Привет мир")
        assert str(msg) == "Привет мир"


class TestMailingModel(TestCase, _TestDataMixin):
    """Тесты модели Mailing."""

    def test_str_representation(self) -> None:
        mailing = self._create_mailing()
        result = str(mailing)
        assert "Рассылка #" in result
        assert MAILING_STATUS_CREATED in result

    def test_default_status_is_created(self) -> None:
        mailing = self._create_mailing()
        assert mailing.status == MAILING_STATUS_CREATED

    def test_recipients_many_to_many(self) -> None:
        mailing = self._create_mailing()
        r1 = self._create_recipient(email="a@test.com")
        r2 = self._create_recipient(email="b@test.com")
        mailing.recipients.add(r1, r2)
        assert mailing.recipients.count() == 2


class TestMailingAttemptModel(TestCase, _TestDataMixin):
    """Тесты модели MailingAttempt."""

    def test_str_representation(self) -> None:
        mailing = self._create_mailing()
        attempt = MailingAttempt.objects.create(
            mailing=mailing,
            status=ATTEMPT_STATUS_SUCCESS,
            server_response="OK",
        )
        assert ATTEMPT_STATUS_SUCCESS in str(attempt)


# ========== Сервисы ==========


class TestSendMailing(TestCase, _TestDataMixin):
    """Тесты бизнес-логики отправки рассылок."""

    def test_nonexistent_mailing_returns_zeros(self) -> None:
        result = send_mailing(99999)
        assert result == (0, 0)

    def test_expired_mailing_sets_completed_status(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(days=-2),
            delta_end=timedelta(days=-1),
        )
        result = send_mailing(mailing.pk)
        assert result == (0, 0)

        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_COMPLETED

    def test_mailing_without_recipients_returns_zeros(self) -> None:
        mailing = self._create_mailing()
        result = send_mailing(mailing.pk)
        assert result == (0, 0)

    @patch("mailing.services.send_mail")
    def test_successful_send_creates_success_attempts(self, mock_send: object) -> None:
        mailing = self._create_mailing()
        r1 = self._create_recipient(email="a@test.com")
        r2 = self._create_recipient(email="b@test.com")
        mailing.recipients.add(r1, r2)

        success, failure = send_mailing(mailing.pk)

        assert success == 2
        assert failure == 0
        assert MailingAttempt.objects.filter(mailing=mailing, status=ATTEMPT_STATUS_SUCCESS).count() == 2

        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_STARTED

    @patch("mailing.services.send_mail", side_effect=Exception("SMTP error"))
    def test_failed_send_creates_failure_attempts(self, mock_send: object) -> None:
        mailing = self._create_mailing()
        recipient = self._create_recipient()
        mailing.recipients.add(recipient)

        success, failure = send_mailing(mailing.pk)

        assert success == 0
        assert failure == 1
        attempt = MailingAttempt.objects.get(mailing=mailing)
        assert attempt.status == ATTEMPT_STATUS_FAILURE
        assert "SMTP error" in attempt.server_response

    @patch("mailing.services.send_mail")
    def test_partial_failure(self, mock_send: object) -> None:
        mock_send.side_effect = [None, Exception("fail"), None]

        mailing = self._create_mailing()
        for i in range(3):
            r = self._create_recipient(email=f"user{i}@test.com")
            mailing.recipients.add(r)

        success, failure = send_mailing(mailing.pk)

        assert success == 2
        assert failure == 1


# ========== Формы ==========


class TestRecipientForm(TestCase):
    """Тесты формы получателя."""

    def test_valid_form(self) -> None:
        form = RecipientForm(data={"email": "test@mail.ru", "full_name": "Петров Петр", "comment": ""})
        assert form.is_valid()

    def test_invalid_email(self) -> None:
        form = RecipientForm(data={"email": "not-an-email", "full_name": "Тест"})
        assert not form.is_valid()
        assert "email" in form.errors

    def test_empty_name_invalid(self) -> None:
        form = RecipientForm(data={"email": "ok@mail.ru", "full_name": ""})
        assert not form.is_valid()
        assert "full_name" in form.errors


class TestMessageForm(TestCase):
    """Тесты формы сообщения."""

    def test_valid_form(self) -> None:
        form = MessageForm(data={"subject": "Тема", "body": "Текст"})
        assert form.is_valid()

    def test_empty_subject_invalid(self) -> None:
        form = MessageForm(data={"subject": "", "body": "Текст"})
        assert not form.is_valid()

    def test_empty_body_invalid(self) -> None:
        form = MessageForm(data={"subject": "Тема", "body": ""})
        assert not form.is_valid()


class TestMailingForm(TestCase, _TestDataMixin):
    """Тесты формы рассылки."""

    def test_valid_form(self) -> None:
        msg = self._create_message()
        r = self._create_recipient()
        now = timezone.now()
        form = MailingForm(
            data={
                "start_datetime": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                "end_datetime": (now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
                "message": msg.pk,
                "recipients": [r.pk],
            }
        )
        assert form.is_valid(), form.errors


# ========== Представления: доступ ==========


class TestHomeViewAccess(TestCase, _TestDataMixin):
    """Тесты доступности главной страницы."""

    def setUp(self) -> None:
        from django.core.cache import cache

        cache.clear()

    def test_home_page_accessible_anonymously(self) -> None:
        response = self.client.get(reverse("mailing:home"))
        assert response.status_code == 200

    def test_home_page_contains_statistics(self) -> None:
        response = self.client.get(reverse("mailing:home"))
        assert "total_mailings" in response.context


class TestViewsRequireLogin(TestCase):
    """Тесты: CRUD-страницы требуют авторизацию."""

    def test_recipient_list_requires_login(self) -> None:
        response = self.client.get(reverse("mailing:recipient_list"))
        assert response.status_code == 302

    def test_message_list_requires_login(self) -> None:
        response = self.client.get(reverse("mailing:message_list"))
        assert response.status_code == 302

    def test_mailing_list_requires_login(self) -> None:
        response = self.client.get(reverse("mailing:mailing_list"))
        assert response.status_code == 302

    def test_statistics_requires_login(self) -> None:
        response = self.client.get(reverse("mailing:statistics"))
        assert response.status_code == 302

    def test_attempts_requires_login(self) -> None:
        response = self.client.get(reverse("mailing:attempt_list"))
        assert response.status_code == 302


class TestOwnerAccess(TestCase, _TestDataMixin):
    """Тесты разграничения доступа: владелец vs чужой пользователь."""

    def setUp(self) -> None:
        self.owner = self._create_user(email="owner@test.com")
        self.other = self._create_user(email="other@test.com")
        self.staff = self._create_staff(email="admin@test.com")

        self.recipient = self._create_recipient(email="owned@test.com", owner=self.owner)
        self.mailing = self._create_mailing(owner=self.owner)
        self.mailing.recipients.add(self.recipient)

    def test_owner_can_edit_own_recipient(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.get(reverse("mailing:recipient_update", args=[self.recipient.pk]))
        assert response.status_code == 200

    def test_other_user_cannot_edit_recipient(self) -> None:
        self.client.force_login(self.other)
        response = self.client.get(reverse("mailing:recipient_update", args=[self.recipient.pk]))
        assert response.status_code == 403

    def test_staff_can_access_other_recipient(self) -> None:
        self.client.force_login(self.staff)
        response = self.client.get(reverse("mailing:recipient_update", args=[self.recipient.pk]))
        assert response.status_code == 200

    def test_owner_can_delete_own_mailing(self) -> None:
        self.client.force_login(self.owner)
        response = self.client.get(reverse("mailing:mailing_delete", args=[self.mailing.pk]))
        assert response.status_code == 200

    def test_other_user_cannot_delete_mailing(self) -> None:
        self.client.force_login(self.other)
        response = self.client.get(reverse("mailing:mailing_delete", args=[self.mailing.pk]))
        assert response.status_code == 403

    def test_owner_sees_only_own_recipients_in_list(self) -> None:
        self._create_recipient(email="another@test.com", owner=self.other)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("mailing:recipient_list"))
        assert len(response.context["recipients"]) == 1

    def test_staff_sees_all_recipients(self) -> None:
        self._create_recipient(email="another@test.com", owner=self.other)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("mailing:recipient_list"))
        assert len(response.context["recipients"]) == 2


class TestMailingSendView(TestCase, _TestDataMixin):
    """Тесты ручной отправки рассылки через UI."""

    @patch("mailing.services.send_mail")
    def test_send_via_post(self, mock_send: object) -> None:
        user = self._create_user()
        mailing = self._create_mailing(owner=user)
        recipient = self._create_recipient(owner=user)
        mailing.recipients.add(recipient)

        self.client.force_login(user)
        response = self.client.post(reverse("mailing:mailing_send", args=[mailing.pk]))

        assert response.status_code == 302
        assert MailingAttempt.objects.filter(mailing=mailing).exists()

    def test_send_nonexistent_mailing_returns_404(self) -> None:
        user = self._create_user()
        self.client.force_login(user)
        response = self.client.post(reverse("mailing:mailing_send", args=[99999]))
        assert response.status_code == 404


class TestStatisticsView(TestCase, _TestDataMixin):
    """Тесты страницы статистики."""

    @patch("mailing.services.send_mail")
    def test_statistics_counts_for_user(self, mock_send: object) -> None:
        user = self._create_user()
        mailing = self._create_mailing(owner=user)
        recipient = self._create_recipient(owner=user)
        mailing.recipients.add(recipient)
        send_mailing(mailing.pk)

        self.client.force_login(user)
        response = self.client.get(reverse("mailing:statistics"))

        assert response.context["total_attempts"] == 1
        assert response.context["success_attempts"] == 1
        assert response.context["total_mailings"] == 1
