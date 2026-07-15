from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from ai_engine.external_research_agent import (
    ExternalResearchAgent,
    ExternalResearchRunResult,
)
from ai_engine.models import (
    ExternalResearchRequest,
    ProviderResponse,
    ValidatedResearchPackage,
)
from ai_engine.research_package import (
    ResearchPackage,
    build_research_package,
)
from experiments.models import (
    Experiment,
    ExperimentChatMessage,
)


@dataclass
class ExperimentResearchResult:
    """
    Result returned after one engineer question has been processed
    by the external research agent.
    """

    research_request: ExternalResearchRequest
    agent_result: ExternalResearchRunResult
    created_chat_messages: list[ExperimentChatMessage]

    @property
    def success(self) -> bool:
        return self.agent_result.success


class ExperimentResearchService:
    """
    Connect an experiment chat question with the external AI pipeline.

    Responsibilities:
    - read the selected digital twin;
    - create a sanitized ResearchPackage;
    - create a database research request;
    - call one or more external providers;
    - preserve database records for every provider;
    - preserve paths to raw and validated JSON files;
    - add successful provider answers to the experiment chat;
    - update the experiment lifecycle.

    This service must not send confidential fields such as:
    - CAD files;
    - internal labor or energy costs;
    - selling prices;
    - profit margins;
    - usernames or customer data.
    """

    PROVIDER_MODEL_MAPPING = {
        "OPENAI": ProviderResponse.Provider.OPENAI,
        "CLAUDE": ProviderResponse.Provider.ANTHROPIC,
        "ANTHROPIC": ProviderResponse.Provider.ANTHROPIC,
        "GEMINI": ProviderResponse.Provider.GEMINI,
        "GROK": ProviderResponse.Provider.GROK,
    }

    CHAT_PROVIDER_MAPPING = {
        "OPENAI": ExperimentChatMessage.Provider.OPENAI,
        "CLAUDE": ExperimentChatMessage.Provider.CLAUDE,
        "ANTHROPIC": ExperimentChatMessage.Provider.CLAUDE,
        "GEMINI": ExperimentChatMessage.Provider.GEMINI,
        "GROK": ExperimentChatMessage.Provider.GROK,
    }

    def __init__(
        self,
        *,
        external_agent: ExternalResearchAgent | None = None,
    ) -> None:
        self.external_agent = (
            external_agent or ExternalResearchAgent()
        )

    def run_question(
        self,
        *,
        experiment: Experiment,
        engineer_question: str,
        requested_by,
        provider_names: list[str] | None = None,
        required_properties: list[str] | None = None,
        batch_size: int | None = None,
        provider_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> ExperimentResearchResult:
        """
        Send one engineer question through the external research pipeline.

        The engineer can call this method repeatedly. Every call becomes
        another question-and-answer cycle in the same experiment.
        """

        if not isinstance(experiment, Experiment):
            raise TypeError(
                "experiment must be an Experiment instance."
            )

        if experiment.pk is None:
            raise ValueError(
                "experiment must be saved before research can run."
            )

        cleaned_question = str(engineer_question or "").strip()

        if not cleaned_question:
            raise ValueError(
                "engineer_question cannot be empty."
            )

        research_package = self._build_package(
            experiment=experiment,
            engineer_question=cleaned_question,
            required_properties=required_properties,
            batch_size=batch_size,
        )

        with transaction.atomic():
            engineer_message = (
                ExperimentChatMessage.objects.create(
                    experiment=experiment,
                    role=ExperimentChatMessage.Role.ENGINEER,
                    provider=ExperimentChatMessage.Provider.NONE,
                    content=cleaned_question,
                    created_by=requested_by,
                    metadata={
                        "research_package": (
                            research_package.to_dict()
                        ),
                    },
                )
            )

            research_request = (
                ExternalResearchRequest.objects.create(
                    experiment=experiment,
                    sanitized_query=research_package.to_dict(),
                    status=(
                        ExternalResearchRequest.Status.RUNNING
                    ),
                    requested_by=requested_by,
                    started_at=timezone.now(),
                )
            )

            if experiment.status in {
                Experiment.Status.DRAFT,
                Experiment.Status.READY_FOR_ANALYSIS,
                Experiment.Status.FAILED,
            }:
                experiment.status = Experiment.Status.CHATTING
                experiment.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

        try:
            agent_result = self.external_agent.run(
                research_package=research_package,
                provider_names=provider_names,
                provider_overrides=provider_overrides,
            )

        except Exception as exc:
            research_request.status = (
                ExternalResearchRequest.Status.FAILED
            )
            research_request.completed_at = timezone.now()
            research_request.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            ExperimentChatMessage.objects.create(
                experiment=experiment,
                role=ExperimentChatMessage.Role.SYSTEM,
                provider=ExperimentChatMessage.Provider.NONE,
                content=(
                    "External research failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
                created_by=requested_by,
                metadata={
                    "research_request_id": research_request.pk,
                },
            )

            raise

        created_chat_messages = self._persist_agent_result(
            experiment=experiment,
            research_request=research_request,
            agent_result=agent_result,
            requested_by=requested_by,
        )

        # Engineer message is included for convenient caller access.
        all_created_messages = [
            engineer_message,
            *created_chat_messages,
        ]

        return ExperimentResearchResult(
            research_request=research_request,
            agent_result=agent_result,
            created_chat_messages=all_created_messages,
        )

    def _build_package(
        self,
        *,
        experiment: Experiment,
        engineer_question: str,
        required_properties: list[str] | None,
        batch_size: int | None,
    ) -> ResearchPackage:
        """
        Build the public and sanitized package sent outside the LAN.

        Deliberately excluded:
        - part number;
        - CAD files;
        - volume and exact mass;
        - material prices;
        - labor and energy costs;
        - total cost and selling price;
        - desired profit margin.
        """

        twin = experiment.digital_twin

        material_name = (
            twin.material.name
            if twin.material is not None
            else None
        )

        technology_name = (
            twin.technology.name
            if twin.technology is not None
            else None
        )

        cycle_time = self._decimal_to_float(
            twin.production_time_minutes
        )

        generic_product_type = (
            twin.name.strip()
            if twin.name
            else "Industrial component"
        )

        objective = (
            experiment.objective.strip()
            if experiment.objective
            else None
        )

        return build_research_package(
            engineer_question=engineer_question,
            generic_product_type=generic_product_type,
            current_material=material_name,
            current_technology=technology_name,
            batch_size=batch_size,
            current_cycle_time_minutes=cycle_time,
            required_properties=required_properties or [],
            objective=objective,
        )

    def _persist_agent_result(
        self,
        *,
        experiment: Experiment,
        research_request: ExternalResearchRequest,
        agent_result: ExternalResearchRunResult,
        requested_by,
    ) -> list[ExperimentChatMessage]:
        """
        Save provider records, one combined validated package and chat replies.
        """

        created_chat_messages: list[
            ExperimentChatMessage
        ] = []

        validated_provider_results: dict[str, Any] = {}
        validation_errors: list[dict[str, str]] = []

        with transaction.atomic():
            for record in agent_result.provider_records:
                provider_code = self._database_provider_code(
                    record.provider_name
                )

                orchestration_result = (
                    record.orchestration_result
                )

                provider_result = (
                    orchestration_result.provider_result
                )

                structured_response = (
                    orchestration_result.structured_response
                    or {}
                )

                raw_response = ""

                model_name = ""
                response_time_ms = None

                if provider_result is not None:
                    raw_response = (
                        provider_result.raw_response or ""
                    )

                    response_time_ms = (
                        provider_result.response_time_ms
                    )

                    model_name = provider_result.model

                provider_status = (
                    ProviderResponse.Status.SUCCESS
                    if record.success
                    else ProviderResponse.Status.FAILED
                )

                ProviderResponse.objects.update_or_create(
                    research_request=research_request,
                    provider=provider_code,
                    defaults={
                        "model_name": model_name,
                        "status": provider_status,
                        "raw_response": raw_response,
                        "structured_response": (
                            structured_response
                        ),
                        "error_message": (
                            record.error_message or ""
                        ),
                        "response_time_ms": response_time_ms,
                    },
                )

                if record.success and structured_response:
                    normalized_name = (
                        record.provider_name.upper()
                    )

                    validated_provider_results[
                        normalized_name
                    ] = {
                        "research_result": (
                            structured_response
                        ),
                        "raw_file_path": (
                            record.raw_file_path
                        ),
                        "validated_file_path": (
                            record.validated_file_path
                        ),
                    }

                    assistant_message = (
                        ExperimentChatMessage.objects.create(
                            experiment=experiment,
                            role=(
                                ExperimentChatMessage
                                .Role.ASSISTANT
                            ),
                            provider=self._chat_provider_code(
                                record.provider_name
                            ),
                            content=self._build_chat_content(
                                structured_response
                            ),
                            created_by=None,
                            metadata={
                                "research_request_id": (
                                    research_request.pk
                                ),
                                "run_id": agent_result.run_id,
                                "raw_file_path": (
                                    record.raw_file_path
                                ),
                                "validated_file_path": (
                                    record.validated_file_path
                                ),
                                "structured_response": (
                                    structured_response
                                ),
                            },
                        )
                    )

                    created_chat_messages.append(
                        assistant_message
                    )

                else:
                    validation_errors.append(
                        {
                            "provider": (
                                record.provider_name
                            ),
                            "error": (
                                record.error_message
                                or "Provider failed."
                            ),
                        }
                    )

            validation_status = (
                ValidatedResearchPackage
                .ValidationStatus.VALID
                if validated_provider_results
                else ValidatedResearchPackage
                .ValidationStatus.INVALID
            )

            ValidatedResearchPackage.objects.update_or_create(
                research_request=research_request,
                defaults={
                    "validated_data": {
                        "run_id": agent_result.run_id,
                        "providers": (
                            validated_provider_results
                        ),
                    },
                    "validation_status": validation_status,
                    "validation_errors": validation_errors,
                    "validated_at": timezone.now(),
                },
            )

            research_request.status = (
                self._research_request_status(
                    agent_result
                )
            )

            research_request.completed_at = timezone.now()

            research_request.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            experiment.external_results = (
                self._merge_experiment_results(
                    current_results=(
                        experiment.external_results
                    ),
                    research_request=research_request,
                    agent_result=agent_result,
                    validated_results=(
                        validated_provider_results
                    ),
                )
            )

            experiment.save(
                update_fields=[
                    "external_results",
                    "updated_at",
                ]
            )

        return created_chat_messages

    @staticmethod
    def _merge_experiment_results(
        *,
        current_results: dict[str, Any],
        research_request: ExternalResearchRequest,
        agent_result: ExternalResearchRunResult,
        validated_results: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Append one research run without deleting previous chat research.
        """

        merged = (
            dict(current_results)
            if isinstance(current_results, dict)
            else {}
        )

        runs = merged.get("runs", [])

        if not isinstance(runs, list):
            runs = []

        runs.append(
            {
                "research_request_id": research_request.pk,
                "run_id": agent_result.run_id,
                "started_at": agent_result.started_at,
                "completed_at": agent_result.completed_at,
                "successful_providers": (
                    agent_result.successful_providers
                ),
                "failed_providers": (
                    agent_result.failed_providers
                ),
                "providers": validated_results,
            }
        )

        merged["runs"] = runs
        merged["latest_run_id"] = agent_result.run_id

        return merged

    @staticmethod
    def _build_chat_content(
        structured_response: dict[str, Any],
    ) -> str:
        """
        Produce a readable answer for the experiment chat.

        The complete structured JSON remains available in metadata
        and in the validated JSON file.
        """

        summary = str(
            structured_response.get("summary", "")
        ).strip()

        if summary:
            return summary

        materials = structured_response.get(
            "materials",
            {},
        )

        if isinstance(materials, dict):
            recommended_material = str(
                materials.get(
                    "recommended_material",
                    "",
                )
            ).strip()

            if recommended_material:
                return (
                    "Recommended material: "
                    f"{recommended_material}"
                )

        return (
            "The provider returned a structured engineering "
            "research result. See the attached metadata for "
            "the complete validated response."
        )

    @classmethod
    def _database_provider_code(
        cls,
        provider_name: str,
    ) -> str:
        normalized = str(provider_name).strip().upper()

        try:
            return cls.PROVIDER_MODEL_MAPPING[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported database provider: {provider_name}"
            ) from exc

    @classmethod
    def _chat_provider_code(
        cls,
        provider_name: str,
    ) -> str:
        normalized = str(provider_name).strip().upper()

        try:
            return cls.CHAT_PROVIDER_MAPPING[normalized]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported chat provider: {provider_name}"
            ) from exc

    @staticmethod
    def _research_request_status(
        agent_result: ExternalResearchRunResult,
    ) -> str:
        if agent_result.all_providers_succeeded:
            return ExternalResearchRequest.Status.COMPLETED

        if agent_result.success:
            return ExternalResearchRequest.Status.PARTIAL

        return ExternalResearchRequest.Status.FAILED

    @staticmethod
    def _decimal_to_float(
        value: Decimal | None,
    ) -> float | None:
        if value is None:
            return None

        return float(value)
