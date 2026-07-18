from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.models import (
    Experiment,
    ExperimentProposal,
)
from experiments.twin_creation import (
    AppliedProposalChange,
    ManualProposalChange,
    TwinCreationError,
)
from experiments.twin_creation.proposal_applier import (
    ProposalApplier,
)


User = get_user_model()


class ProposalApplierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="proposal-applier-engineer",
            password="test-password",
        )

        self.steel = MaterialCatalog.objects.create(
            name="Proposal Steel",
            code="PA-S235",
            density_kg_m3="7850",
            price_per_kg="2.50",
        )

        self.aluminium = MaterialCatalog.objects.create(
            name="Proposal Aluminium",
            code="PA-AL6061",
            density_kg_m3="2700",
            price_per_kg="12.50",
        )

        self.laser = TechnologyCatalog.objects.create(
            name="Proposal Laser",
            code="PA-LASER",
            machine_hour_rate="40.00",
        )

        self.cnc = TechnologyCatalog.objects.create(
            name="Proposal CNC",
            code="PA-CNC",
            machine_hour_rate="80.00",
        )

        self.source_twin = DigitalTwin.objects.create(
            name="Proposal Bracket",
            part_number="PA-001",
            description="Original proposal test twin.",
            material=self.steel,
            technology=self.laser,
            volume_m3="0.001",
            mass_kg="7.850",
            production_time_minutes="30",
            labor_cost="10",
            energy_cost="4",
            defect_rate_percent="3",
            desired_profit_margin_percent="20",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.source_twin,
            name="Proposal applier experiment",
            objective="Apply approved proposals.",
            status=Experiment.Status.APPROVED,
            created_by=self.user,
            approved_by=self.user,
        )

        self.applier = ProposalApplier()

    def create_proposal(
        self,
        *,
        title: str,
        category: str,
        parameter_name: str | None,
        current_value,
        proposed_value,
        validation_requirements=None,
    ):
        return ExperimentProposal.objects.create(
            experiment=self.experiment,
            category=category,
            title=title,
            description="Proposal applier test.",
            parameter_name=parameter_name,
            current_value=current_value,
            proposed_value=proposed_value,
            unit=None,
            reason="Engineering optimization.",
            expected_benefit="Improved result.",
            risk_level=ExperimentProposal.RiskLevel.LOW,
            confidence_percent=90,
            requires_validation=True,
            validation_requirements=(
                validation_requirements or []
            ),
            status=ExperimentProposal.Status.APPROVED,
            reviewed_by=self.user,
        )

    def build_unsaved_copy(self):
        return DigitalTwin(
            name=self.source_twin.name,
            part_number="PA-001-V2",
            description=self.source_twin.description,
            material=self.source_twin.material,
            technology=self.source_twin.technology,
            volume_m3=self.source_twin.volume_m3,
            mass_kg=self.source_twin.mass_kg,
            production_time_minutes=(
                self.source_twin.production_time_minutes
            ),
            labor_cost=self.source_twin.labor_cost,
            energy_cost=self.source_twin.energy_cost,
            defect_rate_percent=(
                self.source_twin.defect_rate_percent
            ),
            desired_profit_margin_percent=(
                self.source_twin
                .desired_profit_margin_percent
            ),
            created_by=self.user,
        )

    def test_resolves_supported_alias(self):
        field_name = self.applier.resolve_field_name(
            "cycle time"
        )

        self.assertEqual(
            field_name,
            "production_time_minutes",
        )

    def test_applies_decimal_change(self):
        proposal = self.create_proposal(
            title="Reduce cycle time",
            category=ExperimentProposal.Category.PRODUCTION,
            parameter_name="cycle_time_minutes",
            current_value=30,
            proposed_value=20,
        )

        twin = self.build_unsaved_copy()

        result = self.applier.apply(
            twin=twin,
            proposal=proposal,
        )

        self.assertIsInstance(
            result,
            AppliedProposalChange,
        )
        self.assertEqual(
            twin.production_time_minutes,
            Decimal("20"),
        )
        self.assertEqual(
            result.field_name,
            "production_time_minutes",
        )
        self.assertEqual(
            Decimal(result.old_value),
            Decimal("30"),
        )
        self.assertEqual(
            Decimal(result.new_value),
            Decimal("20"),
        )

    def test_applies_material_change_by_code(self):
        proposal = self.create_proposal(
            title="Use aluminium",
            category=ExperimentProposal.Category.MATERIAL,
            parameter_name="material",
            current_value="PA-S235",
            proposed_value={
                "code": "PA-AL6061",
            },
        )

        twin = self.build_unsaved_copy()

        result = self.applier.apply(
            twin=twin,
            proposal=proposal,
        )

        self.assertIsInstance(
            result,
            AppliedProposalChange,
        )
        self.assertEqual(
            twin.material,
            self.aluminium,
        )
        self.assertEqual(
            result.new_value["code"],
            "PA-AL6061",
        )

    def test_applies_technology_change_by_name(self):
        proposal = self.create_proposal(
            title="Use CNC",
            category=ExperimentProposal.Category.TECHNOLOGY,
            parameter_name="manufacturing_process",
            current_value="Proposal Laser",
            proposed_value={
                "name": "Proposal CNC",
            },
        )

        twin = self.build_unsaved_copy()

        result = self.applier.apply(
            twin=twin,
            proposal=proposal,
        )

        self.assertIsInstance(
            result,
            AppliedProposalChange,
        )
        self.assertEqual(
            twin.technology,
            self.cnc,
        )

    def test_converts_unsupported_geometry_to_manual_change(self):
        proposal = self.create_proposal(
            title="Increase wall thickness",
            category=ExperimentProposal.Category.GEOMETRY,
            parameter_name="wall_thickness_mm",
            current_value=2,
            proposed_value=3,
            validation_requirements=[
                "Regenerate CAD model.",
                "Validate structural strength.",
            ],
        )

        twin = self.build_unsaved_copy()

        result = self.applier.apply(
            twin=twin,
            proposal=proposal,
        )

        self.assertIsInstance(
            result,
            ManualProposalChange,
        )
        self.assertEqual(
            result.parameter_name,
            "wall_thickness_mm",
        )
        self.assertEqual(
            result.proposed_value,
            3,
        )
        self.assertEqual(
            result.validation_requirements,
            (
                "Regenerate CAD model.",
                "Validate structural strength.",
            ),
        )

    def test_rejects_unknown_material(self):
        proposal = self.create_proposal(
            title="Use unknown material",
            category=ExperimentProposal.Category.MATERIAL,
            parameter_name="material",
            current_value="PA-S235",
            proposed_value="UNKNOWN-MATERIAL",
        )

        twin = self.build_unsaved_copy()

        with self.assertRaisesMessage(
            TwinCreationError,
            "was not found",
        ):
            self.applier.apply(
                twin=twin,
                proposal=proposal,
            )

    def test_rejects_non_numeric_decimal_value(self):
        proposal = self.create_proposal(
            title="Invalid labor cost",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value="not-a-number",
        )

        twin = self.build_unsaved_copy()

        with self.assertRaisesMessage(
            TwinCreationError,
            "is not numeric",
        ):
            self.applier.apply(
                twin=twin,
                proposal=proposal,
            )
