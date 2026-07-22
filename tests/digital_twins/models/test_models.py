from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)


class DigitalTwinModelTests(TestCase):
    def setUp(self):
        self.material = MaterialCatalog.objects.create(
            name="Aluminium 6061",
            code="AL6061",
            density_kg_m3=Decimal("2700.000"),
            price_per_kg=Decimal("12.50"),
            yield_strength_mpa=Decimal("276.00"),
        )

        self.technology = TechnologyCatalog.objects.create(
            name="CNC Milling",
            code="CNC-MILL",
            machine_hour_rate=Decimal("80.00"),
        )

        self.twin = DigitalTwin.objects.create(
            name="Robot Gripper Bracket",
            part_number="RGB-001",
            material=self.material,
            technology=self.technology,
            volume_m3=Decimal("0.00045000"),
            production_time_minutes=Decimal("35.00"),
            labor_cost=Decimal("8.00"),
            energy_cost=Decimal("3.00"),
            defect_rate_percent=Decimal("2.00"),
            desired_profit_margin_percent=Decimal("20.00"),
        )

    def test_calculates_mass_from_volume_and_density(self):
        self.assertEqual(
            self.twin.calculated_mass_kg,
            Decimal("1.215"),
        )

    def test_uses_entered_mass_when_available(self):
        self.twin.mass_kg = Decimal("1.300")

        self.assertEqual(
            self.twin.effective_mass_kg,
            Decimal("1.300"),
        )

    def test_calculates_material_cost(self):
        self.assertEqual(
            self.twin.estimated_material_cost,
            Decimal("15.19"),
        )

    def test_calculates_machine_cost(self):
        self.assertEqual(
            self.twin.estimated_machine_cost,
            Decimal("46.67"),
        )

    def test_calculates_direct_cost(self):
        self.assertEqual(
            self.twin.estimated_direct_cost,
            Decimal("72.86"),
        )

    def test_calculates_defect_cost(self):
        self.assertEqual(
            self.twin.estimated_defect_cost,
            Decimal("1.46"),
        )

    def test_calculates_total_cost(self):
        self.assertEqual(
            self.twin.estimated_total_cost,
            Decimal("74.32"),
        )

    def test_calculates_selling_price(self):
        self.assertEqual(
            self.twin.estimated_selling_price,
            Decimal("92.90"),
        )

    def test_calculates_profit(self):
        self.assertEqual(
            self.twin.estimated_profit,
            Decimal("18.58"),
        )

    def test_rejects_negative_production_time(self):
        self.twin.production_time_minutes = Decimal("-1")

        with self.assertRaises(ValidationError):
            self.twin.full_clean()

    def test_rejects_defect_rate_above_one_hundred(self):
        self.twin.defect_rate_percent = Decimal("101")

        with self.assertRaises(ValidationError):
            self.twin.full_clean()

    def test_requires_material_when_mass_is_entered(self):
        self.twin.material = None
        self.twin.mass_kg = Decimal("1.500")

        with self.assertRaises(ValidationError):
            self.twin.full_clean()

    def test_requires_technology_when_time_is_entered(self):
        self.twin.technology = None
        self.twin.production_time_minutes = Decimal("30")

        with self.assertRaises(ValidationError):
            self.twin.full_clean()
    
    def test_calculates_mass_when_entered_mass_is_zero(self):
        self.twin.mass_kg = Decimal("0.000")

        self.assertEqual(
            self.twin.effective_mass_kg,
            Decimal("1.215"),
        )