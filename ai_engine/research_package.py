from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_EXTERNAL_FIELDS = {
    "generic_product_type",
    "current_material",
    "current_technology",
    "batch_size",
    "current_cycle_time_minutes",
    "required_properties",
    "objective",
}


@dataclass
class ResearchPackage:
    """
    Safe data package sent to external AI providers.

    The package contains only explicitly permitted and sanitized information.
    Confidential internal data such as CAD files, company names, customer data,
    internal costs and profit margins must never be included.
    """

    engineer_question: str
    generic_product_type: str | None = None
    current_material: str | None = None
    current_technology: str | None = None
    batch_size: int | None = None
    current_cycle_time_minutes: float | None = None
    required_properties: list[str] = field(default_factory=list)
    objective: str | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Return the research package as a plain dictionary.
        """
        return asdict(self)


def _clean_text(value: Any) -> str | None:
    """
    Normalize optional text values.
    """

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _clean_string_list(value: Any) -> list[str]:
    """
    Convert a value to a cleaned list of non-empty strings.
    """

    if value is None:
        return []

    if not isinstance(value, (list, tuple, set)):
        value = [value]

    cleaned: list[str] = []

    for item in value:
        text = _clean_text(item)
        if text:
            cleaned.append(text)

    return cleaned


def _clean_positive_int(value: Any) -> int | None:
    """
    Return a positive integer or None.
    """

    if value in (None, ""):
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed >= 0 else None


def _clean_non_negative_float(value: Any) -> float | None:
    """
    Return a non-negative float or None.
    """

    if value in (None, ""):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed >= 0 else None


def _filter_additional_context(
    additional_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Keep only approved additional context fields.

    This function acts as a whitelist and prevents confidential data from
    being passed accidentally to external AI providers.
    """

    if not isinstance(additional_context, dict):
        return {}

    filtered: dict[str, Any] = {}

    for key, value in additional_context.items():
        if key not in ALLOWED_EXTERNAL_FIELDS:
            continue

        if key == "batch_size":
            filtered[key] = _clean_positive_int(value)

        elif key == "current_cycle_time_minutes":
            filtered[key] = _clean_non_negative_float(value)

        elif key == "required_properties":
            filtered[key] = _clean_string_list(value)

        else:
            filtered[key] = _clean_text(value)

    return filtered


def build_research_package(
    *,
    engineer_question: str,
    generic_product_type: str | None = None,
    current_material: str | None = None,
    current_technology: str | None = None,
    batch_size: int | None = None,
    current_cycle_time_minutes: float | None = None,
    required_properties: list[str] | None = None,
    objective: str | None = None,
    additional_context: dict[str, Any] | None = None,
) -> ResearchPackage:
    """
    Build a validated and sanitized research package.

    The engineer question is mandatory.
    All remaining values are optional and will be normalized.
    """

    cleaned_question = _clean_text(engineer_question)

    if not cleaned_question:
        raise ValueError("engineer_question cannot be empty.")

    filtered_context = _filter_additional_context(additional_context)

    return ResearchPackage(
        engineer_question=cleaned_question,
        generic_product_type=_clean_text(generic_product_type),
        current_material=_clean_text(current_material),
        current_technology=_clean_text(current_technology),
        batch_size=_clean_positive_int(batch_size),
        current_cycle_time_minutes=_clean_non_negative_float(
            current_cycle_time_minutes
        ),
        required_properties=_clean_string_list(required_properties),
        objective=_clean_text(objective),
        additional_context=filtered_context,
    )