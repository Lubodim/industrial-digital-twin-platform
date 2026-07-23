from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from audit.models import AuditLog
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.forms import ExperimentForm
from experiments.models import (
    Experiment,
    ExperimentChatMessage,
)
from experiments.services import (
    ExperimentDeleteError,
    ExperimentNotFoundError,
    ExperimentService,
    ExperimentServiceError,
    ExperimentUpdateError,
)


User = get_user_model()


class ExperimentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="experiment-service-user",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="experiment-other-user",
            password="test-password",
        )

        self.inactive_user = User.objects.create_user(
            username="experiment-inactive-user",
            password="test-password",
            is_active=False,
        )

        self.material = MaterialCatalog.objects.create(
            name="42CrMo4",
            code="42CRMO4-EXP-SERVICE",
            density_kg_m3=Decimal("7850.000"),
            price_per_kg=Decimal("4.50"),
            is_active=True,
        )

        self.technology = (
            TechnologyCatalog.objects.create(
                name="CNC Turning",
                code="CNC-TURN-EXP-SERVICE",
                machine_hour_rate=Decimal("60.00"),
                is_active=True,
            )
        )

        self.twin = DigitalTwin.objects.create(
            name="Reducer Shaft",
            part_number="EXP-SHAFT-001",
            description="Source twin",
            material=self.material,
            technology=self.technology,
            volume_m3=Decimal("0.00100000"),
            mass_kg=Decimal("7.850"),
            production_time_minutes=Decimal("60.00"),
            labor_cost=Decimal("20.00"),
            energy_cost=Decimal("5.00"),
            defect_rate_percent=Decimal("2.00"),
            desired_profit_margin_percent=Decimal("20.00"),
            created_by=self.user,
            updated_by=self.user,
            is_active=True,
        )

        self.second_twin = DigitalTwin.objects.create(
            name="Housing",
            part_number="EXP-HOUSING-002",
            created_by=self.user,
            updated_by=self.user,
            is_active=True,
        )

        self.inactive_twin = DigitalTwin.objects.create(
            name="Inactive Twin",
            part_number="EXP-INACTIVE-003",
            created_by=self.user,
            updated_by=self.user,
            is_active=False,
        )

        self.valid_data = {
            "digital_twin": str(
                self.twin.pk
            ),
            "name": "Weight reduction",
            "description": (
                "Investigate lighter alternatives."
            ),
            "objective": (
                "Reduce mass by ten percent."
            ),
        }

    def build_form(
        self,
        *,
        data=None,
        instance=None,
    ) -> ExperimentForm:
        return ExperimentForm(
            data=(
                data
                if data is not None
                else self.valid_data
            ),
            instance=instance,
        )

    def create_experiment(
        self,
        *,
        name="Existing experiment",
        status=Experiment.Status.DRAFT,
    ) -> Experiment:
        return Experiment.objects.create(
            digital_twin=self.twin,
            name=name,
            description="Original description",
            objective="Original objective",
            status=status,
            base_snapshot={
                "part_number": (
                    self.twin.part_number
                ),
            },
            created_by=self.user,
        )

    def test_create_persists_experiment(self):
        experiment = ExperimentService.create(
            form=self.build_form(),
            user=self.user,
        )

        experiment.refresh_from_db()

        self.assertEqual(
            experiment.name,
            "Weight reduction",
        )
        self.assertEqual(
            experiment.digital_twin,
            self.twin,
        )
        self.assertEqual(
            experiment.created_by,
            self.user,
        )
        self.assertEqual(
            experiment.status,
            Experiment.Status.DRAFT,
        )

    def test_create_builds_base_snapshot(self):
        experiment = ExperimentService.create(
            form=self.build_form(),
            user=self.user,
        )

        self.assertEqual(
            experiment.base_snapshot[
                "part_number"
            ],
            self.twin.part_number,
        )
        self.assertEqual(
            experiment.base_snapshot[
                "material"
            ]["code"],
            self.material.code,
        )
        self.assertEqual(
            experiment.base_snapshot[
                "technology"
            ]["code"],
            self.technology.code,
        )
        self.assertEqual(
            experiment.base_snapshot[
                "mass_kg"
            ],
            "7.850",
        )

    def test_create_stores_request_metadata(self):
        experiment = ExperimentService.create(
            form=self.build_form(),
            user=self.user,
            ip_address="192.168.1.20",
            computer_name="ENGINEERING-PC",
            user_agent="Experiment Browser",
        )

        experiment.refresh_from_db()

        self.assertEqual(
            experiment.ip_address,
            "192.168.1.20",
        )
        self.assertEqual(
            experiment.computer_name,
            "ENGINEERING-PC",
        )

    def test_create_generates_audit_log(self):
        experiment = ExperimentService.create(
            form=self.build_form(),
            user=self.user,
            ip_address="192.168.1.20",
        )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.CREATE,
            entity_type="Experiment",
            entity_id=str(
                experiment.pk
            ),
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )
        self.assertEqual(
            audit_log.details["operation"],
            "create",
        )
        self.assertEqual(
            audit_log.details[
                "digital_twin_part_number"
            ],
            self.twin.part_number,
        )

    def test_create_rejects_invalid_form(self):
        form = self.build_form(data={**self.valid_data, "name": "", })

        with self.assertRaises(ExperimentServiceError):
            ExperimentService.create(form=form, user=self.user, )

    def test_create_rejects_anonymous_user(self):
        with self.assertRaises(ExperimentServiceError):
            ExperimentService.create(form=self.build_form(), user=AnonymousUser(), )

    def test_create_rejects_inactive_user(self):
        with self.assertRaises(ExperimentServiceError):
            ExperimentService.create(form=self.build_form(), user=self.inactive_user,)

    def test_update_changes_editable_fields(self):
        experiment = self.create_experiment()

        form = self.build_form(
            data={
                **self.valid_data,
                "name": "Updated experiment",
                "description": ("Updated description"),
                "objective": ("Updated objective"), },
            instance=experiment,)

        updated = ExperimentService.update(experiment=experiment, form=form, user=self.other_user, )

        updated.refresh_from_db()

        self.assertEqual(updated.name, "Updated experiment", )
        self.assertEqual(updated.description, "Updated description", )
        self.assertEqual(updated.objective, "Updated objective", )

    def test_update_preserves_source_twin(self):
        experiment = self.create_experiment()

        form = self.build_form(
            data={**self.valid_data, "digital_twin": str(self.second_twin.pk), "name": "Changed name", },
            instance=experiment,)

        updated = ExperimentService.update(experiment=experiment, form=form, user=self.user, )

        self.assertEqual(updated.digital_twin, self.twin, )

    def test_update_preserves_base_snapshot(self):
        experiment = self.create_experiment()

        original_snapshot = (experiment.base_snapshot.copy())

        form = self.build_form(data={**self.valid_data, "name": "Changed name", },
            instance=experiment, )

        updated = ExperimentService.update(experiment=experiment, form=form, user=self.user,)

        self.assertEqual(updated.base_snapshot, original_snapshot, )

    def test_update_creates_audit_log(self):
        experiment = self.create_experiment()

        form = self.build_form(data={**self.valid_data, "name": "Changed name", },
            instance=experiment, )

        ExperimentService.update(experiment=experiment, form=form, user=self.user, )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_type="Experiment",
            entity_id=str(experiment.pk), )

        self.assertEqual(audit_log.details["operation"], "update", )
        self.assertIn("name", audit_log.details["changed_fields"], )

    def test_update_rejects_completed_experiment(self):
        experiment = self.create_experiment(status=(Experiment.Status.COMPLETED))

        form = self.build_form(data={**self.valid_data, "name": "Changed name",},
            instance=experiment,)

        with self.assertRaises(ExperimentUpdateError):
            ExperimentService.update(experiment=experiment, form=form, user=self.user, )

    def test_archive_changes_status(self):
        experiment = self.create_experiment()

        archived = ExperimentService.archive(experiment=experiment, user=self.user, )

        archived.refresh_from_db()

        self.assertEqual(archived.status, Experiment.Status.ARCHIVED, )

    def test_archive_generates_audit_log(self):
        experiment = self.create_experiment()

        ExperimentService.archive(experiment=experiment, user=self.user, )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_type="Experiment",
            entity_id=str(experiment.pk),)

        self.assertEqual(audit_log.details["operation"], "archive", )

    def test_delete_removes_unused_draft(self):
        experiment = self.create_experiment()
        experiment_id = experiment.pk

        deleted_id = ExperimentService.delete(experiment=experiment, user=self.user, )

        self.assertEqual(deleted_id, experiment_id, )
        self.assertFalse(Experiment.objects.filter(pk=experiment_id).exists())

    def test_delete_generates_audit_log(self):
        experiment = self.create_experiment()
        experiment_id = experiment.pk

        ExperimentService.delete(experiment=experiment, user=self.user,)

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.DELETE,
            entity_type="Experiment",
            entity_id=str(experiment_id),)

        self.assertEqual(audit_log.details["operation"], "delete", )

    def test_delete_rejects_non_draft(self):
        experiment = self.create_experiment(status=(Experiment.Status.CHATTING))

        with self.assertRaises(ExperimentDeleteError):
            ExperimentService.delete(experiment=experiment, user=self.user, )

    def test_delete_rejects_chat_history(self):
        experiment = self.create_experiment()

        ExperimentChatMessage.objects.create(
            experiment=experiment,
            role=(ExperimentChatMessage.Role.ENGINEER),
            provider=(ExperimentChatMessage.Provider.NONE),
            content="Can the mass be reduced?", created_by=self.user, )

        with self.assertRaises(ExperimentDeleteError):
            ExperimentService.delete(experiment=experiment, user=self.user, )

    def test_get_by_id(self):
        experiment = self.create_experiment()

        result = ExperimentService.get_by_id(experiment.pk)

        self.assertEqual(result, experiment, )

    def test_get_by_id_rejects_missing(self):
        with self.assertRaises(ExperimentNotFoundError):
            ExperimentService.get_by_id("00000000-0000-0000-0000-000000000001")

    def test_search_by_name(self):
        expected = self.create_experiment(name="Mass reduction")

        self.create_experiment(name="Technology comparison")

        results = ExperimentService.search(query="Mass")

        self.assertEqual(list(results), [expected], )

    def test_filter_by_digital_twin(self):
        expected = self.create_experiment()

        Experiment.objects.create(
            digital_twin=self.second_twin, 
            name="Second twin experiment", 
            created_by=self.user, )

        results = ExperimentService.search(digital_twin=self.twin)

        self.assertEqual(list(results), [expected], )

    def test_filter_by_status(self):
        draft = self.create_experiment()

        self.create_experiment(name="Archived experiment", status=(Experiment.Status.ARCHIVED), )

        results = ExperimentService.search(status=Experiment.Status.DRAFT)

        self.assertEqual(list(results), [draft], )

    def test_search_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            ExperimentService.search(status="UNKNOWN")

    def test_statistics(self):
        self.create_experiment(name="Draft experiment", status=Experiment.Status.DRAFT, )

        self.create_experiment(name="Active experiment", status=(Experiment.Status.ANALYZING), )

        self.create_experiment(name="Completed experiment", status=(Experiment.Status.COMPLETED), )

        self.create_experiment(name="Archived experiment", status=(Experiment.Status.ARCHIVED), )

        statistics = (ExperimentService.get_statistics())

        self.assertEqual(statistics.total_count, 4, )
        self.assertEqual(statistics.draft_count, 1, )
        self.assertEqual(statistics.active_count, 1, )
        self.assertEqual(statistics.completed_count, 1, )
        self.assertEqual(statistics.archived_count, 1, )
