"""
Utilities for extracting information from Django HttpRequest objects.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def get_client_ip(
    request: HttpRequest,
) -> str | None:
    """
    Return the client IP address.

    X-Forwarded-For is trusted only when explicitly enabled
    in Django settings.
    """

    trust_forwarded = getattr(
        settings,
        "TRUST_X_FORWARDED_FOR",
        False,
    )

    if trust_forwarded:

        forwarded = request.META.get(
            "HTTP_X_FORWARDED_FOR",
            "",
        )

        if forwarded:

            return (
                forwarded
                .split(",")[0]
                .strip()
            )

    remote = request.META.get(
        "REMOTE_ADDR"
    )

    if not remote:

        return None

    return remote.strip()


def get_client_computer_name(
    request: HttpRequest,
) -> str:
    """
    Browsers normally do not expose workstation names.

    This value is returned only when supplied by a trusted
    proxy or a future desktop client.
    """

    return (
        request.META.get(
            "HTTP_X_COMPUTER_NAME",
            ""
        )
        or request.META.get(
            "REMOTE_HOST",
            ""
        )
    ).strip()


def get_user_agent(
    request: HttpRequest,
) -> str:
    """
    Return browser user-agent.
    """

    return (
        request.META.get(
            "HTTP_USER_AGENT",
            ""
        )
    ).strip()


def get_request_path(
    request: HttpRequest,
) -> str:
    """
    Return requested URL path.
    """

    return request.path


def get_request_method(
    request: HttpRequest,
) -> str:
    """
    Return HTTP method.
    """

    return request.method.upper()


def get_authenticated_user(
    request: HttpRequest,
):
    """
    Return authenticated user or None.
    """

    user = getattr(
        request,
        "user",
        None,
    )

    if (
        user is None
        or not user.is_authenticated
    ):
        return None

    return user
