"""
Local engineering analysis agent.

The agent collects local project data, builds a deterministic prompt,
calls Ollama and persists the structured engineering analysis.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from ai_engine.local_ai.analysis_result import (
    EngineeringAnalysisResult,
    EngineeringAnalysisValidationError,
)
from ai_engine.local_ai.ollama_client import (
    OllamaClient,
)
from ai_engine.local_ai.prompt_builder import (
    EngineeringPromptBuilder,
)
from ai_engine.models import (
    InternalAnalysis,
    ValidatedResearchPackage,
)
from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)
from experiments.models import (
    Experiment,
    ExperimentChatMessage,
)


class EngineeringAgentError(RuntimeError):
    """
    Raised when local engineering analysis cannot be completed.
    """


class EngineeringAgent:
    """
    Orchestrate one complete local engineering analysis.

    The agent:
    - reads the selected digital twin;
    - reads experiment chat history;
    - reads validated external research;
    - reads local catalogs and previous experiments;
    - asks the local Ollama model for structured analysis;
    - validates and persists the result.

    It never changes the original digital twin.
    """

    def __init__(
        self,
        *,
        client: OllamaClient | None = None,
        prompt_builder: (
            EngineeringPromptBuilder | None
        ) = None,
    ) -> None:
        self.client = (
            client or OllamaClient()
        )

        self.prompt_builder = (
            prompt_builder
            or EngineeringPromptBuilder()
        )

    def analyze(
        self,
        *,
        experiment: Experiment,
        requested_by=None,
        persist: bool = True,
    ) -> EngineeringAnalysisResult:
        """
        Execute local analysis for one saved experiment.
        """

        self._validate_experiment(
            experiment
        )

        context = self.build_context(
            experiment=experiment
        )

        built_prompt = self.prompt_builder.build(
            digital_twin=context[
                "digital_twin"
            ],
            experiment=context["experiment"],
            chat_history=context[
                "chat_history"
            ],
            external_research=context[
                "external_research"
            ],
            materials=context["materials"],
            technologies=context[
                "technologies"
            ],
            previous_experiments=context[
                "previous_experiments"
            ],
        )

        self._mark_analysis_started(
            experiment
        )

        response = self.client.ask(
            prompt=built_prompt.user_prompt,
            system_prompt=(
                built_prompt.system_prompt
            ),
            response_schema=(
                built_prompt.response_schema
            ),
        )

        if not response.success:
            self._mark_analysis_failed(
                experiment=experiment,
                error=response.error,
            )

            raise EngineeringAgentError(
                response.error
                or "Local AI analysis failed."
            )

        try:
            result = (
                EngineeringAnalysisResult.from_dict(
                    response.structured_response,
                    model_name=response.model,
                    response_time_ms=(
                        response.response_time_ms
                    ),
                    prompt_token_count=(
                        response.prompt_token_count
                    ),
                    output_token_count=(
                        response.output_token_count
                    ),
                )
            )

        except EngineeringAnalysisValidationError as exc:
            self._mark_analysis_failed(
                experiment=experiment,
                error=str(exc),
            )

            raise EngineeringAgentError(
                "The local model returned an invalid "
                f"engineering analysis: {exc}"
            ) from exc

        if persist:
            self.persist_result(
                experiment=experiment,
                result=result,
                context=context,
                requested_by=requested_by,
            )

        return result

    def build_context(
        self,
        *,
        experiment: Experiment,
    ) -> dict[str, Any]:
        """
        Collect all local information needed by the model.
        """

        twin = experiment.digital_twin

        return {
            "digital_twin": (
                self._serialize_digital_twin(
                    twin
                )
            ),
            "experiment": (
                self._serialize_experiment(
                    experiment
                )
            ),
            "chat_history": (
                self._serialize_chat_history(
                    experiment
                )
            ),
            "external_research": (
                self._serialize_external_research(
                    experiment
                )
            ),
            "materials": (
                self._serialize_material_catalog()
            ),
            "technologies": (
                self._serialize_technology_catalog()
            ),
            "previous_experiments": (
                self._serialize_previous_experiments(
                    experiment
                )
            ),
        }

    @transaction.atomic
    def persist_result(
        self,
        *,
        experiment: Experiment,
        result: EngineeringAnalysisResult,
        context: dict[str, Any],
        requested_by=None,
    ) -> InternalAnalysis:
        """
        Store the completed result without changing the source twin.
        """

        result_data = result.to_dict()

        latest_package = (
            ValidatedResearchPackage.objects.filter(
                research_request__experiment=(
                    experiment
                ),
                validation_status=(
                    ValidatedResearchPackage
                    .ValidationStatus.VALID
                ),
            )
            .order_by(
                "-validated_at",
                "-research_request__created_at",
            )
            .first()
        )

        internal_analysis = (
            InternalAnalysis.objects.create(
                experiment=experiment,
                research_package=latest_package,
                local_model_name=(
                    result.model_name
                ),
                twin_snapshot=context[
                    "digital_twin"
                ],
                base_calculations={
                    "estimated_material_cost": (
                        context["digital_twin"]
                        .get(
                            "estimated_material_cost"
                        )
                    ),
                    "estimated_machine_cost": (
                        context["digital_twin"]
                        .get(
                            "estimated_machine_cost"
                        )
                    ),
                    "estimated_total_cost": (
                        context["digital_twin"]
                        .get(
                            "estimated_total_cost"
                        )
                    ),
                    "estimated_selling_price": (
                        context["digital_twin"]
                        .get(
                            "estimated_selling_price"
                        )
                    ),
                    "estimated_profit": (
                        context["digital_twin"]
                        .get(
                            "estimated_profit"
                        )
                    ),
                },
                experimental_calculations={},
                provider_comparison={
                    "findings": list(
                        result.findings
                    ),
                    "conflicts": [
                        {
                            "topic": conflict.topic,
                            "description": (
                                conflict.description
                            ),
                            "sources": list(
                                conflict.sources
                            ),
                        }
                        for conflict in result.conflicts
                    ],
                    "missing_information": list(
                        result.missing_information
                    ),
                    "proposal_count": (
                        result.proposal_count
                    ),
                },
                recommendation=result.summary,
                risks=[
                    {
                        "proposal": (
                            proposal.title
                        ),
                        "risk_level": (
                            proposal.risk_level
                        ),
                        "requires_validation": (
                            proposal
                            .requires_validation
                        ),
                    }
                    for proposal in result.proposals
                ],
                confidence_percent=(
                    result
                    .overall_confidence_percent
                ),
                created_by=requested_by,
            )
        )

        experiment.local_analysis = result_data

        experiment.status = (
            Experiment.Status.PROPOSALS_READY
            if result.has_proposals
            else Experiment.Status.COMPLETED
        )

        experiment.analysis_completed_at = (
            timezone.now()
        )

        experiment.save(
            update_fields=[
                "local_analysis",
                "status",
                "analysis_completed_at",
                "updated_at",
            ]
        )

        ExperimentChatMessage.objects.create(
            experiment=experiment,
            role=(
                ExperimentChatMessage
                .Role.ASSISTANT
            ),
            provider=(
                ExperimentChatMessage
                .Provider.LOCAL_AI
            ),
            content=result.summary,
            created_by=None,
            metadata={
                "internal_analysis_id": (
                    internal_analysis.pk
                ),
                "model": result.model_name,
                "overall_confidence_percent": (
                    result
                    .overall_confidence_percent
                ),
                "proposal_count": (
                    result.proposal_count
                ),
                "structured_analysis": (
                    result_data
                ),
            },
        )

        return internal_analysis

    @staticmethod
    def _validate_experiment(
        experiment: Experiment,
    ) -> None:
        if not isinstance(
            experiment,
            Experiment,
        ):
            raise TypeError(
                "experiment must be an "
                "Experiment instance."
            )

        if experiment.pk is None:
            raise EngineeringAgentError(
                "The experiment must be saved "
                "before analysis."
            )

        if not experiment.can_request_analysis:
            raise EngineeringAgentError(
                "The experiment needs at least one "
                "engineer question and one external "
                "AI response before local analysis."
            )

        if not (
            ValidatedResearchPackage.objects.filter(
                research_request__experiment=(
                    experiment
                ),
                validation_status=(
                    ValidatedResearchPackage
                    .ValidationStatus.VALID
                ),
            ).exists()
        ):
            raise EngineeringAgentError(
                "The experiment has no valid external "
                "research package."
            )

    @staticmethod
    def _mark_analysis_started(
        experiment: Experiment,
    ) -> None:
        experiment.status = (
            Experiment.Status.ANALYZING
        )

        experiment.analysis_started_at = (
            timezone.now()
        )

        experiment.save(
            update_fields=[
                "status",
                "analysis_started_at",
                "updated_at",
            ]
        )

    @staticmethod
    def _mark_analysis_failed(
        *,
        experiment: Experiment,
        error: str | None,
    ) -> None:
        experiment.status = (
            Experiment.Status.FAILED
        )

        experiment.local_analysis = {
            "error": (
                error
                or "Unknown local analysis error."
            ),
        }

        experiment.analysis_completed_at = (
            timezone.now()
        )

        experiment.save(
            update_fields=[
                "status",
                "local_analysis",
                "analysis_completed_at",
                "updated_at",
            ]
        )

    @classmethod
    def _serialize_digital_twin(
        cls,
        twin: DigitalTwin,
    ) -> dict[str, Any]:
        return {
            "id": str(twin.pk),
            "part_number": twin.part_number,
            "name": twin.name,
            "description": twin.description,
            "material": (
                cls._serialize_material(
                    twin.material
                )
                if twin.material
                else None
            ),
            "technology": (
                cls._serialize_technology(
                    twin.technology
                )
                if twin.technology
                else None
            ),
            "volume_m3": cls._json_value(
                twin.volume_m3
            ),
            "entered_mass_kg": cls._json_value(
                twin.mass_kg
            ),
            "effective_mass_kg": cls._json_value(
                twin.effective_mass_kg
            ),
            "production_time_minutes": (
                cls._json_value(
                    twin.production_time_minutes
                )
            ),
            "labor_cost": cls._json_value(
                twin.labor_cost
            ),
            "energy_cost": cls._json_value(
                twin.energy_cost
            ),
            "defect_rate_percent": (
                cls._json_value(
                    twin.defect_rate_percent
                )
            ),
            "desired_profit_margin_percent": (
                cls._json_value(
                    twin
                    .desired_profit_margin_percent
                )
            ),
            "estimated_material_cost": (
                cls._json_value(
                    twin.estimated_material_cost
                )
            ),
            "estimated_machine_cost": (
                cls._json_value(
                    twin.estimated_machine_cost
                )
            ),
            "estimated_direct_cost": (
                cls._json_value(
                    twin.estimated_direct_cost
                )
            ),
            "estimated_defect_cost": (
                cls._json_value(
                    twin.estimated_defect_cost
                )
            ),
            "estimated_total_cost": (
                cls._json_value(
                    twin.estimated_total_cost
                )
            ),
            "estimated_selling_price": (
                cls._json_value(
                    twin.estimated_selling_price
                )
            ),
            "estimated_profit": cls._json_value(
                twin.estimated_profit
            ),
            "cad_file_available": bool(
                twin.cad_file
            ),
            "image_file_available": bool(
                twin.image_file
            ),
            "is_active": twin.is_active,
        }

    @classmethod
    def _serialize_experiment(
        cls,
        experiment: Experiment,
    ) -> dict[str, Any]:
        return {
            "id": str(experiment.pk),
            "name": experiment.name,
            "description": (
                experiment.description
            ),
            "objective": experiment.objective,
            "status": experiment.status,
            "base_snapshot": (
                experiment.base_snapshot
            ),
            "changed_parameters": (
                experiment.changed_parameters
            ),
            "experimental_values": (
                experiment.experimental_values
            ),
            "calculated_results": (
                experiment.calculated_results
            ),
            "created_at": (
                experiment.created_at.isoformat()
                if experiment.created_at
                else None
            ),
        }

    @staticmethod
    def _serialize_chat_history(
        experiment: Experiment,
    ) -> list[dict[str, Any]]:
        return [
            {
                "sequence": message.sequence,
                "role": message.role,
                "provider": message.provider,
                "content": message.content,
                "created_at": (
                    message.created_at.isoformat()
                    if message.created_at
                    else None
                ),
            }
            for message in (
                experiment.chat_messages
                .order_by("sequence")
            )
        ]

    @staticmethod
    def _serialize_external_research(
        experiment: Experiment,
    ) -> dict[str, Any]:
        packages = (
            ValidatedResearchPackage.objects
            .filter(
                research_request__experiment=(
                    experiment
                ),
                validation_status=(
                    ValidatedResearchPackage
                    .ValidationStatus.VALID
                ),
            )
            .select_related(
                "research_request"
            )
            .order_by(
                "research_request__created_at"
            )
        )

        return {
            "packages": [
                {
                    "research_request_id": (
                        package
                        .research_request_id
                    ),
                    "query": (
                        package
                        .research_request
                        .sanitized_query
                    ),
                    "validated_data": (
                        package.validated_data
                    ),
                    "validated_at": (
                        package
                        .validated_at
                        .isoformat()
                        if package.validated_at
                        else None
                    ),
                }
                for package in packages
            ]
        }

    @classmethod
    def _serialize_material_catalog(
        cls,
    ) -> list[dict[str, Any]]:
        return [
            cls._serialize_material(material)
            for material in (
                MaterialCatalog.objects.filter(
                    is_active=True
                ).order_by("name")
            )
        ]

    @classmethod
    def _serialize_technology_catalog(
        cls,
    ) -> list[dict[str, Any]]:
        return [
            cls._serialize_technology(
                technology
            )
            for technology in (
                TechnologyCatalog.objects.filter(
                    is_active=True
                ).order_by("name")
            )
        ]

    @classmethod
    def _serialize_previous_experiments(
        cls,
        experiment: Experiment,
    ) -> list[dict[str, Any]]:
        previous = (
            Experiment.objects.filter(
                digital_twin=(
                    experiment.digital_twin
                ),
            )
            .exclude(pk=experiment.pk)
            .exclude(local_analysis={})
            .order_by("-created_at")[:5]
        )

        return [
            {
                "id": str(item.pk),
                "name": item.name,
                "objective": item.objective,
                "status": item.status,
                "experimental_values": (
                    item.experimental_values
                ),
                "calculated_results": (
                    item.calculated_results
                ),
                "local_analysis": (
                    item.local_analysis
                ),
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at
                    else None
                ),
            }
            for item in previous
        ]

    @classmethod
    def _serialize_material(
        cls,
        material: MaterialCatalog,
    ) -> dict[str, Any]:
        return {
            "code": material.code,
            "name": material.name,
            "density_kg_m3": cls._json_value(
                material.density_kg_m3
            ),
            "price_per_kg": cls._json_value(
                material.price_per_kg
            ),
            "yield_strength_mpa": (
                cls._json_value(
                    material
                    .yield_strength_mpa
                )
            ),
            "description": (
                material.description
            ),
        }

    @classmethod
    def _serialize_technology(
        cls,
        technology: TechnologyCatalog,
    ) -> dict[str, Any]:
        return {
            "code": technology.code,
            "name": technology.name,
            "machine_hour_rate": (
                cls._json_value(
                    technology
                    .machine_hour_rate
                )
            ),
            "description": (
                technology.description
            ),
        }

    @staticmethod
    def _json_value(
        value: Any,
    ) -> Any:
        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, UUID):
            return str(value)

        return value
