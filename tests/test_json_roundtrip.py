from __future__ import annotations

import json
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
from experiments.models import Experiment


User = get_user_model()


class JSONRoundTripTests(TestCase):
    """
    Integration tests for the complete external-research JSON pipeline.

    The tests verify the flow:

    ProviderResult
        -> OrchestrationResult
        -> ExternalResearchAgent
        -> raw JSON file
        -> validated JSON file
        -> database records
        -> JSON data loaded again
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="json-roundtrip-engineer",
            password="test-password",
        )

        self.material = MaterialCatalog.objects.create(
            name="42CrMo4",
            code="42CRMO4-JSON-TEST",
            density_kg_m3="7850.000",
            price_per_kg="4.50",
        )

        self.technology = TechnologyCatalog.objects.create(
            name="CNC Turning",
            code="CNC-TURN-JSON-TEST",
            machine_hour_rate="55.00",
        )

        self.digital_twin = DigitalTwin.objects.create(
            name="Редукторен вал",
            part_number="SHAFT-JSON-001",
            material=self.material,
            technology=self.technology,
            production_time_minutes="42.00",
            labor_cost="20.00",
            energy_cost="8.00",
            desired_profit_margin_percent="20.00",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.digital_twin,
            name="Оптимизация на материала",
            objective=(
                "Намаляване на производствената цена при "
                "запазване на необходимата якост."
            ),
            created_by=self.user,
        )

        self.temporary_directory = TemporaryDirectory()

        root_directory = Path(
            self.temporary_directory.name
        )

        self.raw_directory = (
            root_directory / "raw_research"
        )

        self.validated_directory = (
            root_directory / "validated_research"
        )

        self.agent = ExternalResearchAgent(
            raw_research_directory=self.raw_directory,
            validated_research_directory=(
                self.validated_directory
            ),
        )

        self.service = ExperimentResearchService(
            external_agent=self.agent,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def build_structured_response() -> dict:
        """
        Return deterministic engineering data for the test.
        """

        return {
            "schema_version": "1.0",
            "summary": (
                "Материалът C45 може да намали цената, "
                "но е необходима инженерна проверка."
            ),
            "materials": {
                "recommended_material": "C45",
                "alternative_materials": [
                    "42CrMo4",
                    "34CrNiMo6",
                ],
                "comparison_notes": (
                    "C45 е по-евтин, но има по-ниска "
                    "якост след стандартна обработка."
                ),
            },
            "manufacturing": {
                "recommended_process": (
                    "CNC turning and heat treatment"
                ),
                "estimated_cycle_time_change_percent": -5,
            },
            "costs": {
                "currency": "EUR",
                "estimated_material_cost_change_percent": -12,
                "estimated_production_cost_change_percent": -7,
                "estimated_total_cost_change_percent": -9,
            },
            "quality": {
                "expected_quality_effect": (
                    "requires_validation"
                ),
                "quality_risks": [
                    "Недостатъчна твърдост",
                    "Повишено износване",
                ],
            },
            "recommendation": {
                "summary": (
                    "Да се направят механични изпитвания "
                    "преди одобряване на промяната."
                ),
                "required_validation_steps": [
                    "Изпитване на твърдост",
                    "Изпитване на опън",
                    "Проверка на износването",
                ],
            },
            "requires_engineer_review": True,
        }

    @classmethod
    def build_successful_orchestration_result(
        cls,
    ) -> OrchestrationResult:
        """
        Build a successful result matching the real project classes.
        """

        structured_response = (
            cls.build_structured_response()
        )

        raw_response = json.dumps(
            structured_response,
            ensure_ascii=False,
        )

        provider_result = ProviderResult(
            provider="OPENAI",
            model="test-engineering-model",
            success=True,
            raw_response=raw_response,
            structured_response=structured_response,
            response_time_ms=125,
            usage={
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
            },
            metadata={
                "finish_reason": "stop",
                "test_run": True,
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

    @patch(
        "ai_engine.external_research_agent."
        "run_external_research"
    )
    def test_complete_json_disk_and_database_roundtrip(
        self,
        mock_run_external_research,
    ):
        """
        Verify the complete disk and database JSON lifecycle.
        """

        orchestration_result = (
            self.build_successful_orchestration_result()
        )

        expected_response = (
            orchestration_result.structured_response
        )

        mock_run_external_research.return_value = (
            orchestration_result
        )

        result = self.service.run_question(
            experiment=self.experiment,
            engineer_question=(
                "Може ли 42CrMo4 да бъде заменен с C45?"
            ),
            requested_by=self.user,
            provider_names=["openai"],
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.agent_result.successful_providers,
            ["OPENAI"],
        )

        self.assertEqual(
            result.agent_result.failed_providers,
            [],
        )

        self.assertEqual(
            len(result.agent_result.provider_records),
            1,
        )

        record = (
            result.agent_result.provider_records[0]
        )

        self.assertEqual(
            record.provider_name,
            "OPENAI",
        )

        self.assertTrue(record.success)

        self.assertIsNotNone(
            record.raw_file_path
        )

        self.assertIsNotNone(
            record.validated_file_path
        )

        raw_file = Path(record.raw_file_path)

        validated_file = Path(
            record.validated_file_path
        )

        self.assertTrue(raw_file.exists())
        self.assertTrue(validated_file.exists())

        self.assertEqual(
            raw_file.suffix,
            ".json",
        )

        self.assertEqual(
            validated_file.suffix,
            ".json",
        )

        raw_payload = json.loads(
            raw_file.read_text(
                encoding="utf-8"
            )
        )

        validated_payload = json.loads(
            validated_file.read_text(
                encoding="utf-8"
            )
        )

        # Raw file assertions.
        self.assertEqual(
            raw_payload["run_id"],
            result.agent_result.run_id,
        )

        self.assertEqual(
            raw_payload["provider"],
            "openai",
        )

        self.assertTrue(
            raw_payload["success"]
        )

        self.assertEqual(
            raw_payload["response_time_ms"],
            125,
        )

        self.assertEqual(
            raw_payload["usage"]["total_tokens"],
            300,
        )

        self.assertEqual(
            raw_payload["metadata"]["finish_reason"],
            "stop",
        )

        decoded_raw_response = json.loads(
            raw_payload["raw_response"]
        )

        self.assertEqual(
            decoded_raw_response,
            expected_response,
        )

        self.assertEqual(
            decoded_raw_response["summary"],
            (
                "Материалът C45 може да намали цената, "
                "но е необходима инженерна проверка."
            ),
        )

        # Validated file assertions.
        self.assertEqual(
            validated_payload["run_id"],
            result.agent_result.run_id,
        )

        self.assertEqual(
            validated_payload["provider"],
            "openai",
        )

        self.assertIn(
            "validated_at",
            validated_payload,
        )

        self.assertEqual(
            validated_payload["research_result"],
            expected_response,
        )

        self.assertEqual(
            validated_payload[
                "research_result"
            ]["materials"][
                "recommended_material"
            ],
            "C45",
        )

        self.assertEqual(
            validated_payload[
                "research_result"
            ]["quality"]["quality_risks"],
            [
                "Недостатъчна твърдост",
                "Повишено износване",
            ],
        )

        # ExternalResearchRequest database record.
        research_request = (
            ExternalResearchRequest.objects.get(
                pk=result.research_request.pk
            )
        )

        self.assertEqual(
            research_request.status,
            ExternalResearchRequest
            .Status.COMPLETED,
        )

        self.assertEqual(
            research_request.requested_by,
            self.user,
        )

        self.assertEqual(
            research_request.experiment,
            self.experiment,
        )

        # ProviderResponse database record.
        provider_response = (
            ProviderResponse.objects.get(
                research_request=(
                    research_request
                ),
                provider=(
                    ProviderResponse.Provider.OPENAI
                ),
            )
        )

        self.assertEqual(
            provider_response.status,
            ProviderResponse.Status.SUCCESS,
        )

        self.assertEqual(
            provider_response.model_name,
            "test-engineering-model",
        )

        self.assertEqual(
            provider_response.response_time_ms,
            125,
        )

        self.assertEqual(
            provider_response.structured_response,
            expected_response,
        )

        self.assertEqual(
            json.loads(
                provider_response.raw_response
            ),
            expected_response,
        )

        # ValidatedResearchPackage database record.
        validated_package = (
            ValidatedResearchPackage.objects.get(
                research_request=(
                    research_request
                )
            )
        )

        self.assertEqual(
            validated_package.validation_status,
            (
                ValidatedResearchPackage
                .ValidationStatus.VALID
            ),
        )

        validated_data = (
            validated_package.validated_data
        )

        self.assertEqual(
            validated_data["run_id"],
            result.agent_result.run_id,
        )

        self.assertIn(
            "OPENAI",
            validated_data["providers"],
        )

        openai_validated_result = (
            validated_data["providers"]["OPENAI"]
        )

        self.assertEqual(
            openai_validated_result[
                "research_result"
            ],
            expected_response,
        )

        self.assertEqual(
            openai_validated_result[
                "raw_file_path"
            ],
            str(raw_file),
        )

        self.assertEqual(
            openai_validated_result[
                "validated_file_path"
            ],
            str(validated_file),
        )

        self.assertEqual(
            validated_package.validation_errors,
            [],
        )

        self.assertIsNotNone(
            validated_package.validated_at
        )

        # Reload from database to prove persistence.
        provider_response.refresh_from_db()
        validated_package.refresh_from_db()
        self.experiment.refresh_from_db()

        self.assertEqual(
            provider_response
            .structured_response[
                "recommendation"
            ]["required_validation_steps"],
            [
                "Изпитване на твърдост",
                "Изпитване на опън",
                "Проверка на износването",
            ],
        )

        self.assertEqual(
            validated_package
            .validated_data[
                "providers"
            ]["OPENAI"][
                "research_result"
            ]["costs"][
                "estimated_total_cost_change_percent"
            ],
            -9,
        )

        # The service must also append the result
        # to Experiment.external_results.
        experiment_runs = (
            self.experiment.external_results.get(
                "runs",
                [],
            )
        )

        self.assertEqual(
            len(experiment_runs),
            1,
        )

        self.assertEqual(
            experiment_runs[0]["run_id"],
            result.agent_result.run_id,
        )

        self.assertIn(
            "OPENAI",
            experiment_runs[0]["providers"],
        )

        # Atomic writer must not leave temporary files.
        raw_temp_files = list(
            self.raw_directory.glob("*.tmp")
        )

        validated_temp_files = list(
            self.validated_directory.glob(
                "*.tmp"
            )
        )

        self.assertEqual(
            raw_temp_files,
            [],
        )

        self.assertEqual(
            validated_temp_files,
            [],
        )

    @patch(
        "ai_engine.external_research_agent."
        "run_external_research"
    )
    def test_json_files_can_be_loaded_after_agent_finishes(
        self,
        mock_run_external_research,
    ):
        """
        Verify that generated JSON files remain readable.
        """

        mock_run_external_research.return_value = (
            self.build_successful_orchestration_result()
        )

        result = self.service.run_question(
            experiment=self.experiment,
            engineer_question=(
                "Предложи оптимизация на материала."
            ),
            requested_by=self.user,
            provider_names=["openai"],
        )

        record = (
            result.agent_result.provider_records[0]
        )

        raw_file = Path(record.raw_file_path)

        validated_file = Path(
            record.validated_file_path
        )

        with raw_file.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            raw_payload = json.load(file)

        with validated_file.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            validated_payload = json.load(file)

        self.assertIsInstance(
            raw_payload,
            dict,
        )

        self.assertIsInstance(
            validated_payload,
            dict,
        )

        self.assertIn(
            "raw_response",
            raw_payload,
        )

        self.assertIn(
            "research_result",
            validated_payload,
        )

        self.assertEqual(
            validated_payload[
                "research_result"
            ]["schema_version"],
            "1.0",
        )

        self.assertEqual(
            validated_payload[
                "research_result"
            ]["materials"][
                "recommended_material"
            ],
            "C45",
        )

    def test_atomic_json_writer_preserves_unicode_and_types(
        self,
    ):
        """
        Verify direct serialization of Unicode and JSON types.
        """

        target_file = (
            self.raw_directory
            / "roundtrip_test.json"
        )

        source_data = {
            "text": (
                "Инженерен анализ "
                "на цифров двойник"
            ),
            "integer": 42,
            "decimal_as_float": 12.5,
            "boolean": True,
            "empty_value": None,
            "list": [
                "стомана",
                "алуминий",
                "полимер",
            ],
            "nested": {
                "material": "42CrMo4",
                "risk_percent": 17.5,
            },
        }

        ExternalResearchAgent._write_json_file(
            file_path=target_file,
            data=source_data,
        )

        loaded_data = json.loads(
            target_file.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            loaded_data,
            source_data,
        )

        self.assertEqual(
            loaded_data["text"],
            (
                "Инженерен анализ "
                "на цифров двойник"
            ),
        )

        self.assertIsInstance(
            loaded_data["integer"],
            int,
        )

        self.assertIsInstance(
            loaded_data["decimal_as_float"],
            float,
        )

        self.assertIsInstance(
            loaded_data["boolean"],
            bool,
        )

        self.assertIsNone(
            loaded_data["empty_value"]
        )

        temporary_files = list(
            self.raw_directory.glob("*.tmp")
        )

        self.assertEqual(
            temporary_files,
            [],
        )

    @patch(
    "ai_engine.external_research_agent."
    "run_external_research"
    )
    def test_all_research_providers_are_saved_independently(
        self,
        mock_run_external_research,
    ):
        """
        Verify that OpenAI, Gemini, Claude and Grok use the same
        JSON and database persistence pipeline.
        """

        provider_models = {
            "OPENAI": "gpt-test-model",
            "GEMINI": "gemini-test-model",
            "CLAUDE": "claude-test-model",
            "GROK": "grok-test-model",
        }

        provider_recommendations = {
            "OPENAI": "C45",
            "GEMINI": "42CrMo4",
            "CLAUDE": "34CrNiMo6",
            "GROK": "C45E",
        }

        def build_result(
            research_package,
            provider_name,
            **kwargs,
        ):
            normalized_name = provider_name.strip().upper()

            structured_response = (
                self.build_structured_response()
            )

            structured_response = json.loads(
                json.dumps(
                    structured_response,
                    ensure_ascii=False,
                )
            )

            structured_response[
                "materials"
            ]["recommended_material"] = (
                provider_recommendations[
                    normalized_name
                ]
            )

            structured_response["provider_test"] = {
                "provider": normalized_name,
                "model": provider_models[
                    normalized_name
                ],
            }

            raw_response = json.dumps(
                structured_response,
                ensure_ascii=False,
            )

            provider_result = ProviderResult(
                provider=normalized_name,
                model=provider_models[
                    normalized_name
                ],
                success=True,
                raw_response=raw_response,
                structured_response=(
                    structured_response
                ),
                response_time_ms=100,
                usage={
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30,
                },
                metadata={
                    "finish_reason": "stop",
                    "test_provider": (
                        normalized_name
                    ),
                },
            )

            return OrchestrationResult(
                success=True,
                provider_name=normalized_name,
                provider_result=provider_result,
                error_message="",
                metadata={
                    "pipeline_stage": "completed",
                },
            )

        mock_run_external_research.side_effect = (
            build_result
        )

        result = self.service.run_question(
            experiment=self.experiment,
            engineer_question=(
                "Сравни възможни материали чрез "
                "всички външни AI доставчици."
            ),
            requested_by=self.user,
            provider_names=[
                "openai",
                "gemini",
                "claude",
                "grok",
            ],
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.agent_result.successful_providers,
            [
                "OPENAI",
                "GEMINI",
                "CLAUDE",
                "GROK",
            ],
        )

        self.assertEqual(
            result.agent_result.failed_providers,
            [],
        )

        self.assertEqual(
            len(
                result.agent_result.provider_records
            ),
            4,
        )

        records_by_provider = {
            record.provider_name: record
            for record
            in result.agent_result.provider_records
        }

        self.assertEqual(
            set(records_by_provider),
            {
                "OPENAI",
                "GEMINI",
                "CLAUDE",
                "GROK",
            },
        )

        for provider_name in (
            "OPENAI",
            "GEMINI",
            "CLAUDE",
            "GROK",
        ):
            record = records_by_provider[
                provider_name
            ]

            self.assertTrue(record.success)

            raw_file = Path(
                record.raw_file_path
            )

            validated_file = Path(
                record.validated_file_path
            )

            self.assertTrue(raw_file.exists())
            self.assertTrue(
                validated_file.exists()
            )

            raw_payload = json.loads(
                raw_file.read_text(
                    encoding="utf-8"
                )
            )

            validated_payload = json.loads(
                validated_file.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                raw_payload["provider"],
                provider_name.lower(),
            )

            self.assertEqual(
                validated_payload["provider"],
                provider_name.lower(),
            )

            self.assertEqual(
                validated_payload[
                    "research_result"
                ]["provider_test"]["provider"],
                provider_name,
            )

            self.assertEqual(
                validated_payload[
                    "research_result"
                ]["materials"][
                    "recommended_material"
                ],
                provider_recommendations[
                    provider_name
                ],
            )

        research_request = (
            ExternalResearchRequest.objects.get(
                pk=result.research_request.pk
            )
        )

        provider_responses = (
            ProviderResponse.objects.filter(
                research_request=(
                    research_request
                )
            )
        )

        self.assertEqual(
            provider_responses.count(),
            4,
        )

        responses_by_provider = {
            response.provider: response
            for response in provider_responses
        }

        expected_database_providers = {
            ProviderResponse.Provider.OPENAI,
            ProviderResponse.Provider.GEMINI,
            ProviderResponse.Provider.ANTHROPIC,
            ProviderResponse.Provider.GROK,
        }

        self.assertEqual(
            set(responses_by_provider),
            expected_database_providers,
        )
        
        database_provider_mapping = {
            "OPENAI": ProviderResponse.Provider.OPENAI,
            "GEMINI": ProviderResponse.Provider.GEMINI,
            "CLAUDE": ProviderResponse.Provider.ANTHROPIC,
            "GROK": ProviderResponse.Provider.GROK,
        }

        for provider_name in ("OPENAI","GEMINI","CLAUDE","GROK",):
            
            database_provider = database_provider_mapping[provider_name]

            provider_response = (responses_by_provider[database_provider])

            self.assertEqual(provider_response.status,ProviderResponse.Status.SUCCESS,)

            self.assertEqual(
                provider_response.model_name,
                provider_models[
                    provider_name
                ],
            )

            self.assertEqual(
                provider_response
                .structured_response[
                    "provider_test"
                ]["provider"],
                provider_name,
            )

            self.assertEqual(
                provider_response
                .structured_response[
                    "materials"
                ]["recommended_material"],
                provider_recommendations[
                    provider_name
                ],
            )

        validated_package = (
            ValidatedResearchPackage.objects.get(
                research_request=(
                    research_request
                )
            )
        )

        validated_providers = (
            validated_package
            .validated_data["providers"]
        )

        self.assertEqual(
            set(validated_providers),
            {
                "OPENAI",
                "GEMINI",
                "CLAUDE",
                "GROK",
            },
        )

        for provider_name in (
            "OPENAI",
            "GEMINI",
            "CLAUDE",
            "GROK",
        ):
            provider_data = (
                validated_providers[
                    provider_name
                ]
            )

            self.assertEqual(
                provider_data[
                    "research_result"
                ]["provider_test"]["provider"],
                provider_name,
            )

            self.assertTrue(
                Path(
                    provider_data[
                        "raw_file_path"
                    ]
                ).exists()
            )

            self.assertTrue(
                Path(
                    provider_data[
                        "validated_file_path"
                    ]
                ).exists()
            )

        self.experiment.refresh_from_db()

        experiment_runs = (
            self.experiment.external_results.get(
                "runs",
                [],
            )
        )

        self.assertEqual(
            len(experiment_runs),
            1,
        )

        experiment_run = (
            experiment_runs[0]
        )

        self.assertEqual(
            experiment_run[
                "successful_providers"
            ],
            [
                "OPENAI",
                "GEMINI",
                "CLAUDE",
                "GROK",
            ],
        )

        self.assertEqual(
            set(
                experiment_run[
                    "providers"
                ]
            ),
            {
                "OPENAI",
                "GEMINI",
                "CLAUDE",
                "GROK",
            },
        )

        raw_json_files = list(
            self.raw_directory.glob(
                "*.json"
            )
        )

        validated_json_files = list(
            self.validated_directory.glob(
                "*.json"
            )
        )

        self.assertEqual(
            len(raw_json_files),
            4,
        )

        self.assertEqual(
            len(validated_json_files),
            4,
        )

        self.assertEqual(
            list(
                self.raw_directory.glob(
                    "*.tmp"
                )
            ),
            [],
        )

        self.assertEqual(
            list(
                self.validated_directory.glob(
                    "*.tmp"
                )
            ),
            [],
        )