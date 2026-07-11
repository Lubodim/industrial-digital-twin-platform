from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from ai_engine.schemas import (
    EMPTY_EXTERNAL_RESEARCH_RESULT,
    EXTERNAL_RESEARCH_SCHEMA_VERSION,
)


@dataclass
class ValidationResult:
    """
    Stores the result of a research JSON validation.
    """

    is_valid: bool
    normalized_data: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _merge_with_schema(
    schema: dict[str, Any],
    supplied_data: dict[str, Any],
    path: str = "",
) -> tuple[dict[str, Any], list[str]]:
    """
    Recursively merge supplied data with the standard schema.

    Missing keys are added automatically with their default empty values.
    Unknown keys are ignored and reported as warnings.
    """

    normalized = deepcopy(schema)
    warnings: list[str] = []

    for key, value in supplied_data.items():
        current_path = f"{path}.{key}" if path else key

        if key not in schema:
            warnings.append(f"Unknown key ignored: {current_path}")
            continue

        expected_value = schema[key]

        if isinstance(expected_value, dict):
            if value is None:
                normalized[key] = deepcopy(expected_value)
            elif isinstance(value, dict):
                merged_value, nested_warnings = _merge_with_schema(
                    expected_value,
                    value,
                    current_path,
                )
                normalized[key] = merged_value
                warnings.extend(nested_warnings)
            else:
                warnings.append(
                    f"Invalid object at {current_path}; "
                    f"default value was used."
                )
        else:
            normalized[key] = value

    return normalized, warnings


def _validate_type(
    value: Any,
    expected_type: type | tuple[type, ...],
    path: str,
    errors: list[str],
    allow_none: bool = True,
) -> None:
    """
    Validate the type of a value and append an error when invalid.
    """

    if value is None and allow_none:
        return

    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_name = " or ".join(
                expected.__name__ for expected in expected_type
            )
        else:
            expected_name = expected_type.__name__

        errors.append(
            f"{path} must be {expected_name}, "
            f"received {type(value).__name__}."
        )


def _validate_percentage(
    value: Any,
    path: str,
    errors: list[str],
) -> None:
    """
    Validate a percentage value in the range 0 to 100.
    """

    if value is None:
        return

    if not isinstance(value, (int, float)):
        errors.append(f"{path} must be a number between 0 and 100.")
        return

    if value < 0 or value > 100:
        errors.append(f"{path} must be between 0 and 100.")


