from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import errors, types


DEFAULT_SYSTEM_INSTRUCTION = """
You are the global engineering assistant of an industrial digital twin
platform.

Your primary user is an engineer working with:
- digital twins;
- industrial robotics;
- manufacturing processes;
- materials;
- production technologies;
- experiments;
- quality risks;
- production risks;
- cost analysis;
- engineering documentation.

Rules:
1. Answer clearly, technically, and practically.
2. Use Bulgarian when the engineer writes in Bulgarian.
3. Use English when the engineer writes in English.
4. Distinguish confirmed facts from assumptions.
5. Do not invent measurements, standards, material properties, prices,
   experimental results, or database records.
6. When information is missing, explain what additional data is needed.
7. Do not claim that you accessed the platform database unless explicit
   context has been supplied to you.
8. Do not return JSON unless the engineer explicitly requests JSON.
9. Prefer structured but readable explanations.
10. Treat all supplied industrial information as confidential.
""".strip()


@dataclass
class GeminiChatResponse:
    """
    Standard response returned by the global Gemini assistant.
    """

    success: bool
    text: str = ""
    model: str = ""
    response_time_ms: int | None = None
    error_message: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result to a serializable dictionary.
        """

        return {
            "success": self.success,
            "text": self.text,
            "model": self.model,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "usage": self.usage,
            "metadata": self.metadata,
        }


class GeminiGlobalAssistant:
    """
    Global conversational assistant for engineers.

    This class is intentionally separate from GeminiProvider.

    GeminiProvider:
        - structured engineering research;
        - JSON output;
        - schema validation;
        - ProviderResult.

    GeminiGlobalAssistant:
        - natural conversation;
        - plain-text output;
        - multi-turn chat history;
        - GeminiChatResponse.
    """

    provider_name = "GEMINI_GLOBAL_CHAT"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout_seconds: int = 90,
        max_output_tokens: int = 2000,
        temperature: float = 0.3,
        system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Gemini API key is required.")

        if not isinstance(model, str) or not model.strip():
            raise ValueError("Gemini chat model is required.")

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero."
            )

        if max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be greater than zero."
            )

        if not 0.0 <= temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0.0 and 2.0."
            )

        if (
            not isinstance(system_instruction, str)
            or not system_instruction.strip()
        ):
            raise ValueError(
                "system_instruction must contain non-empty text."
            )

        self.api_key = api_key.strip()
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.system_instruction = system_instruction.strip()

        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=self.timeout_seconds * 1000,
            ),
        )

        self._chat = None
        self.start_new_chat()

    def start_new_chat(
        self,
        *,
        history: list[types.Content] | None = None,
    ) -> None:
        """
        Start a new in-memory conversation.

        The current chat history is discarded unless a new history
        collection is explicitly supplied.
        """

        self._chat = self.client.chats.create(
            model=self.model,
            history=history or [],
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                max_output_tokens=self.max_output_tokens,
                temperature=self.temperature,
            ),
        )

    def reset_chat(self) -> None:
        """
        Clear the current conversation history.
        """

        self.start_new_chat()

    def ask(
        self,
        message: str,
        *,
        digital_twin_context: str | None = None,
        experiment_context: str | None = None,
    ) -> GeminiChatResponse:
        """
        Send one message to the global engineering assistant.

        Optional digital-twin and experiment context may be included
        without claiming direct database access.
        """

        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                "message must contain non-empty text."
            )

        if self._chat is None:
            self.start_new_chat()

        prompt = self._build_prompt(
            message=message,
            digital_twin_context=digital_twin_context,
            experiment_context=experiment_context,
        )

        started_at = time.perf_counter()

        try:
            response = self._chat.send_message(prompt)

            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            response_text = self._extract_response_text(response)
            response_model = self._get_response_model(response)
            usage = self._extract_usage(response)

            if not response_text:
                return GeminiChatResponse(
                    success=False,
                    model=response_model,
                    response_time_ms=response_time_ms,
                    error_message=(
                        "Gemini returned an empty chat response."
                    ),
                    usage=usage,
                    metadata={
                        "provider": self.provider_name,
                        "stage": "response_extraction",
                        "finish_reason": self._extract_finish_reason(
                            response
                        ),
                    },
                )

            return GeminiChatResponse(
                success=True,
                text=response_text,
                model=response_model,
                response_time_ms=response_time_ms,
                usage=usage,
                metadata={
                    "provider": self.provider_name,
                    "finish_reason": self._extract_finish_reason(
                        response
                    ),
                },
            )

        except errors.APIError as error:
            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            return self._build_api_error_response(
                error=error,
                response_time_ms=response_time_ms,
            )

        except Exception as error:
            response_time_ms = round(
                (time.perf_counter() - started_at) * 1000
            )

            return GeminiChatResponse(
                success=False,
                model=self.model,
                response_time_ms=response_time_ms,
                error_message=(
                    "Unexpected Gemini global chat error: "
                    f"{type(error).__name__}: {error}"
                ),
                metadata={
                    "provider": self.provider_name,
                    "stage": "unexpected_error",
                    "error_type": type(error).__name__,
                },
            )

    def chat(
        self,
        message: str,
        *,
        digital_twin_context: str | None = None,
        experiment_context: str | None = None,
    ) -> GeminiChatResponse:
        """
        Alias for ask().
        """

        return self.ask(
            message,
            digital_twin_context=digital_twin_context,
            experiment_context=experiment_context,
        )

    def _build_prompt(
        self,
        *,
        message: str,
        digital_twin_context: str | None,
        experiment_context: str | None,
    ) -> str:
        """
        Build a prompt containing optional platform context.
        """

        prompt_parts: list[str] = []

        if digital_twin_context:
            prompt_parts.append(
                "CURRENT DIGITAL TWIN CONTEXT:\n"
                f"{digital_twin_context.strip()}"
            )

        if experiment_context:
            prompt_parts.append(
                "CURRENT EXPERIMENT CONTEXT:\n"
                f"{experiment_context.strip()}"
            )

        prompt_parts.append(
            "ENGINEER MESSAGE:\n"
            f"{message.strip()}"
        )

        return "\n\n".join(prompt_parts)

    def _build_api_error_response(
        self,
        *,
        error: errors.APIError,
        response_time_ms: int,
    ) -> GeminiChatResponse:
        """
        Convert a Gemini SDK API error into a clean chat response.
        """

        status_code = getattr(error, "code", None)
        sdk_message = getattr(error, "message", None) or str(error)

        if status_code == 429:
            public_message = (
                "Gemini Flash quota or rate limit was exceeded. "
                "Check the API project's quota and billing settings."
            )
            error_type = "rate_limit"
        elif status_code in {401, 403}:
            public_message = (
                "Gemini rejected the API credentials or access "
                "permissions."
            )
            error_type = "authentication"
        elif status_code == 404:
            public_message = (
                "The configured Gemini chat model was not found."
            )
            error_type = "model_not_found"
        elif status_code is not None:
            public_message = (
                "Gemini API returned an error with status "
                f"{status_code}."
            )
            error_type = "api_error"
        else:
            public_message = "Gemini API request failed."
            error_type = "api_error"

        return GeminiChatResponse(
            success=False,
            model=self.model,
            response_time_ms=response_time_ms,
            error_message=public_message,
            metadata={
                "provider": self.provider_name,
                "stage": "api_request",
                "error_type": error_type,
                "status_code": status_code,
                "sdk_message": sdk_message,
            },
        )

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """
        Safely extract text from a Gemini chat response.
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

    def _get_response_model(self, response: Any) -> str:
        """
        Return the model version supplied by Gemini when available.
        """

        response_model = getattr(response, "model_version", None)

        if isinstance(response_model, str) and response_model:
            return response_model

        return self.model

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, Any]:
        """
        Return serializable Gemini token usage metadata.
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
        Extract the first candidate finish reason.
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

    def get_assistant_info(self) -> dict[str, Any]:
        """
        Return non-sensitive assistant configuration.
        """

        return {
            "provider": self.provider_name,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "conversation_mode": "multi_turn",
            "response_format": "text",
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider_name!r}, "
            f"model={self.model!r})"
        )
