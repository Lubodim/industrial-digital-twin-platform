from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.orchestrator import (
    ExternalResearchOrchestrator,
    run_external_research,
)
from ai_engine.providers.base import ProviderResult
from ai_engine.research_package import build_research_package


class DummyProvider:
    provider_name = "TEST"

    def get_provider_info(self):
        return {
            "provider": "TEST",
            "model": "test-model",
        }

    def send_messages(self, messages):
        return ProviderResult(
            provider="TEST",
            model="test-model",
            success=True,
            raw_response='{"summary": "Test result"}',
            structured_response={
                "summary": "Test result",
            },
            response_time_ms=10,
        )


class ExternalResearchOrchestratorTests(SimpleTestCase):
    def setUp(self):
        self.package = build_research_package(
            engineer_question=(
                "Предложи начин за намаляване "
                "на производственото време."
            ),
            generic_product_type="Machined bracket",
            current_material="Aluminium 6061",
            current_technology="CNC milling",
        )

    @patch(
        "ai_engine.orchestrator.ProviderFactory.create"
    )
    def test_runs_complete_pipeline(self, mock_create):
        mock_create.return_value = DummyProvider()

        orchestrator = ExternalResearchOrchestrator()

        result = orchestrator.run(
            research_package=self.package,
            provider_name="openai",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider_name, "TEST")
        self.assertEqual(
            result.structured_response["summary"],
            "Test result",
        )
        self.assertEqual(
            result.metadata["pipeline_stage"],
            "completed",
        )

    @patch(
        "ai_engine.orchestrator.ProviderFactory.create"
    )
    def test_convenience_function_runs_pipeline(
        self,
        mock_create,
    ):
        mock_create.return_value = DummyProvider()

        result = run_external_research(
            research_package=self.package,
            provider_name="openai",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider_name, "TEST")

    def test_rejects_invalid_research_package(self):
        orchestrator = ExternalResearchOrchestrator()

        with self.assertRaises(TypeError):
            orchestrator.run(
                research_package={},
                provider_name="openai",
            )

    def test_rejects_empty_provider_name(self):
        orchestrator = ExternalResearchOrchestrator()

        with self.assertRaises(ValueError):
            orchestrator.run(
                research_package=self.package,
                provider_name="   ",
            )

    def test_rejects_non_dictionary_overrides(self):
        orchestrator = ExternalResearchOrchestrator()

        with self.assertRaises(TypeError):
            orchestrator.run(
                research_package=self.package,
                provider_name="openai",
                provider_overrides="invalid",
            )

    def test_returns_configuration_error(self):
        orchestrator = ExternalResearchOrchestrator()

        result = orchestrator.run(
            research_package=self.package,
            provider_name="gemini",
        )

        self.assertFalse(result.success)
        self.assertTrue(result.error_message)