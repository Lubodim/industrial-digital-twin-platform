"""Copy a source Digital Twin and its related file records."""

from __future__ import annotations

from digital_twins.models import (
    DigitalTwin,
    DigitalTwinFile,
)

from .exceptions import TwinCreationError
from .part_number import PartNumberGenerator


class DigitalTwinCopier:
    """Create an unsaved copy of a source Digital Twin."""

    def __init__(
        self,
        *,
        part_number_generator: type[
            PartNumberGenerator
        ] = PartNumberGenerator,
    ) -> None:
        self.part_number_generator = (
            part_number_generator
        )

    def build_copy(
        self,
        *,
        source_twin: DigitalTwin,
        created_by,
        part_number: str | None = None,
        name: str | None = None,
    ) -> DigitalTwin:
        if part_number is None:
            generated_part_number = (
                self.part_number_generator.generate(
                    source_twin.part_number
                )
            )
        else:
            generated_part_number = (
                self.part_number_generator.validate_custom(
                    part_number
                )
            )

        if name is None:
            generated_name = (
                f"{source_twin.name} - Derived"
            )
        else:
            generated_name = str(name).strip()

        if not generated_name:
            raise TwinCreationError(
                "The result Digital Twin name cannot be empty."
            )

        return DigitalTwin(
            name=generated_name,
            part_number=generated_part_number,
            description=source_twin.description,
            material=source_twin.material,
            technology=source_twin.technology,
            cad_file=source_twin.cad_file,
            image_file=source_twin.image_file,
            volume_m3=source_twin.volume_m3,
            mass_kg=source_twin.mass_kg,
            production_time_minutes=(
                source_twin.production_time_minutes
            ),
            labor_cost=source_twin.labor_cost,
            energy_cost=source_twin.energy_cost,
            defect_rate_percent=(
                source_twin.defect_rate_percent
            ),
            desired_profit_margin_percent=(
                source_twin
                .desired_profit_margin_percent
            ),
            created_by=created_by,
            updated_by=created_by,
            is_active=True,
        )

    @staticmethod
    def copy_related_files(
        *,
        source_twin: DigitalTwin,
        result_twin: DigitalTwin,
        uploaded_by,
    ) -> int:
        source_files = list(source_twin.files.all())

        if not source_files:
            return 0

        copied_files = [
            DigitalTwinFile(
                digital_twin=result_twin,
                file_type=item.file_type,
                file=item.file.name,
                description=item.description,
                uploaded_by=uploaded_by,
            )
            for item in source_files
        ]

        DigitalTwinFile.objects.bulk_create(
            copied_files
        )

        return len(copied_files)
