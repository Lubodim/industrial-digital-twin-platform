from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from audit.models import AuditLog
from digital_twins.forms import DigitalTwinForm
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from digital_twins.services import (
    DigitalTwinDeleteError,
    DigitalTwinNotFoundError,
    DigitalTwinService,
    DigitalTwinServiceError,
)


User = get_user_model()


class DigitalTwinServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="twin-service-user",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="other-user",
            password="test-password",
        )

        self.inactive_user = User.objects.create_user(
            username="inactive-user",
            password="test-password",
            is_active=False,
        )

        self.material = MaterialCatalog.objects.create(
            name="42CrMo4",
            code="42CRMO4-SERVICE",
            density_kg_m3=Decimal("7850.000"),
            price_per_kg=Decimal("4.50"),
            is_active=True,
        )

        self.second_material = MaterialCatalog.objects.create(
            name="C45",
            code="C45-SERVICE",
            density_kg_m3=Decimal("7850.000"),
            price_per_kg=Decimal("2.80"),
            is_active=True,
        )

        self.technology = TechnologyCatalog.objects.create(
            name="CNC Turning",
            code="CNC-TURN-SERVICE",
            machine_hour_rate=Decimal("60.00"),
            is_active=True,
        )

        self.second_technology = (
            TechnologyCatalog.objects.create(
                name="CNC Milling",
                code="CNC-MILL-SERVICE",
                machine_hour_rate=Decimal("75.00"),
                is_active=True,
            )
        )

        self.valid_data = {
            "name": "Редукторен вал",
            "part_number": "shaft-service-001",
            "description": "Service test twin",
            "material": str(self.material.pk),
            "technology": str(self.technology.pk),
            "volume_m3": "0.00100000",
            "mass_kg": "7.850",
            "production_time_minutes": "60.00",
            "labor_cost": "20.00",
            "energy_cost": "5.00",
            "defect_rate_percent": "2.00",
            "desired_profit_margin_percent": "20.00",
            "is_active": True,
        }

    def build_form(
        self,
        *,
        data=None,
        instance=None,
    ):
        return DigitalTwinForm(
            data=data or self.valid_data,
            instance=instance,
        )

    def create_twin(
        self,
        *,
        part_number="EXISTING-001",
        name="Existing Twin",
        created_by=None,
        is_active=True,
    ):
        return DigitalTwin.objects.create(
            name=name,
            part_number=part_number,
            description="Existing description",
            material=self.material,
            technology=self.technology,
            volume_m3=Decimal("0.00100000"),
            mass_kg=Decimal("7.850"),
            production_time_minutes=Decimal("60.00"),
            labor_cost=Decimal("20.00"),
            energy_cost=Decimal("5.00"),
            defect_rate_percent=Decimal("2.00"),
            desired_profit_margin_percent=Decimal("20.00"),
            created_by=created_by or self.user,
            updated_by=created_by or self.user,
            is_active=is_active,
        )

    def test_create_persists_twin_and_assigns_users(self):
        twin = DigitalTwinService.create(
            form=self.build_form(),
            user=self.user,
        )

        twin.refresh_from_db()

        self.assertEqual(
            twin.part_number,
            "SHAFT-SERVICE-001",
        )
        self.assertEqual(
            twin.created_by,
            self.user,
        )
        self.assertEqual(
            twin.updated_by,
            self.user,
        )

    def test_create_generates_audit_record(self):
        twin = DigitalTwinService.create(
            form=self.build_form(),
            user=self.user,
            ip_address="192.168.1.10",
            computer_name="ENGINEERING-PC",
            user_agent="Test Browser",
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.CREATE,
            entity_type="DigitalTwin",
            entity_id=str(twin.pk),
        )

        self.assertEqual(audit.user, self.user)
        self.assertEqual(
            audit.ip_address,
            "192.168.1.10",
        )
        self.assertEqual(
            audit.computer_name,
            "ENGINEERING-PC",
        )
        self.assertEqual(
            audit.user_agent,
            "Test Browser",
        )
        self.assertEqual(
            audit.details["operation"],
            "create",
        )

    def test_create_rejects_invalid_form(self):
        form = self.build_form(
            data={
                **self.valid_data,
                "name": "",
            }
        )

        with self.assertRaises(
            DigitalTwinServiceError
        ):
            DigitalTwinService.create(
                form=form,
                user=self.user,
            )

        self.assertFalse(
            DigitalTwin.objects.exists()
        )

    def test_create_rejects_unbound_form(self):
        with self.assertRaises(
            DigitalTwinServiceError
        ):
            DigitalTwinService.create(
                form=DigitalTwinForm(),
                user=self.user,
            )

    def test_create_rejects_wrong_form_type(self):
        with self.assertRaises(TypeError):
            DigitalTwinService.create(
                form=SimpleNamespace(),
                user=self.user,
            )

    def test_create_rejects_anonymous_user(self):
        with self.assertRaises(
            DigitalTwinServiceError
        ):
            DigitalTwinService.create(
                form=self.build_form(),
                user=AnonymousUser(),
            )

    def test_create_rejects_inactive_user(self):
        with self.assertRaises(
            DigitalTwinServiceError
        ):
            DigitalTwinService.create(
                form=self.build_form(),
                user=self.inactive_user,
            )

    def test_update_changes_fields_and_updated_by(self):
        twin = self.create_twin()

        form = self.build_form(
            data={
                **self.valid_data,
                "name": "Updated Twin",
                "part_number": twin.part_number,
                "material": self.second_material.pk,
                "technology": self.second_technology.pk,
            },
            instance=twin,
        )

        updated = DigitalTwinService.update(
            twin=twin,
            form=form,
            user=self.other_user,
        )

        updated.refresh_from_db()

        self.assertEqual(
            updated.name,
            "Updated Twin",
        )
        self.assertEqual(
            updated.material,
            self.second_material,
        )
        self.assertEqual(
            updated.technology,
            self.second_technology,
        )
        self.assertEqual(
            updated.created_by,
            self.user,
        )
        self.assertEqual(
            updated.updated_by,
            self.other_user,
        )

    def test_update_creates_before_after_audit(self):
        twin = self.create_twin()

        form = self.build_form(
            data={
                **self.valid_data,
                "name": "Changed Name",
                "part_number": twin.part_number,
            },
            instance=twin,
        )

        updated = DigitalTwinService.update(
            twin=twin,
            form=form,
            user=self.user,
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_id=str(updated.pk),
        )

        self.assertEqual(
            audit.details["operation"],
            "update",
        )
        self.assertEqual(
            audit.details["before"]["name"],
            "Existing Twin",
        )
        self.assertEqual(
            audit.details["after"]["name"],
            "Changed Name",
        )
        self.assertIn(
            "name",
            audit.details["changed_fields"],
        )

    def test_update_rejects_mismatched_form_instance(self):
        twin = self.create_twin()
        other_twin = self.create_twin(
            part_number="OTHER-001",
        )

        form = self.build_form(
            data={
                **self.valid_data,
                "part_number": other_twin.part_number,
            },
            instance=other_twin,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        with self.assertRaises(
            DigitalTwinServiceError
        ):
            DigitalTwinService.update(
                twin=twin,
                form=form,
                user=self.user,
            )

    def test_deactivate_changes_status_and_audits(self):
        twin = self.create_twin()

        result = DigitalTwinService.deactivate(
            twin=twin,
            user=self.user,
        )

        result.refresh_from_db()

        self.assertFalse(result.is_active)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_id=str(result.pk),
        )

        self.assertEqual(
            audit.details["operation"],
            "deactivate",
        )

    def test_activate_changes_status_and_audits(self):
        twin = self.create_twin(
            is_active=False
        )

        result = DigitalTwinService.activate(
            twin=twin,
            user=self.user,
        )

        result.refresh_from_db()

        self.assertTrue(result.is_active)

        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_id=str(result.pk),
        )

        self.assertEqual(
            audit.details["operation"],
            "activate",
        )

    def test_delete_removes_twin_and_creates_audit(self):
        twin = self.create_twin()
        twin_id = twin.pk

        deleted_id = DigitalTwinService.delete(
            twin=twin,
            user=self.user,
        )

        self.assertEqual(deleted_id, twin_id)
        self.assertFalse(
            DigitalTwin.objects.filter(
                pk=twin_id
            ).exists()
        )

        audit = AuditLog.objects.get(
            action=AuditLog.Action.DELETE,
            entity_id=str(twin_id),
        )

        self.assertEqual(
            audit.details["operation"],
            "delete",
        )
        self.assertEqual(
            audit.details[
                "deleted_twin"
            ]["part_number"],
            "EXISTING-001",
        )

    def test_validate_before_delete_accepts_unused_twin(
        self,
    ):
        twin = self.create_twin()

        DigitalTwinService.validate_before_delete(
            twin
        )


    def test_validate_before_delete_rejects_related_experiment(self,):
        twin = self.create_twin()

        class FakeExperimentsManager:
            @staticmethod
            def exists():
                return True

        with patch.object(
            DigitalTwin,
            "experiments",
            new_callable=PropertyMock,
        ) as mocked_experiments:
            mocked_experiments.return_value = (
                FakeExperimentsManager()
            )

            with self.assertRaises(
                DigitalTwinDeleteError
            ):
                DigitalTwinService.validate_before_delete(
                    twin
                )

    def test_get_by_id(self):
        twin = self.create_twin()

        result = DigitalTwinService.get_by_id(
            twin.pk
        )

        self.assertEqual(result, twin)

    def test_get_by_id_can_exclude_inactive(self):
        twin = self.create_twin(
            is_active=False
        )

        with self.assertRaises(
            DigitalTwinNotFoundError
        ):
            DigitalTwinService.get_by_id(
                twin.pk,
                include_inactive=False,
            )

    def test_get_by_id_rejects_invalid_uuid(self):
        with self.assertRaises(
            DigitalTwinNotFoundError
        ):
            DigitalTwinService.get_by_id(
                "not-a-valid-uuid"
            )

    def test_get_by_part_number_is_case_insensitive(
        self,
    ):
        twin = self.create_twin(
            part_number="PART-ABC-001",
        )

        result = (
            DigitalTwinService
            .get_by_part_number(
                "part-abc-001"
            )
        )

        self.assertEqual(result, twin)

    def test_get_by_part_number_rejects_missing_twin(
        self,
    ):
        with self.assertRaises(
            DigitalTwinNotFoundError
        ):
            DigitalTwinService.get_by_part_number(
                "MISSING-001"
            )

    def test_normalize_part_number(self):
        self.assertEqual(
            DigitalTwinService.normalize_part_number(
                "  shaft   001  "
            ),
            "SHAFT 001",
        )

    def test_search_by_name(self):
        first = self.create_twin(
            name="Редукторен вал",
            part_number="SEARCH-001",
        )
        self.create_twin(
            name="Корпус",
            part_number="SEARCH-002",
        )

        results = DigitalTwinService.search(query="Редукторен")


        self.assertEqual(
            list(results),
            [first],
        )

    def test_search_by_material_code(self):
        twin = self.create_twin()

        results = DigitalTwinService.search(
            query=self.material.code
        )

        self.assertIn(twin, results)

    def test_filter_by_material_and_technology(self):
        matching = self.create_twin(
            part_number="FILTER-001"
        )

        other = self.create_twin(
            part_number="FILTER-002"
        )
        other.material = self.second_material
        other.technology = self.second_technology
        other.save()

        results = DigitalTwinService.search(
            material=self.material,
            technology=self.technology,
        )

        self.assertEqual(
            list(results),
            [matching],
        )

    def test_filter_by_active_status(self):
        active = self.create_twin(
            part_number="ACTIVE-001",
            is_active=True,
        )
        self.create_twin(
            part_number="INACTIVE-001",
            is_active=False,
        )

        results = DigitalTwinService.search(
            status="active"
        )

        self.assertEqual(
            list(results),
            [active],
        )

    def test_search_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            DigitalTwinService.search(
                status="unknown"
            )

    def test_statistics(self):
        self.create_twin(
            part_number="STAT-001",
            is_active=True,
        )

        inactive = self.create_twin(
            part_number="STAT-002",
            is_active=False,
        )
        inactive.material = None
        inactive.technology = None
        inactive.production_time_minutes = 0
        inactive.mass_kg = 0
        inactive.save()

        statistics = (
            DigitalTwinService.get_statistics()
        )

        self.assertEqual(
            statistics.total_count,
            2,
        )
        self.assertEqual(
            statistics.active_count,
            1,
        )
        self.assertEqual(
            statistics.inactive_count,
            1,
        )
        self.assertEqual(
            statistics.with_material_count,
            1,
        )
        self.assertEqual(
            statistics.without_material_count,
            1,
        )

    def test_get_cost_summary(self):
        twin = self.create_twin()

        summary = (
            DigitalTwinService
            .get_cost_summary(twin)
        )

        self.assertEqual(
            summary["effective_mass_kg"],
            Decimal("7.850"),
        )
        self.assertEqual(
            summary["estimated_material_cost"],
            Decimal("35.32"),
        )
        self.assertEqual(
            summary["estimated_machine_cost"],
            Decimal("60.00"),
        )
        self.assertIn(
            "estimated_total_cost",
            summary,
        )
        self.assertIn(
            "estimated_profit",
            summary,
        )

    def test_get_cost_summary_rejects_wrong_type(
        self,
    ):
        with self.assertRaises(TypeError):
            DigitalTwinService.get_cost_summary(
                object()
            )
