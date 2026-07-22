from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages

from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)

User = get_user_model()


class DigitalTwinViewTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="view-user",
            password="password123",
        )

        self.client.login(
            username="view-user",
            password="password123",
        )

        self.material = MaterialCatalog.objects.create(
            name="42CrMo4",
            code="42CRMO4",
            density_kg_m3=Decimal("7850"),
            price_per_kg=Decimal("4.50"),
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Turning",
            code="TURN",
            machine_hour_rate=Decimal("60"),
        )

        self.twin = DigitalTwin.objects.create(
            name="Reducer Shaft",
            part_number="SHAFT-001",
            description="Testing",
            material=self.material,
            technology=self.technology,
            volume_m3=Decimal("0.001"),
            mass_kg=Decimal("7.85"),
            production_time_minutes=Decimal("60"),
            labor_cost=Decimal("20"),
            energy_cost=Decimal("5"),
            defect_rate_percent=Decimal("2"),
            desired_profit_margin_percent=Decimal("20"),
            created_by=self.user,
            updated_by=self.user,
        )

    def test_list_view_returns_200(self):

        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_detail_view_returns_200(self):

        response = self.client.get(
            reverse(
                "digital_twins:detail",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_list_view_uses_correct_template(self):
        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertTemplateUsed(
            response,
            "digital_twins/digital_twin_list.html",
        )

    def test_list_view_contains_twin(self):
        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertContains(
            response,
            self.twin.name,
        )

    def test_list_view_context_contains_twin(self):
        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertIn(
            self.twin,
            response.context["digital_twins"],
        )

    def test_list_view_context_contains_filter_form(self):
        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertIn(
            "filter_form",
            response.context,
        )

    def test_list_view_context_contains_statistics(self):
        response = self.client.get(
            reverse("digital_twins:list")
        )

        self.assertIn(
            "statistics",
            response.context,
        )

    def test_detail_view_uses_correct_template(self):
        response = self.client.get(
            reverse(
                "digital_twins:detail",
                kwargs={"pk": self.twin.pk},
            )
        )

        self.assertTemplateUsed(
            response,
            "digital_twins/digital_twin_detail.html",
        )

    def test_detail_view_context_contains_twin(self):
        response = self.client.get(
            reverse(
                "digital_twins:detail",
                kwargs={"pk": self.twin.pk},
            )
        )

        self.assertEqual(response.context["digital_twin"], self.twin,)

    def test_detail_view_context_contains_cost_summary(self):
        response = self.client.get(reverse("digital_twins:detail", kwargs={"pk": self.twin.pk}, ))

        self.assertIn("cost_summary", response.context, )

    def test_detail_view_returns_404_for_missing_twin(self):
        import uuid

        response = self.client.get(reverse("digital_twins:detail", kwargs={"pk": uuid.uuid4()}, ))

        self.assertEqual(response.status_code, 404, )
    def test_create_view_returns_200(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.status_code,200, )

    def test_create_view_uses_correct_template(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertTemplateUsed(response, "digital_twins/digital_twin_form.html", )

    def test_create_view_contains_form(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertIn("form", response.context, )

    def test_create_view_contains_submit_label(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.context["submit_label"], "Create", )

    def test_create_view_contains_page_title(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.context["page_title"], "Create Digital Twin", )
    
    def test_create_view_returns_200(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.status_code, 200, )

    def test_create_view_uses_correct_template(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertTemplateUsed(response, "digital_twins/digital_twin_form.html", )

    def test_create_view_contains_form(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertIn("form", response.context,)

    def test_create_view_contains_submit_label(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.context["submit_label"], "Create", )

    def test_create_view_contains_page_title(self):
        response = self.client.get(reverse("digital_twins:create"))

        self.assertEqual(response.context["page_title"], "Create Digital Twin", )
    
    def test_create_view_creates_digital_twin(self):
        response = self.client.post(reverse("digital_twins:create"),
            data={
                "name": "New Gear Shaft",
                "part_number": "new-shaft-002",
                "description": "Created through the web form",
                "material": str(self.material.pk),
                "technology": str(self.technology.pk),
                "volume_m3": "0.00200000",
                "mass_kg": "15.700",
                "production_time_minutes": "75.00",
                "labor_cost": "25.00",
                "energy_cost": "7.00",
                "defect_rate_percent": "3.00",
                "desired_profit_margin_percent": "25.00",
                "is_active": "on",
            }, )

        self.assertEqual(response.status_code, 302, )

        created_twin = DigitalTwin.objects.get(part_number="NEW-SHAFT-002")

        self.assertEqual(created_twin.name, "New Gear Shaft", )

        self.assertEqual(created_twin.created_by, self.user, )

        self.assertEqual(created_twin.updated_by, self.user, )

    def test_create_view_redirects_to_created_twin_detail(self):
        response = self.client.post(reverse("digital_twins:create"),
            data={
                "name": "Created Twin",
                "part_number": "CREATE-003",
                "description": "Redirect test",
                "material": str(self.material.pk),
                "technology": str(self.technology.pk),
                "volume_m3": "0.00150000",
                "mass_kg": "11.775",
                "production_time_minutes": "45.00",
                "labor_cost": "18.00",
                "energy_cost": "4.00",
                "defect_rate_percent": "1.50",
                "desired_profit_margin_percent": "20.00",
                "is_active": "on",
            },)

        created_twin = DigitalTwin.objects.get(part_number="CREATE-003")

        self.assertRedirects(response, reverse("digital_twins:detail", kwargs={"pk": created_twin.pk,}, ), )

    def test_create_view_displays_success_message(self):
        response = self.client.post(reverse("digital_twins:create"),
            data={
                "name": "Message Twin",
                "part_number": "MESSAGE-004",
                "description": "Success message test",
                "material": str(self.material.pk),
                "technology": str(self.technology.pk),
                "volume_m3": "0.00100000",
                "mass_kg": "7.850",
                "production_time_minutes": "60.00",
                "labor_cost": "20.00",
                "energy_cost": "5.00",
                "defect_rate_percent": "2.00",
                "desired_profit_margin_percent": "20.00",
                "is_active": "on",
            }, )

        messages = [str(message) for message in get_messages(response.wsgi_request)]

        self.assertTrue(any("was created successfully" in message for message in messages))

    def test_create_view_rejects_invalid_data(self):
        twins_before = DigitalTwin.objects.count()

        response = self.client.post(reverse("digital_twins:create"),
            data={
                "name": "",
                "part_number": "",
                "description": "Invalid form",
                "material": "",
                "technology": "",
                "volume_m3": "",
                "mass_kg": "",
                "production_time_minutes": "",
                "labor_cost": "0.00",
                "energy_cost": "0.00",
                "defect_rate_percent": "0.00",
                "desired_profit_margin_percent": "20.00",
                "is_active": "on",
            }, )

        self.assertEqual(response.status_code, 200, )

        self.assertEqual(DigitalTwin.objects.count(), twins_before, )

        self.assertTrue(response.context["form"].errors)
    
    def test_update_view_returns_200(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_update_view_uses_correct_template(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertTemplateUsed(
            response,
            "digital_twins/digital_twin_form.html",
        )

    def test_update_view_contains_form(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertIn(
            "form",
            response.context,
        )

    def test_update_view_contains_existing_instance(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        form = response.context["form"]

        self.assertEqual(
            form.instance,
            self.twin,
        )

    def test_update_view_contains_page_title(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertEqual(
            response.context["page_title"],
            "Update Digital Twin",
        )

    def test_update_view_contains_submit_label(self):
        response = self.client.get(
            reverse(
                "digital_twins:update",
                kwargs={
                    "pk": self.twin.pk,
                },
            )
        )

        self.assertEqual(response.context["submit_label"], "Save changes", )

    def test_update_view_returns_404_for_missing_object(self):
        import uuid

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
    