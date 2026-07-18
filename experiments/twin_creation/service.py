"""Orchestrate creation of a derived Digital Twin."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from digital_twins.models import DigitalTwin
from experiments.models import (
    Experiment,
    ExperimentProposal,
)

from .audit_service import TwinCreationAuditService
from .proposal_applier import ProposalApplier
from .results import (
    AppliedProposalChange,
    ManualProposalChange,
    TwinCreationResult,
)
from .serializers import TwinCreationSerializer
from .twin_copier import DigitalTwinCopier
from .validator import TwinCreationValidator


class TwinCreationService:
    """
    Finalize an approved experiment by creating a derived Digital Twin.

    The original Digital Twin is never modified.
    """

    def __init__(
        self,
        *,
        validator: TwinCreationValidator | None = None,
        copier: DigitalTwinCopier | None = None,
        proposal_applier: ProposalApplier | None = None,
        serializer: TwinCreationSerializer | None = None,
        audit_service: TwinCreationAuditService | None = None,
    ) -> None:
        self.validator = (
            validator or TwinCreationValidator()
        )
        self.copier = copier or DigitalTwinCopier()
        self.proposal_applier = (
            proposal_applier or ProposalApplier()
        )
        self.serializer = (
            serializer or TwinCreationSerializer()
        )
        self.audit_service = (
            audit_service or TwinCreationAuditService()
        )

    @transaction.atomic
    def create(
        self,
        *,
        experiment: Experiment,
        created_by,
        part_number: str | None = None,
        name: str | None = None,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> TwinCreationResult:
        self.validator.validate_input(
            experiment=experiment,
            created_by=created_by,
        )

        locked_experiment = (
            Experiment.objects.select_for_update()
            .select_related(
                "digital_twin",
                "result_twin",
                "created_by",
                "approved_by",
            )
            .get(pk=experiment.pk)
        )

        self.validator.validate_experiment(
            locked_experiment
        )

        source_twin = (
            DigitalTwin.objects.select_for_update()
            .select_related(
                "material",
                "technology",
            )
            .get(
                pk=locked_experiment.digital_twin_id
            )
        )

        approved_proposals = list(
            locked_experiment.proposals.filter(
                status=(
                    ExperimentProposal.Status.APPROVED
                )
            ).order_by("sequence")
        )

        self.validator.validate_approved_proposals(
            approved_proposals
        )

        result_twin = self.copier.build_copy(
            source_twin=source_twin,
            created_by=created_by,
            part_number=part_number,
            name=name,
        )

        applied_changes: list[
            AppliedProposalChange
        ] = []

        manual_changes: list[
            ManualProposalChange
        ] = []

        for proposal in approved_proposals:
            change = self.proposal_applier.apply(
                twin=result_twin,
                proposal=proposal,
            )

            if isinstance(
                change,
                AppliedProposalChange,
            ):
                applied_changes.append(change)
            else:
                manual_changes.append(change)

        result_twin.full_clean()
        result_twin.save()

        copied_file_count = (
            self.copier.copy_related_files(
                source_twin=source_twin,
                result_twin=result_twin,
                uploaded_by=created_by,
            )
        )

        changed_parameters = (
            self.serializer.build_changed_parameters(
                applied_changes=applied_changes,
                manual_changes=manual_changes,
            )
        )

        calculated_results = (
            self.serializer.build_calculated_results(
                result_twin
            )
        )

        self._complete_experiment(
            experiment=locked_experiment,
            result_twin=result_twin,
            created_by=created_by,
            changed_parameters=changed_parameters,
            calculated_results=calculated_results,
        )

        self.audit_service.log_creation(
            experiment=locked_experiment,
            source_twin=source_twin,
            result_twin=result_twin,
            created_by=created_by,
            applied_change_count=len(
                applied_changes
            ),
            manual_change_count=len(
                manual_changes
            ),
            copied_file_count=copied_file_count,
            ip_address=ip_address,
            computer_name=computer_name,
            user_agent=user_agent,
        )

        return TwinCreationResult(
            source_twin=source_twin,
            result_twin=result_twin,
            applied_changes=tuple(applied_changes),
            manual_changes=tuple(manual_changes),
            copied_file_count=copied_file_count,
        )

    @staticmethod
    def _complete_experiment(
        *,
        experiment: Experiment,
        result_twin: DigitalTwin,
        created_by,
        changed_parameters: dict,
        calculated_results: dict,
    ) -> None:
        experiment.result_twin = result_twin
        experiment.status = (
            Experiment.Status.TWIN_CREATED
        )
        experiment.completed_at = timezone.now()
        experiment.changed_parameters = (
            changed_parameters
        )
        experiment.calculated_results = (
            calculated_results
        )

        if experiment.approved_by_id is None:
            experiment.approved_by = created_by

        experiment.full_clean()

        experiment.save(
            update_fields=[
                "result_twin",
                "status",
                "completed_at",
                "changed_parameters",
                "calculated_results",
                "approved_by",
                "updated_at",
            ]
        )
