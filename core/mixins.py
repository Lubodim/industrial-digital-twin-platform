"""
Reusable access-control mixins for Django class-based views.

These mixins connect the centralized permission functions from
``core.permissions`` with Django's class-based view system.

Unauthenticated users are redirected to the configured login page.
Authenticated users without sufficient permissions receive HTTP 403.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpRequest, HttpResponse

from core.permissions import (
    can_access_platform,
    can_approve_experiment,
    can_change_object,
    can_create_business_data,
    can_delete_object,
    can_manage_catalogs,
    can_run_external_research,
    can_run_internal_analysis,
    can_view_audit_log,
    can_view_business_data,
    can_view_object,
    is_authenticated_user,
    user_has_any_role,
    user_has_role,
)


PermissionCheck = Callable[..., bool]


class PlatformPermissionMixin(AccessMixin):
    """
    Base mixin for centralized platform permission checks.

    Subclasses must provide either:

    - ``permission_check`` as a callable; or
    - override ``has_permission()``.

    Anonymous users are redirected to login. Authenticated users who fail
    the permission check receive ``PermissionDenied``.
    """

    permission_check: PermissionCheck | None = None

    permission_denied_message = (
        "Нямате необходимите права за достъп до тази страница."
    )

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        self.request = request
        self.args = args
        self.kwargs = kwargs

        if not is_authenticated_user(request.user):
            return self.handle_no_permission()

        if not self.has_permission():
            raise PermissionDenied(
                self.get_permission_denied_message()
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_permission_check(self) -> PermissionCheck:
        """
        Return the configured permission-check callable.
        """

        if self.permission_check is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "'permission_check' or override has_permission()."
            )

        if not callable(self.permission_check):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__}.permission_check "
                "must be callable."
            )

        return self.permission_check

    def get_permission_denied_message(self) -> str:
        """
        Return the user-facing access-denied message.
        """

        message = str(
            self.permission_denied_message
            or ""
        ).strip()

        return message or (
            "Нямате необходимите права за това действие."
        )

    def get_permission_object(self):
        """
        Return the object used by object-level permission checks.

        The default implementation calls ``get_object()`` when available.
        """

        get_object = getattr(
            self,
            "get_object",
            None,
        )

        if not callable(get_object):
            return None

        return get_object()

    def get_permission_arguments(self) -> tuple[Any, ...]:
        """
        Return extra positional arguments for the permission function.

        The base implementation performs a user-only permission check.
        """

        return ()

    def get_permission_keyword_arguments(
        self,
    ) -> dict[str, Any]:
        """
        Return extra keyword arguments for the permission function.
        """

        return {}

    def has_permission(self) -> bool:
        """
        Evaluate the configured permission function.
        """

        permission_check = self.get_permission_check()

        return bool(
            permission_check(
                self.request.user,
                *self.get_permission_arguments(),
                **self.get_permission_keyword_arguments(),
            )
        )


class PlatformAccessRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require an active authenticated platform account.
    """

    permission_check = staticmethod(
        can_access_platform
    )


class RoleRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require one specific Django group/role.

    Example:

    class EngineerOnlyView(RoleRequiredMixin, TemplateView):
        required_role = "Engineer"
    """

    required_role: str | None = None

    def get_required_role(self) -> str:
        """
        Return the required role name.
        """

        if (
            not isinstance(self.required_role, str)
            or not self.required_role.strip()
        ):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "a non-empty 'required_role'."
            )

        return self.required_role.strip()

    def has_permission(self) -> bool:
        return user_has_role(
            self.request.user,
            self.get_required_role(),
        )


class AnyRoleRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require at least one role from ``required_roles``.

    Example:

    required_roles = ("Administrator", "Engineer")
    """

    required_roles: Iterable[str] = ()

    def get_required_roles(self) -> tuple[str, ...]:
        """
        Return validated required role names.
        """

        try:
            roles = tuple(self.required_roles)
        except TypeError as error:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__}.required_roles "
                "must be iterable."
            ) from error

        if not roles:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "at least one required role."
            )

        return roles

    def has_permission(self) -> bool:
        return user_has_any_role(
            self.request.user,
            self.get_required_roles(),
        )


class BusinessDataViewRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require permission to view digital twins and experiments.
    """

    permission_check = staticmethod(
        can_view_business_data
    )


class BusinessDataCreateRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require permission to create business objects.
    """

    permission_check = staticmethod(
        can_create_business_data
    )

