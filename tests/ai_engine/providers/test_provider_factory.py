from unittest.mock import patch

from django.test import SimpleTestCase

from ai_engine.provider_factory import (
    ProviderConfigurationError,
    ProviderFactory,
    UnsupportedProviderError,
)
from ai_engine.providers.claude import ClaudeProvider
from ai_engine.providers.gemini import GeminiProvider
from ai_engine.providers.grok import GrokProvider
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

    def test_recognizes_supported_provider_names(self):
        self.assertTrue(
            ProviderFactory.is_provider_supported("openai")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("gemini")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("claude")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("grok")
        )

    def test_recognizes_supported_provider_aliases(self):
        self.assertTrue(
            ProviderFactory.is_provider_supported("chatgpt")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("google")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("anthropic")
        )
        self.assertTrue(
            ProviderFactory.is_provider_supported("xai")
        )

    def test_unknown_provider_is_not_supported(self):
        self.assertFalse(
            ProviderFactory.is_provider_supported(
                "unknown-provider"
            )
        )

    def test_empty_provider_is_not_supported(self):
        self.assertFalse(
            ProviderFactory.is_provider_supported("")
        )

    def test_non_string_provider_is_not_supported(self):
        self.assertFalse(
            ProviderFactory.is_provider_supported(123)
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

    def test_accepts_openai_alias(self):
        provider = ProviderFactory.create(
            "chatgpt",
            api_key="test-key",
            model="test-model",
        )

        self.assertIsInstance(provider, OpenAIProvider)

    def test_creates_gemini_provider_with_overrides(self):
        provider = ProviderFactory.create(
            "gemini",
            api_key="test-key",
            model="test-gemini-model",
            timeout_seconds=30,
            max_output_tokens=1000,
        )

        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(
            provider.model,
            "test-gemini-model",
        )
        self.assertEqual(provider.timeout_seconds, 30)
        self.assertEqual(provider.max_output_tokens, 1000)

    def test_accepts_gemini_alias(self):
        provider = ProviderFactory.create(
            "google",
            api_key="test-key",
            model="test-gemini-model",
        )

        self.assertIsInstance(provider, GeminiProvider)

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "environment-test-key",
            "GEMINI_ANALYSIS_MODEL": "environment-gemini-model",
            "GEMINI_TIMEOUT_SECONDS": "45",
            "GEMINI_MAX_OUTPUT_TOKENS": "1500",
        },
        clear=False,
    )
    def test_gemini_uses_analysis_environment_settings(self):
        provider = ProviderFactory.create("gemini")

        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(
            provider.model,
            "environment-gemini-model",
        )
        self.assertEqual(provider.timeout_seconds, 45)
        self.assertEqual(provider.max_output_tokens, 1500)

    def test_creates_claude_provider_with_overrides(self):
        provider = ProviderFactory.create(
            "claude",
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
        )

        self.assertIsInstance(provider, ClaudeProvider)
        self.assertEqual(provider.model, "test-model")
        self.assertEqual(provider.timeout_seconds, 30)
        self.assertEqual(provider.max_output_tokens, 1000)

    def test_accepts_claude_alias(self):
        provider = ProviderFactory.create(
            "anthropic",
            api_key="test-key",
            model="test-model",
        )

        self.assertIsInstance(provider, ClaudeProvider)

    def test_creates_grok_provider_with_overrides(self):
        provider = ProviderFactory.create(
            "grok",
            api_key="test-key",
            model="test-model",
            timeout_seconds=30,
            max_output_tokens=1000,
            base_url="https://api.x.ai/v1",
        )

        self.assertIsInstance(provider, GrokProvider)
        self.assertEqual(provider.model, "test-model")
        self.assertEqual(provider.timeout_seconds, 30)
        self.assertEqual(provider.max_output_tokens, 1000)
        self.assertEqual(
            provider.base_url,
            "https://api.x.ai/v1",
        )

    def test_accepts_grok_alias(self):
        provider = ProviderFactory.create(
            "xai",
            api_key="test-key",
            model="test-model",
        )

        self.assertIsInstance(provider, GrokProvider)

    def test_rejects_unknown_provider(self):
        with self.assertRaises(UnsupportedProviderError):
            ProviderFactory.create("unknown-provider")

    def test_empty_provider_name_is_rejected(self):
        with self.assertRaises(ValueError):
            ProviderFactory.create("")

    def test_non_string_provider_name_is_rejected(self):
        with self.assertRaises(TypeError):
            ProviderFactory.create(123)

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "",
        },
        clear=False,
    )
    def test_missing_openai_api_key_is_rejected(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderFactory.create("openai")

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "",
        },
        clear=False,
    )
    def test_missing_gemini_api_key_is_rejected(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderFactory.create("gemini")

    def test_invalid_timeout_is_rejected(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderFactory.create(
                "openai",
                api_key="test-key",
                timeout_seconds=0,
            )

    def test_non_integer_max_output_tokens_are_rejected(self):
        with self.assertRaises(ProviderConfigurationError):
            ProviderFactory.create(
                "openai",
                api_key="test-key",
                max_output_tokens="not-an-integer",
            )

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "openai-key",
            "GEMINI_API_KEY": "gemini-key",
            "ANTHROPIC_API_KEY": "",
            "GROK_API_KEY": "grok-key",
        },
        clear=False,
    )
    def test_returns_only_configured_providers(self):
        providers = ProviderFactory.get_configured_providers()

        self.assertEqual(
            providers,
            [
                "openai",
                "gemini",
                "grok",
            ],
        )

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "gemini-key",
        },
        clear=False,
    )
    def test_reports_provider_as_configured(self):
        self.assertTrue(
            ProviderFactory.is_provider_configured("gemini")
        )

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "",
        },
        clear=False,
    )
    def test_reports_provider_as_not_configured(self):
        self.assertFalse(
            ProviderFactory.is_provider_configured("gemini")
        )

    def test_configuration_check_rejects_unknown_provider(self):
        with self.assertRaises(UnsupportedProviderError):
            ProviderFactory.is_provider_configured(
                "unknown-provider"
            )
