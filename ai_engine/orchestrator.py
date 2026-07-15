from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_engine.prompts import build_messages_from_research_package
from ai_engine.provider_factory import (
    ProviderConfigurationError,
    ProviderFactory,
    ProviderFactoryError,
)
from ai_engine.providers.base import ProviderResult
from ai_engine.research_package import ResearchPackage


@dataclass
class OrchestrationResult:
    """
    Standard result returned by the external research orchestrator.
    """

    success: bool
    provider_name: str
    provider_result: ProviderResult | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def structured_response(self) -> dict[str, Any]:
        """
        Return the normalized provider response when available.
        """

        if self.provider_result is None:
            return {}

        return self.provider_result.structured_response

    @property
    def raw_response(self) -> str:
        """
        Return the original provider response when available.
        """

        if self.provider_result is None:
            return ""

        return self.provider_result.raw_response

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the orchestration result to a serializable dictionary.
        """

        return {
            "success": self.success,
            "provider_name": self.provider_name,
            "provider_result": (
                self.provider_result.to_dict()
                if self.provider_result
                else None
            ),
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class ExternalResearchOrchestrator:
    """
    Coordinates the external AI research pipeline.

    Flow:
    ResearchPackage
        -> Prompt Builder
        -> Provider Factory
        -> External AI Provider
        -> JSON Parser
        -> Schema Validator
        -> ProviderResult
    """

    def run(
        self,
        *,
        research_package: ResearchPackage,
        provider_name: str,
        provider_overrides: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        """
        Run one engineering research request through one provider.
        """

        if not isinstance(research_package, ResearchPackage):
            raise TypeError(
                "research_package must be a ResearchPackage instance."
            )

        if not isinstance(provider_name, str):
            raise TypeError("provider_name must be a string.")

        cleaned_provider_name = provider_name.strip()

        if not cleaned_provider_name:
            raise ValueError("provider_name cannot be empty.")

        overrides = provider_overrides or {}

        if not isinstance(overrides, dict):
            raise TypeError("provider_overrides must be a dictionary.")

        try:
            provider = ProviderFactory.create(
                cleaned_provider_name,
                **overrides,
            )

            messages = build_messages_from_research_package(
                research_package
            )

            provider_result = provider.send_messages(messages)

            return OrchestrationResult(
                success=provider_result.success,
                provider_name=provider.provider_name,
                provider_result=provider_result,
                error_message=provider_result.error_message,
                metadata={
                    "provider_info": provider.get_provider_info(),
                    "message_count": len(messages),
                    "pipeline_stage": (
                        "completed"
                        if provider_result.success
                        else "provider_failed"
                    ),
                },
            )

        except ProviderConfigurationError as error:
            return OrchestrationResult(
                success=False,
                provider_name=cleaned_provider_name.upper(),
                error_message=str(error),
                metadata={
                    "pipeline_stage": "provider_configuration",
                },
            )

        except ProviderFactoryError as error:
            return OrchestrationResult(
                success=False,
                provider_name=cleaned_provider_name.upper(),
                error_message=str(error),
                metadata={
                    "pipeline_stage": "provider_factory",
                },
            )

        except ValueError as error:
            return OrchestrationResult(
                success=False,
                provider_name=cleaned_provider_name.upper(),
                error_message=str(error),
                metadata={
                    "pipeline_stage": "request_validation",
                },
            )

        except Exception as error:
            return OrchestrationResult(
                success=False,
                provider_name=cleaned_provider_name.upper(),
                error_message=(
                    "Unexpected orchestration error: "
                    f"{type(error).__name__}: {error}"
                ),
                metadata={
                    "pipeline_stage": "unexpected",
                },
            )


def run_external_research(
    *,
    research_package: ResearchPackage,
    provider_name: str = "openai",
    provider_overrides: dict[str, Any] | None = None,
) -> OrchestrationResult:
    """
    Convenience function for running one external research request.
    """

    orchestrator = ExternalResearchOrchestrator()

    return orchestrator.run(
        research_package=research_package,
        provider_name=provider_name,
        provider_overrides=provider_overrides,
    )