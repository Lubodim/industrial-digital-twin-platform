"""Part-number generation for derived Digital Twins."""

from __future__ import annotations

import re

from digital_twins.models import DigitalTwin

from .exceptions import TwinCreationError


class PartNumberGenerator:
    """
    Generate sequential derived part numbers.

    Examples:

    RB-001 -> RB-001-V2
    RB-001-V2 -> RB-001-V3
    """

    VERSION_PATTERN = re.compile(
        r"(.+)-V(\d+)",
        flags=re.IGNORECASE,
    )

    @classmethod
    def generate(
        cls,
        source_part_number: str,
    ) -> str:
        normalized_source = str(
            source_part_number or ""
        ).strip()

        if not normalized_source:
            raise TwinCreationError(
                "The source Digital Twin has no valid part number."
            )

        match = cls.VERSION_PATTERN.fullmatch(
            normalized_source
        )

        if match:
            base_part_number = match.group(1)
            version = int(match.group(2)) + 1
        else:
            base_part_number = normalized_source
            version = 2

        while True:
            candidate = f"{base_part_number}-V{version}"

            exists = DigitalTwin.objects.filter(
                part_number=candidate
            ).exists()

            if not exists:
                return candidate

            version += 1

    @staticmethod
    def validate_custom(
        part_number: str,
    ) -> str:
        normalized = str(part_number or "").strip()

        if not normalized:
            raise TwinCreationError(
                "The result part number cannot be empty."
            )

        if DigitalTwin.objects.filter(
            part_number=normalized
        ).exists():
            raise TwinCreationError(
                f"Digital Twin part number "
                f"'{normalized}' already exists."
            )

        return normalized
