from __future__ import annotations

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)


User = get_user_model()


class DigitalTwinUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="update-user",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            username="other-update-user",
            password="password123",
        )

        self.client.login(
            username="update-user",
            password="password123",
        )

        self.material = MaterialCatalog.objects.create(
            name="42CrMo4",
            code="42CRMO4-UPDATE",
            density_kg_m3=Decimal("7850"),
            price_per_kg=Decimal("4.50"),
            is_active=True,
        )

        self.second_material = MaterialCatalog.objects.create(
            name="C45",
            code="C45-UPDATE",
            density_kg_m3=Decimal("7850"),
            price_per_kg=Decimal("2.80"),
            is_active=True,
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Turning",
            code="TURN-UPDATE",
            machine_hour_rate=Decimal("60.00"),
            is_active=True,
        )

        self.second_technology = TechnologyCatalog.objects.create(
            name="Milling",
            code="MILL-UPDATE",
            machine_hour_rate=Decimal("75.00"),
            is_active=True,
        )

        self.twin = DigitalTwin.objects.create(
            name="Reducer Shaft",
            part_number="SHAFT-UPDATE-001",
            description="Original description",
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

    def get_update_url(self) -> str:
        return reverse(
            "digital_twins:update",
            kwargs={
                "pk": self.twin.pk,
            },
        )

    def get_valid_update_data(self) -> dict[str, str]:
        return {
            "name": "Updated Reducer Shaft",
            "part_number": "shaft-update-001",
            "description": "Updated description",
            "material": str(self.second_material.pk),
            "technology": str(self.second_technology.pk),
            "volume_m3": "0.00200000",
            "mass_kg": "15.700",
            "production_time_minutes": "75.00",
            "labor_cost": "25.00",
            "energy_cost": "7.00",
            "defect_rate_percent": "3.00",
            "desired_profit_margin_percent": "25.00",
            "is_active": "on",
        }

    def test_update_view_returns_200(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_update_view_uses_correct_template(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertTemplateUsed(
            response,
            "digital_twins/digital_twin_form.html",
        )

    def test_update_view_contains_form(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertIn(
            "form",
            response.context,
        )

    def test_update_view_contains_existing_instance(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertEqual(
            response.context["form"].instance,
            self.twin,
        )

    def test_update_view_contains_page_title(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertEqual(
            response.context["page_title"],
            "Update Digital Twin",
        )

    def test_update_view_contains_submit_label(self):
        response = self.client.get(
            self.get_update_url()
        )

        self.assertEqual(
            response.context["submit_label"],
            "Save changes",
        )

    def test_update_view_returns_404_for_missing_object(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": uuid.uuid4(),
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_update_view_updates_digital_twin(self):
        response = self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.twin.refresh_from_db()

        self.assertEqual(
            self.twin.name,
            "Updated Reducer Shaft",
        )
        self.assertEqual(
            self.twin.part_number,
            "SHAFT-UPDATE-001",
        )
        self.assertEqual(
            self.twin.description,
            "Updated description",
        )
        self.assertEqual(
            self.twin.material,
            self.second_material,
        )
        self.assertEqual(
            self.twin.technology,
            self.second_technology,
        )
        self.assertEqual(
            self.twin.mass_kg,
            Decimal("15.700"),
        )

    def test_update_view_preserves_created_by(self):
        original_creator = self.twin.created_by

        self.client.logout()
        self.client.login(
            username="other-update-user",
            password="password123",
        )

        self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        self.twin.refresh_from_db()

        self.assertEqual(
            self.twin.created_by,
            original_creator,
        )

    def test_update_view_changes_updated_by(self):
        self.client.logout()
        self.client.login(
            username="other-update-user",
            password="password123",
        )

        self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        self.twin.refresh_from_db()

        self.assertEqual(
            self.twin.updated_by,
            self.other_user,
        )

    def test_update_view_redirects_to_detail(self):
        response = self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        self.assertRedirects(
            response,
            reverse(
                "digital_twins:detail",
                kwargs={
                    "pk": self.twin.pk,
                },
            ),
        )

    def test_update_view_displays_success_message(self):
        response = self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        response_messages = [
            str(message)
            for message in get_messages(
                response.wsgi_request
            )
        ]

        self.assertTrue(
            any(
                "was updated successfully"
                in message
                for message in response_messages
            )
        )

    def test_update_view_creates_audit_log(self):
        self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
            REMOTE_ADDR="192.168.1.25",
            HTTP_USER_AGENT="Update Test Browser",
        )

        audit_log = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE,
            entity_type="DigitalTwin",
            entity_id=str(self.twin.pk),
        )

        self.assertEqual(
            audit_log.user,
            self.user,
        )
        self.assertEqual(
            audit_log.ip_address,
            "192.168.1.25",
        )
        self.assertEqual(
            audit_log.user_agent,
            "Update Test Browser",
        )
        self.assertEqual(
            audit_log.details["operation"],
            "update",
        )
        self.assertIn(
            "name",
            audit_log.details["changed_fields"],
        )

    def test_update_view_rejects_invalid_data(self):
        original_name = self.twin.name
        original_part_number = self.twin.part_number

        response = self.client.post(
            self.get_update_url(),
            data={
                **self.get_valid_update_data(),
                "name": "",
                "part_number": "",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.twin.refresh_from_db()

        self.assertEqual(
            self.twin.name,
            original_name,
        )
        self.assertEqual(
            self.twin.part_number,
            original_part_number,
        )
        self.assertTrue(
            response.context["form"].errors
        )

    def test_update_view_does_not_create_second_twin(self):
        twins_before = DigitalTwin.objects.count()

        self.client.post(
            self.get_update_url(),
            data=self.get_valid_update_data(),
        )

        self.assertEqual(
            DigitalTwin.objects.count(),
            twins_before,
        )
