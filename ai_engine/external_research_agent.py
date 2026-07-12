from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_engine.orchestrator import (
    OrchestrationResult,
    run_external_research,
)
from ai_engine.provider_factory import ProviderFactory
from ai_engine.research_package import ResearchPackage


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_RAW_RESEARCH_DIRECTORY = (
    PROJECT_ROOT / "data" / "exchange" / "raw_research"
)

DEFAULT_VALIDATED_RESEARCH_DIRECTORY = (
    PROJECT_ROOT / "data" / "exchange" / "validated_research"
)


@dataclass
class ProviderResearchRecord:
    """
    Result produced by one external AI provider.
    """

    provider_name: str
    success: bool
    orchestration_result: OrchestrationResult
    raw_file_path: str | None = None
    validated_file_path: str | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "success": self.success,
            "orchestration_result": (
                self.orchestration_result.to_dict()
            ),
            "raw_file_path": self.raw_file_path,
            "validated_file_path": self.validated_file_path,
            "error_message": self.error_message,
        }


@dataclass
class ExternalResearchRunResult:
    """
    Complete result from one external research agent run.
    """

    run_id: str
    started_at: str
    completed_at: str
    requested_providers: list[str]
    successful_providers: list[str] = field(default_factory=list)
    failed_providers: list[str] = field(default_factory=list)
    provider_records: list[ProviderResearchRecord] = field(
        default_factory=list
    )

    @property
    def success(self) -> bool:
        """
        The run is considered successful when at least one provider succeeds.
        """

        return bool(self.successful_providers)

    @property
    def all_providers_succeeded(self) -> bool:
        return (
            bool(self.requested_providers)
            and not self.failed_providers
            and len(self.successful_providers)
            == len(self.requested_providers)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "success": self.success,
            "all_providers_succeeded": self.all_providers_succeeded,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "requested_providers": self.requested_providers,
            "successful_providers": self.successful_providers,
            "failed_providers": self.failed_providers,
            "provider_records": [
                record.to_dict()
                for record in self.provider_records
            ],
        }


