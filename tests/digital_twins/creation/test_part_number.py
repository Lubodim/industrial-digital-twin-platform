from django.contrib.auth import get_user_model
from django.test import TestCase

from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.twin_creation import TwinCreationError
from experiments.twin_creation.part_number import (
    PartNumberGenerator,
)


User = get_user_model()


class PartNumberGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="part-number-engineer",
            password="test-password",
        )

        self.material = MaterialCatalog.objects.create(
            name="Part Number Steel",
            code="PN-S235",
            density_kg_m3="7850",
            price_per_kg="2.50",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="Part Number Laser",
            code="PN-LASER",
            machine_hour_rate="40.00",
        )

    def create_twin(
        self,
        *,
        part_number: str,
        name: str = "Part Number Twin",
    ):
        return DigitalTwin.objects.create(
            name=name,
            part_number=part_number,
            material=self.material,
            technology=self.technology,
            production_time_minutes="10",
            created_by=self.user,
        )

    def test_generates_version_two_for_original_number(self):
        result = PartNumberGenerator.generate(
            "BRACKET-001"
        )

        self.assertEqual(
            result,
            "BRACKET-001-V2",
        )

    def test_increments_existing_version(self):
        result = PartNumberGenerator.generate(
            "BRACKET-001-V2"
        )

        self.assertEqual(
            result,
            "BRACKET-001-V3",
        )

    def test_skips_existing_versions(self):
        self.create_twin(
            part_number="BRACKET-001-V2"
        )
        self.create_twin(
            part_number="BRACKET-001-V3",
            name="Part Number Twin V3",
        )

        result = PartNumberGenerator.generate(
            "BRACKET-001"
        )

        self.assertEqual(
            result,
            "BRACKET-001-V4",
        )

    def test_version_matching_is_case_insensitive(self):
        result = PartNumberGenerator.generate(
            "BRACKET-001-v7"
        )

        self.assertEqual(
            result,
            "BRACKET-001-V8",
        )

    def test_rejects_empty_source_part_number(self):
        with self.assertRaisesMessage(
            TwinCreationError,
            "no valid part number",
        ):
            PartNumberGenerator.generate("")

    def test_accepts_unique_custom_part_number(self):
        result = PartNumberGenerator.validate_custom(
            "CUSTOM-RESULT-001"
        )

        self.assertEqual(
            result,
            "CUSTOM-RESULT-001",
        )

    def test_trims_custom_part_number(self):
        result = PartNumberGenerator.validate_custom(
            "  CUSTOM-RESULT-002  "
        )

        self.assertEqual(
            result,
            "CUSTOM-RESULT-002",
        )

    def test_rejects_existing_custom_part_number(self):
        self.create_twin(
            part_number="CUSTOM-EXISTING"
        )

        with self.assertRaisesMessage(
            TwinCreationError,
            "already exists",
        ):
            PartNumberGenerator.validate_custom(
                "CUSTOM-EXISTING"
            )
