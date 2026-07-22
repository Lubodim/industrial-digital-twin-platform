"""
Centralized role and object-access checks.

The functions in this module do not return HTTP responses and do not
raise PermissionDenied. They return Boolean values so they can be reused
from:

- function-based views;
- class-based view mixins;
- services;
- templates;
- unit tests.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from core.constants import (
    ROLE_ADMIN,
    ROLE_ENGINEER,
    ROLE_VIEWER,
)


OWNER_FIELD_CANDIDATES = (
    "created_by",
    "requested_by",
    "user",
    "owner",
)


def is_authenticated_user(user: Any) -> bool:
    """
    Return True only for an authenticated and active user.
    """

    if user is None:
        return False

    if isinstance(user, AnonymousUser):
        return False

    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
    )


def normalize_role_name(role_name: str) -> str:
    """
    Normalize a user-role or Django-group name.

    Group-name matching is intentionally case-insensitive.
    """

    if not isinstance(role_name, str):
        raise TypeError("role_name must be a string.")

    normalized_name = role_name.strip()

    if not normalized_name:
        raise ValueError("role_name cannot be empty.")

    return normalized_name.casefold()


def get_user_role_names(user: Any) -> set[str]:
    """
    Return normalized Django group names for an authenticated user.
    """

    if not is_authenticated_user(user):
        return set()

    groups_manager = getattr(user, "groups", None)

    if groups_manager is None:
        return set()

    return {
        group_name.casefold()
        for group_name
        in groups_manager.values_list(
            "name",
            flat=True,
        )
    }


def user_has_role(
    user: Any,
    role_name: str,
) -> bool:
    """
    Return whether a user belongs to a named role/group.

    A superuser is considered to have every platform role.
    """

    if not is_authenticated_user(user):
        return False

    if getattr(user, "is_superuser", False):
        return True

    normalized_role = normalize_role_name(role_name)

    return normalized_role in get_user_role_names(user)


def user_has_any_role(
    user: Any,
    role_names: Iterable[str],
) -> bool:
    """
    Return whether a user belongs to at least one requested role.
    """

    if not is_authenticated_user(user):
        return False

    if getattr(user, "is_superuser", False):
        return True

    normalized_roles = {
        normalize_role_name(role_name)
        for role_name in role_names
    }

    if not normalized_roles:
        return False

    return bool(
        get_user_role_names(user)
        & normalized_roles
    )


def is_platform_admin(user: Any) -> bool:
    """
    Return whether the user has full platform administration rights.
    """

    if not is_authenticated_user(user):
        return False

    return bool(
        getattr(user, "is_superuser", False)
        or user_has_role(user, ROLE_ADMIN)
    )


def is_engineer(user: Any) -> bool:
    """
    Return whether the user may perform engineering operations.

    Administrators also have engineering access.
    """

    return bool(
        is_platform_admin(user)
        or user_has_role(user, ROLE_ENGINEER)
    )


def is_viewer(user: Any) -> bool:
    """
    Return whether the user has the explicit Viewer role.

    Engineers and administrators can also view platform data, but this
    function answers only whether the Viewer role itself is available.
    """

    return user_has_role(user, ROLE_VIEWER)


def can_access_platform(user: Any) -> bool:
    """
    Return whether an active authenticated user may enter the platform.

    At this stage every active authenticated account may enter. Business
    operations are controlled by the more specific checks below.
    """

    return is_authenticated_user(user)


def can_view_business_data(user: Any) -> bool:
    """
    Return whether a user may view digital twins and experiments.
    """

    return bool(
        is_platform_admin(user)
        or is_engineer(user)
        or is_viewer(user)
    )


def can_create_business_data(user: Any) -> bool:
    """
    Return whether a user may create twins, experiments and analyses.
    """

    return is_engineer(user)


def resolve_object_owner(
    obj: Any,
    *,
    owner_fields: Iterable[str] = OWNER_FIELD_CANDIDATES,
):
    """
    Return an object's owner-like user when one is available.

    The first existing field from ``owner_fields`` is used. Both relation
    objects and ``<field>_id`` values are supported.
    """

    if obj is None:
        return None

    for field_name in owner_fields:
        if not hasattr(obj, field_name):
            continue

        return getattr(obj, field_name)

    return None


def is_object_owner(
    user: Any,
    obj: Any,
    *,
    owner_fields: Iterable[str] = OWNER_FIELD_CANDIDATES,
) -> bool:
    """
    Return whether the supplied user owns the object.
    """

    if not is_authenticated_user(user):
        return False

    owner = resolve_object_owner(
        obj,
        owner_fields=owner_fields,
    )

    if owner is None:
        return False

    user_pk = getattr(user, "pk", None)
    owner_pk = getattr(owner, "pk", None)

    if (
        user_pk is not None
        and owner_pk is not None
    ):
        return user_pk == owner_pk

    return user == owner


def can_view_object(
    user: Any,
    obj: Any,
) -> bool:
    """
    Return whether a user may view a business object.

    Platform data is shared between authorized internal users. Therefore,
    viewing is role-based rather than ownership-based.
    """

    if obj is None:
        return False

    return can_view_business_data(user)


def can_change_object(
    user: Any,
    obj: Any,
    *,
    owner_fields: Iterable[str] = OWNER_FIELD_CANDIDATES,
) -> bool:
    """
    Return whether a user may modify an object.

    Rules:
    - platform administrators may modify all objects;
    - engineers may modify objects that they own;
    - viewers may not modify objects.
    """

    if obj is None:
        return False

    if is_platform_admin(user):
        return True

    return bool(
        is_engineer(user)
        and is_object_owner(
            user,
            obj,
            owner_fields=owner_fields,
        )
    )


def can_delete_object(
    user: Any,
    obj: Any,
    *,
    owner_fields: Iterable[str] = OWNER_FIELD_CANDIDATES,
) -> bool:
    """
    Return whether a user may delete an object.

    Initially the rule matches change access. Individual workflows may
    add stricter lifecycle checks, such as blocking deletion of approved
    experiments.
    """

    return can_change_object(
        user,
        obj,
        owner_fields=owner_fields,
    )


def can_run_external_research(
    user: Any,
    experiment: Any | None = None,
) -> bool:
    """
    Return whether a user may start external AI research.

    Administrators may start research for every experiment. Engineers may
    start research only for experiments they created.
    """

    if is_platform_admin(user):
        return True

    if not is_engineer(user):
        return False

    if experiment is None:
        return True

    return is_object_owner(
        user,
        experiment,
        owner_fields=("created_by",),
    )


def can_run_internal_analysis(
    user: Any,
    experiment: Any | None = None,
) -> bool:
    """
    Return whether a user may start local engineering analysis.
    """

    return can_run_external_research(
        user,
        experiment,
    )


def can_approve_experiment(
    user: Any,
    experiment: Any | None = None,
) -> bool:
    """
    Return whether a user may approve an experiment.

    Approval is deliberately restricted to platform administrators.
    This avoids an engineer approving their own proposal.
    """

    return is_platform_admin(user)


def can_manage_catalogs(user: Any) -> bool:
    """
    Return whether a user may manage material and technology catalogs.
    """

    return is_platform_admin(user)


def can_view_audit_log(user: Any) -> bool:
    """
    Return whether a user may inspect platform audit records.
    """

    return is_platform_admin(user)
