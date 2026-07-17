"""
Validation of engineering proposals before database persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engine.local_ai.analysis_result import (
    EngineeringProposal,
)
from digital_twins.models import (
    MaterialCatalog,
    TechnologyCatalog,
)


@dataclass(frozen=True, slots=True)
class ProposalValidationResult:
    """
    Result of validating one local-AI proposal.
    """

    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ProposalValidator:
    """
    Validate proposals against local project rules and catalogs.

    The validator does not approve or reject proposals.
    It only verifies whether they are suitable for persistence
    and later engineering review.
    """

    def validate(
        self,
        proposal: EngineeringProposal,
    ) -> ProposalValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not proposal.title.strip():
            errors.append(
                "Proposal title cannot be empty."
            )

        if not proposal.reason.strip():
            errors.append(
                "Proposal reason cannot be empty."
            )

        if not 0 <= proposal.confidence_percent <= 100:
            errors.append(
                "Confidence must be between 0 and 100."
            )

        if (
            proposal.proposed_value is None
            and proposal.parameter_name
        ):
            warnings.append(
                "The proposal identifies a parameter but "
                "does not provide a proposed value."
            )

        if proposal.category == "MATERIAL":
            self._validate_material_proposal(
                proposal=proposal,
                errors=errors,
                warnings=warnings,
            )

        if proposal.category == "TECHNOLOGY":
            self._validate_technology_proposal(
                proposal=proposal,
                errors=errors,
                warnings=warnings,
            )

        if (
            proposal.requires_validation
            and not proposal.validation_requirements
        ):
            warnings.append(
                "Validation is required, but no validation "
                "requirements were supplied."
            )

        return ProposalValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_material_proposal(
        *,
        proposal: EngineeringProposal,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        proposed_material = (
            ProposalValidator._normalize_text_value(
                proposal.proposed_value
            )
        )

        if not proposed_material:
            warnings.append(
                "Material proposal does not identify "
                "a target material."
            )
            return

        exists = MaterialCatalog.objects.filter(
            is_active=True,
        ).filter(
            name__iexact=proposed_material,
        ).exists() or MaterialCatalog.objects.filter(
            is_active=True,
            code__iexact=proposed_material,
        ).exists()

        if not exists:
            warnings.append(
                "The proposed material is not present "
                "in the active local material catalog."
            )

    @staticmethod
    def _validate_technology_proposal(
        *,
        proposal: EngineeringProposal,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        proposed_technology = (
            ProposalValidator._normalize_text_value(
                proposal.proposed_value
            )
        )

        if not proposed_technology:
            warnings.append(
                "Technology proposal does not identify "
                "a target technology."
            )
            return

        exists = TechnologyCatalog.objects.filter(
            is_active=True,
        ).filter(
            name__iexact=proposed_technology,
        ).exists() or TechnologyCatalog.objects.filter(
            is_active=True,
            code__iexact=proposed_technology,
        ).exists()

        if not exists:
            warnings.append(
                "The proposed technology is not present "
                "in the active local technology catalog."
            )

    @staticmethod
    def _normalize_text_value(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        if isinstance(value, dict):
            for key in (
                "code",
                "name",
                "value",
            ):
                candidate = value.get(key)

                if candidate is not None:
                    return str(candidate).strip()

            return ""

        return str(value).strip()
