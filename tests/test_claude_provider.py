from django.test import SimpleTestCase

from ai_engine.providers.claude import ClaudeProvider


class ClaudeProviderTests(SimpleTestCase):
    def setUp(self):
        self.provider = ClaudeProvider(
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
        )

    def test_provider_configuration(self):
        self.assertEqual(
            self.provider.provider_name,
            "CLAUDE",
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

    def test_provider_info_does_not_expose_api_key(self):
        info = self.provider.get_provider_info()

        self.assertEqual(
            info["provider"],
            "CLAUDE",
        )
        self.assertEqual(
            info["model"],
            "test-model",
        )
        self.assertEqual(
            info["api"],
            "messages",
        )
        self.assertEqual(
            info["max_output_tokens"],
            1000,
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
            ClaudeProvider(
                api_key="test-key",
                model="test-model",
                max_output_tokens=0,
            )

    def test_separates_system_prompt_from_messages(self):
        messages = [
            {
                "role": "system",
                "content": " First system instruction. ",
            },
            {
                "role": "system",
                "content": " Second system instruction. ",
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

        system_prompt, conversation_messages = (
            self.provider._prepare_request(messages)
        )

        self.assertEqual(
            system_prompt,
            (
                "First system instruction.\n\n"
                "Second system instruction."
            ),
        )

        self.assertEqual(
            conversation_messages,
            [
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

    def test_requires_conversation_message(self):
        messages = [
            {
                "role": "system",
                "content": "System instruction.",
            },
        ]

        with self.assertRaises(ValueError):
            self.provider._prepare_request(messages)
