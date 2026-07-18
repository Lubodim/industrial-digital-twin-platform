"""Audit logging for derived Digital Twin creation."""

from __future__ import annotations

from audit.models import AuditLog
from digital_twins.models import DigitalTwin
from experiments.models import Experiment


class TwinCreationAuditService:
    """Create the audit record for a completed twin-creation operation."""

    @staticmethod
    def log_creation(
        *,
        experiment: Experiment,
        source_twin: DigitalTwin,
        result_twin: DigitalTwin,
        created_by,
        applied_change_count: int,
        manual_change_count: int,
        copied_file_count: int,
        ip_address: str | None = None,
        computer_name: str = "",
        user_agent: str = "",
    ) -> AuditLog:
        resolved_ip_address = (
            ip_address or experiment.ip_address
        )

        resolved_computer_name = (
            str(computer_name or "").strip()
            or experiment.computer_name
        )

        resolved_user_agent = str(
            user_agent or ""
        ).strip()

        return AuditLog.objects.create(
            user=created_by,
            action=AuditLog.Action.CREATE,
            entity_type="DigitalTwin",
            entity_id=str(result_twin.pk),
            details={
                "operation": "create_from_experiment",
                "experiment_id": str(experiment.pk),
                "source_twin_id": str(source_twin.pk),
                "result_twin_id": str(result_twin.pk),
                "result_part_number": (
                    result_twin.part_number
                ),
                "applied_change_count": (
                    applied_change_count
                ),
                "manual_change_count": (
                    manual_change_count
                ),
                "copied_file_count": copied_file_count,
            },
            ip_address=resolved_ip_address,
            computer_name=resolved_computer_name,
            user_agent=resolved_user_agent,
        )
