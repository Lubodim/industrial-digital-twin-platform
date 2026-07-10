from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderResult:
    """
    Standard result returned by every external AI provider.

    All provider adapters must convert their native API response
    to this common structure.
    """

    provider: str
    model: str
    success: bool

    raw_response: str = ""
    structured_response: dict[str, Any] = field(default_factory=dict)

    response_time_ms: int | None = None
    error_message: str = ""

    usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the provider result to a serializable dictionary.
        """

        return {
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "raw_response": self.raw_response,
            "structured_response": self.structured_response,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "usage": self.usage,
            "metadata": self.metadata,
        }


class BaseAIProvider(ABC):
    """
    Abstract base class for all external AI providers.

    Concrete implementations:
    - OpenAIProvider
    - ClaudeProvider
    - GeminiProvider
    - GrokProvider
    """

    provider_name: str = "unknown"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                f"API key is required for provider '{self.provider_name}'."
            )

        if not model or not model.strip():
            raise ValueError(
                f"Model name is required for provider '{self.provider_name}'."
            )

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        """
        Send system/user messages to the external AI provider.

        Every implementation must:
        1. send the supplied messages;
        2. measure response time;
        3. preserve the raw response;
        4. parse JSON when possible;
        5. return ProviderResult;
        6. never expose the API key.
        """

        raise NotImplementedError

    def validate_messages(
        self,
        messages: list[dict[str, str]],
    ) -> None:
        """
        Validate the common message format before calling an API.
        """

        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list.")

        allowed_roles = {"system", "user", "assistant"}

        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                raise TypeError(
                    f"Message at index {index} must be a dictionary."
                )

            role = message.get("role")
            content = message.get("content")

            if role not in allowed_roles:
                raise ValueError(
                    f"Message at index {index} has unsupported role: {role!r}."
                )

            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"Message at index {index} must contain non-empty text."
                )

    def get_provider_info(self) -> dict[str, Any]:
        """
        Return non-sensitive provider configuration information.
        """

        return {
            "provider": self.provider_name,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider_name!r}, "
            f"model={self.model!r})"
        )