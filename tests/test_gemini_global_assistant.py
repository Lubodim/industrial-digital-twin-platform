from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai_engine.providers.gemini_glob import (
    GeminiChatResponse,
    GeminiGlobalAssistant,
)


class FakeAPIError(Exception):
    def __init__(
        self,
        *,
        code=None,
        message="API error",
    ):
        super().__init__(message)
        self.code = code
        self.message = message


class GeminiGlobalAssistantTests(SimpleTestCase):
    def setUp(self):
        self.client_patcher = patch(
            "ai_engine.providers.gemini_glob.genai.Client"
        )
        self.mock_client_class = self.client_patcher.start()

        self.mock_client = MagicMock()
        self.mock_chat = MagicMock()

        self.mock_client_class.return_value = self.mock_client
        self.mock_client.chats.create.return_value = self.mock_chat

        self.assistant = GeminiGlobalAssistant(
            api_key="test-gemini-key",
            model="gemini-2.5-flash",
            timeout_seconds=30,
            max_output_tokens=1000,
            temperature=0.3,
        )

    def tearDown(self):
        self.client_patcher.stop()

    def test_assistant_configuration(self):
        self.assertEqual(
            self.assistant.provider_name,
            "GEMINI_GLOBAL_CHAT",
        )
        self.assertEqual(
            self.assistant.model,
            "gemini-2.5-flash",
        )
        self.assertEqual(
            self.assistant.timeout_seconds,
            30,
        )
        self.assertEqual(
            self.assistant.max_output_tokens,
            1000,
        )
        self.assertEqual(
            self.assistant.temperature,
            0.3,
        )

    def test_assistant_info_does_not_expose_api_key(self):
        info = self.assistant.get_assistant_info()

        self.assertEqual(
            info["provider"],
            "GEMINI_GLOBAL_CHAT",
        )
        self.assertEqual(
            info["model"],
            "gemini-2.5-flash",
        )
        self.assertEqual(
            info["conversation_mode"],
            "multi_turn",
        )
        self.assertEqual(
            info["response_format"],
            "text",
        )

        self.assertNotIn(
            "api_key",
            info,
        )
        self.assertNotIn(
            "test-gemini-key",
            str(info),
        )

    def test_repr_does_not_expose_api_key(self):
        representation = repr(self.assistant)

        self.assertIn(
            "GeminiGlobalAssistant",
            representation,
        )
        self.assertIn(
            "gemini-2.5-flash",
            representation,
        )
        self.assertNotIn(
            "test-gemini-key",
            representation,
        )

    def test_missing_api_key_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="",
            )

    def test_empty_model_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="test-key",
                model="",
            )

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="test-key",
                timeout_seconds=0,
            )

    def test_invalid_max_output_tokens_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="test-key",
                max_output_tokens=0,
            )

    def test_invalid_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="test-key",
                temperature=2.1,
            )

    def test_empty_system_instruction_is_rejected(self):
        with self.assertRaises(ValueError):
            GeminiGlobalAssistant(
                api_key="test-key",
                system_instruction="",
            )

    def test_creates_chat_during_initialization(self):
        self.mock_client.chats.create.assert_called_once()

        call_kwargs = (
            self.mock_client.chats.create.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["model"],
            "gemini-2.5-flash",
        )
        self.assertEqual(
            call_kwargs["history"],
            [],
        )

    def test_reset_chat_creates_new_chat(self):
        self.assistant.reset_chat()

        self.assertEqual(
            self.mock_client.chats.create.call_count,
            2,
        )

    def test_start_new_chat_accepts_history(self):
        history = [
            SimpleNamespace(
                role="user",
            )
        ]

        self.assistant.start_new_chat(
            history=history,
        )

        call_kwargs = (
            self.mock_client.chats.create.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["history"],
            history,
        )

    def test_builds_prompt_without_context(self):
        prompt = self.assistant._build_prompt(
            message="  Explain the result.  ",
            digital_twin_context=None,
            experiment_context=None,
        )

        self.assertEqual(
            prompt,
            "ENGINEER MESSAGE:\nExplain the result.",
        )

    def test_builds_prompt_with_twin_and_experiment_context(self):
        prompt = self.assistant._build_prompt(
            message="Assess the risk.",
            digital_twin_context=" Material: C45 ",
            experiment_context=" Objective: Reduce cost ",
        )

        self.assertEqual(
            prompt,
            (
                "CURRENT DIGITAL TWIN CONTEXT:\n"
                "Material: C45\n\n"
                "CURRENT EXPERIMENT CONTEXT:\n"
                "Objective: Reduce cost\n\n"
                "ENGINEER MESSAGE:\n"
                "Assess the risk."
            ),
        )

    def test_chat_response_to_dict(self):
        response = GeminiChatResponse(
            success=True,
            text="Hello",
            model="gemini-test",
            response_time_ms=20,
            usage={
                "total_token_count": 10,
            },
            metadata={
                "provider": "GEMINI_GLOBAL_CHAT",
            },
        )

        data = response.to_dict()

        self.assertEqual(
            data["success"],
            True,
        )
        self.assertEqual(
            data["text"],
            "Hello",
        )
        self.assertEqual(
            data["model"],
            "gemini-test",
        )
        self.assertEqual(
            data["usage"]["total_token_count"],
            10,
        )

    def test_successful_chat_response(self):
        sdk_response = SimpleNamespace(
            text="  Аз съм инженерски асистент.  ",
            model_version="gemini-2.5-flash",
            usage_metadata={
                "prompt_token_count": 10,
                "candidates_token_count": 8,
                "total_token_count": 18,
            },
            candidates=[
                SimpleNamespace(
                    finish_reason=SimpleNamespace(
                        value="STOP",
                    )
                )
            ],
        )

        self.mock_chat.send_message.return_value = sdk_response

        result = self.assistant.ask(
            "Представи се.",
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.text,
            "Аз съм инженерски асистент.",
        )
        self.assertEqual(
            result.model,
            "gemini-2.5-flash",
        )
        self.assertEqual(
            result.usage["total_token_count"],
            18,
        )
        self.assertEqual(
            result.metadata["provider"],
            "GEMINI_GLOBAL_CHAT",
        )
        self.assertEqual(
            result.metadata["finish_reason"],
            "STOP",
        )

        self.mock_chat.send_message.assert_called_once_with(
            "ENGINEER MESSAGE:\nПредстави се."
        )

    def test_chat_alias_calls_ask(self):
        sdk_response = SimpleNamespace(
            text="Response",
            model_version="gemini-2.5-flash",
            usage_metadata=None,
            candidates=[],
        )

        self.mock_chat.send_message.return_value = sdk_response

        result = self.assistant.chat(
            "Question",
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.text,
            "Response",
        )

    def test_empty_message_is_rejected(self):
        with self.assertRaises(ValueError):
            self.assistant.ask("   ")

    def test_empty_response_returns_failure(self):
        sdk_response = SimpleNamespace(
            text="",
            model_version="gemini-2.5-flash",
            usage_metadata=None,
            candidates=[],
        )

        self.mock_chat.send_message.return_value = sdk_response

        result = self.assistant.ask(
            "Test message",
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            "Gemini returned an empty chat response.",
        )
        self.assertEqual(
            result.metadata["stage"],
            "response_extraction",
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
                        SimpleNamespace(text="First"),
                        SimpleNamespace(text="Second"),
                    ]
                )
            )
        ]

        text = self.assistant._extract_response_text(
            response
        )

        self.assertEqual(
            text,
            "First\nSecond",
        )

    def test_extracts_usage_metadata(self):
        response = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=4,
                candidates_token_count=6,
                total_token_count=10,
                thoughts_token_count=2,
            )
        )

        usage = self.assistant._extract_usage(response)

        self.assertEqual(
            usage,
            {
                "prompt_token_count": 4,
                "candidates_token_count": 6,
                "total_token_count": 10,
                "thoughts_token_count": 2,
            },
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

        finish_reason = (
            self.assistant._extract_finish_reason(response)
        )

        self.assertEqual(
            finish_reason,
            "STOP",
        )

    def test_unexpected_exception_returns_failure(self):
        self.mock_chat.send_message.side_effect = RuntimeError(
            "Unexpected failure"
        )

        result = self.assistant.ask(
            "Test message",
        )

        self.assertFalse(result.success)
        self.assertIn(
            "RuntimeError",
            result.error_message,
        )
        self.assertEqual(
            result.metadata["stage"],
            "unexpected_error",
        )
        self.assertEqual(
            result.metadata["error_type"],
            "RuntimeError",
        )
        self.assertNotIn(
            "test-gemini-key",
            result.error_message,
        )

    def test_rate_limit_error_is_normalized(self):
        error = FakeAPIError(
            code=429,
            message="Quota exceeded",
        )

        result = self.assistant._build_api_error_response(
            error=error,
            response_time_ms=15,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            (
                "Gemini Flash quota or rate limit was exceeded. "
                "Check the API project's quota and billing settings."
            ),
        )
        self.assertEqual(
            result.metadata["error_type"],
            "rate_limit",
        )
        self.assertEqual(
            result.metadata["status_code"],
            429,
        )

    def test_authentication_error_is_normalized(self):
        error = FakeAPIError(
            code=403,
            message="Permission denied",
        )

        result = self.assistant._build_api_error_response(
            error=error,
            response_time_ms=15,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.metadata["error_type"],
            "authentication",
        )
        self.assertEqual(
            result.metadata["status_code"],
            403,
        )

    def test_model_not_found_error_is_normalized(self):
        error = FakeAPIError(
            code=404,
            message="Model not found",
        )

        result = self.assistant._build_api_error_response(
            error=error,
            response_time_ms=15,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            result.metadata["error_type"],
            "model_not_found",
        )
        self.assertEqual(
            result.metadata["status_code"],
            404,
        )
