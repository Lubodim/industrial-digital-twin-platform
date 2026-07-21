from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from accounts.services import (
    create_audit_log,
    get_client_computer_name,
    get_client_ip,
    get_user_agent,
)
from audit.models import AuditLog


User = get_user_model()


class AccountsServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="service-test-user",
            password="Strong-Test-Password-2026",
        )

    def test_client_ip_uses_remote_address_by_default(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.20.30.40",
            HTTP_X_FORWARDED_FOR="203.0.113.10",
        )

        self.assertEqual(
            get_client_ip(request),
            "10.20.30.40",
        )

    @override_settings(
        TRUST_X_FORWARDED_FOR=True
    )
    def test_forwarded_ip_is_used_when_explicitly_trusted(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.20.30.40",
            HTTP_X_FORWARDED_FOR=(
                "203.0.113.10, 10.20.30.40"
            ),
        )

        self.assertEqual(
            get_client_ip(request),
            "203.0.113.10",
        )

    def test_missing_client_ip_returns_none(self):
        request = self.factory.get("/")

        request.META.pop(
            "REMOTE_ADDR",
            None,
        )

        self.assertIsNone(
            get_client_ip(request)
        )

    def test_computer_name_is_read_from_header(self):
        request = self.factory.get(
            "/",
            HTTP_X_COMPUTER_NAME="INDUSTRIAL-PC-07",
        )

        self.assertEqual(
            get_client_computer_name(request),
            "INDUSTRIAL-PC-07",
        )

    def test_user_agent_is_read_from_request(self):
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT="Test-Agent/3.0",
        )

        self.assertEqual(
            get_user_agent(request),
            "Test-Agent/3.0",
        )

    def test_create_audit_log_persists_request_context(self):
        request = self.factory.post(
            "/test-action/",
            REMOTE_ADDR="172.16.1.20",
            HTTP_USER_AGENT="Audit-Test-Agent",
            HTTP_X_COMPUTER_NAME="AUDIT-WS-01",
        )

        request.user = self.user

        audit_log = create_audit_log(
            request=request,
            action=AuditLog.Action.CREATE,
            entity_type="TestEntity",
            entity_id="42",
            details={
                "test": True,
            },
        )

        audit_log.refresh_from_db()

        self.assertEqual(
            audit_log.user,
            self.user,
        )

        self.assertEqual(
            audit_log.action,
            AuditLog.Action.CREATE,
        )

        self.assertEqual(
            audit_log.entity_type,
            "TestEntity",
        )

        self.assertEqual(
            audit_log.entity_id,
            "42",
        )

        self.assertEqual(
            audit_log.details,
            {
                "test": True,
            },
        )

        self.assertEqual(
            audit_log.ip_address,
            "172.16.1.20",
        )

        self.assertEqual(
            audit_log.computer_name,
            "AUDIT-WS-01",
        )

        self.assertEqual(
            audit_log.user_agent,
            "Audit-Test-Agent",
        )
