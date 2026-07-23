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
from digital_twins.models import DigitalTwin
from experiments.models import Experiment


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

    next_url = (request.POST.get("next") or request.GET.get("next") or "")

    logout_url = reverse("accounts:logout")

    if next_url == logout_url: next_url = ""

    form = PlatformAuthenticationForm(request=request, data=request.POST or None, )

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
        "logout_url": logout_url,
        "page_title": "Вход в системата",
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
    Display the main industrial platform dashboard.
    """

    active_experiment_statuses = {
        Experiment.Status.CHATTING,
        Experiment.Status.READY_FOR_ANALYSIS,
        Experiment.Status.ANALYZING,
        Experiment.Status.PROPOSALS_READY,
        Experiment.Status.PARTIALLY_APPROVED,
        Experiment.Status.APPROVED,
        Experiment.Status.TWIN_CREATED,
    }

    completed_experiment_statuses = {
        Experiment.Status.COMPLETED,
        Experiment.Status.TWIN_CREATED,
    }

    digital_twins = (
        DigitalTwin.objects
        .select_related(
            "material",
            "technology",
            "created_by",
        )
    )

    experiments = (
        Experiment.objects
        .select_related(
            "digital_twin",
            "created_by",
        )
    )

    context = {
        "page_title": "Начално табло",
        "digital_twin_count": (
            digital_twins.count()
        ),
        "active_digital_twin_count": (
            digital_twins.filter(
                is_active=True
            ).count()
        ),
        "experiment_count": (
            experiments.count()
        ),
        "active_experiment_count": (
            experiments.filter(
                status__in=active_experiment_statuses
            ).count()
        ),
        "completed_experiment_count": (
            experiments.filter(
                status__in=completed_experiment_statuses
            ).count()
        ),
        "draft_experiment_count": (
            experiments.filter(
                status=Experiment.Status.DRAFT
            ).count()
        ),
        "recent_digital_twins": (
            digital_twins
            .order_by("-created_at")[:5]
        ),
        "recent_experiments": (
            experiments
            .order_by("-created_at")[:5]
        ),
    }

    return render(
        request,
        "accounts/home.html",
        context,
    )
    