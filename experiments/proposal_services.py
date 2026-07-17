"""
Engineer review operations for experiment proposals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from experiments.models import (
    Experiment,
    ExperimentProposal,
)


class ProposalReviewError(RuntimeError):
    """
    Raised when a proposal cannot be reviewed.
    """


@dataclass(frozen=True, slots=True)
class ProposalReviewSummary:
    approved_count: int
    rejected_count: int
    pending_count: int

    @property
    def reviewed_count(self) -> int:
        return (
            self.approved_count
            + self.rejected_count
        )


class ProposalReviewService:
    """
    Approve or reject proposals without modifying a digital twin.
    """

    @transaction.atomic
    def approve(
        self,
        *,
        proposal: ExperimentProposal,
        reviewed_by,
        note: str = "",
    ) -> ExperimentProposal:
        return self._review(
            proposal=proposal,
            status=(
                ExperimentProposal.Status.APPROVED
            ),
            reviewed_by=reviewed_by,
            note=note,
        )

    @transaction.atomic
    def reject(
        self,
        *,
        proposal: ExperimentProposal,
        reviewed_by,
        note: str = "",
    ) -> ExperimentProposal:
        return self._review(
            proposal=proposal,
            status=(
                ExperimentProposal.Status.REJECTED
            ),
            reviewed_by=reviewed_by,
            note=note,
        )

    @transaction.atomic
    def review_many(
        self,
        *,
        approved: Iterable[ExperimentProposal],
        rejected: Iterable[ExperimentProposal],
        reviewed_by,
        note: str = "",
    ) -> ProposalReviewSummary:
        approved_items = list(approved)
        rejected_items = list(rejected)

        proposal_ids = {
            proposal.pk
            for proposal in (
                approved_items
                + rejected_items
            )
        }

        if len(proposal_ids) != (
            len(approved_items)
            + len(rejected_items)
        ):
            raise ProposalReviewError(
                "A proposal cannot be both approved "
                "and rejected in the same operation."
            )

        experiments = {
            proposal.experiment_id
            for proposal in (
                approved_items
                + rejected_items
            )
        }

        if len(experiments) > 1:
            raise ProposalReviewError(
                "All reviewed proposals must belong "
                "to the same experiment."
            )

        for proposal in approved_items:
            self._review(
                proposal=proposal,
                status=(
                    ExperimentProposal.Status.APPROVED
                ),
                reviewed_by=reviewed_by,
                note=note,
            )

        for proposal in rejected_items:
            self._review(
                proposal=proposal,
                status=(
                    ExperimentProposal.Status.REJECTED
                ),
                reviewed_by=reviewed_by,
                note=note,
            )

        if experiments:
            experiment = Experiment.objects.get(
                pk=next(iter(experiments))
            )

            return self._update_experiment_status(
                experiment
            )

        return ProposalReviewSummary(
            approved_count=0,
            rejected_count=0,
            pending_count=0,
        )

    def summarize(
        self,
        *,
        experiment: Experiment,
    ) -> ProposalReviewSummary:
        return ProposalReviewSummary(
            approved_count=(
                experiment.proposals.filter(
                    status=(
                        ExperimentProposal
                        .Status.APPROVED
                    )
                ).count()
            ),
            rejected_count=(
                experiment.proposals.filter(
                    status=(
                        ExperimentProposal
                        .Status.REJECTED
                    )
                ).count()
            ),
            pending_count=(
                experiment.proposals.filter(
                    status=(
                        ExperimentProposal
                        .Status.PENDING
                    )
                ).count()
            ),
        )

    def _review(
        self,
        *,
        proposal: ExperimentProposal,
        status: str,
        reviewed_by,
        note: str,
    ) -> ExperimentProposal:
        if proposal.pk is None:
            raise ProposalReviewError(
                "The proposal must be saved before review."
            )

        if reviewed_by is None:
            raise ProposalReviewError(
                "The reviewing engineer is required."
            )

        if (
            proposal.status
            != ExperimentProposal.Status.PENDING
        ):
            raise ProposalReviewError(
                "Only pending proposals can be reviewed."
            )

        proposal.status = status
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = timezone.now()
        proposal.review_note = str(note or "").strip()

        proposal.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "review_note",
                "updated_at",
            ]
        )

        self._update_experiment_status(
            proposal.experiment
        )

        return proposal

    def _update_experiment_status(
        self,
        experiment: Experiment,
    ) -> ProposalReviewSummary:
        summary = self.summarize(
            experiment=experiment
        )

        if summary.pending_count > 0:
            if summary.reviewed_count > 0:
                new_status = (
                    Experiment.Status
                    .PARTIALLY_APPROVED
                )
            else:
                new_status = (
                    Experiment.Status
                    .PROPOSALS_READY
                )

        elif summary.approved_count > 0:
            new_status = Experiment.Status.APPROVED

        else:
            new_status = Experiment.Status.COMPLETED

        experiment.status = new_status

        if new_status == Experiment.Status.APPROVED:
            experiment.approved_at = timezone.now()

        experiment.save(
            update_fields=[
                "status",
                "approved_at",
                "updated_at",
            ]
        )

        return summary
