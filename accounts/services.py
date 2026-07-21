from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest

from audit.models import AuditLog


def get_client_ip(request: HttpRequest) -> str | None:
    """
    Return the client IP address.

    REMOTE_ADDR is used by default because arbitrary forwarded headers
    must not be trusted unless the application is behind a controlled
    reverse proxy.

    X-Forwarded-For is used only when the project explicitly enables
    TRUST_X_FORWARDED_FOR.
    """

    trust_forwarded_for = getattr(
        settings,
        "TRUST_X_FORWARDED_FOR",
        False,
    )

    if trust_forwarded_for:
        forwarded_for = request.META.get(
            "HTTP_X_FORWARDED_FOR",
            "",
        )

        if forwarded_for:
            first_address = forwarded_for.split(",")[0].strip()

            if first_address:
                return first_address

    remote_address = request.META.get("REMOTE_ADDR")

    if not remote_address:
        return None

    return remote_address.strip() or None


def get_client_computer_name(request: HttpRequest) -> str:
    """
    Return a client workstation name when supplied by trusted infrastructure.

    Standard web browsers do not normally expose the computer name.
    Therefore, the value remains empty unless a controlled proxy or client
    application supplies X-Computer-Name or REMOTE_HOST.
    """

    computer_name = (
        request.META.get("HTTP_X_COMPUTER_NAME")
        or request.META.get("REMOTE_HOST")
        or ""
    )

    return str(computer_name).strip()[:255]


def get_user_agent(request: HttpRequest) -> str:
    """Return the browser user-agent string."""

    return str(
        request.META.get("HTTP_USER_AGENT", "")
    ).strip()


def create_audit_log(
    *,
    request: HttpRequest,
    action: str,
    user=None,
    entity_type: str = "Authentication",
    entity_id: str = "",
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Create a standardized audit record for a web request.
    """

    resolved_user = user

    if resolved_user is None:
        request_user = getattr(request, "user", None)

        if (
            request_user is not None
            and request_user.is_authenticated
        ):
            resolved_user = request_user

    return AuditLog.objects.create(
        user=resolved_user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        details=details or {},
        ip_address=get_client_ip(request),
        computer_name=get_client_computer_name(request),
        user_agent=get_user_agent(request),
    )


def record_login(
    *,
    request: HttpRequest,
    user,
) -> AuditLog:
    """Record a successful platform login."""

    return create_audit_log(
        request=request,
        action=AuditLog.Action.LOGIN,
        user=user,
        details={
            "username": user.get_username(),
            "authentication_backend": (
                request.session.get(
                    "_auth_user_backend",
                    "",
                )
            ),
        },
    )


def record_logout(
    *,
    request: HttpRequest,
    user,
) -> AuditLog:
    """Record a platform logout before the session is cleared."""

    return create_audit_log(
        request=request,
        action=AuditLog.Action.LOGOUT,
        user=user,
        details={
            "username": user.get_username(),
        },
    )
