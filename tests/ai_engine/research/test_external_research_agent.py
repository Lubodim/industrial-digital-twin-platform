from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.external_research_agent import (
    ExternalResearchAgent,
)
from ai_engine.orchestrator import OrchestrationResult
from ai_engine.providers.base import ProviderResult
from ai_engine.research_package import (
    build_research_package,
)


def build_successful_orchestration_result(
    provider_name: str = "OPENAI",
) -> OrchestrationResult:
    provider_result = ProviderResult(
        provider=provider_name,
        model="test-model",
        success=True,
        raw_response='{"summary": "Successful research"}',
        structured_response={
            "schema_version": "1.0",
            "summary": "Successful research",
            "requires_engineer_review": True,
        },
        response_time_ms=10,
    )

    return OrchestrationResult(
        success=True,
        provider_name=provider_name,
        provider_result=provider_result,
        metadata={
            "pipeline_stage": "completed",
        },
    )


def build_failed_orchestration_result(
    provider_name: str = "GEMINI",
) -> OrchestrationResult:
    return OrchestrationResult(
        success=False,
        provider_name=provider_name,
        error_message="Provider failed.",
        metadata={
            "pipeline_stage": "provider_failed",
        },
    )


class ExternalResearchAgentTests(SimpleTestCase):
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
        "ai_engine.external_research_agent."
        "run_external_research"
    )
    def test_runs_provider_and_saves_files(
        self,
        mock_run_external_research,
    ):
        mock_run_external_research.return_value = (
            build_successful_orchestration_result()
        )

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            agent = ExternalResearchAgent(
                raw_research_directory=root / "raw",
                validated_research_directory=(
                    root / "validated"
                ),
            )

            result = agent.run(
                research_package=self.package,
                provider_names=["openai"],
            )

            self.assertTrue(result.success)
            self.assertTrue(
                result.all_providers_succeeded
            )
            self.assertEqual(
                result.successful_providers,
                ["OPENAI"],
            )
            self.assertEqual(
                result.failed_providers,
                [],
            )

            record = result.provider_records[0]

            self.assertIsNotNone(record.raw_file_path)
            self.assertIsNotNone(
                record.validated_file_path
            )

            self.assertTrue(
                Path(record.raw_file_path).exists()
            )
            self.assertTrue(
                Path(record.validated_file_path).exists()
            )

    @patch(
        "ai_engine.external_research_agent."
        "run_external_research"
    )
    def test_continues_when_one_provider_fails(
        self,
        mock_run_external_research,
    ):
        mock_run_external_research.side_effect = [
            build_successful_orchestration_result(
                "OPENAI"
            ),
            build_failed_orchestration_result(
                "GEMINI"
            ),
        ]

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            agent = ExternalResearchAgent(
                raw_research_directory=root / "raw",
                validated_research_directory=(
                    root / "validated"
                ),
            )

            result = agent.run(
                research_package=self.package,
                provider_names=[
                    "openai",
                    "gemini",
                ],
            )

            self.assertTrue(result.success)
            self.assertFalse(
                result.all_providers_succeeded
            )
            self.assertEqual(
                result.successful_providers,
                ["OPENAI"],
            )
            self.assertEqual(
                result.failed_providers,
                ["GEMINI"],
            )
            self.assertEqual(
                len(result.provider_records),
                2,
            )

    def test_removes_duplicate_provider_names(self):
        normalized = (
            ExternalResearchAgent
            ._normalize_provider_names(
                [
                    "openai",
                    "OPENAI",
                    " openai ",
                    "gemini",
                ]
            )
        )

        self.assertEqual(
            normalized,
            ["openai", "gemini"],
        )

    def test_rejects_invalid_research_package(self):
        agent = ExternalResearchAgent()

        with self.assertRaises(TypeError):
            agent.run(
                research_package={},
                provider_names=["openai"],
            )

    def test_rejects_empty_provider_list(self):
        agent = ExternalResearchAgent()

        with self.assertRaises(ValueError):
            agent.run(
                research_package=self.package,
                provider_names=[],
            )

    def test_rejects_non_list_provider_names(self):
        agent = ExternalResearchAgent()

        with self.assertRaises(TypeError):
            agent.run(
                research_package=self.package,
                provider_names="openai",
            )