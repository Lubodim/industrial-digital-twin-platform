from __future__ import annotations

import time
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Anthropic,
    AnthropicError,
    RateLimitError,
)

from ai_engine.parsers.json_parser import parse_json_response
from ai_engine.providers.base import BaseAIProvider, ProviderResult
from ai_engine.validators import validate_external_research_result


class ClaudeProvider(BaseAIProvider):
    """
    Provider adapter for the Anthropic Claude Messages API.

    The adapter:

    - accepts the common application message format;
    - separates system instructions from conversation messages;
    - sends requests through the official Anthropic Python SDK;
    - preserves the original response text;
    - parses JSON responses;
    - validates the engineering research schema;
    - returns the common ProviderResult object.
    """

    provider_name = "CLAUDE"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 90,
        max_output_tokens: int = 2500,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )

        if max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be greater than zero."
            )

        self.max_output_tokens = max_output_tokens

        self.client = Anthropic(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
        )

    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        """
        Send messages to Claude and return a normalized ProviderResult.
        """

        self.validate_messages(messages)

        system_prompt, conversation_messages = self._prepare_request(
            messages
        )

        started_at = time.perf_counter()

        try:
            request_parameters: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_output_tokens,
                "messages": conversation_messages,
            }

            if system_prompt:
                request_parameters["system"] = system_prompt

            response = self.client.messages.create(
                **request_parameters,
            )

            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            raw_response = self._extract_response_text(response)

            parse_result = parse_json_response(raw_response)

            if not parse_result.success:
                return ProviderResult(
                    provider=self.provider_name,
                    model=self._get_response_model(response),
                    success=False,
                    raw_response=raw_response,
                    response_time_ms=response_time_ms,
                    error_message=parse_result.error_message,
                    usage=self._extract_usage(response),
                    metadata={
                        "response_id": getattr(
                            response,
                            "id",
                            None,
                        ),
                        "response_type": getattr(
                            response,
                            "type",
                            None,
                        ),
                        "stop_reason": getattr(
                            response,
                            "stop_reason",
                            None,
                        ),
                        "stop_sequence": getattr(
                            response,
                            "stop_sequence",
                            None,
                        ),
                        "stage": "json_parsing",
                    },
                )

            validation_result = validate_external_research_result(
                parse_result.data
            )

            if not validation_result.is_valid:
                return ProviderResult(
                    provider=self.provider_name,
                    model=self._get_response_model(response),
                    success=False,
                    raw_response=raw_response,
                    structured_response=(
                        validation_result.normalized_data
                    ),
                    response_time_ms=response_time_ms,
                    error_message="; ".join(
                        validation_result.errors
                    ),
                    usage=self._extract_usage(response),
                    metadata={
                        "response_id": getattr(
                            response,
                            "id",
                            None,
                        ),
                        "response_type": getattr(
                            response,
                            "type",
                            None,
                        ),
                        "stop_reason": getattr(
                            response,
                            "stop_reason",
                            None,
                        ),
                        "stop_sequence": getattr(
                            response,
                            "stop_sequence",
                            None,
                        ),
                        "stage": "schema_validation",
                        "validation_errors": (
                            validation_result.errors
                        ),
                        "validation_warnings": (
                            validation_result.warnings
                        ),
                    },
                )

            normalized_data = validation_result.normalized_data

            normalized_data["metadata"]["provider"] = (
                self.provider_name
            )
            normalized_data["metadata"]["model"] = (
                self._get_response_model(response)
            )
            normalized_data["metadata"]["status"] = "success"
            normalized_data["metadata"]["response_time_ms"] = (
                response_time_ms
            )

            return ProviderResult(
                provider=self.provider_name,
                model=self._get_response_model(response),
                success=True,
                raw_response=raw_response,
                structured_response=normalized_data,
                response_time_ms=response_time_ms,
                usage=self._extract_usage(response),
                metadata={
                    "response_id": getattr(
                        response,
                        "id",
                        None,
                    ),
                    "response_type": getattr(
                        response,
                        "type",
                        None,
                    ),
                    "stop_reason": getattr(
                        response,
                        "stop_reason",
                        None,
                    ),
                    "stop_sequence": getattr(
                        response,
                        "stop_sequence",
                        None,
                    ),
                    "validation_warnings": (
                        validation_result.warnings
                    ),
                },
            )

        except APITimeoutError:
            return self._build_error_result(
                started_at=started_at,
                error_message="Claude request timed out.",
                error_type="timeout",
            )

        except RateLimitError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Claude rate limit, quota, or available "
                    f"credit was exceeded: {error}"
                ),
                error_type="rate_limit",
                metadata=self._extract_error_metadata(error),
            )

        except APIConnectionError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Could not connect to the Anthropic API: "
                    f"{error}"
                ),
                error_type="connection",
                metadata=self._extract_error_metadata(error),
            )

        except APIStatusError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Anthropic API returned an error with status "
                    f"{error.status_code}: {error}"
                ),
                error_type="api_status",
                metadata={
                    "status_code": error.status_code,
                    "request_id": getattr(
                        error,
                        "request_id",
                        None,
                    ),
                },
            )

        except AnthropicError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    f"Anthropic SDK request error: {error}"
                ),
                error_type="anthropic_sdk",
                metadata=self._extract_error_metadata(error),
            )

        except Exception as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Unexpected Claude provider error: "
                    f"{type(error).__name__}: {error}"
                ),
                error_type="unexpected",
            )

    def _prepare_request(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """
        Separate system instructions from Claude conversation messages.

        Anthropic accepts the system prompt separately. Conversation
        messages may contain only user and assistant roles.
        """

        system_parts: list[str] = []
        conversation_messages: list[dict[str, str]] = []

        for message in messages:
            role = message["role"]
            content = message["content"].strip()

            if role == "system":
                system_parts.append(content)
                continue

            conversation_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        if not conversation_messages:
            raise ValueError(
                "At least one user or assistant message is required."
            )

        system_prompt = "\n\n".join(system_parts)

        return system_prompt, conversation_messages

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """
        Extract and join all text content blocks from a Claude response.
        """

        content_blocks = getattr(response, "content", None)

        if not content_blocks:
            return ""

        text_parts: list[str] = []

        for block in content_blocks:
            block_type = getattr(block, "type", None)
            block_text = getattr(block, "text", None)

            if (
                block_type == "text"
                and isinstance(block_text, str)
            ):
                text_parts.append(block_text)

        return "\n".join(text_parts).strip()

    def _build_error_result(
        self,
        *,
        started_at: float,
        error_message: str,
        error_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        """
        Build a standard failure result without exposing the API key.
        """

        response_time_ms = round(
            (time.perf_counter() - started_at) * 1000
        )

        result_metadata: dict[str, Any] = {
            "error_type": error_type,
        }

        if metadata:
            result_metadata.update(metadata)

        return ProviderResult(
            provider=self.provider_name,
            model=self.model,
            success=False,
            response_time_ms=response_time_ms,
            error_message=error_message,
            metadata=result_metadata,
        )

    def _get_response_model(self, response: Any) -> str:
        """
        Return the actual Claude response model when available.
        """

        response_model = getattr(response, "model", None)

        if isinstance(response_model, str) and response_model:
            return response_model

        return self.model

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any]:
        """
        Convert Anthropic token usage to a serializable dictionary.
        """

        usage = getattr(response, "usage", None)

        if usage is None:
            return {}

        if hasattr(usage, "model_dump"):
            usage_data = usage.model_dump()
        elif isinstance(usage, dict):
            usage_data = dict(usage)
        else:
            usage_data = {
                "input_tokens": getattr(
                    usage,
                    "input_tokens",
                    None,
                ),
                "output_tokens": getattr(
                    usage,
                    "output_tokens",
                    None,
                ),
                "cache_creation_input_tokens": getattr(
                    usage,
                    "cache_creation_input_tokens",
                    None,
                ),
                "cache_read_input_tokens": getattr(
                    usage,
                    "cache_read_input_tokens",
                    None,
                ),
            }

        input_tokens = usage_data.get("input_tokens")
        output_tokens = usage_data.get("output_tokens")

        if (
            isinstance(input_tokens, int)
            and isinstance(output_tokens, int)
        ):
            usage_data["total_tokens"] = (
                input_tokens + output_tokens
            )

        return usage_data

    @staticmethod
    def _extract_error_metadata(
        error: Exception,
    ) -> dict[str, Any]:
        """
        Extract safe diagnostic metadata from an Anthropic SDK error.
        """

        metadata: dict[str, Any] = {}

        request_id = getattr(error, "request_id", None)

        if request_id:
            metadata["request_id"] = request_id

        status_code = getattr(error, "status_code", None)

        if status_code is not None:
            metadata["status_code"] = status_code

        return metadata

    def get_provider_info(self) -> dict[str, Any]:
        """
        Return non-sensitive Claude provider configuration.
        """

        info = super().get_provider_info()

        info["max_output_tokens"] = self.max_output_tokens
        info["api"] = "messages"

        return info
