"""
Application services for Digital Twin management.

The service layer contains the business operations used by Django views:

- create;
- update;
- activate;
- deactivate;
- delete;
- lookup;
- search and filtering;
- calculated cost summaries;
- statistics;
- audit logging.

Views should remain responsible only for HTTP concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet

from audit.models import AuditLog
from digital_twins.forms import DigitalTwinForm
from digital_twins.models import DigitalTwin


class DigitalTwinServiceError(RuntimeError):
    """Base exception for Digital Twin service operations."""


class DigitalTwinNotFoundError(DigitalTwinServiceError):
    """Raised when a requested Digital Twin does not exist."""


class DigitalTwinDeleteError(DigitalTwinServiceError):
    """Raised when a Digital Twin cannot be permanently deleted."""


@dataclass(frozen=True, slots=True)
class DigitalTwinStatistics:
    """Summary information for a Digital Twin collection."""

    total_count: int
    active_count: int
    inactive_count: int
    with_material_count: int
    without_material_count: int
    with_technology_count: int
    without_technology_count: int


class DigitalTwinService:
    """
    Business service for Digital Twin CRUD operations.

    Every write operation:

    1. validates the acting user;
    2. runs inside a database transaction;
    3. performs model validation;
    4. persists the object;
    5. creates an audit record.
    """

    ENTITY_TYPE = "DigitalTwin"

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        form: DigitalTwinForm,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> DigitalTwin:
        """
        Create and persist a Digital Twin from a valid ModelForm.
        """

        cls._validate_actor(user)
        cls._validate_form(form)

        twin = form.save(commit=False)

        twin.created_by = user
        twin.updated_by = user

        twin.full_clean()
        twin.save()

        form.save_m2m()

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.CREATE,
            twin=twin,
            details={
                "operation": "create",
                "part_number": twin.part_number,
                "name": twin.name,
                "is_active": twin.is_active,
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return twin

    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        twin: DigitalTwin,
        form: DigitalTwinForm,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> DigitalTwin:
        """
        Update an existing Digital Twin from a valid ModelForm.
        """

        cls._validate_actor(user)
        cls._validate_saved_twin(twin)
        cls._validate_form(form)

        if form.instance.pk != twin.pk:
            raise DigitalTwinServiceError(
                "The form instance does not match the Digital Twin "
                "being updated."
            )

        locked_twin = (DigitalTwin.objects.select_for_update().get(pk=twin.pk))

        before = cls._build_snapshot(locked_twin)

        updated_twin = form.save(commit=False)

        updated_twin.pk = locked_twin.pk
        
        updated_twin.created_by = twin.created_by
        updated_twin.updated_by = user

        updated_twin.full_clean()
        updated_twin.save()

        form.save_m2m()

        after = cls._build_snapshot(updated_twin)

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            twin=updated_twin,
            details={
                "operation": "update",
                "before": before,
                "after": after,
                "changed_fields": cls._find_changed_fields(
                    before=before,
                    after=after,
                ),
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return updated_twin

    @classmethod
    @transaction.atomic
    def activate(
        cls,
        *,
        twin: DigitalTwin,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> DigitalTwin:
        """Mark a Digital Twin as active."""

        return cls._set_active_status(
            twin=twin,
            user=user,
            is_active=True,
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

    @classmethod
    @transaction.atomic
    def deactivate(
        cls,
        *,
        twin: DigitalTwin,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> DigitalTwin:
        """Mark a Digital Twin as inactive without deleting its history."""

        return cls._set_active_status(
            twin=twin,
            user=user,
            is_active=False,
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        twin: DigitalTwin,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> UUID:
        """
        Permanently delete a Digital Twin.

        A twin that participates in experiments must not be removed because
        that would destroy engineering history. Such twins should be
        deactivated instead.
        """

        cls._validate_actor(user)
        cls._validate_saved_twin(twin)
        cls.validate_before_delete(twin)

        twin_id = twin.pk
        snapshot = cls._build_snapshot(twin)

        twin.delete()

        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.DELETE,
            entity_type=cls.ENTITY_TYPE,
            entity_id=str(twin_id),
            details={
                "operation": "delete",
                "deleted_twin": snapshot,
            },
            ip_address=ip_address,
            computer_name=cls._clean_metadata_text(
                computer_name,
                max_length=255,
            ),
            user_agent=cls._clean_metadata_text(
                user_agent,
            ),
        )

        return twin_id

    @classmethod
    def validate_before_delete(
        cls,
        twin: DigitalTwin,
    ) -> None:
        """
        Validate whether permanent deletion is safe.
        """

        cls._validate_saved_twin(twin)

        experiments_manager = getattr(
            twin,
            "experiments",
            None,
        )

        if (
            experiments_manager is not None
            and experiments_manager.exists()
        ):
            raise DigitalTwinDeleteError(
                "Digital Twin cannot be permanently deleted because "
                "it has related experiments. Deactivate it instead."
            )

    @classmethod
    def get_by_id(
        cls,
        twin_id: UUID | str,
        *,
        include_inactive: bool = True,
    ) -> DigitalTwin:
        """
        Return one Digital Twin by UUID.
        """

        queryset = cls.base_queryset()

        if not include_inactive:
            queryset = queryset.filter(
                is_active=True
            )

        try:
            return queryset.get(pk=twin_id)
        except (
            DigitalTwin.DoesNotExist,
            ValidationError,
            ValueError,
            TypeError,
        ) as error:
            raise DigitalTwinNotFoundError(
                f"Digital Twin '{twin_id}' was not found."
            ) from error

    @classmethod
    def get_by_part_number(
        cls,
        part_number: str,
        *,
        include_inactive: bool = True,
    ) -> DigitalTwin:
        """
        Return one Digital Twin by case-insensitive part number.
        """

        normalized_part_number = cls.normalize_part_number(
            part_number
        )

        queryset = cls.base_queryset()

        if not include_inactive:
            queryset = queryset.filter(
                is_active=True
            )

        try:
            return queryset.get(
                part_number__iexact=normalized_part_number
            )
        except DigitalTwin.DoesNotExist as error:
            raise DigitalTwinNotFoundError(
                "Digital Twin with part number "
                f"'{normalized_part_number}' was not found."
            ) from error

    @staticmethod
    def normalize_part_number(
        part_number: str,
    ) -> str:
        """
        Normalize a part number in the same way as DigitalTwinForm.
        """

        if not isinstance(part_number, str):
            raise TypeError(
                "part_number must be a string."
            )

        normalized = " ".join(
            part_number.strip().upper().split()
        )

        if not normalized:
            raise ValueError(
                "part_number cannot be empty."
            )

        return normalized

    @classmethod
    def base_queryset(cls) -> QuerySet[DigitalTwin]:
        """
        Return the common optimized Digital Twin queryset.
        """

        return (
            DigitalTwin.objects
            .select_related(
                "material",
                "technology",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "files",
            )
        )

    @classmethod
    def search(
        cls,
        *,
        queryset: QuerySet[DigitalTwin] | None = None,
        query: str = "",
        material=None,
        technology=None,
        status: str = "",
    ) -> QuerySet[DigitalTwin]:
        """
        Apply search and catalog filters to a Digital Twin queryset.
        """

        result = (
            queryset
            if queryset is not None
            else cls.base_queryset()
        )

        normalized_query = str(
            query or ""
        ).strip()

        if normalized_query:
            result = result.filter(
                Q(
                    name__icontains=normalized_query
                )
                | Q(
                    part_number__icontains=normalized_query
                )
                | Q(
                    description__icontains=normalized_query
                )
                | Q(
                    material__name__icontains=normalized_query
                )
                | Q(
                    material__code__icontains=normalized_query
                )
                | Q(
                    technology__name__icontains=normalized_query
                )
                | Q(
                    technology__code__icontains=normalized_query
                )
            )

        if material is not None:
            result = result.filter(
                material=material
            )

        if technology is not None:
            result = result.filter(
                technology=technology
            )

        normalized_status = str(
            status or ""
        ).strip().lower()

        if normalized_status == "active":
            result = result.filter(
                is_active=True
            )
        elif normalized_status == "inactive":
            result = result.filter(
                is_active=False
            )
        elif normalized_status:
            raise ValueError(
                "status must be empty, 'active' or 'inactive'."
            )

        return result.distinct().order_by(
            "name",
            "part_number",
        )

    @classmethod
    def get_statistics(
        cls,
        queryset: QuerySet[DigitalTwin] | None = None,
    ) -> DigitalTwinStatistics:
        """
        Calculate list-level Digital Twin statistics.
        """

        result = (
            queryset
            if queryset is not None
            else DigitalTwin.objects.all()
        )

        return DigitalTwinStatistics(
            total_count=result.count(),
            active_count=result.filter(
                is_active=True
            ).count(),
            inactive_count=result.filter(
                is_active=False
            ).count(),
            with_material_count=result.filter(
                material__isnull=False
            ).count(),
            without_material_count=result.filter(
                material__isnull=True
            ).count(),
            with_technology_count=result.filter(
                technology__isnull=False
            ).count(),
            without_technology_count=result.filter(
                technology__isnull=True
            ).count(),
        )

    @staticmethod
    def get_cost_summary(
        twin: DigitalTwin,
    ) -> dict[str, Decimal | None]:
        """
        Return calculated engineering and economic values.
        """

        if not isinstance(twin, DigitalTwin):
            raise TypeError(
                "twin must be a DigitalTwin instance."
            )

        return {
            "effective_mass_kg": twin.effective_mass_kg,
            "estimated_material_cost": (
                twin.estimated_material_cost
            ),
            "estimated_machine_cost": (
                twin.estimated_machine_cost
            ),
            "estimated_direct_cost": (
                twin.estimated_direct_cost
            ),
            "estimated_defect_cost": (
                twin.estimated_defect_cost
            ),
            "estimated_total_cost": (
                twin.estimated_total_cost
            ),
            "estimated_selling_price": (
                twin.estimated_selling_price
            ),
            "estimated_profit": (
                twin.estimated_profit
            ),
        }

    @classmethod
    def _set_active_status(
        cls,
        *,
        twin: DigitalTwin,
        user,
        is_active: bool,
        ip_address: str | None,
        computer_name: str,
        user_agent: str,
    ) -> DigitalTwin:
        """
        Persist one activation-state transition.
        """

        cls._validate_actor(user)
        cls._validate_saved_twin(twin)

        locked_twin = (
            DigitalTwin.objects
            .select_for_update()
            .get(pk=twin.pk)
        )

        previous_status = locked_twin.is_active

        locked_twin.is_active = is_active
        locked_twin.updated_by = user

        locked_twin.full_clean()
        locked_twin.save(
            update_fields=[
                "is_active",
                "updated_by",
                "updated_at",
            ]
        )

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            twin=locked_twin,
            details={
                "operation": (
                    "activate"
                    if is_active
                    else "deactivate"
                ),
                "previous_is_active": previous_status,
                "new_is_active": is_active,
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return locked_twin

    @staticmethod
    def _validate_actor(user) -> None:
        """
        Require a saved and active authenticated user.
        """

        if user is None:
            raise DigitalTwinServiceError(
                "A user is required for this operation."
            )

        if getattr(user, "pk", None) is None:
            raise DigitalTwinServiceError(
                "The user must be saved before this operation."
            )

        if not getattr(
            user,
            "is_authenticated",
            False,
        ):
            raise DigitalTwinServiceError(
                "An authenticated user is required."
            )

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise DigitalTwinServiceError(
                "An active user is required."
            )

    @staticmethod
    def _validate_saved_twin(
        twin: DigitalTwin,
    ) -> None:
        """
        Require a persisted DigitalTwin instance.
        """

        if not isinstance(twin, DigitalTwin):
            raise TypeError(
                "twin must be a DigitalTwin instance."
            )

        if twin.pk is None:
            raise DigitalTwinServiceError(
                "The Digital Twin must be saved."
            )

        if not DigitalTwin.objects.filter(
            pk=twin.pk
        ).exists():
            raise DigitalTwinNotFoundError(
                "The Digital Twin no longer exists."
            )

    @staticmethod
    def _validate_form(
        form: DigitalTwinForm,
    ) -> None:
        """
        Require a valid DigitalTwinForm.
        """

        if not isinstance(
            form,
            DigitalTwinForm,
        ):
            raise TypeError(
                "form must be a DigitalTwinForm instance."
            )

        if not form.is_bound:
            raise DigitalTwinServiceError(
                "The Digital Twin form must be bound to data."
            )

        if not form.is_valid():
            raise DigitalTwinServiceError(
                "The Digital Twin form contains validation errors."
            )

    @classmethod
    def _create_audit_log(
        cls,
        *,
        user,
        action: str,
        twin: DigitalTwin,
        details: dict[str, Any],
        ip_address: str | None,
        computer_name: str,
        user_agent: str,
    ) -> AuditLog:
        """
        Create a standardized Digital Twin audit entry.
        """

        return AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=cls.ENTITY_TYPE,
            entity_id=str(twin.pk),
            details=details,
            ip_address=ip_address,
            computer_name=cls._clean_metadata_text(
                computer_name,
                max_length=255,
            ),
            user_agent=cls._clean_metadata_text(
                user_agent,
            ),
        )

    @staticmethod
    def _clean_metadata_text(
        value: Any,
        *,
        max_length: int | None = None,
    ) -> str:
        """
        Normalize optional audit metadata.
        """

        result = str(
            value or ""
        ).strip()

        if max_length is not None:
            result = result[:max_length]

        return result

    @staticmethod
    def _build_snapshot(
        twin: DigitalTwin,
    ) -> dict[str, Any]:
        """
        Build a JSON-serializable Digital Twin state snapshot.
        """

        return {
            "id": str(twin.pk),
            "name": twin.name,
            "part_number": twin.part_number,
            "description": twin.description,
            "material_id": twin.material_id,
            "material_code": (
                twin.material.code
                if twin.material is not None
                else None
            ),
            "technology_id": twin.technology_id,
            "technology_code": (
                twin.technology.code
                if twin.technology is not None
                else None
            ),
            "volume_m3": cls_decimal_to_string(
                twin.volume_m3
            ),
            "mass_kg": cls_decimal_to_string(
                twin.mass_kg
            ),
            "production_time_minutes": (
                cls_decimal_to_string(
                    twin.production_time_minutes
                )
            ),
            "labor_cost": cls_decimal_to_string(
                twin.labor_cost
            ),
            "energy_cost": cls_decimal_to_string(
                twin.energy_cost
            ),
            "defect_rate_percent": (
                cls_decimal_to_string(
                    twin.defect_rate_percent
                )
            ),
            "desired_profit_margin_percent": (
                cls_decimal_to_string(
                    twin.desired_profit_margin_percent
                )
            ),
            "is_active": twin.is_active,
            "created_by_id": twin.created_by_id,
            "updated_by_id": twin.updated_by_id,
        }

    @staticmethod
    def _find_changed_fields(
        *,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> list[str]:
        """
        Return fields whose serialized values changed.
        """

        return sorted(
            key
            for key in before.keys() | after.keys()
            if before.get(key) != after.get(key)
        )


def cls_decimal_to_string(
    value: Decimal | None,
) -> str | None:
    """
    Convert Decimal values to JSON-safe strings.
    """

    if value is None:
        return None

    return str(value)
