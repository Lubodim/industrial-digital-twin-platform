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
from experiments.twin_creation import TwinCreationError
from experiments.twin_creation.validator import (
    TwinCreationValidator,
)


User = get_user_model()


class TwinCreationValidatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="validator-engineer",
            password="test-password",
        )

        self.material = MaterialCatalog.objects.create(
            name="Validator Steel",
            code="VAL-S235",
            density_kg_m3="7850",
            price_per_kg="2.50",
            yield_strength_mpa="235",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Validator Laser",
            code="VAL-LASER",
            machine_hour_rate="40.00",
        )

        self.source_twin = DigitalTwin.objects.create(
            name="Validator Bracket",
            part_number="VAL-001",
            material=self.material,
            technology=self.technology,
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
            name="Validator experiment",
            objective="Validate twin creation.",
            status=Experiment.Status.APPROVED,
            created_by=self.user,
            approved_by=self.user,
        )

        self.validator = TwinCreationValidator()

    def create_proposal(
        self,
        *,
        status=ExperimentProposal.Status.APPROVED,
        title="Validator proposal",
    ):
        reviewed_by = (
            self.user
            if status
            in {
                ExperimentProposal.Status.APPROVED,
                ExperimentProposal.Status.REJECTED,
            }
            else None
        )

        return ExperimentProposal.objects.create(
            experiment=self.experiment,
            category=ExperimentProposal.Category.COST,
            title=title,
            description="Validator test proposal.",
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=8,
            reason="Reduce production cost.",
            expected_benefit="Lower direct cost.",
            risk_level=ExperimentProposal.RiskLevel.LOW,
            confidence_percent=90,
            requires_validation=True,
            validation_requirements=[],
            status=status,
            reviewed_by=reviewed_by,
        )

    def test_accepts_valid_saved_input(self):
        self.validator.validate_input(
            experiment=self.experiment,
            created_by=self.user,
        )

    def test_rejects_non_experiment_input(self):
        with self.assertRaises(TypeError):
            self.validator.validate_input(
                experiment="not-an-experiment",
                created_by=self.user,
            )

    def test_rejects_unsaved_experiment(self):
        unsaved_experiment = Experiment(
            digital_twin=self.source_twin,
            name="Unsaved experiment",
            created_by=self.user,
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "must be saved",
        ):
            self.validator.validate_input(
                experiment=unsaved_experiment,
                created_by=self.user,
            )

    def test_rejects_unsaved_engineer(self):
        unsaved_user = User(
            username="unsaved-engineer"
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "saved engineer",
        ):
            self.validator.validate_input(
                experiment=self.experiment,
                created_by=unsaved_user,
            )

    def test_rejects_experiment_with_wrong_status(self):
        self.experiment.status = (
            Experiment.Status.PROPOSALS_READY
        )
        self.experiment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "status APPROVED",
        ):
            self.validator.validate_experiment(
                self.experiment
            )

    def test_rejects_experiment_with_existing_result_twin(self):
        result_twin = DigitalTwin.objects.create(
            name="Existing result",
            part_number="VAL-RESULT-001",
            material=self.material,
            technology=self.technology,
            production_time_minutes="10",
            created_by=self.user,
        )

        self.experiment.result_twin = result_twin
        self.experiment.save(
            update_fields=[
                "result_twin",
                "updated_at",
            ]
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "already has a result",
        ):
            self.validator.validate_experiment(
                self.experiment
            )

    def test_rejects_pending_proposal(self):
        self.create_proposal(
            status=ExperimentProposal.Status.PENDING,
            title="Pending proposal",
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "pending proposals",
        ):
            self.validator.validate_experiment(
                self.experiment
            )

    def test_requires_at_least_one_approved_proposal(self):
        with self.assertRaisesMessage(
            TwinCreationError,
            "At least one approved proposal",
        ):
            self.validator.validate_approved_proposals([])

    def test_accepts_approved_proposals(self):
        proposal = self.create_proposal()

        self.validator.validate_approved_proposals(
            [proposal]
        )