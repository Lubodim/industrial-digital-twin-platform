from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_engine.experiment_research_service import (
    ExperimentResearchService,
)
from ai_engine.external_research_agent import (
    ExternalResearchAgent,
)
from ai_engine.models import (
    ExternalResearchRequest,
    ProviderResponse,
    ValidatedResearchPackage,
)
from ai_engine.orchestrator import OrchestrationResult
from ai_engine.providers.base import ProviderResult
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


class ExperimentResearchServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="research-engineer",
            password="test-password",
        )

        self.material = MaterialCatalog.objects.create(
            name="Aluminium 6082",
            code="AL6082-TEST",
            density_kg_m3="2710.000",
            price_per_kg="6.80",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="CNC Milling Test",
            code="CNC-TEST",
            machine_hour_rate="40.00",
        )

        self.twin = DigitalTwin.objects.create(
            name="Mounting Bracket",
            part_number="SERVICE-BRACKET-001",
            material=self.material,
            technology=self.technology,
            production_time_minutes="35.00",
            labor_cost="18.00",
            energy_cost="6.00",
            desired_profit_margin_percent="20.00",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.twin,
            name="Weight reduction",
            objective=(
                "Reduce mass while preserving sufficient "
                "mechanical strength."
            ),
            created_by=self.user,
        )

        self.temporary_directory = TemporaryDirectory()

        base_path = Path(self.temporary_directory.name)

        self.agent = ExternalResearchAgent(
            raw_research_directory=base_path / "raw",
            validated_research_directory=(
                base_path / "validated"
            ),
        )

        self.service = ExperimentResearchService(
            external_agent=self.agent,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def successful_result():
        structured_response = {
            "schema_version": "1.0",
            "summary": (
                "Aluminium 6082 may reduce mass, but the "
                "geometry requires engineering validation."
            ),
            "materials": {
                "recommended_material": "Aluminium 6082",
            },
            "requires_engineer_review": True,
        }

        provider_result = ProviderResult(
            provider="OPENAI",
            model="test-model",
            success=True,
            structured_response=structured_response,
            raw_response='{"summary": "test"}',
            response_time_ms=120,
            usage={
                "input_tokens": 10,
                "output_tokens": 20,
            },
            metadata={
                "model": "test-model",
            },
        )

        return OrchestrationResult(
            success=True,
            provider_name="OPENAI",
            provider_result=provider_result,
            error_message="",
            metadata={
                "pipeline_stage": "completed",
            },
        )

    def test_creates_question_and_answer_messages(self):
        with patch(
            "ai_engine.external_research_agent."
            "run_external_research",
            return_value=self.successful_result(),
        ):
            result = self.service.run_question(
                experiment=self.experiment,
                engineer_question=(
                    "Can the bracket mass be reduced?"
                ),
                requested_by=self.user,
                provider_names=["openai"],
            )

        self.assertTrue(result.success)

        messages = list(
            self.experiment.chat_messages.order_by(
                "sequence"
            )
        )

        self.assertEqual(len(messages), 2)

        self.assertEqual(
            messages[0].role,
            ExperimentChatMessage.Role.ENGINEER,
        )

        self.assertEqual(
            messages[1].role,
            ExperimentChatMessage.Role.ASSISTANT,
        )

        self.assertEqual(
            messages[1].provider,
            ExperimentChatMessage.Provider.OPENAI,
        )

    def test_creates_research_database_records(self):
        with patch(
            "ai_engine.external_research_agent."
            "run_external_research",
            return_value=self.successful_result(),
        ):
            result = self.service.run_question(
                experiment=self.experiment,
                engineer_question=(
                    "Suggest a lower-mass material."
                ),
                requested_by=self.user,
                provider_names=["openai"],
            )

        request = result.research_request

        self.assertEqual(
            request.status,
            ExternalResearchRequest.Status.COMPLETED,
        )

        self.assertEqual(
            ProviderResponse.objects.filter(
                research_request=request
            ).count(),
            1,
        )

        validated = ValidatedResearchPackage.objects.get(
            research_request=request
        )

        self.assertEqual(
            validated.validation_status,
            ValidatedResearchPackage
            .ValidationStatus.VALID,
        )

    def test_sanitized_package_excludes_confidential_costs(self):
        with patch(
            "ai_engine.external_research_agent."
            "run_external_research",
            return_value=self.successful_result(),
        ):
            result = self.service.run_question(
                experiment=self.experiment,
                engineer_question=(
                    "Could another material be suitable?"
                ),
                requested_by=self.user,
                provider_names=["openai"],
            )

        query = result.research_request.sanitized_query

        self.assertEqual(
            query["current_material"],
            "Aluminium 6082",
        )

        self.assertEqual(
            query["current_technology"],
            "CNC Milling Test",
        )

        self.assertNotIn("labor_cost", query)
        self.assertNotIn("energy_cost", query)
        self.assertNotIn("estimated_total_cost", query)
        self.assertNotIn(
            "desired_profit_margin_percent",
            query,
        )
        self.assertNotIn("cad_file", query)
        self.assertNotIn("part_number", query)

    def test_appends_multiple_questions_to_same_experiment(self):
        with patch(
            "ai_engine.external_research_agent."
            "run_external_research",
            return_value=self.successful_result(),
        ):
            self.service.run_question(
                experiment=self.experiment,
                engineer_question="Question one.",
                requested_by=self.user,
                provider_names=["openai"],
            )

            self.service.run_question(
                experiment=self.experiment,
                engineer_question="Question two.",
                requested_by=self.user,
                provider_names=["openai"],
            )

        self.assertEqual(
            self.experiment.chat_messages.count(),
            4,
        )

        self.assertEqual(
            self.experiment.research_requests.count(),
            2,
        )

        self.experiment.refresh_from_db()

        self.assertEqual(
            len(
                self.experiment.external_results.get(
                    "runs",
                    [],
                )
            ),
            2,
        )
