from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from audit.models import AuditLog
from digital_twins.models import (
    DigitalTwin,
    DigitalTwinFile,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.models import (
    Experiment,
    ExperimentProposal,
)
from experiments.twin_creation import (
    TwinCreationError,
    TwinCreationService,
)


User = get_user_model()


class TwinCreationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="twin-creation-engineer",
            password="test-password",
        )

        self.steel = MaterialCatalog.objects.create(
            name="Service Steel",
            code="TC-S235",
            density_kg_m3="7850",
            price_per_kg="2.50",
            yield_strength_mpa="235",
        )

        self.aluminium = MaterialCatalog.objects.create(
            name="Service Aluminium",
            code="TC-AL6061",
            density_kg_m3="2700",
            price_per_kg="12.50",
            yield_strength_mpa="276",
        )

        self.laser = TechnologyCatalog.objects.create(
            name="Service Laser",
            code="TC-LASER",
            machine_hour_rate="40.00",
        )

        self.cnc = TechnologyCatalog.objects.create(
            name="Service CNC",
            code="TC-CNC",
            machine_hour_rate="80.00",
        )

        self.source_twin = DigitalTwin.objects.create(
            name="Service Bracket",
            part_number="TC-001",
            description="Original service test twin.",
            material=self.steel,
            technology=self.laser,
            volume_m3="0.00100000",
            mass_kg="7.850",
            production_time_minutes="30.00",
            labor_cost="10.00",
            energy_cost="4.00",
            defect_rate_percent="3.00",
            desired_profit_margin_percent="20.00",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.source_twin,
            name="Twin creation experiment",
            objective="Create an improved result twin.",
            status=Experiment.Status.APPROVED,
            created_by=self.user,
            approved_by=self.user,
            ip_address="192.168.1.25",
            computer_name="ENGINEERING-PC",
        )

        self.service = TwinCreationService()

    def create_proposal(
        self,
        *,
        title: str,
        category: str,
        parameter_name: str | None,
        current_value,
        proposed_value,
        status=ExperimentProposal.Status.APPROVED,
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
            category=category,
            title=title,
            description="Service integration proposal.",
            parameter_name=parameter_name,
            current_value=current_value,
            proposed_value=proposed_value,
            reason="Engineering optimization.",
            expected_benefit="Improved production result.",
            risk_level=ExperimentProposal.RiskLevel.LOW,
            confidence_percent=90,
            requires_validation=True,
            validation_requirements=[],
            status=status,
            reviewed_by=reviewed_by,
        )

    def test_creates_new_twin_without_modifying_source(self):
        self.create_proposal(
            title="Reduce production time",
            category=ExperimentProposal.Category.PRODUCTION,
            parameter_name="production_time_minutes",
            current_value=30,
            proposed_value=20,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.source_twin.refresh_from_db()
        result.result_twin.refresh_from_db()

        self.assertNotEqual(
            result.result_twin.pk,
            self.source_twin.pk,
        )
        self.assertEqual(
            self.source_twin.production_time_minutes,
            Decimal("30.00"),
        )
        self.assertEqual(
            result.result_twin.production_time_minutes,
            Decimal("20.00"),
        )
        self.assertEqual(
            result.result_twin.part_number,
            "TC-001-V2",
        )
        self.assertEqual(
            result.applied_change_count,
            1,
        )

    def test_applies_only_approved_proposals(self):
        self.create_proposal(
            title="Approved labor change",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=7,
        )

        self.create_proposal(
            title="Rejected energy change",
            category=ExperimentProposal.Category.COST,
            parameter_name="energy_cost",
            current_value=4,
            proposed_value=1,
            status=ExperimentProposal.Status.REJECTED,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.assertEqual(
            result.result_twin.labor_cost,
            Decimal("7"),
        )
        self.assertEqual(
            result.result_twin.energy_cost,
            Decimal("4.00"),
        )
        self.assertEqual(
            result.applied_change_count,
            1,
        )

    def test_applies_material_and_technology_changes(self):
        self.create_proposal(
            title="Use aluminium",
            category=ExperimentProposal.Category.MATERIAL,
            parameter_name="material",
            current_value="TC-S235",
            proposed_value="TC-AL6061",
        )

        self.create_proposal(
            title="Use CNC",
            category=ExperimentProposal.Category.TECHNOLOGY,
            parameter_name="technology",
            current_value="TC-LASER",
            proposed_value="TC-CNC",
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.assertEqual(
            result.result_twin.material,
            self.aluminium,
        )
        self.assertEqual(
            result.result_twin.technology,
            self.cnc,
        )
        self.assertEqual(
            result.applied_change_count,
            2,
        )

    def test_preserves_geometry_change_as_manual_instruction(self):
        self.create_proposal(
            title="Increase wall thickness",
            category=ExperimentProposal.Category.GEOMETRY,
            parameter_name="wall_thickness_mm",
            current_value=2,
            proposed_value=3,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.experiment.refresh_from_db()

        self.assertEqual(
            result.manual_change_count,
            1,
        )
        self.assertEqual(
            result.applied_change_count,
            0,
        )

        manual_changes = (
            self.experiment.changed_parameters[
                "manual_changes"
            ]
        )

        self.assertEqual(
            len(manual_changes),
            1,
        )
        self.assertEqual(
            manual_changes[0]["parameter_name"],
            "wall_thickness_mm",
        )
        self.assertEqual(
            manual_changes[0]["proposed_value"],
            3,
        )

    def test_updates_experiment_and_calculated_results(self):
        self.create_proposal(
            title="Reduce defect rate",
            category=ExperimentProposal.Category.QUALITY,
            parameter_name="defect_rate_percent",
            current_value=3,
            proposed_value=1,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.experiment.refresh_from_db()

        self.assertEqual(
            self.experiment.result_twin,
            result.result_twin,
        )
        self.assertEqual(
            self.experiment.status,
            Experiment.Status.TWIN_CREATED,
        )
        self.assertIsNotNone(
            self.experiment.completed_at,
        )
        self.assertIn(
            "applied_changes",
            self.experiment.changed_parameters,
        )
        self.assertIn(
            "estimated_total_cost",
            self.experiment.calculated_results,
        )
        self.assertIn(
            "estimated_profit",
            self.experiment.calculated_results,
        )

    def test_creates_audit_log(self):
        self.create_proposal(
            title="Reduce labor cost",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=8,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
            user_agent="Twin Creation Test Agent",
        )

        audit_log = AuditLog.objects.get(
            entity_type="DigitalTwin",
            entity_id=str(result.result_twin.pk),
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )
        self.assertEqual(
            audit_log.action,
            AuditLog.Action.CREATE,
        )
        self.assertEqual(
            audit_log.ip_address,
            "192.168.1.25",
        )
        self.assertEqual(
            audit_log.computer_name,
            "ENGINEERING-PC",
        )
        self.assertEqual(
            audit_log.user_agent,
            "Twin Creation Test Agent",
        )
        self.assertEqual(
            audit_log.details["operation"],
            "create_from_experiment",
        )
        self.assertEqual(
            audit_log.details["applied_change_count"],
            1,
        )

    def test_copies_related_file_records(self):
        DigitalTwinFile.objects.create(
            digital_twin=self.source_twin,
            file_type=DigitalTwinFile.FileType.DOCUMENT,
            file="digital_twins/files/specification.pdf",
            description="Technical specification",
            uploaded_by=self.user,
        )

        self.create_proposal(
            title="Reduce labor cost",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=8,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.assertEqual(
            result.copied_file_count,
            1,
        )

        copied_file = result.result_twin.files.get()

        self.assertEqual(
            copied_file.file.name,
            "digital_twins/files/specification.pdf",
        )
        self.assertEqual(
            copied_file.description,
            "Technical specification",
        )
        self.assertEqual(
            copied_file.uploaded_by,
            self.user,
        )

    def test_generates_next_available_version(self):
        DigitalTwin.objects.create(
            name="Existing derived version",
            part_number="TC-001-V2",
            material=self.steel,
            technology=self.laser,
            production_time_minutes="30",
            created_by=self.user,
        )

        self.create_proposal(
            title="Reduce labor cost",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=9,
        )

        result = self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        self.assertEqual(
            result.result_twin.part_number,
            "TC-001-V3",
        )

    def test_rejects_second_creation_attempt(self):
        self.create_proposal(
            title="Reduce labor cost",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=8,
        )

        self.service.create(
            experiment=self.experiment,
            created_by=self.user,
        )

        with self.assertRaises(
            TwinCreationError
        ):
            self.service.create(
                experiment=self.experiment,
                created_by=self.user,
            )

        self.assertEqual(
            DigitalTwin.objects.count(),
            2,
        )
        self.assertEqual(
            AuditLog.objects.count(),
            1,
        )

    def test_rejects_pending_proposals(self):
        self.create_proposal(
            title="Approved proposal",
            category=ExperimentProposal.Category.COST,
            parameter_name="labor_cost",
            current_value=10,
            proposed_value=8,
        )

        self.create_proposal(
            title="Pending proposal",
            category=ExperimentProposal.Category.COST,
            parameter_name="energy_cost",
            current_value=4,
            proposed_value=2,
            status=ExperimentProposal.Status.PENDING,
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "pending proposals",
        ):
            self.service.create(
                experiment=self.experiment,
                created_by=self.user,
            )

        self.assertEqual(
            DigitalTwin.objects.count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.count(),
            0,
        )

    def test_transaction_rolls_back_on_invalid_material(self):
        self.create_proposal(
            title="Use missing material",
            category=ExperimentProposal.Category.MATERIAL,
            parameter_name="material",
            current_value="TC-S235",
            proposed_value="MISSING-MATERIAL",
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "was not found",
        ):
            self.service.create(
                experiment=self.experiment,
                created_by=self.user,
            )

        self.experiment.refresh_from_db()

        self.assertEqual(
            DigitalTwin.objects.count(),
            1,
        )
        self.assertIsNone(
            self.experiment.result_twin,
        )
        self.assertEqual(
            self.experiment.status,
            Experiment.Status.APPROVED,
        )
        self.assertEqual(
            AuditLog.objects.count(),
            0,
        )
