"""
Application services for Experiment management.
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
from digital_twins.models import DigitalTwin
from experiments.forms import ExperimentForm
from experiments.models import Experiment


class ExperimentServiceError(RuntimeError):
    """
    Base exception for Experiment service operations.
    """


class ExperimentNotFoundError(
    ExperimentServiceError
):
    """
    Raised when an Experiment cannot be found.
    """


class ExperimentUpdateError(
    ExperimentServiceError
):
    """
    Raised when an Experiment cannot be edited.
    """


class ExperimentDeleteError(
    ExperimentServiceError
):
    """
    Raised when permanent deletion is not allowed.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class ExperimentStatistics:
    """
    Summary information for an Experiment collection.
    """

    total_count: int
    draft_count: int
    active_count: int
    completed_count: int
    archived_count: int
    failed_count: int


class ExperimentService:
    """
    Business service for Experiment CRUD operations.
    """

    ENTITY_TYPE = "Experiment"

    EDITABLE_STATUSES = {
        Experiment.Status.DRAFT,
        Experiment.Status.CHATTING,
    }

    ACTIVE_STATUSES = {
        Experiment.Status.CHATTING,
        Experiment.Status.READY_FOR_ANALYSIS,
        Experiment.Status.ANALYZING,
        Experiment.Status.PROPOSALS_READY,
        Experiment.Status.PARTIALLY_APPROVED,
        Experiment.Status.APPROVED,
        Experiment.Status.TWIN_CREATED,
    }

    COMPLETED_STATUSES = {
        Experiment.Status.COMPLETED,
        Experiment.Status.TWIN_CREATED,
    }

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        form: ExperimentForm,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> Experiment:
        """
        Create an Experiment and preserve a snapshot of its source twin.
        """

        cls._validate_actor(user)
        cls._validate_form(form)

        experiment = form.save(
            commit=False
        )

        cls._validate_source_twin(
            experiment.digital_twin
        )

        experiment.created_by = user
        experiment.status = (
            Experiment.Status.DRAFT
        )
        experiment.base_snapshot = (
            cls.build_digital_twin_snapshot(
                experiment.digital_twin
            )
        )
        experiment.ip_address = (
            ip_address
        )
        experiment.computer_name = (
            cls._clean_metadata_text(
                computer_name,
                max_length=255,
            )
        )

        experiment.full_clean()
        experiment.save()

        form.save_m2m()

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.CREATE,
            experiment=experiment,
            details={
                "operation": "create",
                "name": experiment.name,
                "status": experiment.status,
                "digital_twin_id": str(
                    experiment.digital_twin_id
                ),
                "digital_twin_part_number": (
                    experiment
                    .digital_twin
                    .part_number
                ),
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return experiment

    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        experiment: Experiment,
        form: ExperimentForm,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> Experiment:
        """
        Update the editable descriptive fields of an Experiment.
        """

        cls._validate_actor(user)
        cls._validate_saved_experiment(
            experiment
        )
        cls._validate_form(form)

        if form.instance.pk != experiment.pk:
            raise ExperimentServiceError(
                "The form instance does not match "
                "the Experiment being updated."
            )

        locked_experiment = (
            cls.base_queryset()
            .select_for_update()
            .get(pk=experiment.pk)
        )

        cls.validate_before_update(
            locked_experiment
        )

        before = (
            cls.build_experiment_snapshot(
                locked_experiment
            )
        )

        updated_experiment = form.save(
            commit=False
        )

        updated_experiment.pk = (
            locked_experiment.pk
        )

        updated_experiment.digital_twin = (
            locked_experiment.digital_twin
        )
        updated_experiment.created_by = (
            locked_experiment.created_by
        )
        updated_experiment.status = (
            locked_experiment.status
        )
        updated_experiment.base_snapshot = (
            locked_experiment.base_snapshot
        )
        updated_experiment.changed_parameters = (
            locked_experiment
            .changed_parameters
        )
        updated_experiment.experimental_values = (
            locked_experiment
            .experimental_values
        )
        updated_experiment.calculated_results = (
            locked_experiment
            .calculated_results
        )
        updated_experiment.external_results = (
            locked_experiment
            .external_results
        )
        updated_experiment.local_analysis = (
            locked_experiment
            .local_analysis
        )
        updated_experiment.result_twin = (
            locked_experiment.result_twin
        )
        updated_experiment.approved_by = (
            locked_experiment.approved_by
        )
        updated_experiment.approved_at = (
            locked_experiment.approved_at
        )
        updated_experiment.completed_at = (
            locked_experiment.completed_at
        )
        updated_experiment.analysis_started_at = (
            locked_experiment
            .analysis_started_at
        )
        updated_experiment.analysis_completed_at = (
            locked_experiment
            .analysis_completed_at
        )

        updated_experiment.full_clean()
        updated_experiment.save()

        form.save_m2m()

        after = (
            cls.build_experiment_snapshot(
                updated_experiment
            )
        )

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            experiment=updated_experiment,
            details={
                "operation": "update",
                "before": before,
                "after": after,
                "changed_fields": (
                    cls._find_changed_fields(
                        before=before,
                        after=after,
                    )
                ),
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return updated_experiment

    @classmethod
    def validate_before_update(
        cls,
        experiment: Experiment,
    ) -> None:
        """
        Ensure the Experiment is still editable.
        """

        cls._validate_saved_experiment(
            experiment
        )

        if (
            experiment.status
            not in cls.EDITABLE_STATUSES
        ):
            raise ExperimentUpdateError(
                "Only Draft or Chatting experiments "
                "can be edited."
            )

        if experiment.result_twin_id is not None:
            raise ExperimentUpdateError(
                "An Experiment that already produced "
                "a result twin cannot be edited."
            )

    @classmethod
    @transaction.atomic
    def archive(
        cls,
        *,
        experiment: Experiment,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> Experiment:
        """
        Archive an Experiment without deleting its engineering history.
        """

        cls._validate_actor(user)
        cls._validate_saved_experiment(
            experiment
        )

        locked_experiment = (
            Experiment.objects
            .select_for_update()
            .get(pk=experiment.pk)
        )

        previous_status = (
            locked_experiment.status
        )

        if (
            previous_status
            == Experiment.Status.ARCHIVED
        ):
            return locked_experiment

        locked_experiment.status = (
            Experiment.Status.ARCHIVED
        )

        locked_experiment.full_clean()

        locked_experiment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._create_audit_log(
            user=user,
            action=AuditLog.Action.UPDATE,
            experiment=locked_experiment,
            details={
                "operation": "archive",
                "previous_status": (
                    previous_status
                ),
                "new_status": (
                    Experiment.Status.ARCHIVED
                ),
            },
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return locked_experiment

    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        experiment: Experiment,
        user,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> UUID:
        """
        Permanently delete an unused Draft Experiment.
        """

        cls._validate_actor(user)
        cls._validate_saved_experiment(
            experiment
        )

        locked_experiment = (
            cls.base_queryset()
            .select_for_update()
            .get(pk=experiment.pk)
        )

        cls.validate_before_delete(
            locked_experiment
        )

        experiment_id = (
            locked_experiment.pk
        )

        snapshot = (
            cls.build_experiment_snapshot(
                locked_experiment
            )
        )

        locked_experiment.delete()

        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.DELETE,
            entity_type=cls.ENTITY_TYPE,
            entity_id=str(
                experiment_id
            ),
            details={
                "operation": "delete",
                "deleted_experiment": snapshot,
            },
            ip_address=ip_address,
            computer_name=(
                cls._clean_metadata_text(
                    computer_name,
                    max_length=255,
                )
            ),
            user_agent=(
                cls._clean_metadata_text(
                    user_agent
                )
            ),
        )

        return experiment_id

    @classmethod
    def validate_before_delete(
        cls,
        experiment: Experiment,
    ) -> None:
        """
        Ensure permanent deletion does not destroy engineering history.
        """

        cls._validate_saved_experiment(
            experiment
        )

        if (
            experiment.status
            != Experiment.Status.DRAFT
        ):
            raise ExperimentDeleteError(
                "Only Draft experiments can be "
                "deleted permanently. Archive this "
                "experiment instead."
            )

        if experiment.result_twin_id is not None:
            raise ExperimentDeleteError(
                "An Experiment with a result twin "
                "cannot be deleted."
            )

        if experiment.chat_messages.exists():
            raise ExperimentDeleteError(
                "An Experiment with chat history "
                "cannot be deleted."
            )

        if experiment.proposals.exists():
            raise ExperimentDeleteError(
                "An Experiment with engineering "
                "proposals cannot be deleted."
            )

        if experiment.external_results:
            raise ExperimentDeleteError(
                "An Experiment with external AI "
                "results cannot be deleted."
            )

        if experiment.local_analysis:
            raise ExperimentDeleteError(
                "An Experiment with local analysis "
                "cannot be deleted."
            )

    @classmethod
    def get_by_id(
        cls,
        experiment_id: UUID | str,
    ) -> Experiment:
        """
        Return one Experiment by UUID.
        """

        try:
            return cls.base_queryset().get(
                pk=experiment_id
            )
        except (
            Experiment.DoesNotExist,
            ValidationError,
            ValueError,
            TypeError,
        ) as error:
            raise ExperimentNotFoundError(
                f"Experiment '{experiment_id}' "
                "was not found."
            ) from error

    @classmethod
    def base_queryset(
        cls,
    ) -> QuerySet[Experiment]:
        """
        Return the common optimized Experiment queryset.
        """

        return (
            Experiment.objects
            .select_related(
                "digital_twin",
                "digital_twin__material",
                "digital_twin__technology",
                "result_twin",
                "created_by",
                "approved_by",
            )
            .prefetch_related(
                "chat_messages",
                "proposals",
            )
        )

    @classmethod
    def search(
        cls,
        *,
        queryset: (
            QuerySet[Experiment] | None
        ) = None,
        query: str = "",
        digital_twin: (
            DigitalTwin | None
        ) = None,
        status: str = "",
    ) -> QuerySet[Experiment]:
        """
        Search and filter Experiments.
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
                    name__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    description__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    objective__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    digital_twin__name__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    digital_twin__part_number__icontains=(
                        normalized_query
                    )
                )
            )

        if digital_twin is not None:
            result = result.filter(
                digital_twin=digital_twin
            )

        normalized_status = str(
            status or ""
        ).strip()

        if normalized_status:
            valid_statuses = {
                value
                for value, _label
                in Experiment.Status.choices
            }

            if (
                normalized_status
                not in valid_statuses
            ):
                raise ValueError(
                    "Unknown Experiment status."
                )

            result = result.filter(
                status=normalized_status
            )

        return result.distinct().order_by(
            "-created_at"
        )

    @classmethod
    def get_statistics(
        cls,
        queryset: (
            QuerySet[Experiment] | None
        ) = None,
    ) -> ExperimentStatistics:
        """
        Calculate Experiment list statistics.
        """

        result = (
            queryset
            if queryset is not None
            else Experiment.objects.all()
        )

        return ExperimentStatistics(
            total_count=result.count(),
            draft_count=result.filter(
                status=Experiment.Status.DRAFT
            ).count(),
            active_count=result.filter(
                status__in=cls.ACTIVE_STATUSES
            ).count(),
            completed_count=result.filter(
                status__in=(
                    cls.COMPLETED_STATUSES
                )
            ).count(),
            archived_count=result.filter(
                status=(
                    Experiment.Status.ARCHIVED
                )
            ).count(),
            failed_count=result.filter(
                status=(
                    Experiment.Status.FAILED
                )
            ).count(),
        )

    @classmethod
    def build_digital_twin_snapshot(
        cls,
        digital_twin: DigitalTwin,
    ) -> dict[str, Any]:
        """
        Build a JSON-safe source Digital Twin snapshot.
        """

        if not isinstance(
            digital_twin,
            DigitalTwin,
        ):
            raise TypeError(
                "digital_twin must be a "
                "DigitalTwin instance."
            )

        if digital_twin.pk is None:
            raise ExperimentServiceError(
                "The source Digital Twin must "
                "be saved."
            )

        return {
            "id": str(
                digital_twin.pk
            ),
            "name": digital_twin.name,
            "part_number": (
                digital_twin.part_number
            ),
            "description": (
                digital_twin.description
            ),
            "material": (
                {
                    "id": (
                        digital_twin.material_id
                    ),
                    "code": (
                        digital_twin.material.code
                    ),
                    "name": (
                        digital_twin.material.name
                    ),
                    "density_kg_m3": (
                        cls._decimal_to_string(
                            digital_twin
                            .material
                            .density_kg_m3
                        )
                    ),
                    "price_per_kg": (
                        cls._decimal_to_string(
                            digital_twin
                            .material
                            .price_per_kg
                        )
                    ),
                }
                if digital_twin.material
                is not None
                else None
            ),
            "technology": (
                {
                    "id": (
                        digital_twin
                        .technology_id
                    ),
                    "code": (
                        digital_twin
                        .technology
                        .code
                    ),
                    "name": (
                        digital_twin
                        .technology
                        .name
                    ),
                    "machine_hour_rate": (
                        cls._decimal_to_string(
                            digital_twin
                            .technology
                            .machine_hour_rate
                        )
                    ),
                }
                if digital_twin.technology
                is not None
                else None
            ),
            "volume_m3": (
                cls._decimal_to_string(
                    digital_twin.volume_m3
                )
            ),
            "mass_kg": (
                cls._decimal_to_string(
                    digital_twin.mass_kg
                )
            ),
            "effective_mass_kg": (
                cls._decimal_to_string(
                    digital_twin
                    .effective_mass_kg
                )
            ),
            "production_time_minutes": (
                cls._decimal_to_string(
                    digital_twin
                    .production_time_minutes
                )
            ),
            "labor_cost": (
                cls._decimal_to_string(
                    digital_twin.labor_cost
                )
            ),
            "energy_cost": (
                cls._decimal_to_string(
                    digital_twin.energy_cost
                )
            ),
            "defect_rate_percent": (
                cls._decimal_to_string(
                    digital_twin
                    .defect_rate_percent
                )
            ),
            "desired_profit_margin_percent": (
                cls._decimal_to_string(
                    digital_twin
                    .desired_profit_margin_percent
                )
            ),
            "estimated_material_cost": (
                cls._decimal_to_string(
                    digital_twin
                    .estimated_material_cost
                )
            ),
            "estimated_machine_cost": (
                cls._decimal_to_string(
                    digital_twin
                    .estimated_machine_cost
                )
            ),
            "estimated_total_cost": (
                cls._decimal_to_string(
                    digital_twin
                    .estimated_total_cost
                )
            ),
            "estimated_selling_price": (
                cls._decimal_to_string(
                    digital_twin
                    .estimated_selling_price
                )
            ),
            "estimated_profit": (
                cls._decimal_to_string(
                    digital_twin
                    .estimated_profit
                )
            ),
            "is_active": (
                digital_twin.is_active
            ),
            "created_at": (
                digital_twin
                .created_at
                .isoformat()
                if digital_twin.created_at
                else None
            ),
            "updated_at": (
                digital_twin
                .updated_at
                .isoformat()
                if digital_twin.updated_at
                else None
            ),
        }

    @classmethod
    def build_experiment_snapshot(
        cls,
        experiment: Experiment,
    ) -> dict[str, Any]:
        """
        Build a JSON-safe Experiment snapshot.
        """

        if not isinstance(
            experiment,
            Experiment,
        ):
            raise TypeError(
                "experiment must be an "
                "Experiment instance."
            )

        return {
            "id": (
                str(experiment.pk)
                if experiment.pk
                else None
            ),
            "digital_twin_id": (
                str(
                    experiment
                    .digital_twin_id
                )
                if experiment
                .digital_twin_id
                else None
            ),
            "name": experiment.name,
            "description": (
                experiment.description
            ),
            "objective": (
                experiment.objective
            ),
            "status": (
                experiment.status
            ),
            "result_twin_id": (
                str(
                    experiment
                    .result_twin_id
                )
                if experiment
                .result_twin_id
                else None
            ),
            "created_by_id": (
                experiment.created_by_id
            ),
        }

    @staticmethod
    def _validate_actor(
        user,
    ) -> None:
        """
        Require a saved, active, authenticated user.
        """

        if user is None:
            raise ExperimentServiceError(
                "A user is required."
            )

        if getattr(
            user,
            "pk",
            None,
        ) is None:
            raise ExperimentServiceError(
                "The user must be saved."
            )

        if not getattr(
            user,
            "is_authenticated",
            False,
        ):
            raise ExperimentServiceError(
                "An authenticated user "
                "is required."
            )

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise ExperimentServiceError(
                "An active user is required."
            )

    @staticmethod
    def _validate_form(
        form: ExperimentForm,
    ) -> None:
        """
        Require a valid bound ExperimentForm.
        """

        if not isinstance(
            form,
            ExperimentForm,
        ):
            raise TypeError(
                "form must be an "
                "ExperimentForm instance."
            )

        if not form.is_bound:
            raise ExperimentServiceError(
                "The Experiment form must "
                "be bound to data."
            )

        if not form.is_valid():
            raise ExperimentServiceError(
                "The Experiment form contains "
                "validation errors."
            )

    @staticmethod
    def _validate_source_twin(
        digital_twin: DigitalTwin,
    ) -> None:
        """
        Require an existing active Digital Twin.
        """

        if not isinstance(
            digital_twin,
            DigitalTwin,
        ):
            raise TypeError(
                "The source must be a "
                "DigitalTwin instance."
            )

        if digital_twin.pk is None:
            raise ExperimentServiceError(
                "The source Digital Twin "
                "must be saved."
            )

        if not digital_twin.is_active:
            raise ExperimentServiceError(
                "New Experiments can only be "
                "created for active Digital Twins."
            )

    @staticmethod
    def _validate_saved_experiment(
        experiment: Experiment,
    ) -> None:
        """
        Require a persisted Experiment.
        """

        if not isinstance(
            experiment,
            Experiment,
        ):
            raise TypeError(
                "experiment must be an "
                "Experiment instance."
            )

        if experiment.pk is None:
            raise ExperimentServiceError(
                "The Experiment must be saved."
            )

        if not Experiment.objects.filter(
            pk=experiment.pk
        ).exists():
            raise ExperimentNotFoundError(
                "The Experiment no longer exists."
            )

    @classmethod
    def _create_audit_log(
        cls,
        *,
        user,
        action: str,
        experiment: Experiment,
        details: dict[str, Any],
        ip_address: str | None,
        computer_name: str,
        user_agent: str,
    ) -> AuditLog:
        """
        Create a standardized Experiment audit entry.
        """

        return AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=cls.ENTITY_TYPE,
            entity_id=str(
                experiment.pk
            ),
            details=details,
            ip_address=ip_address,
            computer_name=(
                cls._clean_metadata_text(
                    computer_name,
                    max_length=255,
                )
            ),
            user_agent=(
                cls._clean_metadata_text(
                    user_agent
                )
            ),
        )

    @staticmethod
    def _find_changed_fields(
        *,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> list[str]:
        """
        Return fields whose values changed.
        """

        return sorted(
            key
            for key
            in before.keys() | after.keys()
            if before.get(key)
            != after.get(key)
        )

    @staticmethod
    def _clean_metadata_text(value: Any, *, max_length: int | None = None,) -> str:
        """
        Normalize optional audit metadata.
        """

        result = str(value or "").strip()

        if max_length is not None:
            result = result[:max_length]

        return result

    @staticmethod
    def _decimal_to_string(value: Decimal | None,) -> str | None:
        """
        Convert Decimal values to JSON-safe strings.
        """

        if value is None:
            return None

        return str(value)
