from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import types

from ai_engine.parsers.json_parser import parse_json_response
from ai_engine.providers.base import BaseAIProvider, ProviderResult
from ai_engine.validators import validate_external_research_result


class GeminiProvider(BaseAIProvider):
    """
    Provider adapter for the Google Gemini generateContent API.

    This provider is intended for structured engineering research.
    It expects Gemini to return JSON matching the common external
    research schema used by the application.
    """

    provider_name = "GEMINI"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 90,
        max_output_tokens: int = 2500,
        temperature: float = 0.1,
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

        if not 0.0 <= temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0.0 and 2.0."
            )

        self.max_output_tokens = max_output_tokens
        self.temperature = temperature

        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=self.timeout_seconds * 1000,
            ),
        )

    def send_messages(
        self,
        messages: list[dict[str, str]],
    ) -> ProviderResult:
        """
        Send messages to Gemini and return a normalized ProviderResult.
        """

        self.validate_messages(messages)

        system_prompt, contents = self._prepare_request(messages)

        started_at = time.perf_counter()

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt or None,
                    max_output_tokens=self.max_output_tokens,
                    temperature=self.temperature,
                    response_mime_type="application/json",
                ),
            )

            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            raw_response = self._extract_response_text(response)
            usage = self._extract_usage(response)
            response_model = self._get_response_model(response)

            parse_result = parse_json_response(raw_response)

            if not parse_result.success:
                return ProviderResult(
                    provider=self.provider_name,
                    model=response_model,
                    success=False,
                    raw_response=raw_response,
                    response_time_ms=response_time_ms,
                    error_message=parse_result.error_message,
                    usage=usage,
                    metadata={
                        "stage": "json_parsing",
                        "finish_reason": self._extract_finish_reason(
                            response
                        ),
                    },
                )

            validation_result = validate_external_research_result(
                parse_result.data
            )

            if not validation_result.is_valid:
                return ProviderResult(
                    provider=self.provider_name,
                    model=response_model,
                    success=False,
                    raw_response=raw_response,
                    structured_response=(
                        validation_result.normalized_data
                    ),
                    response_time_ms=response_time_ms,
                    error_message="; ".join(
                        validation_result.errors
                    ),
                    usage=usage,
                    metadata={
                        "stage": "schema_validation",
                        "validation_errors": (
                            validation_result.errors
                        ),
                        "validation_warnings": (
                            validation_result.warnings
                        ),
                        "finish_reason": self._extract_finish_reason(
                            response
                        ),
                    },
                )

            normalized_data = validation_result.normalized_data

            normalized_data["metadata"]["provider"] = (
                self.provider_name
            )
            normalized_data["metadata"]["model"] = response_model
            normalized_data["metadata"]["status"] = "success"
            normalized_data["metadata"]["response_time_ms"] = (
                response_time_ms
            )

            return ProviderResult(
                provider=self.provider_name,
                model=response_model,
                success=True,
                raw_response=raw_response,
                structured_response=normalized_data,
                response_time_ms=response_time_ms,
                usage=usage,
                metadata={
                    "validation_warnings": (
                        validation_result.warnings
                    ),
                    "finish_reason": self._extract_finish_reason(
                        response
                    ),
                },
            )

        except Exception as error:
            return self._build_error_result(
                started_at=started_at,
                error_message=(
                    "Gemini API request failed: "
                    f"{type(error).__name__}: {error}"
                ),
                error_type=type(error).__name__,
            )

    def _prepare_request(
        self,
        messages: list[dict[str, str]],
    ) -> tuple[str, list[types.Content]]:
        """
        Convert the common message format into Gemini content objects.

        System messages are combined into a single system instruction.
        Assistant messages use Gemini's `model` role.
        """

        system_parts: list[str] = []
        contents: list[types.Content] = []

        for message in messages:
            role = message["role"]
            content = message["content"].strip()

            if role == "system":
                system_parts.append(content)
                continue

            gemini_role = (
                "model" if role == "assistant" else "user"
            )

            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[
                        types.Part.from_text(
                            text=content,
                        )
                    ],
                )
            )

        if not contents:
            raise ValueError(
                "At least one user or assistant message is required."
            )

        return "\n\n".join(system_parts), contents

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """
        Safely extract text from a Gemini response.
        """

        try:
            response_text = response.text
        except (AttributeError, ValueError):
            response_text = None

        if isinstance(response_text, str):
            return response_text.strip()

        candidates = getattr(response, "candidates", None) or []
        text_parts: list[str] = []

        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []

            for part in parts:
                part_text = getattr(part, "text", None)

                if isinstance(part_text, str):
                    text_parts.append(part_text)

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
            "stage": "api_request",
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
        Return the response model when Gemini supplies one.
        """

        response_model = getattr(response, "model_version", None)

        if isinstance(response_model, str) and response_model:
            return response_model

        return self.model

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any]:
        """
        Convert Gemini usage metadata to a serializable dictionary.
        """

        usage = getattr(response, "usage_metadata", None)

        if usage is None:
            return {}

        if hasattr(usage, "model_dump"):
            usage_data = usage.model_dump()
        elif isinstance(usage, dict):
            usage_data = dict(usage)
        else:
            usage_data = {
                "prompt_token_count": getattr(
                    usage,
                    "prompt_token_count",
                    None,
                ),
                "candidates_token_count": getattr(
                    usage,
                    "candidates_token_count",
                    None,
                ),
                "total_token_count": getattr(
                    usage,
                    "total_token_count",
                    None,
                ),
                "thoughts_token_count": getattr(
                    usage,
                    "thoughts_token_count",
                    None,
                ),
            }

        return {
            key: value
            for key, value in usage_data.items()
            if value is not None
        }

    @staticmethod
    def _extract_finish_reason(response: Any) -> str | None:
        """
        Return the first Gemini candidate finish reason.
        """

        candidates = getattr(response, "candidates", None) or []

        if not candidates:
            return None

        finish_reason = getattr(
            candidates[0],
            "finish_reason",
            None,
        )

        if finish_reason is None:
            return None

        finish_reason_value = getattr(
            finish_reason,
            "value",
            None,
        )

        if isinstance(finish_reason_value, str):
            return finish_reason_value

        return str(finish_reason)

    def get_provider_info(self) -> dict[str, Any]:
        """
        Return non-sensitive Gemini provider configuration.
        """

        info = super().get_provider_info()

        info["max_output_tokens"] = self.max_output_tokens
        info["temperature"] = self.temperature
        info["api"] = "generateContent"
        info["response_format"] = "application/json"

        return info
