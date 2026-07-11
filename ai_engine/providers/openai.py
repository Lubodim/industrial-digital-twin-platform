from __future__ import annotations

import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from ai_engine.parsers.json_parser import parse_json_response
from ai_engine.providers.base import BaseAIProvider, ProviderResult
from ai_engine.validators import validate_external_research_result


class OpenAIProvider(BaseAIProvider):
    """
    Provider adapter for the OpenAI Responses API.

    The adapter:
    - accepts the common message format used by the application;
    - sends the request through the OpenAI SDK;
    - preserves the original response text;
    - parses the returned JSON;
    - validates and normalizes the engineering research schema;
    - returns a common ProviderResult object.
    """

    provider_name = "OPENAI"

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

        self.client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
        )

    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        """
        Send messages to OpenAI and return a normalized ProviderResult.
        """

        self.validate_messages(messages)

        instructions, input_messages = self._prepare_request(messages)

        started_at = time.perf_counter()

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions or None,
                input=input_messages,
                max_output_tokens=self.max_output_tokens,
                reasoning={"effort": "low",},
            )

            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            raw_response = response.output_text or ""

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
                        "response_id": getattr(response, "id", None),
                        "response_status": getattr(
                            response,
                            "status",
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
                        "response_id": getattr(response, "id", None),
                        "response_status": getattr(
                            response,
                            "status",
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
                    "response_id": getattr(response, "id", None),
                    "response_status": getattr(
                        response,
                        "status",
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
                error_message="OpenAI request timed out.",
                error_type="timeout",
            )

        except RateLimitError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "OpenAI rate limit or quota was exceeded: "
                    f"{error}"
                ),
                error_type="rate_limit",
            )

        except APIConnectionError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Could not connect to the OpenAI API: "
                    f"{error}"
                ),
                error_type="connection",
            )

        except APIStatusError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "OpenAI API returned an error with status "
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

        except OpenAIError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=f"OpenAI SDK error: {error}",
                error_type="openai_sdk",
            )

        except Exception as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Unexpected OpenAI provider error: "
                    f"{type(error).__name__}: {error}"
                ),
                error_type="unexpected",
            )

    def _prepare_request(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """
        Separate system instructions from conversation input.

        The Responses API accepts the system instructions separately,
        while the remaining messages are sent as input.
        """

        instruction_parts: list[str] = []
        input_messages: list[dict[str, str]] = []

        for message in messages:
            role = message["role"]
            content = message["content"].strip()

            if role == "system":
                instruction_parts.append(content)
                continue

            input_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        if not input_messages:
            raise ValueError(
                "At least one user or assistant message is required."
            )

        instructions = "\n\n".join(instruction_parts)

        return instructions, input_messages

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

        result_metadata = {
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
        Return the actual response model when available.
        """

        response_model = getattr(response, "model", None)

        if isinstance(response_model, str) and response_model:
            return response_model

        return self.model

    def _extract_usage(self, response: Any) -> dict[str, Any]:
        """
        Convert OpenAI usage information to a serializable dictionary.
        """

        usage = getattr(response, "usage", None)

        if usage is None:
            return {}

        if hasattr(usage, "model_dump"):
            return usage.model_dump()

        if isinstance(usage, dict):
            return usage

        return {
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
            "total_tokens": getattr(
                usage,
                "total_tokens",
                None,
            ),
        }

    def get_provider_info(self) -> dict[str, Any]:
        """
        Return non-sensitive OpenAI provider configuration.
        """

        info = super().get_provider_info()

        info["max_output_tokens"] = self.max_output_tokens
        info["api"] = "responses"

        return info