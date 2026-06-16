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
        user = User.objects.create_user(email=email, password=password)
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return user

    def _create_staff(self, email: str = "staff@test.com", password: str = "TestPass123!") -> User:
        user = User.objects.create_user(email=email, password=password, is_staff=True)
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return user

    def _create_message(
        self, subject: str = "Тема", body: str = "Текст", owner: User | None = None
    ) -> Message:
        return Message.objects.create(subject=subject, body=body, owner=owner)

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
            start_time=now + delta_start,
            end_time=now + delta_end,
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

    def test_message_has_owner(self) -> None:
        user = self._create_user()
        msg = self._create_message(owner=user)
        assert msg.owner == user


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

    def test_update_status_before_start(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(hours=1),
            delta_end=timedelta(hours=2),
            status=MAILING_STATUS_STARTED,
        )
        mailing.update_status()
        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_CREATED

    def test_update_status_during_window(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(hours=-1),
            delta_end=timedelta(hours=1),
        )
        mailing.update_status()
        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_STARTED

    def test_update_status_after_end(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(days=-2),
            delta_end=timedelta(days=-1),
        )
        mailing.update_status()
        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_COMPLETED

    def test_update_status_no_save_if_unchanged(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(hours=1),
            delta_end=timedelta(hours=2),
            status=MAILING_STATUS_CREATED,
        )
        mailing.update_status()
        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_CREATED


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

    def test_future_mailing_not_sent(self) -> None:
        mailing = self._create_mailing(
            delta_start=timedelta(hours=1),
            delta_end=timedelta(hours=2),
        )
        r = self._create_recipient()
        mailing.recipients.add(r)
        result = send_mailing(mailing.pk)
        assert result == (0, 0)

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

    def _local_fmt(self, dt) -> str:
        """Format a datetime as local time string for form input."""
        return timezone.localtime(dt).strftime("%Y-%m-%dT%H:%M")

    def test_valid_form(self) -> None:
        msg = self._create_message()
        r = self._create_recipient()
        now = timezone.now()
        form = MailingForm(
            data={
                "start_time": self._local_fmt(now + timedelta(hours=1)),
                "end_time": self._local_fmt(now + timedelta(hours=2)),
                "message": msg.pk,
                "recipients": [r.pk],
            }
        )
        assert form.is_valid(), form.errors

    def test_start_time_in_past_invalid(self) -> None:
        msg = self._create_message()
        r = self._create_recipient()
        now = timezone.now()
        form = MailingForm(
            data={
                "start_time": self._local_fmt(now - timedelta(hours=1)),
                "end_time": self._local_fmt(now + timedelta(hours=1)),
                "message": msg.pk,
                "recipients": [r.pk],
            }
        )
        assert not form.is_valid()
        assert "start_time" in form.errors

    def test_end_time_before_start_time_invalid(self) -> None:
        msg = self._create_message()
        r = self._create_recipient()
        now = timezone.now()
        form = MailingForm(
            data={
                "start_time": self._local_fmt(now + timedelta(hours=2)),
                "end_time": self._local_fmt(now + timedelta(hours=1)),
                "message": msg.pk,
                "recipients": [r.pk],
            }
        )
        assert not form.is_valid()
        assert "end_time" in form.errors

    def test_edit_existing_mailing_with_past_start_time_allowed(self) -> None:
        msg = self._create_message()
        r = self._create_recipient()
        now = timezone.now()
        mailing = Mailing.objects.create(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=5),
            message=msg,
        )
        mailing.recipients.add(r)
        form = MailingForm(
            data={
                "start_time": self._local_fmt(now - timedelta(hours=1)),
                "end_time": self._local_fmt(now + timedelta(hours=5)),
                "message": msg.pk,
                "recipients": [r.pk],
            },
            instance=mailing,
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

    def test_owner_sees_only_own_messages(self) -> None:
        self._create_message(owner=self.owner)
        self._create_message(subject="Чужая", owner=self.other)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("mailing:message_list"))
        owned_messages = [m for m in response.context["messages_list"] if m.owner == self.owner]
        assert len(owned_messages) == 1

    def test_staff_sees_all_messages(self) -> None:
        msg_count_before = Message.objects.count()
        self._create_message(owner=self.owner)
        self._create_message(subject="Чужая", owner=self.other)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("mailing:message_list"))
        assert len(response.context["messages_list"]) == msg_count_before + 2

    def test_message_create_sets_owner(self) -> None:
        self.client.force_login(self.owner)
        self.client.post(
            reverse("mailing:message_create"),
            data={"subject": "Новое", "body": "Текст"},
        )
        msg = Message.objects.get(subject="Новое")
        assert msg.owner == self.owner


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

    def test_send_outside_time_window_fails(self) -> None:
        user = self._create_user()
        mailing = self._create_mailing(
            owner=user,
            delta_start=timedelta(hours=1),
            delta_end=timedelta(hours=2),
        )
        self.client.force_login(user)
        response = self.client.post(reverse("mailing:mailing_send", args=[mailing.pk]))
        assert response.status_code == 302
        assert not MailingAttempt.objects.filter(mailing=mailing).exists()

    def test_non_owner_cannot_send(self) -> None:
        owner = self._create_user(email="sender@test.com")
        other = self._create_user(email="intruder@test.com")
        mailing = self._create_mailing(owner=owner)

        self.client.force_login(other)
        response = self.client.post(reverse("mailing:mailing_send", args=[mailing.pk]))
        assert response.status_code == 403


