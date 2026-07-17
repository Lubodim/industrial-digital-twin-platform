from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_engine.local_ai.analysis_result import (
    EngineeringAnalysisResult,
    EngineeringProposal,
)
from ai_engine.local_ai.proposal_generator import (
    ProposalGenerator,
)
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.models import (
    Experiment,
    ExperimentProposal,
)


User = get_user_model()


class ProposalGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="proposal-engineer",
            password="test-password",
        )

        self.material = MaterialCatalog.objects.create(
            name="Test Steel",
            code="TEST-S235",
            density_kg_m3="7850.000",
            price_per_kg="2.50",
            yield_strength_mpa="235.00",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Test Laser Cutting",
            code="TEST-LASER",
            machine_hour_rate="45.00",
        )

        self.twin = DigitalTwin.objects.create(
            name="Test Flange",
            part_number="PROPOSAL-TEST-001",
            material=self.material,
            technology=self.technology,
            volume_m3="0.00010000",
            production_time_minutes="15.00",
            labor_cost="5.00",
            energy_cost="2.00",
            defect_rate_percent="2.00",
            desired_profit_margin_percent="20.00",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.twin,
            name="Proposal generation test",
            objective="Reduce manufacturing cost.",
            created_by=self.user,
        )

        self.generator = ProposalGenerator()

    def build_proposal(
        self,
        *,
        title="Optimize cutting layout",
        category="PRODUCTION",
        confidence_percent=80,
    ):
        return EngineeringProposal(
            category=category,
            title=title,
            description="Review nesting and cutting sequence.",
            parameter_name="nesting_efficiency",
            current_value=70,
            proposed_value=85,
            unit="%",
            reason="Reduced waste may lower manufacturing cost.",
            expected_benefit="Lower material consumption.",
            risk_level="LOW",
            confidence_percent=confidence_percent,
            requires_validation=True,
            validation_requirements=(
                "Compare material utilization.",
            ),
        )

    def build_result(
        self,
        *proposals,
    ):
        return EngineeringAnalysisResult(
            summary="The process can be optimized.",
            findings=(
                "Material utilization affects cost.",
            ),
            conflicts=(),
            missing_information=(),
            proposals=tuple(proposals),
            overall_confidence_percent=80,
            requires_engineer_review=True,
            model_name="qwen3.5:9b",
        )

    def test_generates_persistent_proposal(self):
        result = self.build_result(
            self.build_proposal()
        )

        generation = self.generator.generate(
            experiment=self.experiment,
            analysis_result=result,
        )

        self.assertEqual(
            generation.created_count,
            1,
        )
        self.assertEqual(
            generation.skipped_count,
            0,
        )
        self.assertEqual(
            ExperimentProposal.objects.count(),
            1,
        )

        proposal = ExperimentProposal.objects.get()

        self.assertEqual(
            proposal.experiment,
            self.experiment,
        )
        self.assertEqual(
            proposal.sequence,
            1,
        )
        self.assertEqual(
            proposal.category,
            ExperimentProposal.Category.PRODUCTION,
        )
        self.assertEqual(
            proposal.title,
            "Optimize cutting layout",
        )
        self.assertEqual(
            proposal.current_value,
            70,
        )
        self.assertEqual(
            proposal.proposed_value,
            85,
        )
        self.assertEqual(
            proposal.status,
            ExperimentProposal.Status.PENDING,
        )

    def test_generates_multiple_proposals_in_sequence(self):
        result = self.build_result(
            self.build_proposal(
                title="Optimize layout",
            ),
            self.build_proposal(
                title="Reduce cycle time",
            ),
        )

        generation = self.generator.generate(
            experiment=self.experiment,
            analysis_result=result,
        )

        self.assertEqual(
            generation.created_count,
            2,
        )

        proposals = list(
            ExperimentProposal.objects.order_by(
                "sequence"
            )
        )

        self.assertEqual(
            proposals[0].sequence,
            1,
        )
        self.assertEqual(
            proposals[1].sequence,
            2,
        )
        self.assertEqual(
            proposals[0].title,
            "Optimize layout",
        )
        self.assertEqual(
            proposals[1].title,
            "Reduce cycle time",
        )

    def test_replaces_old_pending_proposals(self):
        first_result = self.build_result(
            self.build_proposal(
                title="Old proposal",
            )
        )

        self.generator.generate(
            experiment=self.experiment,
            analysis_result=first_result,
        )

        second_result = self.build_result(
            self.build_proposal(
                title="New proposal",
            )
        )

        self.generator.generate(
            experiment=self.experiment,
            analysis_result=second_result,
            replace_pending=True,
        )

        old_proposal = ExperimentProposal.objects.get(
            title="Old proposal"
        )
        new_proposal = ExperimentProposal.objects.get(
            title="New proposal"
        )

        self.assertEqual(
            old_proposal.status,
            ExperimentProposal.Status.SUPERSEDED,
        )
        self.assertEqual(
            new_proposal.status,
            ExperimentProposal.Status.PENDING,
        )

    def test_does_not_replace_reviewed_proposals(self):
        reviewed = ExperimentProposal.objects.create(
            experiment=self.experiment,
            category=ExperimentProposal.Category.COST,
            title="Reviewed proposal",
            description="Existing reviewed proposal.",
            parameter_name="production_cost",
            current_value=100,
            proposed_value=90,
            reason="Reduce cost.",
            expected_benefit="Lower unit cost.",
            risk_level=ExperimentProposal.RiskLevel.LOW,
            confidence_percent=80,
            requires_validation=True,
            validation_requirements=[
                "Verify production cost."
            ],
            status=ExperimentProposal.Status.APPROVED,
            reviewed_by=self.user,
        )

        result = self.build_result(
            self.build_proposal(
                title="New pending proposal",
            )
        )

        self.generator.generate(
            experiment=self.experiment,
            analysis_result=result,
            replace_pending=True,
        )

        reviewed.refresh_from_db()

        self.assertEqual(
            reviewed.status,
            ExperimentProposal.Status.APPROVED,
        )

    def test_invalid_proposal_is_skipped(self):
        invalid_proposal = self.build_proposal(
            title="   ",
        )

        result = self.build_result(
            invalid_proposal
        )

        generation = self.generator.generate(
            experiment=self.experiment,
            analysis_result=result,
        )

        self.assertEqual(
            generation.created_count,
            0,
        )
        self.assertEqual(
            generation.skipped_count,
            1,
        )
        self.assertEqual(
            ExperimentProposal.objects.count(),
            0,
        )
        self.assertTrue(
            generation.warnings
        )

    def test_unknown_material_creates_warning_but_is_saved(self):
        material_proposal = EngineeringProposal(
            category="MATERIAL",
            title="Use alternative alloy",
            description="Evaluate an alternative alloy.",
            parameter_name="material",
            current_value="TEST-S235",
            proposed_value="UNKNOWN-ALLOY",
            unit=None,
            reason="Potential weight reduction.",
            expected_benefit="Lower component mass.",
            risk_level="MEDIUM",
            confidence_percent=65,
            requires_validation=True,
            validation_requirements=(
                "Perform material validation.",
            ),
        )

        result = self.build_result(
            material_proposal
        )

        generation = self.generator.generate(
            experiment=self.experiment,
            analysis_result=result,
        )

        self.assertEqual(
            generation.created_count,
            1,
        )
        self.assertEqual(
            generation.skipped_count,
            0,
        )
        self.assertTrue(
            generation.warnings
        )
        self.assertEqual(
            ExperimentProposal.objects.count(),
            1,
        )
