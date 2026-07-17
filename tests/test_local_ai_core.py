import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from ai_engine.local_ai.ollama_client import (
    OllamaClient,
)
from ai_engine.local_ai.prompt_builder import (
    EngineeringPromptBuilder,
)


class OllamaClientTests(SimpleTestCase):
    def setUp(self):
        self.client = OllamaClient(
            host="http://localhost:11434",
            model="qwen3.5:9b",
            timeout_seconds=30,
            think=False,
            temperature=0.1,
        )

    @patch(
        "ai_engine.local_ai.ollama_client."
        "requests.get"
    )
    def test_is_available_returns_true(
        self,
        mock_get,
    ):
        mock_get.return_value.status_code = 200

        self.assertTrue(
            self.client.is_available()
        )

    @patch(
        "ai_engine.local_ai.ollama_client."
        "requests.get"
    )
    def test_is_available_returns_false_on_error(
        self,
        mock_get,
    ):
        import requests

        mock_get.side_effect = (
            requests.ConnectionError()
        )

        self.assertFalse(
            self.client.is_available()
        )

    @patch(
        "ai_engine.local_ai.ollama_client."
        "requests.post"
    )
    def test_ask_sends_system_and_schema(
        self,
        mock_post,
    ):
        response_schema = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                }
            },
            "required": [
                "summary",
            ],
        }

        response_data = {
            "model": "qwen3.5:9b",
            "response": json.dumps(
                {
                    "summary": "Test result",
                }
            ),
            "thinking": "",
            "total_duration": 2_000_000,
            "load_duration": 1_000_000,
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

        mocked_response = Mock()
        mocked_response.json.return_value = (
            response_data
        )
        mocked_response.raise_for_status.return_value = (
            None
        )

        mock_post.return_value = mocked_response

        result = self.client.ask(
            prompt="Analyse this component.",
            system_prompt=(
                "You are an engineer."
            ),
            response_schema=response_schema,
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.structured_response,
            {
                "summary": "Test result",
            },
        )

        sent_payload = (
            mock_post.call_args.kwargs["json"]
        )

        self.assertEqual(
            sent_payload["system"],
            "You are an engineer.",
        )

        self.assertEqual(
            sent_payload["format"],
            response_schema,
        )

        self.assertFalse(
            sent_payload["think"]
        )

    @patch(
        "ai_engine.local_ai.ollama_client."
        "requests.post"
    )
    def test_invalid_structured_json_is_failure(
        self,
        mock_post,
    ):
        mocked_response = Mock()
        mocked_response.json.return_value = {
            "model": "qwen3.5:9b",
            "response": "not-json",
        }
        mocked_response.raise_for_status.return_value = (
            None
        )

        mock_post.return_value = mocked_response

        result = self.client.ask(
            prompt="Return JSON.",
            response_schema={
                "type": "object",
            },
        )

        self.assertFalse(result.success)
        self.assertIn(
            "structured JSON",
            result.error,
        )

    def test_empty_prompt_is_rejected(self):
        result = self.client.ask(
            prompt="   "
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.error,
            "Prompt cannot be empty.",
        )


class EngineeringPromptBuilderTests(
    SimpleTestCase
):
    def test_builds_complete_prompt_package(self):
        builder = EngineeringPromptBuilder()

        result = builder.build(
            digital_twin={
                "part_number": "TEST-001",
                "material": "S235",
            },
            experiment={
                "objective": "Reduce mass",
            },
            chat_history=[
                {
                    "role": "ENGINEER",
                    "content": (
                        "Can the mass be reduced?"
                    ),
                }
            ],
            external_research={
                "providers": {
                    "OPENAI": {
                        "summary": "Possible.",
                    }
                }
            },
            materials=[],
            technologies=[],
            previous_experiments=[],
        )

        self.assertIn(
            '"part_number": "TEST-001"',
            result.user_prompt,
        )

        self.assertIn(
            '"objective": "Reduce mass"',
            result.user_prompt,
        )

        self.assertTrue(
            result.system_prompt
        )

        self.assertEqual(
            result.response_schema["type"],
            "object",
        )
