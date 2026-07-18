"""Result objects used by the Digital Twin creation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from digital_twins.models import DigitalTwin


@dataclass(frozen=True, slots=True)
class AppliedProposalChange:
    """One approved proposal applied directly to a Digital Twin field."""

    proposal_id: str
    proposal_sequence: int
    proposal_title: str
    field_name: str
    old_value: Any
    new_value: Any


@dataclass(frozen=True, slots=True)
class ManualProposalChange:
    """
    Approved proposal that cannot be applied to a direct model field.

    Such proposals remain engineering or CAD instructions and are stored
    in the experiment history.
    """

    proposal_id: str
    proposal_sequence: int
    proposal_title: str
    category: str
    parameter_name: str | None
    current_value: Any
    proposed_value: Any
    unit: str | None
    reason: str
    expected_benefit: str
    validation_requirements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TwinCreationResult:
    """Structured result returned after creating a derived Digital Twin."""

    source_twin: DigitalTwin
    result_twin: DigitalTwin
    applied_changes: tuple[AppliedProposalChange, ...]
    manual_changes: tuple[ManualProposalChange, ...]
    copied_file_count: int

    @property
    def applied_change_count(self) -> int:
        return len(self.applied_changes)

    @property
    def manual_change_count(self) -> int:
        return len(self.manual_changes)

    @property
    def total_change_count(self) -> int:
        return self.applied_change_count + self.manual_change_count
