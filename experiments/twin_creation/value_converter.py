"""Conversion and catalog lookup helpers for proposal values."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from digital_twins.models import (
    MaterialCatalog,
    TechnologyCatalog,
)

from .exceptions import TwinCreationError


class ProposalValueConverter:
    """Convert proposal values into values accepted by DigitalTwin fields."""

    @staticmethod
    def extract_lookup_value(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        if isinstance(value, dict):
            for key in ("code", "name", "value"):
                candidate = value.get(key)

                if candidate is not None:
                    return str(candidate).strip()

            return ""

        return str(value).strip()

    @classmethod
    def resolve_material(
        cls,
        value: Any,
    ) -> MaterialCatalog:
        lookup_value = cls.extract_lookup_value(value)

        if not lookup_value:
            raise TwinCreationError(
                "The material proposal does not contain "
                "a material code or name."
            )

        material = MaterialCatalog.objects.filter(
            is_active=True,
            code__iexact=lookup_value,
        ).first()

        if material is None:
            material = MaterialCatalog.objects.filter(
                is_active=True,
                name__iexact=lookup_value,
            ).first()

        if material is None:
            raise TwinCreationError(
                f"Material '{lookup_value}' was not found "
                "in the active material catalog."
            )

        return material

    @classmethod
    def resolve_technology(
        cls,
        value: Any,
    ) -> TechnologyCatalog:
        lookup_value = cls.extract_lookup_value(value)

        if not lookup_value:
            raise TwinCreationError(
                "The technology proposal does not contain "
                "a technology code or name."
            )

        technology = TechnologyCatalog.objects.filter(
            is_active=True,
            code__iexact=lookup_value,
        ).first()

        if technology is None:
            technology = TechnologyCatalog.objects.filter(
                is_active=True,
                name__iexact=lookup_value,
            ).first()

        if technology is None:
            raise TwinCreationError(
                f"Technology '{lookup_value}' was not found "
                "in the active technology catalog."
            )

        return technology

    @staticmethod
    def to_decimal(
        *,
        value: Any,
        field_name: str,
    ) -> Decimal:
        extracted_value = value

        if isinstance(extracted_value, dict):
            for key in (
                "value",
                "amount",
                "proposed_value",
            ):
                if key in extracted_value:
                    extracted_value = extracted_value[key]
                    break

        if (
            extracted_value is None
            or isinstance(extracted_value, bool)
        ):
            raise TwinCreationError(
                f"Proposal for '{field_name}' must contain "
                "a numeric proposed value."
            )

        try:
            return Decimal(str(extracted_value))
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise TwinCreationError(
                f"Proposed value '{extracted_value}' for "
                f"'{field_name}' is not numeric."
            ) from exc

    @staticmethod
    def to_text(
        *,
        value: Any,
        field_name: str,
    ) -> str:
        extracted_value = value

        if isinstance(extracted_value, dict):
            for key in ("value", "name", "text"):
                if key in extracted_value:
                    extracted_value = extracted_value[key]
                    break

        if extracted_value is None:
            raise TwinCreationError(
                f"Proposal for '{field_name}' does not "
                "contain a proposed value."
            )

        result = str(extracted_value).strip()

        if not result:
            raise TwinCreationError(
                f"Proposed value for '{field_name}' "
                "cannot be empty."
            )

        return result

    @staticmethod
    def serialize(
        value: Any,
    ) -> Any:
        if isinstance(value, Decimal):
            return str(value)

        if isinstance(
            value,
            (
                MaterialCatalog,
                TechnologyCatalog,
            ),
        ):
            return {
                "id": value.pk,
                "code": value.code,
                "name": value.name,
            }

        return value
