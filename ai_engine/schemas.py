from __future__ import annotations

from copy import deepcopy
from typing import Any


EXTERNAL_RESEARCH_SCHEMA_VERSION = "1.0"


EMPTY_EXTERNAL_RESEARCH_RESULT: dict[str, Any] = {
    "schema_version": EXTERNAL_RESEARCH_SCHEMA_VERSION,

    "metadata": {
        "provider": None,
        "model": None,
        "status": "pending",
        "response_time_ms": None,
        "provider_confidence_percent": None,
        "created_at": None,
    },

    "research_context": {
        "generic_product_type": None,
        "current_material": None,
        "current_technology": None,
        "objective": None,
        "required_properties": [],
    },

    "materials": {
        "recommended_material": None,
        "alternative_materials": [],
        "comparison_notes": None,
    },

    "manufacturing": {
        "recommended_process": None,
        "alternative_processes": [],
        "estimated_cycle_time_change_percent": None,
        "process_notes": None,
    },

    "costs": {
        "estimated_material_price_per_kg": None,
        "currency": None,
        "estimated_material_cost_change_percent": None,
        "estimated_production_cost_change_percent": None,
        "estimated_total_cost_change_percent": None,
        "cost_notes": None,
    },

    "quality": {
        "expected_quality_effect": None,
        "quality_risk_level": None,
        "quality_notes": None,
    },

    "risks": {
        "technical_risks": [],
        "production_risks": [],
        "economic_risks": [],
        "supply_risks": [],
    },

    "optimization": {
        "proposed_changes": [],
        "expected_benefits": [],
        "limitations": [],
    },

    "sources": [],

    "summary": None,

    "missing_information": [],
    
    "custom_findings": [],

    "additional_metrics": {},

    "unanswered_questions": [],

    "requires_engineer_review": True,
}


def create_empty_research_result(
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Return a new independent research result structure.

    deepcopy is required because the schema contains nested dictionaries
    and lists that must not be shared between provider responses.
    """
    result = deepcopy(EMPTY_EXTERNAL_RESEARCH_RESULT)

    result["metadata"]["provider"] = provider
    result["metadata"]["model"] = model

    return result