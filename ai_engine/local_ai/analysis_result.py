"""
Structured results produced by the local engineering agent.

These classes are independent from Django models. They define the
internal Python representation of the JSON returned by the local LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


ALLOWED_PROPOSAL_CATEGORIES = {
    "MATERIAL",
    "TECHNOLOGY",
    "GEOMETRY",
    "COST",
    "QUALITY",
    "PRODUCTION",
    "SAFETY",
    "OTHER",
}

ALLOWED_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN",
}


class EngineeringAnalysisValidationError(ValueError):
    """
    Raised when the structured local-AI result is invalid.
    """


@dataclass(frozen=True, slots=True)
class EngineeringConflict:
    topic: str
    description: str
    sources: tuple[str, ...] = ()

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "EngineeringConflict":
        return cls(
            topic=_required_text(
                value,
                "topic",
            ),
            description=_required_text(
                value,
                "description",
            ),
            sources=tuple(
                _string_list(
                    value.get("sources", [])
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class EngineeringProposal:
    category: str
    title: str
    description: str
    parameter_name: str | None
    current_value: Any
    proposed_value: Any
    unit: str | None
    reason: str
    expected_benefit: str
    risk_level: str
    confidence_percent: int
    requires_validation: bool
    validation_requirements: tuple[str, ...] = ()

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "EngineeringProposal":
        category = _required_text(
            value,
            "category",
        ).upper()

        if category not in ALLOWED_PROPOSAL_CATEGORIES:
            raise EngineeringAnalysisValidationError(
                f"Unsupported proposal category: {category}"
            )

        risk_level = _required_text(
            value,
            "risk_level",
        ).upper()

        if risk_level not in ALLOWED_RISK_LEVELS:
            raise EngineeringAnalysisValidationError(
                f"Unsupported risk level: {risk_level}"
            )

        confidence = _percentage(
            value.get("confidence_percent"),
            field_name="confidence_percent",
        )

        requires_validation = value.get(
            "requires_validation"
        )

        if not isinstance(
            requires_validation,
            bool,
        ):
            raise EngineeringAnalysisValidationError(
                "requires_validation must be a boolean."
            )

        return cls(
            category=category,
            title=_required_text(
                value,
                "title",
            ),
            description=_required_text(
                value,
                "description",
            ),
            parameter_name=_optional_text(
                value.get("parameter_name")
            ),
            current_value=value.get(
                "current_value"
            ),
            proposed_value=value.get(
                "proposed_value"
            ),
            unit=_optional_text(
                value.get("unit")
            ),
            reason=_required_text(
                value,
                "reason",
            ),
            expected_benefit=_required_text(
                value,
                "expected_benefit",
            ),
            risk_level=risk_level,
            confidence_percent=confidence,
            requires_validation=(
                requires_validation
            ),
            validation_requirements=tuple(
                _string_list(
                    value.get(
                        "validation_requirements",
                        [],
                    )
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class EngineeringAnalysisResult:
    summary: str
    findings: tuple[str, ...] = ()
    conflicts: tuple[
        EngineeringConflict,
        ...
    ] = ()
    missing_information: tuple[str, ...] = ()
    proposals: tuple[
        EngineeringProposal,
        ...
    ] = ()
    overall_confidence_percent: int = 0
    requires_engineer_review: bool = True

    model_name: str = ""
    response_time_ms: float | None = None
    prompt_token_count: int | None = None
    output_token_count: int | None = None

    raw_structured_response: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
    )

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        model_name: str = "",
        response_time_ms: float | None = None,
        prompt_token_count: int | None = None,
        output_token_count: int | None = None,
    ) -> "EngineeringAnalysisResult":
        if not isinstance(value, Mapping):
            raise EngineeringAnalysisValidationError(
                "Engineering analysis must be an object."
            )

        requires_review = value.get(
            "requires_engineer_review"
        )

        if requires_review is not True:
            raise EngineeringAnalysisValidationError(
                "requires_engineer_review must be true."
            )

        conflicts_value = value.get(
            "conflicts",
            [],
        )

        proposals_value = value.get(
            "proposals",
            [],
        )

        if not isinstance(
            conflicts_value,
            list,
        ):
            raise EngineeringAnalysisValidationError(
                "conflicts must be a list."
            )

        if not isinstance(
            proposals_value,
            list,
        ):
            raise EngineeringAnalysisValidationError(
                "proposals must be a list."
            )

        return cls(
            summary=_required_text(
                value,
                "summary",
            ),
            findings=tuple(
                _string_list(
                    value.get("findings", [])
                )
            ),
            conflicts=tuple(
                EngineeringConflict.from_dict(item)
                for item in conflicts_value
                if isinstance(item, Mapping)
            ),
            missing_information=tuple(
                _string_list(
                    value.get(
                        "missing_information",
                        [],
                    )
                )
            ),
            proposals=tuple(
                EngineeringProposal.from_dict(item)
                for item in proposals_value
                if isinstance(item, Mapping)
            ),
            overall_confidence_percent=(
                _percentage(
                    value.get(
                        "overall_confidence_percent"
                    ),
                    field_name=(
                        "overall_confidence_percent"
                    ),
                )
            ),
            requires_engineer_review=True,
            model_name=str(
                model_name or ""
            ).strip(),
            response_time_ms=response_time_ms,
            prompt_token_count=prompt_token_count,
            output_token_count=output_token_count,
            raw_structured_response=dict(value),
        )

    @property
    def proposal_count(self) -> int:
        return len(self.proposals)

    @property
    def has_proposals(self) -> bool:
        return bool(self.proposals)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result into JSON-serializable data.
        """

        result = asdict(self)

        result["findings"] = list(
            self.findings
        )

        result["missing_information"] = list(
            self.missing_information
        )

        result["conflicts"] = [
            {
                **asdict(conflict),
                "sources": list(
                    conflict.sources
                ),
            }
            for conflict in self.conflicts
        ]

        result["proposals"] = [
            {
                **asdict(proposal),
                "validation_requirements": list(
                    proposal.validation_requirements
                ),
            }
            for proposal in self.proposals
        ]

        return result


def _required_text(
    value: Mapping[str, Any],
    key: str,
) -> str:
    text = str(
        value.get(key, "")
    ).strip()

    if not text:
        raise EngineeringAnalysisValidationError(
            f"{key} cannot be empty."
        )

    return text


def _optional_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _string_list(
    value: Any,
) -> list[str]:
    if not isinstance(value, list):
        raise EngineeringAnalysisValidationError(
            "Expected a list of strings."
        )

    result: list[str] = []

    for item in value:
        text = str(item).strip()

        if text:
            result.append(text)

    return result


def _percentage(
    value: Any,
    *,
    field_name: str,
) -> int:
    if isinstance(value, bool):
        raise EngineeringAnalysisValidationError(
            f"{field_name} must be an integer."
        )

    try:
        number = int(value)

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise EngineeringAnalysisValidationError(
            f"{field_name} must be an integer."
        ) from exc

    if not 0 <= number <= 100:
        raise EngineeringAnalysisValidationError(
            f"{field_name} must be between 0 and 100."
        )

    return number
