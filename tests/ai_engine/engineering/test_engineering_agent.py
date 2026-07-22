from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ai_engine.local_ai.engineering_agent import (
    EngineeringAgent,
    EngineeringAgentError,
)
from ai_engine.local_ai.ollama_client import (
    OllamaResponse,
)
from ai_engine.models import (
    ExternalResearchRequest,
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


User = get_user_model()


class EngineeringAgentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="local-engineer",
            password="test-password",
        )

        self.material = (
            MaterialCatalog.objects.create(
                name="Test Steel",
                code="TEST-S235",
                density_kg_m3="7850.000",
                price_per_kg="2.50",
                yield_strength_mpa="235.00",
            )
        )

        self.technology = (
            TechnologyCatalog.objects.create(
                name="Test Laser Cutting",
                code="TEST-LASER",
                machine_hour_rate="45.00",
            )
        )

        self.twin = DigitalTwin.objects.create(
            name="Test Flange",
            part_number="LOCAL-AI-TEST-001",
            material=self.material,
            technology=self.technology,
            volume_m3="0.00010000",
            production_time_minutes="15.00",
            labor_cost="5.00",
            energy_cost="2.00",
            defect_rate_percent="2.00",
            desired_profit_margin_percent="20.00",
            created_by=self.user,
        )

        self.experiment = (
            Experiment.objects.create(
                digital_twin=self.twin,
                name="Reduce manufacturing cost",
                objective=(
                    "Reduce cost without reducing "
                    "functional reliability."
                ),
                created_by=self.user,
            )
        )

        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=(
                ExperimentChatMessage
                .Role.ENGINEER
            ),
            provider=(
                ExperimentChatMessage
                .Provider.NONE
            ),
            content=(
                "Can the manufacturing cost "
                "be reduced?"
            ),
            created_by=self.user,
        )

        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=(
                ExperimentChatMessage
                .Role.ASSISTANT
            ),
            provider=(
                ExperimentChatMessage
                .Provider.OPENAI
            ),
            content=(
                "Review cutting parameters and "
                "material utilization."
            ),
        )

        self.research_request = (
            ExternalResearchRequest.objects.create(
                experiment=self.experiment,
                sanitized_query={
                    "objective": (
                        "Reduce manufacturing cost"
                    )
                },
                status=(
                    ExternalResearchRequest
                    .Status.COMPLETED
                ),
                requested_by=self.user,
                started_at=timezone.now(),
                completed_at=timezone.now(),
            )
        )

        self.validated_package = (
            ValidatedResearchPackage.objects.create(
                research_request=(
                    self.research_request
                ),
                validated_data={
                    "providers": {
                        "OPENAI": {
                            "summary": (
                                "Optimize nesting and "
                                "cutting parameters."
                            )
                        }
                    }
                },
                validation_status=(
                    ValidatedResearchPackage
                    .ValidationStatus.VALID
                ),
                validated_at=timezone.now(),
            )
        )

        self.client = Mock()

        self.client.ask.return_value = (
            OllamaResponse(
                success=True,
                model="qwen3.5:9b",
                response="{}",
                raw_response={},
                response_time_ms=1250.0,
                load_time_ms=100.0,
                prompt_token_count=500,
                output_token_count=150,
                thinking="",
                structured_response={
                    "summary": (
                        "Optimize laser-cutting "
                        "parameters and nesting."
                    ),
                    "findings": [
                        (
                            "Material utilization may "
                            "affect total cost."
                        )
                    ],
                    "conflicts": [],
                    "missing_information": [
                        (
                            "Actual sheet nesting "
                            "efficiency is unknown."
                        )
                    ],
                    "proposals": [
                        {
                            "category": "PRODUCTION",
                            "title": (
                                "Optimize cutting layout"
                            ),
                            "description": (
                                "Review nesting and "
                                "cutting sequence."
                            ),
                            "parameter_name": (
                                "nesting_efficiency"
                            ),
                            "current_value": None,
                            "proposed_value": None,
                            "unit": "%",
                            "reason": (
                                "Reduced material waste "
                                "may lower unit cost."
                            ),
                            "expected_benefit": (
                                "Lower material usage."
                            ),
                            "risk_level": "LOW",
                            "confidence_percent": 75,
                            "requires_validation": True,
                            "validation_requirements": [
                                (
                                    "Compare material "
                                    "utilization before "
                                    "and after nesting."
                                )
                            ],
                        }
                    ],
                    "overall_confidence_percent": 72,
                    "requires_engineer_review": True,
                },
                error=None,
            )
        )

        self.agent = EngineeringAgent(
            client=self.client
        )

    def test_build_context_contains_twin_data(self):
        context = self.agent.build_context(
            experiment=self.experiment
        )

        self.assertEqual(
            context["digital_twin"][
                "part_number"
            ],
            "LOCAL-AI-TEST-001",
        )

        self.assertEqual(
            context["digital_twin"][
                "material"
            ]["code"],
            "TEST-S235",
        )

        self.assertEqual(
            len(context["chat_history"]),
            2,
        )

        self.assertEqual(
            len(
                context["external_research"][
                    "packages"
                ]
            ),
            1,
        )

    def test_analyze_returns_structured_result(self):
        result = self.agent.analyze(
            experiment=self.experiment,
            requested_by=self.user,
            persist=False,
        )

        self.assertEqual(
            result.model_name,
            "qwen3.5:9b",
        )

        self.assertEqual(
            result.proposal_count,
            1,
        )

        self.assertEqual(
            result.proposals[0].category,
            "PRODUCTION",
        )

        self.client.ask.assert_called_once()

    def test_analyze_persists_internal_analysis(self):
        result = self.agent.analyze(
            experiment=self.experiment,
            requested_by=self.user,
            persist=True,
        )

        self.assertEqual(
            InternalAnalysis.objects.count(),
            1,
        )

        self.experiment.refresh_from_db()

        self.assertEqual(
            self.experiment.status,
            Experiment.Status.PROPOSALS_READY,
        )

        self.assertEqual(
            self.experiment.local_analysis[
                "summary"
            ],
            result.summary,
        )

        local_messages = (
            self.experiment.chat_messages.filter(
                provider=(
                    ExperimentChatMessage
                    .Provider.LOCAL_AI
                )
            )
        )

        self.assertEqual(
            local_messages.count(),
            1,
        )

    def test_rejects_experiment_without_research(
        self,
    ):
        self.validated_package.delete()

        with self.assertRaises(
            EngineeringAgentError
        ):
            self.agent.analyze(
                experiment=self.experiment,
                requested_by=self.user,
            )

    def test_failed_client_marks_experiment_failed(
        self,
    ):
        self.client.ask.return_value = (
            OllamaResponse(
                success=False,
                model="qwen3.5:9b",
                response="",
                raw_response={},
                response_time_ms=None,
                load_time_ms=None,
                prompt_token_count=None,
                output_token_count=None,
                thinking="",
                structured_response={},
                error="Local model unavailable.",
            )
        )

        with self.assertRaises(
            EngineeringAgentError
        ):
            self.agent.analyze(
                experiment=self.experiment,
                requested_by=self.user,
            )

        self.experiment.refresh_from_db()

        self.assertEqual(
            self.experiment.status,
            Experiment.Status.FAILED,
        )
