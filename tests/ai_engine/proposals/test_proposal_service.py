from django.contrib.auth import get_user_model
from django.test import TestCase

from experiments.models import (
    Experiment,
    ExperimentProposal,
)
from experiments.proposal_services import (
    ProposalReviewError,
    ProposalReviewService,
)
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)

User = get_user_model()


class ProposalReviewServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="engineer",
            password="password",
        )

        self.material = MaterialCatalog.objects.create(
            name="Steel",
            code="S235",
            density_kg_m3="7850",
            price_per_kg="2.5",
            yield_strength_mpa="235",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Laser",
            code="LASER",
            machine_hour_rate="40",
        )

        self.twin = DigitalTwin.objects.create(
            name="Bracket",
            part_number="TEST-001",
            material=self.material,
            technology=self.technology,
            volume_m3="0.001",
            production_time_minutes="10",
            labor_cost="5",
            energy_cost="1",
            defect_rate_percent="2",
            desired_profit_margin_percent="20",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.twin,
            name="Review Test",
            objective="Review proposals",
            created_by=self.user,
        )

        self.service = ProposalReviewService()

    def create_proposal(self, title):
        return ExperimentProposal.objects.create(
            experiment=self.experiment,
            category=ExperimentProposal.Category.COST,
            title=title,
            description="Description",
            parameter_name="cost",
            current_value=100,
            proposed_value=90,
            reason="Reason",
            expected_benefit="Benefit",
            risk_level=ExperimentProposal.RiskLevel.LOW,
            confidence_percent=80,
            requires_validation=True,
            validation_requirements=[],
        )

    def test_approve_proposal(self):
        proposal = self.create_proposal("Approve")

        self.service.approve(
            proposal=proposal,
            reviewed_by=self.user,
        )

        proposal.refresh_from_db()

        self.assertEqual(
            proposal.status,
            ExperimentProposal.Status.APPROVED,
        )

        self.assertEqual(
            proposal.reviewed_by,
            self.user,
        )

        self.assertIsNotNone(
            proposal.reviewed_at,
        )

    def test_reject_proposal(self):
        proposal = self.create_proposal("Reject")

        self.service.reject(
            proposal=proposal,
            reviewed_by=self.user,
        )

        proposal.refresh_from_db()

        self.assertEqual(
            proposal.status,
            ExperimentProposal.Status.REJECTED,
        )

    def test_cannot_review_twice(self):
        proposal = self.create_proposal("Once")

        self.service.approve(
            proposal=proposal,
            reviewed_by=self.user,
        )

        with self.assertRaises(
            ProposalReviewError
        ):
            self.service.reject(
                proposal=proposal,
                reviewed_by=self.user,
            )

    def test_review_requires_engineer(self):
        proposal = self.create_proposal("User")

        with self.assertRaises(
            ProposalReviewError
        ):
            self.service.approve(
                proposal=proposal,
                reviewed_by=None,
            )

    def test_review_many(self):
        p1 = self.create_proposal("A")
        p2 = self.create_proposal("B")
        p3 = self.create_proposal("C")

        summary = self.service.review_many(
            approved=[p1, p2],
            rejected=[p3],
            reviewed_by=self.user,
        )

        self.assertEqual(summary.approved_count, 2)
        self.assertEqual(summary.rejected_count, 1)
        self.assertEqual(summary.pending_count, 0)

    def test_summary(self):
        self.create_proposal("1")
        self.create_proposal("2")

        summary = self.service.summarize(
            experiment=self.experiment,
        )

        self.assertEqual(summary.pending_count, 2)
        self.assertEqual(summary.approved_count, 0)
        self.assertEqual(summary.rejected_count, 0)
