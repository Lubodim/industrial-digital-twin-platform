"""Apply approved experiment proposals to a derived Digital Twin."""

from __future__ import annotations

import re

from digital_twins.models import DigitalTwin
from experiments.models import ExperimentProposal

from .exceptions import TwinCreationError
from .results import (
    AppliedProposalChange,
    ManualProposalChange,
)
from .value_converter import ProposalValueConverter


class ProposalApplier:
    """Resolve proposal parameters and apply supported changes."""

    FIELD_ALIASES = {
        # General information
        "name": "name",
        "twin_name": "name",
        "product_name": "name",
        "description": "description",

        # Material
        "material": "material",
        "material_code": "material",
        "material_name": "material",

        # Technology
        "technology": "technology",
        "technology_code": "technology",
        "technology_name": "technology",
        "manufacturing_process": "technology",
        "production_process": "technology",
        "manufacturing_technology": "technology",

        # Engineering values
        "volume": "volume_m3",
        "volume_m3": "volume_m3",
        "mass": "mass_kg",
        "mass_kg": "mass_kg",
        "weight": "mass_kg",
        "weight_kg": "mass_kg",

        # Production
        "production_time": "production_time_minutes",
        "production_time_minutes": "production_time_minutes",
        "cycle_time": "production_time_minutes",
        "cycle_time_minutes": "production_time_minutes",

        # Costs
        "labor_cost": "labor_cost",
        "labour_cost": "labor_cost",
        "energy_cost": "energy_cost",

        # Quality
        "defect_rate": "defect_rate_percent",
        "defect_rate_percent": "defect_rate_percent",
        "scrap_rate": "defect_rate_percent",
        "scrap_rate_percent": "defect_rate_percent",

        # Profit
        "desired_profit_margin": (
            "desired_profit_margin_percent"
        ),
        "desired_profit_margin_percent": (
            "desired_profit_margin_percent"
        ),
        "profit_margin": (
            "desired_profit_margin_percent"
        ),
        "profit_margin_percent": (
            "desired_profit_margin_percent"
        ),
    }

    DECIMAL_FIELDS = {
        "volume_m3",
        "mass_kg",
        "production_time_minutes",
        "labor_cost",
        "energy_cost",
        "defect_rate_percent",
        "desired_profit_margin_percent",
    }

    TEXT_FIELDS = {
        "name",
        "description",
    }

    def __init__(
        self,
        *,
        converter: ProposalValueConverter | None = None,
    ) -> None:
        self.converter = (
            converter or ProposalValueConverter()
        )

    def resolve_field_name(
        self,
        parameter_name: str | None,
    ) -> str | None:
        if not parameter_name:
            return None

        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            str(parameter_name).strip().lower(),
        ).strip("_")

        return self.FIELD_ALIASES.get(normalized)

    def apply(
        self,
        *,
        twin: DigitalTwin,
        proposal: ExperimentProposal,
    ) -> AppliedProposalChange | ManualProposalChange:
        field_name = self.resolve_field_name(
            proposal.parameter_name
        )

        if field_name is None:
            return self.build_manual_change(proposal)

        old_value = getattr(twin, field_name)

        if field_name == "material":
            new_value = self.converter.resolve_material(
                proposal.proposed_value
            )

        elif field_name == "technology":
            new_value = self.converter.resolve_technology(
                proposal.proposed_value
            )

        elif field_name in self.DECIMAL_FIELDS:
            new_value = self.converter.to_decimal(
                value=proposal.proposed_value,
                field_name=field_name,
            )

        elif field_name in self.TEXT_FIELDS:
            new_value = self.converter.to_text(
                value=proposal.proposed_value,
                field_name=field_name,
            )

        else:
            raise TwinCreationError(
                f"Unsupported Digital Twin field "
                f"'{field_name}'."
            )

        setattr(twin, field_name, new_value)

        return AppliedProposalChange(
            proposal_id=str(proposal.pk),
            proposal_sequence=proposal.sequence,
            proposal_title=proposal.title,
            field_name=field_name,
            old_value=self.converter.serialize(old_value),
            new_value=self.converter.serialize(new_value),
        )

    @staticmethod
    def build_manual_change(
        proposal: ExperimentProposal,
    ) -> ManualProposalChange:
        requirements = proposal.validation_requirements

        if not isinstance(requirements, list):
            requirements = []

        normalized_requirements = tuple(
            str(item).strip()
            for item in requirements
            if str(item).strip()
        )

        return ManualProposalChange(
            proposal_id=str(proposal.pk),
            proposal_sequence=proposal.sequence,
            proposal_title=proposal.title,
            category=proposal.category,
            parameter_name=proposal.parameter_name,
            current_value=proposal.current_value,
            proposed_value=proposal.proposed_value,
            unit=proposal.unit,
            reason=proposal.reason,
            expected_benefit=proposal.expected_benefit,
            validation_requirements=normalized_requirements,
        )