class ExternalResearchAgent:
    """
    Coordinates research through one or more external AI providers.

    Responsibilities:
    - receive a sanitized ResearchPackage;
    - run configured external providers;
    - preserve raw provider responses;
    - preserve validated structured responses;
    - continue when one provider fails;
    - return one combined run result.

    The agent does not receive the complete Digital Twin.
    It works only with the sanitized ResearchPackage.
    """

    def __init__(
        self,
        *,
        raw_research_directory: Path | str | None = None,
        validated_research_directory: Path | str | None = None,
    ) -> None:
        self.raw_research_directory = Path(
            raw_research_directory
            or DEFAULT_RAW_RESEARCH_DIRECTORY
        )

        self.validated_research_directory = Path(
            validated_research_directory
            or DEFAULT_VALIDATED_RESEARCH_DIRECTORY
        )

        self.raw_research_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.validated_research_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run(
        self,
        *,
        research_package: ResearchPackage,
        provider_names: list[str] | None = None,
        provider_overrides: (
            dict[str, dict[str, Any]] | None
        ) = None,
    ) -> ExternalResearchRunResult:
        """
        Run external research through all requested providers.

        Providers are executed sequentially in the MVP version.
        A failure from one provider does not stop the remaining providers.
        """

        if not isinstance(research_package, ResearchPackage):
            raise TypeError(
                "research_package must be a ResearchPackage instance."
            )

        normalized_providers = self._normalize_provider_names(
            provider_names
        )

        overrides_by_provider = provider_overrides or {}

        if not isinstance(overrides_by_provider, dict):
            raise TypeError(
                "provider_overrides must be a dictionary."
            )

        run_id = uuid4().hex
        started_at = self._utc_now()

        records: list[ProviderResearchRecord] = []
        successful_providers: list[str] = []
        failed_providers: list[str] = []

        for provider_name in normalized_providers:
            provider_specific_overrides = (
                overrides_by_provider.get(provider_name, {})
            )

            if not isinstance(
                provider_specific_overrides,
                dict,
            ):
                raise TypeError(
                    "Each provider override must be a dictionary. "
                    f"Invalid provider: {provider_name}."
                )

            orchestration_result = run_external_research(
                research_package=research_package,
                provider_name=provider_name,
                provider_overrides=provider_specific_overrides,
            )

            record = self._create_provider_record(
                run_id=run_id,
                provider_name=provider_name,
                orchestration_result=orchestration_result,
            )

            records.append(record)

            if record.success:
                successful_providers.append(
                    record.provider_name
                )
            else:
                failed_providers.append(
                    record.provider_name
                )

        completed_at = self._utc_now()

        return ExternalResearchRunResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            requested_providers=normalized_providers,
            successful_providers=successful_providers,
            failed_providers=failed_providers,
            provider_records=records,
        )

    def run_configured_providers(
        self,
        *,
        research_package: ResearchPackage,
    ) -> ExternalResearchRunResult:
        """
        Run all providers that currently have API keys configured.
        """

        configured_providers = (
            ProviderFactory.get_configured_providers()
        )

        if not configured_providers:
            raise RuntimeError(
                "No external AI providers are configured."
            )

        return self.run(
            research_package=research_package,
            provider_names=configured_providers,
        )

    def _create_provider_record(
        self,
        *,
        run_id: str,
        provider_name: str,
        orchestration_result: OrchestrationResult,
    ) -> ProviderResearchRecord:
        """
        Persist raw and validated responses for one provider.
        """

        normalized_provider_name = (
            orchestration_result.provider_name.lower()
            if orchestration_result.provider_name
            else provider_name.lower()
        )

        raw_file_path: str | None = None
        validated_file_path: str | None = None

        provider_result = (
            orchestration_result.provider_result
        )

        if (
            provider_result is not None
            and provider_result.raw_response
        ):
            raw_payload = {
                "run_id": run_id,
                "provider": normalized_provider_name,
                "success": provider_result.success,
                "response_time_ms": (
                    provider_result.response_time_ms
                ),
                "error_message": (
                    provider_result.error_message
                ),
                "usage": provider_result.usage,
                "metadata": provider_result.metadata,
                "raw_response": (
                    provider_result.raw_response
                ),
            }

            raw_path = self._build_file_path(
                directory=self.raw_research_directory,
                run_id=run_id,
                provider_name=normalized_provider_name,
                suffix="raw",
            )

            self._write_json_file(
                file_path=raw_path,
                data=raw_payload,
            )

            raw_file_path = str(raw_path)

        if (
            orchestration_result.success
            and orchestration_result.structured_response
        ):
            validated_payload = {
                "run_id": run_id,
                "provider": normalized_provider_name,
                "validated_at": self._utc_now(),
                "research_result": (
                    orchestration_result.structured_response
                ),
            }

            validated_path = self._build_file_path(
                directory=(
                    self.validated_research_directory
                ),
                run_id=run_id,
                provider_name=normalized_provider_name,
                suffix="validated",
            )

            self._write_json_file(
                file_path=validated_path,
                data=validated_payload,
            )

            validated_file_path = str(validated_path)

        return ProviderResearchRecord(
            provider_name=normalized_provider_name.upper(),
            success=orchestration_result.success,
            orchestration_result=orchestration_result,
            raw_file_path=raw_file_path,
            validated_file_path=validated_file_path,
            error_message=(
                orchestration_result.error_message
            ),
        )

    @staticmethod
    def _normalize_provider_names(
        provider_names: list[str] | None,
    ) -> list[str]:
        """
        Validate, normalize and deduplicate provider names.
        """

        if provider_names is None:
            provider_names = ["openai"]

        if not isinstance(provider_names, list):
            raise TypeError(
                "provider_names must be a list."
            )

        if not provider_names:
            raise ValueError(
                "provider_names cannot be empty."
            )

        normalized: list[str] = []

        for provider_name in provider_names:
            if not isinstance(provider_name, str):
                raise TypeError(
                    "Every provider name must be a string."
                )

            cleaned_name = provider_name.strip().lower()

            if not cleaned_name:
                raise ValueError(
                    "Provider names cannot be empty."
                )

            if cleaned_name not in normalized:
                normalized.append(cleaned_name)

        return normalized

    @staticmethod
    def _build_file_path(
        *,
        directory: Path,
        run_id: str,
        provider_name: str,
        suffix: str,
    ) -> Path:
        safe_provider_name = "".join(
            character
            for character in provider_name
            if character.isalnum()
            or character in {"-", "_"}
        )

        filename = (
            f"{run_id}_{safe_provider_name}_{suffix}.json"
        )

        return directory / filename

    @staticmethod
    def _write_json_file(
        *,
        file_path: Path,
        data: dict[str, Any],
    ) -> None:
        """
        Save UTF-8 JSON atomically enough for the MVP.
        """

        temporary_path = file_path.with_suffix(
            file_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(file_path)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()


def run_external_agent(
    *,
    research_package: ResearchPackage,
    provider_names: list[str] | None = None,
    provider_overrides: (
        dict[str, dict[str, Any]] | None
    ) = None,
) -> ExternalResearchRunResult:
    """
    Convenience function for running the external research agent.
    """

    agent = ExternalResearchAgent()

    return agent.run(
        research_package=research_package,
        provider_names=provider_names,
        provider_overrides=provider_overrides,
    )