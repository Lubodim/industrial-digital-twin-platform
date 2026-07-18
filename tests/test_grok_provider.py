from django.test import SimpleTestCase

from ai_engine.providers.grok import GrokProvider


class GrokProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = GrokProvider(
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
        )

    def test_provider_configuration(self):
        self.assertEqual(
            self.provider.provider_name,
            "GROK",
        )
        self.assertEqual(
            self.provider.model,
            "test-model",
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
            self.provider.base_url,
            "https://api.x.ai/v1",
        )

    def test_provider_info_does_not_expose_api_key(self):
        info = self.provider.get_provider_info()

        self.assertEqual(
            info["provider"],
            "GROK",
        )
        self.assertEqual(
            info["model"],
            "test-model",
        )
        self.assertEqual(
            info["api"],
            "responses",
        )
        self.assertEqual(
            info["base_url"],
            "https://api.x.ai/v1",
        )

        self.assertNotIn(
            "api_key",
            info,
        )
        self.assertNotIn(
            "test-key",
            str(info),
        )

    def test_invalid_max_output_tokens_is_rejected(self):
        with self.assertRaises(ValueError):
            GrokProvider(
                api_key="test-key",
                model="test-model",
                max_output_tokens=0,
            )

    def test_empty_base_url_is_rejected(self):
        with self.assertRaises(ValueError):
            GrokProvider(
                api_key="test-key",
                model="test-model",
                base_url="",
            )

    def test_prepares_messages_without_changing_order(self):
        messages = [
            {
                "role": "system",
                "content": "  System instructions.  ",
            },
            {
                "role": "user",
                "content": "  User question.  ",
            },
            {
                "role": "assistant",
                "content": "  Previous answer.  ",
            },
        ]

        prepared_messages = self.provider._prepare_request(
            messages
        )

        self.assertEqual(
            prepared_messages,
            [
                {
                    "role": "system",
                    "content": "System instructions.",
                },
                {
                    "role": "user",
                    "content": "User question.",
                },
                {
                    "role": "assistant",
                    "content": "Previous answer.",
                },
            ],
        )
