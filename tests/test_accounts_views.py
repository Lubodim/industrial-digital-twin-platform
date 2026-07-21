from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog


User = get_user_model()


class AccountsViewTests(TestCase):
    def setUp(self):
        self.password = "Strong-Test-Password-2026"

        self.user = User.objects.create_user(
            username="test-engineer",
            password=self.password,
            first_name="Test",
            last_name="Engineer",
        )

        self.home_url = reverse("accounts:home")
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")

    def test_login_page_is_available_to_anonymous_user(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "accounts/login.html",)

        self.assertContains(
            response,
            "Вход в системата",
        )

    def test_home_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 302)

        expected_redirect = (
            f"{self.login_url}?next={self.home_url}"
        )

        self.assertRedirects(
            response,
            expected_redirect,
        )

    def test_successful_login_redirects_to_home(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
        )

        self.assertRedirects(
            response,
            self.home_url,
        )

        authenticated_user_id = self.client.session.get(
            "_auth_user_id"
        )

        self.assertEqual(
            authenticated_user_id,
            str(self.user.pk),
        )

    def test_successful_login_creates_audit_record(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
            REMOTE_ADDR="192.168.10.55",
            HTTP_USER_AGENT="Industrial-Test-Browser/1.0",
        )

        self.assertEqual(response.status_code, 302)

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.LOGIN,
            user=self.user,
        )

        self.assertEqual(
            audit_log.entity_type,
            "Authentication",
        )

        self.assertEqual(
            audit_log.ip_address,
            "192.168.10.55",
        )

        self.assertEqual(
            audit_log.user_agent,
            "Industrial-Test-Browser/1.0",
        )

        self.assertEqual(
            audit_log.details["username"],
            self.user.username,
        )

    def test_invalid_login_does_not_create_audit_record(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            AuditLog.objects.filter(
                action=AuditLog.Action.LOGIN,
            ).exists()
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_authenticated_user_can_open_home(self):
        self.client.force_login(self.user)

        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/home.html",
        )

        self.assertContains(
            response,
            self.user.username,
        )

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)

        response = self.client.get(self.login_url)

        self.assertRedirects(
            response,
            self.home_url,
        )

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(self.logout_url)

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_clears_session_and_creates_audit_record(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.logout_url,
            REMOTE_ADDR="192.168.10.60",
            HTTP_USER_AGENT="Industrial-Test-Browser/2.0",
        )

        self.assertRedirects(
            response,
            self.login_url,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.LOGOUT,
            user=self.user,
        )

        self.assertEqual(
            audit_log.ip_address,
            "192.168.10.60",
        )

        self.assertEqual(
            audit_log.user_agent,
            "Industrial-Test-Browser/2.0",
        )

    def test_local_next_url_is_respected_after_login(self):
        local_target = self.home_url

        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
                "next": local_target,
            },
        )

        self.assertRedirects(
            response,
            local_target,
        )

    def test_external_next_url_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
                "next": (
                    "https://malicious.example/"
                    "credential-capture"
                ),
            },
        )

        self.assertRedirects(
            response,
            self.home_url,
        )

    def test_login_records_computer_name_when_supplied(self):
        self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": self.password,
            },
            HTTP_X_COMPUTER_NAME="ENGINEERING-WS-01",
        )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.LOGIN,
            user=self.user,
        )

        self.assertEqual(
            audit_log.computer_name,
            "ENGINEERING-WS-01",
        )