"""Serialize Digital Twin creation results into experiment JSON fields."""

from __future__ import annotations

from typing import Any

from digital_twins.models import DigitalTwin

from .results import (
    AppliedProposalChange,
    ManualProposalChange,
)


class TwinCreationSerializer:
    """Build JSON-safe snapshots for the completed experiment."""

    @staticmethod
    def build_changed_parameters(
        *,
        applied_changes: list[AppliedProposalChange],
        manual_changes: list[ManualProposalChange],
    ) -> dict[str, Any]:
        return {
            "applied_changes": [
                {
                    "proposal_id": item.proposal_id,
                    "proposal_sequence": (
                        item.proposal_sequence
                    ),
                    "proposal_title": item.proposal_title,
                    "field_name": item.field_name,
                    "old_value": item.old_value,
                    "new_value": item.new_value,
                }
                for item in applied_changes
            ],
            "manual_changes": [
                {
                    "proposal_id": item.proposal_id,
                    "proposal_sequence": (
                        item.proposal_sequence
                    ),
                    "proposal_title": item.proposal_title,
                    "category": item.category,
                    "parameter_name": item.parameter_name,
                    "current_value": item.current_value,
                    "proposed_value": item.proposed_value,
                    "unit": item.unit,
                    "reason": item.reason,
                    "expected_benefit": (
                        item.expected_benefit
                    ),
                    "validation_requirements": list(
                        item.validation_requirements
                    ),
                }
                for item in manual_changes
            ],
        }

    @staticmethod
    def build_calculated_results(
        twin: DigitalTwin,
    ) -> dict[str, str | None]:
        return {
            "effective_mass_kg": (
                str(twin.effective_mass_kg)
                if twin.effective_mass_kg is not None
                else None
            ),
            "estimated_material_cost": (
                str(twin.estimated_material_cost)
                if twin.estimated_material_cost
                is not None
                else None
            ),
            "estimated_machine_cost": (
                str(twin.estimated_machine_cost)
                if twin.estimated_machine_cost
                is not None
                else None
            ),
            "estimated_direct_cost": str(
                twin.estimated_direct_cost
            ),
            "estimated_defect_cost": str(
                twin.estimated_defect_cost
            ),
            "estimated_total_cost": str(
                twin.estimated_total_cost
            ),
            "estimated_selling_price": (
                str(twin.estimated_selling_price)
                if twin.estimated_selling_price
                is not None
                else None
            ),
            "estimated_profit": (
                str(twin.estimated_profit)
                if twin.estimated_profit is not None
                else None
            ),
        }
