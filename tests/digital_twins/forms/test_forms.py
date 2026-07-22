from __future__ import annotations

from decimal import Decimal

from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import TestCase

from digital_twins.forms import (
    DigitalTwinDeleteForm,
    DigitalTwinFilterForm,
    DigitalTwinForm,
)
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)


class DigitalTwinFormTests(TestCase):
    def setUp(self):
        self.material = (
            MaterialCatalog.objects.create(
                name="42CrMo4",
                code="42CRMO4",
                density_kg_m3=Decimal(
                    "7850.000"
                ),
                price_per_kg=Decimal(
                    "4.50"
                ),
                is_active=True,
            )
        )

        self.inactive_material = (
            MaterialCatalog.objects.create(
                name="Inactive steel",
                code="INACTIVE-MAT",
                is_active=False,
            )
        )

        self.technology = (
            TechnologyCatalog.objects.create(
                name="CNC Turning",
                code="CNC-TURN",
                machine_hour_rate=Decimal(
                    "55.00"
                ),
                is_active=True,
            )
        )

        self.inactive_technology = (
            TechnologyCatalog.objects.create(
                name="Inactive process",
                code="INACTIVE-TECH",
                is_active=False,
            )
        )

        self.valid_data = {
            "name": "Редукторен вал",
            "part_number": "shaft-001",
            "description": (
                "Цифров двойник на редукторен вал."
            ),
            "material": str(
                self.material.pk
            ),
            "technology": str(
                self.technology.pk
            ),
            "volume_m3": "0.00100000",
            "mass_kg": "7.850",
            "production_time_minutes": "45.00",
            "labor_cost": "20.00",
            "energy_cost": "8.00",
            "defect_rate_percent": "2.50",
            "desired_profit_margin_percent": (
                "20.00"
            ),
            "is_active": True,
        }

    def test_valid_form(self):
        form = DigitalTwinForm(
            data=self.valid_data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_form_normalizes_name(self):
        data = {
            **self.valid_data,
            "name": (
                "  Редукторен    вал  "
            ),
        }

        form = DigitalTwinForm(
            data=data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["name"],
            "Редукторен вал",
        )

    def test_form_normalizes_part_number_to_uppercase(
        self,
    ):
        form = DigitalTwinForm(
            data=self.valid_data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data[
                "part_number"
            ],
            "SHAFT-001",
        )

    def test_form_rejects_case_insensitive_duplicate_part_number(
        self,
    ):
        DigitalTwin.objects.create(
            name="Existing Twin",
            part_number="SHAFT-001",
        )

        form = DigitalTwinForm(
            data=self.valid_data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "part_number",
            form.errors,
        )

    def test_update_form_allows_current_part_number(
        self,
    ):
        twin = DigitalTwin.objects.create(
            name="Existing Twin",
            part_number="SHAFT-001",
            material=self.material,
            technology=self.technology,
            production_time_minutes=Decimal(
                "10.00"
            ),
        )

        form = DigitalTwinForm(
            data={
                **self.valid_data,
                "name": "Updated Twin",
                "part_number": "shaft-001",
            },
            instance=twin,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_form_rejects_negative_mass(self):
        form = DigitalTwinForm(
            data={
                **self.valid_data,
                "mass_kg": "-1.000",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "mass_kg",
            form.errors,
        )

    def test_form_rejects_defect_rate_above_100(
        self,
    ):
        form = DigitalTwinForm(
            data={
                **self.valid_data,
                "defect_rate_percent": "100.01",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "defect_rate_percent",
            form.errors,
        )

    def test_form_rejects_profit_margin_of_100(
        self,
    ):
        form = DigitalTwinForm(
            data={
                **self.valid_data,
                (
                    "desired_profit_margin_percent"
                ): "100.00",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "desired_profit_margin_percent",
            form.errors,
        )

    def test_material_is_required_when_mass_is_positive(
        self,
    ):
        data = {
            **self.valid_data,
            "material": "",
            "mass_kg": "5.000",
        }

        form = DigitalTwinForm(
            data=data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "material",
            form.errors,
        )

    def test_technology_is_required_when_time_is_positive(
        self,
    ):
        data = {
            **self.valid_data,
            "technology": "",
            "production_time_minutes": "15.00",
        }

        form = DigitalTwinForm(
            data=data
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "technology",
            form.errors,
        )

    def test_material_may_be_empty_when_mass_is_zero(
        self,
    ):
        data = {
            **self.valid_data,
            "material": "",
            "mass_kg": "0.000",
        }

        form = DigitalTwinForm(
            data=data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_technology_may_be_empty_when_time_is_zero(
        self,
    ):
        data = {
            **self.valid_data,
            "technology": "",
            "production_time_minutes": "0.00",
        }

        form = DigitalTwinForm(
            data=data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_only_active_materials_are_available(
        self,
    ):
        form = DigitalTwinForm()

        queryset = (
            form.fields["material"].queryset
        )

        self.assertIn(
            self.material,
            queryset,
        )

        self.assertNotIn(
            self.inactive_material,
            queryset,
        )

    def test_only_active_technologies_are_available(
        self,
    ):
        form = DigitalTwinForm()

        queryset = (
            form.fields[
                "technology"
            ].queryset
        )

        self.assertIn(
            self.technology,
            queryset,
        )

        self.assertNotIn(
            self.inactive_technology,
            queryset,
        )

    def test_supported_cad_file_is_accepted(self):
        cad_file = SimpleUploadedFile(
            name="shaft.step",
            content=b"test-cad-content",
            content_type=(
                "application/octet-stream"
            ),
        )

        form = DigitalTwinForm(
            data=self.valid_data,
            files={
                "cad_file": cad_file,
            },
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_unsupported_cad_file_is_rejected(
        self,
    ):
        cad_file = SimpleUploadedFile(
            name="malicious.exe",
            content=b"invalid",
            content_type=(
                "application/octet-stream"
            ),
        )

        form = DigitalTwinForm(
            data=self.valid_data,
            files={
                "cad_file": cad_file,
            },
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "cad_file",
            form.errors,
        )

    def test_supported_image_is_accepted(self):
        image_file = SimpleUploadedFile(
            name="shaft.png",
            content=b"image-content",
            content_type="image/png",
        )

        form = DigitalTwinForm(
            data=self.valid_data,
            files={
                "image_file": image_file,
            },
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_unsupported_image_is_rejected(
        self,
    ):
        image_file = SimpleUploadedFile(
            name="image.pdf",
            content=b"invalid-image",
            content_type="application/pdf",
        )

        form = DigitalTwinForm(
            data=self.valid_data,
            files={
                "image_file": image_file,
            },
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "image_file",
            form.errors,
        )

    def test_form_saves_normalized_part_number(
        self,
    ):
        form = DigitalTwinForm(
            data=self.valid_data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        twin = form.save(
            commit=False
        )

        self.assertEqual(
            twin.part_number,
            "SHAFT-001",
        )


class DigitalTwinFilterFormTests(TestCase):
    def setUp(self):
        self.active_material = (
            MaterialCatalog.objects.create(
                name="Active Material",
                code="ACTIVE-MAT",
                is_active=True,
            )
        )

        self.inactive_material = (
            MaterialCatalog.objects.create(
                name="Inactive Material",
                code="INACTIVE-MAT",
                is_active=False,
            )
        )

        self.active_technology = (
            TechnologyCatalog.objects.create(
                name="Active Technology",
                code="ACTIVE-TECH",
                is_active=True,
            )
        )

        self.inactive_technology = (
            TechnologyCatalog.objects.create(
                name="Inactive Technology",
                code="INACTIVE-TECH",
                is_active=False,
            )
        )

    def test_empty_filter_form_is_valid(self):
        form = DigitalTwinFilterForm(
            data={}
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_filter_form_accepts_all_values(
        self,
    ):
        form = DigitalTwinFilterForm(
            data={
                "query": "shaft",
                "material": (
                    self.active_material.pk
                ),
                "technology": (
                    self.active_technology.pk
                ),
                "status": "active",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_filter_form_excludes_inactive_catalog_entries(
        self,
    ):
        form = DigitalTwinFilterForm()

        self.assertNotIn(
            self.inactive_material,
            form.fields[
                "material"
            ].queryset,
        )

        self.assertNotIn(
            self.inactive_technology,
            form.fields[
                "technology"
            ].queryset,
        )


class DigitalTwinDeleteFormTests(TestCase):
    def test_confirmation_is_required(self):
        form = DigitalTwinDeleteForm(
            data={}
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "confirmation",
            form.errors,
        )

    def test_confirmed_form_is_valid(self):
        form = DigitalTwinDeleteForm(
            data={
                "confirmation": True,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
