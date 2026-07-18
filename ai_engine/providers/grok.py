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


class GrokProvider(BaseAIProvider):
    """
    Provider adapter for the xAI Grok Responses API.

    xAI exposes an OpenAI-compatible API, so the existing OpenAI
    Python SDK can be used with the xAI base URL.

    The adapter:
    - accepts the common application message format;
    - sends requests to the xAI Responses API;
    - preserves the original response text;
    - parses JSON responses;
    - validates the engineering research schema;
    - returns the common ProviderResult object.
    """

    provider_name = "GROK"

    DEFAULT_BASE_URL = "https://api.x.ai/v1"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 90,
        max_output_tokens: int = 2500,
        base_url: str = DEFAULT_BASE_URL,
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

        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError(
                "base_url must be a non-empty string."
            )

        self.max_output_tokens = max_output_tokens
        self.base_url = base_url.strip().rstrip("/")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        )

    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        """
        Send messages to Grok and return a normalized ProviderResult.
        """

        self.validate_messages(messages)

        prepared_messages = self._prepare_request(messages)

        started_at = time.perf_counter()

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prepared_messages,
                max_output_tokens=self.max_output_tokens,
                store=False,
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
                        "response_id": getattr(
                            response,
                            "id",
                            None,
                        ),
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
                        "response_id": getattr(
                            response,
                            "id",
                            None,
                        ),
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
                    "response_id": getattr(
                        response,
                        "id",
                        None,
                    ),
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
                error_message="Grok request timed out.",
                error_type="timeout",
            )

        except RateLimitError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Grok rate limit or quota was exceeded: "
                    f"{error}"
                ),
                error_type="rate_limit",
            )

        except APIConnectionError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Could not connect to the xAI API: "
                    f"{error}"
                ),
                error_type="connection",
            )

        except APIStatusError as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "xAI API returned an error with status "
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
                error_message=f"xAI SDK request error: {error}",
                error_type="xai_sdk",
            )

        except Exception as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Unexpected Grok provider error: "
                    f"{type(error).__name__}: {error}"
                ),
                error_type="unexpected",
            )

    def _prepare_request(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """
        Prepare messages for the xAI Responses API.

        Grok supports system, user, and assistant roles directly,
        so their original order can be preserved.
        """

        return [
            {
                "role": message["role"],
                "content": message["content"].strip(),
            }
            for message in messages
        ]

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
        Convert xAI usage information to a serializable dictionary.
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
        Return non-sensitive Grok provider configuration.
        """

        info = super().get_provider_info()

        info["max_output_tokens"] = self.max_output_tokens
        info["api"] = "responses"
        info["base_url"] = self.base_url

        return info