class ObjectPermissionMixin(
    PlatformPermissionMixin
):
    """
    Base mixin for object-level permission checks.

    The resolved object is cached so get_object() is not called
    repeatedly during permission evaluation and view execution.
    """

    object_permission_check: PermissionCheck | None = None

    owner_fields: Iterable[str] | None = None

    _permission_object_resolved = False

    _permission_object = None

    def get_permission_check(self) -> PermissionCheck:
        """
        Return the configured object-level permission callable.
        """

        if self.object_permission_check is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "'object_permission_check'."
            )

        if not callable(self.object_permission_check):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__}."
                "object_permission_check must be callable."
            )

        return self.object_permission_check

    def get_permission_object(self):
        """
        Return the cached object used for permission checking.
        """

        if self._permission_object_resolved:
            return self._permission_object

        self._permission_object = self.get_object()

        self._permission_object_resolved = True

        return self._permission_object

    def get_permission_arguments(self) -> tuple[Any, ...]:
        """
        Supply the resolved object to the permission function.
        """

        return (
            self.get_permission_object(),
        )

    def get_permission_keyword_arguments(
        self,
    ) -> dict[str, Any]:
        """
        Supply optional ownership-field configuration.
        """

        if self.owner_fields is None:
            return {}

        return {
            "owner_fields": tuple(
                self.owner_fields
            ),
        }

    def get_object(self, queryset=None):
        """
        Resolve and cache an object through the next class in the MRO.

        DetailView, UpdateView and DeleteView provide the actual
        get_object() implementation through Django's SingleObjectMixin.
        """

        if self._permission_object_resolved:
            return self._permission_object

        parent_get_object = getattr(
            super(),
            "get_object",
            None,
        )

        if not callable(parent_get_object):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must be combined "
                "with a view that provides get_object()."
            )

        self._permission_object = parent_get_object(
            queryset=queryset
        )

        self._permission_object_resolved = True

        return self._permission_object

class ObjectViewRequiredMixin(
    ObjectPermissionMixin
):
    """
    Require permission to view a specific business object.
    """

    object_permission_check = staticmethod(
        can_view_object
    )

    permission_denied_message = (
        "Нямате право да разглеждате този обект."
    )


class ObjectChangeRequiredMixin(
    ObjectPermissionMixin
):
    """
    Require permission to edit a specific business object.
    """

    object_permission_check = staticmethod(
        can_change_object
    )

    permission_denied_message = (
        "Нямате право да редактирате този обект."
    )


class ObjectDeleteRequiredMixin(
    ObjectPermissionMixin
):
    """
    Require permission to delete a specific business object.
    """

    object_permission_check = staticmethod(
        can_delete_object
    )

    permission_denied_message = (
        "Нямате право да изтривате този обект."
    )


class ExperimentPermissionMixin(
    PlatformPermissionMixin
):
    """
    Base mixin for actions performed on a specific experiment.
    """

    experiment_url_kwarg = "experiment_id"

    _permission_experiment_resolved = False

    _permission_experiment = None

    def get_experiment(self):
        """
        Return the experiment used for permission checking.

        Subclasses should usually override this method or provide
        ``self.experiment`` before dispatch.
        """

        if self._permission_experiment_resolved:
            return self._permission_experiment

        experiment = getattr(
            self,
            "experiment",
            None,
        )

        if experiment is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "get_experiment() or set self.experiment."
            )

        self._permission_experiment = experiment

        self._permission_experiment_resolved = True

        return experiment

    def get_permission_arguments(self) -> tuple[Any, ...]:
        return (
            self.get_experiment(),
        )


class ExternalResearchRequiredMixin(
    ExperimentPermissionMixin
):
    """
    Require permission to start external AI research.
    """

    permission_check = staticmethod(
        can_run_external_research
    )

    permission_denied_message = (
        "Нямате право да стартирате външно AI проучване "
        "за този експеримент."
    )


class InternalAnalysisRequiredMixin(
    ExperimentPermissionMixin
):
    """
    Require permission to start local engineering analysis.
    """

    permission_check = staticmethod(
        can_run_internal_analysis
    )

    permission_denied_message = (
        "Нямате право да стартирате локален анализ "
        "за този експеримент."
    )


class ExperimentApprovalRequiredMixin(
    ExperimentPermissionMixin
):
    """
    Require permission to approve or reject an experiment.
    """

    permission_check = staticmethod(
        can_approve_experiment
    )

    permission_denied_message = (
        "Само администратор може да одобрява "
        "или отхвърля експерименти."
    )


class CatalogManagementRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require permission to manage materials and technologies.
    """

    permission_check = staticmethod(
        can_manage_catalogs
    )

    permission_denied_message = (
        "Нямате право да управлявате каталозите."
    )


class AuditLogAccessRequiredMixin(
    PlatformPermissionMixin
):
    """
    Require permission to inspect platform audit records.
    """

    permission_check = staticmethod(
        can_view_audit_log
    )

    permission_denied_message = (
        "Нямате право да разглеждате одитния журнал."
    )