"""
Persistence of structured local-AI engineering proposals.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from ai_engine.local_ai.analysis_result import (
    EngineeringAnalysisResult,
    EngineeringProposal,
)
from ai_engine.local_ai.proposal_validator import (
    ProposalValidator,
)
from ai_engine.models import InternalAnalysis
from experiments.models import (
    Experiment,
    ExperimentProposal,
)


class ProposalGenerationError(RuntimeError):
    """
    Raised when proposals cannot be generated safely.
    """


@dataclass(frozen=True, slots=True)
class ProposalGenerationResult:
    """
    Summary of one proposal-generation operation.
    """

    created: tuple[ExperimentProposal, ...]
    skipped_count: int
    warnings: tuple[str, ...]

    @property
    def created_count(self) -> int:
        return len(self.created)


class ProposalGenerator:
    """
    Convert EngineeringAnalysisResult proposals into Django records.
    """

    def __init__(
        self,
        *,
        validator: ProposalValidator | None = None,
    ) -> None:
        self.validator = (
            validator or ProposalValidator()
        )

    @transaction.atomic
    def generate(
        self,
        *,
        experiment: Experiment,
        analysis_result: EngineeringAnalysisResult,
        internal_analysis: InternalAnalysis | None = None,
        replace_pending: bool = True,
    ) -> ProposalGenerationResult:
        """
        Create persistent proposals for one experiment.

        Existing reviewed proposals are never deleted.

        When replace_pending is True, old pending proposals are marked
        as SUPERSEDED before the new analysis proposals are created.
        """

        self._validate_input(
            experiment=experiment,
            analysis_result=analysis_result,
        )

        if replace_pending:
            ExperimentProposal.objects.filter(
                experiment=experiment,
                status=ExperimentProposal.Status.PENDING,
            ).update(
                status=(
                    ExperimentProposal.Status.SUPERSEDED
                ),
            )

        created: list[ExperimentProposal] = []
        warnings: list[str] = []
        skipped_count = 0

        for proposal in analysis_result.proposals:
            validation = self.validator.validate(
                proposal
            )

            warnings.extend(
                f"{proposal.title}: {warning}"
                for warning in validation.warnings
            )

            if not validation.is_valid:
                skipped_count += 1

                warnings.extend(
                    f"{proposal.title}: {error}"
                    for error in validation.errors
                )

                continue

            created.append(
                self._create_proposal(
                    experiment=experiment,
                    proposal=proposal,
                    internal_analysis=internal_analysis,
                    validation_warnings=(
                        validation.warnings
                    ),
                )
            )

        return ProposalGenerationResult(
            created=tuple(created),
            skipped_count=skipped_count,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_input(
        *,
        experiment: Experiment,
        analysis_result: EngineeringAnalysisResult,
    ) -> None:
        if not isinstance(
            experiment,
            Experiment,
        ):
            raise TypeError(
                "experiment must be an Experiment instance."
            )

        if experiment.pk is None:
            raise ProposalGenerationError(
                "The experiment must be saved before "
                "proposals are generated."
            )

        if not isinstance(
            analysis_result,
            EngineeringAnalysisResult,
        ):
            raise TypeError(
                "analysis_result must be an "
                "EngineeringAnalysisResult instance."
            )

    @staticmethod
    def _create_proposal(
        *,
        experiment: Experiment,
        proposal: EngineeringProposal,
        internal_analysis: InternalAnalysis | None,
        validation_warnings: tuple[str, ...],
    ) -> ExperimentProposal:
        review_note = ""

        if validation_warnings:
            review_note = (
                "Automatic validation warnings:\n- "
                + "\n- ".join(validation_warnings)
            )

        return ExperimentProposal.objects.create(
            experiment=experiment,
            internal_analysis=internal_analysis,
            category=proposal.category,
            title=proposal.title,
            description=proposal.description,
            parameter_name=proposal.parameter_name,
            current_value=proposal.current_value,
            proposed_value=proposal.proposed_value,
            unit=proposal.unit,
            reason=proposal.reason,
            expected_benefit=(
                proposal.expected_benefit
            ),
            risk_level=proposal.risk_level,
            confidence_percent=(
                proposal.confidence_percent
            ),
            requires_validation=(
                proposal.requires_validation
            ),
            validation_requirements=list(
                proposal.validation_requirements
            ),
            status=(
                ExperimentProposal.Status.PENDING
            ),
            review_note=review_note,
        )
