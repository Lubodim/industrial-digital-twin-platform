from django.test import SimpleTestCase

from ai_engine.providers.base import BaseAIProvider, ProviderResult


class DummyProvider(BaseAIProvider):
    provider_name = "TEST"

    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        self.validate_messages(messages)

        return ProviderResult(
            provider=self.provider_name,
            model=self.model,
            success=True,
            raw_response='{"summary": "Test response"}',
            structured_response={
                "summary": "Test response",
            },
            response_time_ms=10,
        )


class BaseAIProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = DummyProvider(
            api_key="test-key",
            model="test-model",
        )

    def test_provider_returns_standard_result(self):
        result = self.provider.send_messages(
            [
                {
                    "role": "system",
                    "content": "You are an engineering assistant.",
                },
                {
                    "role": "user",
                    "content": "Analyze this manufacturing process.",
                },
            ]
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "TEST")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(
            result.structured_response["summary"],
            "Test response",
        )

    def test_provider_info_does_not_expose_api_key(self):
        info = self.provider.get_provider_info()

        self.assertEqual(info["provider"], "TEST")
        self.assertEqual(info["model"], "test-model")
        self.assertNotIn("api_key", info)
        self.assertNotIn("test-key", str(info))

    def test_empty_api_key_is_rejected(self):
        with self.assertRaises(ValueError):
            DummyProvider(
                api_key="",
                model="test-model",
            )

    def test_empty_model_is_rejected(self):
        with self.assertRaises(ValueError):
            DummyProvider(
                api_key="test-key",
                model="",
            )

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaises(ValueError):
            DummyProvider(
                api_key="test-key",
                model="test-model",
                timeout_seconds=0,
            )

    def test_empty_messages_are_rejected(self):
        with self.assertRaises(ValueError):
            self.provider.send_messages([])

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValueError):
            self.provider.send_messages(
                [
                    {
                        "role": "invalid-role",
                        "content": "Test message",
                    }
                ]
            )

    def test_empty_message_content_is_rejected(self):
        with self.assertRaises(ValueError):
            self.provider.send_messages(
                [
                    {
                        "role": "user",
                        "content": "   ",
                    }
                ]
            )