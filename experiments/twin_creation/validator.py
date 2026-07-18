"""Validation rules for finalizing an engineering experiment."""

from __future__ import annotations

from experiments.models import Experiment, ExperimentProposal

from .exceptions import TwinCreationError


class TwinCreationValidator:
    """Validate input and experiment state before creating a result twin."""

    @staticmethod
    def validate_input(
        *,
        experiment: Experiment,
        created_by,
    ) -> None:
        if not isinstance(experiment, Experiment):
            raise TypeError(
                "experiment must be an Experiment instance."
            )

        if experiment._state.adding:
            raise TwinCreationError(
                "The experiment must be saved before "
                "a Digital Twin can be created."
            )

        if created_by is None:
            raise TwinCreationError(
                "A saved engineer is required to create "
                "the new Digital Twin."
            )

        if getattr(created_by, "_state", None) is None or created_by._state.adding:
            raise TwinCreationError(
                "A saved engineer is required to create "
                "the new Digital Twin."
            )

    @staticmethod
    def validate_experiment(
        experiment: Experiment,
    ) -> None:
        if experiment.result_twin_id is not None:
            raise TwinCreationError(
                "This experiment already has a result Digital Twin."
            )

        if experiment.status != Experiment.Status.APPROVED:
            raise TwinCreationError(
                "The experiment must have status APPROVED "
                "before a new Digital Twin can be created."
            )

        pending_proposals_exist = experiment.proposals.filter(
            status=ExperimentProposal.Status.PENDING
        ).exists()

        if pending_proposals_exist:
            raise TwinCreationError(
                "All pending proposals must be reviewed "
                "before a new Digital Twin can be created."
            )

    @staticmethod
    def validate_approved_proposals(
        proposals: list[ExperimentProposal],
    ) -> None:
        if not proposals:
            raise TwinCreationError(
                "At least one approved proposal is required "
                "to create a new Digital Twin."
            )