def _validate_research_result(data: dict[str, Any]) -> list[str]:
    """
    Validate the normalized external research result.
    """

    errors: list[str] = []

    _validate_type(
        data.get("schema_version"),
        str,
        "schema_version",
        errors,
        allow_none=False,
    )

    if data.get("schema_version") != EXTERNAL_RESEARCH_SCHEMA_VERSION:
        errors.append(
            "schema_version must be "
            f"{EXTERNAL_RESEARCH_SCHEMA_VERSION}."
        )

    metadata = data["metadata"]

    _validate_type(
        metadata["provider"],
        str,
        "metadata.provider",
        errors,
    )
    _validate_type(
        metadata["model"],
        str,
        "metadata.model",
        errors,
    )
    _validate_type(
        metadata["status"],
        str,
        "metadata.status",
        errors,
        allow_none=False,
    )
    _validate_type(
        metadata["response_time_ms"],
        (int, float),
        "metadata.response_time_ms",
        errors,
    )
    _validate_percentage(
        metadata["provider_confidence_percent"],
        "metadata.provider_confidence_percent",
        errors,
    )
    _validate_type(
        metadata["created_at"],
        str,
        "metadata.created_at",
        errors,
    )

    research_context = data["research_context"]

    for key in (
        "generic_product_type",
        "current_material",
        "current_technology",
        "objective",
    ):
        _validate_type(
            research_context[key],
            str,
            f"research_context.{key}",
            errors,
        )

    _validate_type(
        research_context["required_properties"],
        list,
        "research_context.required_properties",
        errors,
        allow_none=False,
    )

    materials = data["materials"]

    _validate_type(
        materials["recommended_material"],
        str,
        "materials.recommended_material",
        errors,
    )
    _validate_type(
        materials["alternative_materials"],
        list,
        "materials.alternative_materials",
        errors,
        allow_none=False,
    )
    _validate_type(
        materials["comparison_notes"],
        str,
        "materials.comparison_notes",
        errors,
    )

    manufacturing = data["manufacturing"]

    _validate_type(
        manufacturing["recommended_process"],
        str,
        "manufacturing.recommended_process",
        errors,
    )
    _validate_type(
        manufacturing["alternative_processes"],
        list,
        "manufacturing.alternative_processes",
        errors,
        allow_none=False,
    )
    _validate_type(
        manufacturing["estimated_cycle_time_change_percent"],
        (int, float),
        "manufacturing.estimated_cycle_time_change_percent",
        errors,
    )
    _validate_type(
        manufacturing["process_notes"],
        str,
        "manufacturing.process_notes",
        errors,
    )

    costs = data["costs"]

    for key in (
        "estimated_material_price_per_kg",
        "estimated_material_cost_change_percent",
        "estimated_production_cost_change_percent",
        "estimated_total_cost_change_percent",
    ):
        _validate_type(
            costs[key],
            (int, float),
            f"costs.{key}",
            errors,
        )

    _validate_type(
        costs["currency"],
        str,
        "costs.currency",
        errors,
    )
    _validate_type(
        costs["cost_notes"],
        str,
        "costs.cost_notes",
        errors,
    )

    quality = data["quality"]

    for key in (
        "expected_quality_effect",
        "quality_risk_level",
        "quality_notes",
    ):
        _validate_type(
            quality[key],
            str,
            f"quality.{key}",
            errors,
        )

    risks = data["risks"]

    for key in (
        "technical_risks",
        "production_risks",
        "economic_risks",
        "supply_risks",
    ):
        _validate_type(
            risks[key],
            list,
            f"risks.{key}",
            errors,
            allow_none=False,
        )

    optimization = data["optimization"]

    for key in (
        "proposed_changes",
        "expected_benefits",
        "limitations",
    ):
        _validate_type(
            optimization[key],
            list,
            f"optimization.{key}",
            errors,
            allow_none=False,
        )

    _validate_type(
        data["sources"],
        list,
        "sources",
        errors,
        allow_none=False,
    )
    _validate_type(
        data["summary"],
        str,
        "summary",
        errors,
    )
    _validate_type(
        data["missing_information"],
        list,
        "missing_information",
        errors,
        allow_none=False,
    )
    _validate_type(
        data["custom_findings"],
        list,
        "custom_findings",
        errors,
        allow_none=False,
    )

    _validate_type(
        data["additional_metrics"],
        dict,
        "additional_metrics",
        errors,
        allow_none=False,
    )

    _validate_type(
        data["unanswered_questions"],
        list,
        "unanswered_questions",
        errors,
        allow_none=False,
    )
    _validate_type(
        data["requires_engineer_review"],
        bool,
        "requires_engineer_review",
        errors,
        allow_none=False,
    )

    return errors


def validate_external_research_result(
    supplied_data: Any,
) -> ValidationResult:
    """
    Validate and normalize a provider response.

    The function always returns a complete normalized schema.
    Missing fields are replaced with default empty values.

    Unknown fields are ignored and returned as warnings.
    """

    if not isinstance(supplied_data, dict):
        return ValidationResult(
            is_valid=False,
            normalized_data=deepcopy(EMPTY_EXTERNAL_RESEARCH_RESULT),
            errors=["External research result must be a JSON object."],
        )

    normalized_data, warnings = _merge_with_schema(
        EMPTY_EXTERNAL_RESEARCH_RESULT,
        supplied_data,
    )

    _normalize_numeric_fields(normalized_data)

    errors = _validate_research_result(normalized_data)
    
    return ValidationResult(
        is_valid=not errors,
        normalized_data=normalized_data,
        errors=errors,
        warnings=warnings,
    )
    
def _normalize_nullable_number(value: Any) -> Any:
    """
    Convert common AI representations of empty or numeric values.

    The function deliberately does not convert ranges or explanatory text,
    because doing so could silently change engineering meaning.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    if not isinstance(value, str):
        return value

    cleaned = value.strip()

    if cleaned.lower() in {"null", "none", "n/a", "unknown", ""}:
        return None

    normalized = cleaned.replace("%", "").replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return value


def _normalize_numeric_fields(data: dict[str, Any]) -> None:
    """
    Normalize known numeric fields in place before schema validation.
    """

    manufacturing = data["manufacturing"]
    manufacturing["estimated_cycle_time_change_percent"] = (
        _normalize_nullable_number(
            manufacturing["estimated_cycle_time_change_percent"]
        )
    )

    costs = data["costs"]

    for key in (
        "estimated_material_price_per_kg",
        "estimated_material_cost_change_percent",
        "estimated_production_cost_change_percent",
        "estimated_total_cost_change_percent",
    ):
        costs[key] = _normalize_nullable_number(costs[key])

    metadata = data["metadata"]
    metadata["response_time_ms"] = _normalize_nullable_number(
        metadata["response_time_ms"]
    )
    metadata["provider_confidence_percent"] = _normalize_nullable_number(
        metadata["provider_confidence_percent"]
    )