from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai_engine.providers.gemini import GeminiProvider


class GeminiProviderTests(SimpleTestCase):
    def setUp(self):
        self.client_patcher = patch(
            "ai_engine.providers.gemini.genai.Client"
        )
        self.mock_client_class = self.client_patcher.start()

        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client

        self.provider = GeminiProvider(
            api_key="test-gemini-key",
            model="gemini-test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
            temperature=0.2,
        )

    def tearDown(self):
        self.client_patcher.stop()

    def test_provider_configuration(self):
        self.assertEqual(
            self.provider.provider_name,
            "GEMINI",
        )
        self.assertEqual(
            self.provider.model,
            "gemini-test-model",
        )
        self.assertEqual(
            self.provider.timeout_seconds,
            30,
        )
        self.assertEqual(
            self.provider.max_output_tokens,
            1000,
        )
        self.assertEqual(
            self.provider.temperature,
            0.2,
        )

    def test_provider_info_does_not_expose_api_key(self):
        info = self.provider.get_provider_info()

        self.assertEqual(
            info["provider"],
            "GEMINI",
        )
        self.assertEqual(
            info["model"],
            "gemini-test-model",
        )
        self.assertEqual(
            info["api"],
            "generateContent",
        )
        self.assertEqual(
            info["response_format"],
            "application/json",
        )
        self.assertEqual(
            info["max_output_tokens"],
            1000,
        )
        self.assertEqual(
            info["temperature"],
            0.2,
        )

        self.assertNotIn(
            "api_key",
            info,
        )
        self.assertNotIn(
            "test-gemini-key",
            str(info),
        )

    def test_invalid_max_output_tokens_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiProvider(
                api_key="test-key",
                model="test-model",
                max_output_tokens=0,
            )

    def test_invalid_negative_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiProvider(
                api_key="test-key",
                model="test-model",
                temperature=-0.1,
            )

    def test_temperature_above_two_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiProvider(
                api_key="test-key",
                model="test-model",
                temperature=2.1,
            )

    def test_prepares_system_and_conversation_messages(self):
        messages = [
            {
                "role": "system",
                "content": " First instruction. ",
            },
            {
                "role": "system",
                "content": " Second instruction. ",
            },
            {
                "role": "user",
                "content": " User question. ",
            },
            {
                "role": "assistant",
                "content": " Previous answer. ",
            },
        ]

        system_prompt, contents = self.provider._prepare_request(
            messages
        )

        self.assertEqual(
            system_prompt,
            "First instruction.\n\nSecond instruction.",
        )

        self.assertEqual(
            len(contents),
            2,
        )
        self.assertEqual(
            contents[0].role,
            "user",
        )
        self.assertEqual(
            contents[0].parts[0].text,
            "User question.",
        )
        self.assertEqual(
            contents[1].role,
            "model",
        )
        self.assertEqual(
            contents[1].parts[0].text,
            "Previous answer.",
        )

    def test_requires_non_system_message(self):
        messages = [
            {
                "role": "system",
                "content": "Only system instruction.",
            },
        ]

        with self.assertRaises(ValueError):
            self.provider._prepare_request(messages)

    def test_extracts_direct_response_text(self):
        response = SimpleNamespace(
            text="  Gemini response  ",
        )

        text = self.provider._extract_response_text(response)

        self.assertEqual(
            text,
            "Gemini response",
        )

    def test_extracts_text_from_candidates(self):
        class ResponseWithoutText:
            @property
            def text(self):
                raise ValueError("No direct text.")

        response = ResponseWithoutText()
        response.candidates = [
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(text="First part"),
                        SimpleNamespace(text="Second part"),
                    ]
                )
            )
        ]

        text = self.provider._extract_response_text(response)

        self.assertEqual(
            text,
            "First part\nSecond part",
        )

    def test_extracts_usage_metadata(self):
        response = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=12,
                candidates_token_count=8,
                total_token_count=20,
                thoughts_token_count=3,
            )
        )

        usage = self.provider._extract_usage(response)

        self.assertEqual(
            usage,
            {
                "prompt_token_count": 12,
                "candidates_token_count": 8,
                "total_token_count": 20,
                "thoughts_token_count": 3,
            },
        )

    def test_returns_empty_usage_when_missing(self):
        response = SimpleNamespace(
            usage_metadata=None,
        )

        usage = self.provider._extract_usage(response)

        self.assertEqual(
            usage,
            {},
        )

    def test_extracts_response_model(self):
        response = SimpleNamespace(
            model_version="gemini-response-model",
        )

        model = self.provider._get_response_model(response)

        self.assertEqual(
            model,
            "gemini-response-model",
        )

    def test_uses_configured_model_when_response_model_missing(self):
        response = SimpleNamespace(
            model_version=None,
        )

        model = self.provider._get_response_model(response)

        self.assertEqual(
            model,
            "gemini-test-model",
        )

    def test_extracts_finish_reason(self):
        response = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    finish_reason=SimpleNamespace(
                        value="STOP",
                    )
                )
            ]
        )

        finish_reason = self.provider._extract_finish_reason(
            response
        )

        self.assertEqual(
            finish_reason,
            "STOP",
        )

    def test_successful_structured_response(self):
        raw_json = """
        {
          "schema_version": "1.0",
          "metadata": {
            "provider": "",
            "model": "",
            "status": "",
            "response_time_ms": null,
            "provider_confidence_percent": 90,
            "created_at": null
          },
          "research_context": {
            "generic_product_type": "shaft",
            "current_material": "42CrMo4",
            "current_technology": "turning",
            "objective": "reduce cost",
            "required_properties": []
          },
          "materials": {
            "recommended_material": "C45",
            "alternative_materials": [],
            "comparison_notes": ""
          },
          "manufacturing": {
            "recommended_process": "turning",
            "alternative_processes": [],
            "estimated_cycle_time_change_percent": 0,
            "process_notes": ""
          },
          "costs": {
            "estimated_material_price_per_kg": null,
            "currency": "EUR",
            "estimated_material_cost_change_percent": -10,
            "estimated_production_cost_change_percent": -5,
            "estimated_total_cost_change_percent": -7,
            "cost_notes": ""
          },
          "quality": {
            "expected_quality_effect": "neutral",
            "quality_risks": [],
            "expected_defect_change_percent": 0,
            "quality_notes": ""
          },
          "production": {
            "expected_production_effect": "neutral",
            "production_risks": [],
            "expected_lead_time_change_percent": 0,
            "production_notes": ""
          },
          "recommendation": {
            "summary": "Use C45 after validation.",
            "advantages": [],
            "disadvantages": [],
            "risks": [],
            "required_validation_steps": []
          },
          "sources": []
        }
        """

        response = SimpleNamespace(
            text=raw_json,
            model_version="gemini-2.5-pro",
            usage_metadata={
                "prompt_token_count": 100,
                "candidates_token_count": 50,
                "total_token_count": 150,
            },
            candidates=[
                SimpleNamespace(
                    finish_reason=SimpleNamespace(
                        value="STOP",
                    )
                )
            ],
        )

        self.mock_client.models.generate_content.return_value = (
            response
        )

        result = self.provider.send_messages(
            [
                {
                    "role": "system",
                    "content": "Return valid engineering JSON.",
                },
                {
                    "role": "user",
                    "content": "Analyze the material change.",
                },
            ]
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.provider,
            "GEMINI",
        )
        self.assertEqual(
            result.model,
            "gemini-2.5-pro",
        )
        self.assertEqual(
            result.structured_response["metadata"]["provider"],
            "GEMINI",
        )
        self.assertEqual(
            result.structured_response["metadata"]["model"],
            "gemini-2.5-pro",
        )
        self.assertEqual(
            result.structured_response["metadata"]["status"],
            "success",
        )
        self.assertEqual(
            result.usage["total_token_count"],
            150,
        )

    def test_invalid_json_returns_failure_result(self):
        response = SimpleNamespace(
            text="This is not JSON.",
            model_version="gemini-test-model",
            usage_metadata=None,
            candidates=[],
        )

        self.mock_client.models.generate_content.return_value = (
            response
        )

        result = self.provider.send_messages(
            [
                {
                    "role": "user",
                    "content": "Return JSON.",
                },
            ]
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.metadata["stage"],
            "json_parsing",
        )
        self.assertEqual(
            result.raw_response,
            "This is not JSON.",
        )

    def test_api_exception_returns_failure_result(self):
        self.mock_client.models.generate_content.side_effect = (
            RuntimeError("Network failure")
        )

        result = self.provider.send_messages(
            [
                {
                    "role": "user",
                    "content": "Run research.",
                },
            ]
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.provider,
            "GEMINI",
        )
        self.assertIn(
            "RuntimeError",
            result.error_message,
        )
        self.assertEqual(
            result.metadata["stage"],
            "api_request",
        )
        self.assertEqual(
            result.metadata["error_type"],
            "RuntimeError",
        )
        self.assertNotIn(
            "test-gemini-key",
            result.error_message,
        )
