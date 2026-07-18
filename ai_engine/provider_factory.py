from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from ai_engine.providers.base import BaseAIProvider


load_dotenv()


class ProviderFactoryError(Exception):
    """Base exception for provider factory errors."""


class UnsupportedProviderError(ProviderFactoryError):
    """Raised when an unknown provider name is requested."""


class ProviderConfigurationError(ProviderFactoryError):
    """Raised when required provider configuration is missing."""


class ProviderNotImplementedError(ProviderFactoryError):
    """Raised when a supported provider is not implemented yet."""


class ProviderFactory:
    """
    Create external AI providers from a common configuration interface.

    Supported provider names:
    - openai
    - gemini
    - claude
    - grok
    """

    SUPPORTED_PROVIDERS = (
        "openai",
        "gemini",
        "claude",
        "grok",
    )

    @classmethod
    def create(
        cls,
        provider_name: str,
        **overrides: Any,
    ) -> BaseAIProvider:
        """
        Create a configured provider instance.

        Values supplied through overrides have priority over environment
        variables. This is useful for tests and future Django settings.
        """

        normalized_name = cls._normalize_provider_name(provider_name)

        if normalized_name == "openai":
            return cls._create_openai_provider(**overrides)

        if normalized_name == "gemini":
            return cls._create_gemini_provider(**overrides)

        if normalized_name == "claude":
            return cls._create_claude_provider(**overrides)

        if normalized_name == "grok":
            return cls._create_grok_provider(**overrides)

        raise UnsupportedProviderError(
            f"Unsupported AI provider: {provider_name!r}. "
            f"Supported providers: {', '.join(cls.SUPPORTED_PROVIDERS)}."
        )

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Return all provider names recognized by the application."""

        return list(cls.SUPPORTED_PROVIDERS)

    @classmethod
    def get_configured_providers(cls) -> list[str]:
        """
        Return providers that currently have an API key configured.

        This does not guarantee that the provider implementation is complete.
        """

        environment_keys = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "claude": "CLAUDE_API_KEY",
            "grok": "GROK_API_KEY",
        }

        return [
            provider_name
            for provider_name, environment_key in environment_keys.items()
            if cls._get_environment_value(environment_key)
        ]

    @staticmethod
    def _normalize_provider_name(provider_name: str) -> str:
        """Normalize and validate the requested provider name."""

        if not isinstance(provider_name, str):
            raise TypeError("provider_name must be a string.")

        normalized_name = provider_name.strip().lower()

        if not normalized_name:
            raise ValueError("provider_name cannot be empty.")

        aliases = {
            "chatgpt": "openai",
            "gpt": "openai",
            "google": "gemini",
            "anthropic": "claude",
            "xai": "grok",
            "x.ai": "grok",
        }

        return aliases.get(normalized_name, normalized_name)

    @classmethod
    def _create_openai_provider(
        cls,
        **overrides: Any,
    ) -> BaseAIProvider:
        """Create the working OpenAI provider."""

        from ai_engine.providers.openai import OpenAIProvider

        api_key = cls._get_required_value(
            override_value=overrides.get("api_key"),
            environment_key="OPENAI_API_KEY",
            provider_name="OpenAI",
        )

        model = cls._get_value(
            override_value=overrides.get("model"),
            environment_key="OPENAI_MODEL",
            default="gpt-5-mini",
        )

        timeout_seconds = cls._get_integer_value(
            override_value=overrides.get("timeout_seconds"),
            environment_key="OPENAI_TIMEOUT_SECONDS",
            default=90,
            minimum=1,
        )

        max_output_tokens = cls._get_integer_value(
            override_value=overrides.get("max_output_tokens"),
            environment_key="OPENAI_MAX_OUTPUT_TOKENS",
            default=2500,
            minimum=1,
        )

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

    @classmethod
    def _create_gemini_provider(
        cls,
        **overrides: Any,
    ) -> BaseAIProvider:
        """Create Gemini provider after its adapter is implemented."""

        try:
            from ai_engine.providers.gemini import GeminiProvider
        except (ImportError, AttributeError) as error:
            raise ProviderNotImplementedError(
                "Gemini provider is not implemented yet."
            ) from error

        api_key = cls._get_required_value(
            override_value=overrides.get("api_key"),
            environment_key="GEMINI_API_KEY",
            provider_name="Gemini",
        )

        model = cls._get_value(
            override_value=overrides.get("model"),
            environment_key="GEMINI_MODEL",
            default="gemini-2.5-flash",
        )

        timeout_seconds = cls._get_integer_value(
            override_value=overrides.get("timeout_seconds"),
            environment_key="GEMINI_TIMEOUT_SECONDS",
            default=90,
            minimum=1,
        )

        max_output_tokens = cls._get_integer_value(
            override_value=overrides.get("max_output_tokens"),
            environment_key="GEMINI_MAX_OUTPUT_TOKENS",
            default=2500,
            minimum=1,
        )

        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

    @classmethod
    def _create_claude_provider(
        cls,
        **overrides: Any,
    ) -> BaseAIProvider:
        """Create Claude provider after its adapter is implemented."""

        try:
            from ai_engine.providers.claude import ClaudeProvider
        except (ImportError, AttributeError) as error:
            raise ProviderNotImplementedError(
                "Claude provider is not implemented yet."
            ) from error

        api_key = cls._get_required_value(
            override_value=overrides.get("api_key"),
            environment_key="CLAUDE_API_KEY",
            provider_name="Claude",
        )

        model = cls._get_value(
            override_value=overrides.get("model"),
            environment_key="CLAUDE_MODEL",
            default="claude-sonnet",
        )

        timeout_seconds = cls._get_integer_value(
            override_value=overrides.get("timeout_seconds"),
            environment_key="CLAUDE_TIMEOUT_SECONDS",
            default=90,
            minimum=1,
        )

        max_output_tokens = cls._get_integer_value(
            override_value=overrides.get("max_output_tokens"),
            environment_key="CLAUDE_MAX_OUTPUT_TOKENS",
            default=2500,
            minimum=1,
        )

        return ClaudeProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

    @classmethod
    def _create_grok_provider(
        cls,
        **overrides: Any,
    ) -> BaseAIProvider:
        """Create the xAI Grok provider."""

        from ai_engine.providers.grok import GrokProvider

        api_key = cls._get_required_value(
            override_value=overrides.get("api_key"),
            environment_key="GROK_API_KEY",
            provider_name="Grok",
        )

        model = cls._get_value(
            override_value=overrides.get("model"),
            environment_key="GROK_MODEL",
            default="grok-4.5",
        )

        timeout_seconds = cls._get_integer_value(
            override_value=overrides.get("timeout_seconds"),
            environment_key="GROK_TIMEOUT_SECONDS",
            default=90,
            minimum=1,
        )

        max_output_tokens = cls._get_integer_value(
            override_value=overrides.get("max_output_tokens"),
            environment_key="GROK_MAX_OUTPUT_TOKENS",
            default=2500,
            minimum=1,
        )

        base_url = cls._get_value(
            override_value=overrides.get("base_url"),
            environment_key="GROK_BASE_URL",
            default="https://api.x.ai/v1",
        )

        return GrokProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            base_url=base_url,
        )
    @staticmethod
    def _get_environment_value(environment_key: str) -> str | None:
        """Read and clean an environment variable."""

        value = os.getenv(environment_key)

        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None

    @classmethod
    def _get_required_value(
        cls,
        *,
        override_value: Any,
        environment_key: str,
        provider_name: str,
    ) -> str:
        """Return a required configuration value."""

        value = override_value or cls._get_environment_value(environment_key)

        if not isinstance(value, str) or not value.strip():
            raise ProviderConfigurationError(
                f"{provider_name} API key is missing. "
                f"Set {environment_key} in the .env file."
            )

        return value.strip()

    @classmethod
    def _get_value(
        cls,
        *,
        override_value: Any,
        environment_key: str,
        default: str,
    ) -> str:
        """Return an optional string configuration value."""

        value = (
            override_value
            or cls._get_environment_value(environment_key)
            or default
        )

        if not isinstance(value, str) or not value.strip():
            raise ProviderConfigurationError(
                f"Invalid value for {environment_key}."
            )

        return value.strip()

    @classmethod
    def _get_integer_value(
        cls,
        *,
        override_value: Any,
        environment_key: str,
        default: int,
        minimum: int,
    ) -> int:
        """Read and validate an integer configuration value."""

        raw_value = (
            override_value
            if override_value is not None
            else cls._get_environment_value(environment_key)
        )

        if raw_value is None:
            raw_value = default

        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError) as error:
            raise ProviderConfigurationError(
                f"{environment_key} must be an integer."
            ) from error

        if parsed_value < minimum:
            raise ProviderConfigurationError(
                f"{environment_key} must be at least {minimum}."
            )

        return parsed_value
    