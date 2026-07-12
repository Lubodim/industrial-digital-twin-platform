from django.test import SimpleTestCase

from ai_engine.provider_factory import (
    ProviderFactory,
    ProviderNotImplementedError,
    UnsupportedProviderError,
)
from ai_engine.providers.openai import OpenAIProvider


class ProviderFactoryTests(SimpleTestCase):
    def test_returns_supported_provider_names(self):
        providers = ProviderFactory.get_supported_providers()

        self.assertEqual(
            providers,
            [
                "openai",
                "gemini",
                "claude",
                "grok",
            ],
        )

    def test_creates_openai_provider_with_overrides(self):
        provider = ProviderFactory.create(
            "openai",
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
        )

        self.assertIsInstance(provider, OpenAIProvider)
        self.assertEqual(provider.model, "test-model")
        self.assertEqual(provider.timeout_seconds, 30)
        self.assertEqual(provider.max_output_tokens, 1000)

    def test_accepts_openai_aliases(self):
        provider = ProviderFactory.create(
            "chatgpt",
            api_key="test-key",
            model="test-model",
        )

        self.assertIsInstance(provider, OpenAIProvider)

    def test_rejects_unknown_provider(self):
        with self.assertRaises(UnsupportedProviderError):
            ProviderFactory.create(
                "unknown-provider",
            )

    def test_unimplemented_gemini_provider_returns_clear_error(self):
        with self.assertRaises(ProviderNotImplementedError):
            ProviderFactory.create(
                "gemini",
                api_key="test-key",
            )

    def test_empty_provider_name_is_rejected(self):
        with self.assertRaises(ValueError):
            ProviderFactory.create("")

    def test_non_string_provider_name_is_rejected(self):
        with self.assertRaises(TypeError):
            ProviderFactory.create(123)