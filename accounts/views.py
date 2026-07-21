from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from accounts.forms import PlatformAuthenticationForm
from accounts.services import record_login, record_logout


def _get_safe_redirect_url(
    request: HttpRequest,
    candidate_url: str | None,
) -> str:
    """
    Return a safe local redirect URL after login.

    External redirect targets are rejected to prevent open-redirect
    vulnerabilities.
    """

    default_url = reverse("accounts:home")

    if not candidate_url:
        return default_url

    is_safe = url_has_allowed_host_and_scheme(
        url=candidate_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )

    if not is_safe:
        return default_url

    return candidate_url


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Authenticate a user and create a login audit record.
    """

    if request.user.is_authenticated:
        return redirect("accounts:home")

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    )

    form = PlatformAuthenticationForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        login(request, user)

        record_login(
            request=request,
            user=user,
        )

        messages.success(
            request,
            "Входът в системата беше успешен.",
        )

        return redirect(
            _get_safe_redirect_url(
                request,
                next_url,
            )
        )

    context = {
        "form": form,
        "next": next_url,
    }

    return render(
        request,
        "accounts/login.html",
        context,
    )


@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    Record the logout and terminate the authenticated session.
    """

    user = request.user

    record_logout(
        request=request,
        user=user,
    )

    logout(request)

    messages.success(
        request,
        "Излязохте успешно от системата.",
    )

    return redirect("accounts:login")


@login_required
def home_view(request: HttpRequest) -> HttpResponse:
    """
    Protected application entry point.

    The full dashboard will replace this minimal page in Roadmap Stage 10.
    """

    context = {
        "page_title": "Industrial Digital Twin Platform",
    }

    return render(
        request,
        "accounts/home.html",
        context,
    )