class TestMailingDisableView(TestCase, _TestDataMixin):
    """Тесты отключения рассылки менеджером."""

    def test_staff_can_disable_mailing(self) -> None:
        staff = self._create_staff()
        mailing = self._create_mailing(status=MAILING_STATUS_STARTED)
        self.client.force_login(staff)

        response = self.client.post(reverse("mailing:mailing_disable", args=[mailing.pk]))
        assert response.status_code == 302

        mailing.refresh_from_db()
        assert mailing.status == MAILING_STATUS_COMPLETED

    def test_non_staff_cannot_disable_mailing(self) -> None:
        user = self._create_user()
        mailing = self._create_mailing(status=MAILING_STATUS_STARTED)
        self.client.force_login(user)

        response = self.client.post(reverse("mailing:mailing_disable", args=[mailing.pk]))
        assert response.status_code == 403


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


# ========== Пользователи ==========


class TestUserListView(TestCase, _TestDataMixin):
    """Тесты списка пользователей (менеджер)."""

    def test_staff_can_view_user_list(self) -> None:
        staff = self._create_staff()
        self.client.force_login(staff)
        response = self.client.get(reverse("users:user_list"))
        assert response.status_code == 200

    def test_non_staff_cannot_view_user_list(self) -> None:
        user = self._create_user()
        self.client.force_login(user)
        response = self.client.get(reverse("users:user_list"))
        assert response.status_code == 403


class TestUserBlockView(TestCase, _TestDataMixin):
    """Тесты блокировки пользователей."""

    def test_staff_can_block_user(self) -> None:
        staff = self._create_staff()
        user = self._create_user()
        self.client.force_login(staff)

        response = self.client.post(reverse("users:user_block", args=[user.pk]))
        assert response.status_code == 302

        user.refresh_from_db()
        assert not user.is_active

    def test_staff_can_unblock_user(self) -> None:
        staff = self._create_staff()
        user = self._create_user()
        user.is_active = False
        user.save()
        self.client.force_login(staff)

        self.client.post(reverse("users:user_block", args=[user.pk]))
        user.refresh_from_db()
        assert user.is_active

    def test_staff_cannot_block_self(self) -> None:
        staff = self._create_staff()
        self.client.force_login(staff)

        self.client.post(reverse("users:user_block", args=[staff.pk]))
        staff.refresh_from_db()
        assert staff.is_active

    def test_non_staff_cannot_block(self) -> None:
        user = self._create_user()
        other = self._create_user(email="target@test.com")
        self.client.force_login(user)

        response = self.client.post(reverse("users:user_block", args=[other.pk]))
        assert response.status_code == 403


class TestProfileViews(TestCase, _TestDataMixin):
    """Тесты профиля пользователя."""

    def test_profile_view_requires_login(self) -> None:
        response = self.client.get(reverse("users:profile"))
        assert response.status_code == 302

    def test_profile_view_accessible_for_auth_user(self) -> None:
        user = self._create_user()
        self.client.force_login(user)
        response = self.client.get(reverse("users:profile"))
        assert response.status_code == 200

    def test_profile_edit_view_accessible(self) -> None:
        user = self._create_user()
        self.client.force_login(user)
        response = self.client.get(reverse("users:profile_edit"))
        assert response.status_code == 200

    def test_profile_edit_updates_data(self) -> None:
        user = self._create_user()
        self.client.force_login(user)
        self.client.post(
            reverse("users:profile_edit"),
            data={
                "email": user.email,
                "first_name": "Иван",
                "last_name": "Иванов",
                "phone": "+7 999 123-45-67",
                "country": "Россия",
            },
        )
        user.refresh_from_db()
        assert user.first_name == "Иван"
        assert user.country == "Россия"
