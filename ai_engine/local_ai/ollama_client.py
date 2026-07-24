"""
Low-level client for communication with the local Ollama server.

This module knows nothing about Django models, digital twins,
experiments or engineering proposals. Its only responsibility is
communication with Ollama and normalization of the response.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Mapping

import requests
from dotenv import load_dotenv


load_dotenv()


def _read_boolean_environment(
    variable_name: str,
    default: bool,
) -> bool:
    """
    Read a boolean environment variable safely.
    """

    default_text = "true" if default else "false"

    value = os.getenv(
        variable_name,
        default_text,
    ).strip().lower()

    return value in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(slots=True)
class OllamaResponse:
    """
    Normalized response returned by the local Ollama server.
    """

    success: bool
    model: str
    response: str
    raw_response: dict[str, Any]

    response_time_ms: float | None = None
    load_time_ms: float | None = None

    prompt_token_count: int | None = None
    output_token_count: int | None = None

    thinking: str = ""
    structured_response: dict[str, Any] = field(
        default_factory=dict
    )

    error: str | None = None

    @property
    def has_structured_response(self) -> bool:
        """
        Return True when valid structured JSON was parsed.
        """

        return bool(self.structured_response)


class OllamaClient:
    """
    HTTP client for the local Ollama API.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        think: bool | None = None,
        keep_alive: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self.host = (
            host
            or os.getenv(
                "OLLAMA_HOST",
                "http://localhost:11434",
            )
        ).rstrip("/")

        self.model = (
            model
            or os.getenv(
                "OLLAMA_ANALYZER_MODEL",
                "qwen3.5:9b",
            )
        ).strip()

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else int(
                os.getenv(
                    "OLLAMA_TIMEOUT",
                    "300",
                )
            )
        )

        self.think = (
            think
            if think is not None
            else _read_boolean_environment(
                "OLLAMA_THINK",
                False,
            )
        )

        self.keep_alive = (
            keep_alive
            or os.getenv(
                "OLLAMA_KEEP_ALIVE",
                "10m",
            )
        )

        self.temperature = (
            temperature
            if temperature is not None
            else float(
                os.getenv(
                    "OLLAMA_TEMPERATURE",
                    "0.1",
                )
            )
        )

        if not self.model:
            raise ValueError(
                "OLLAMA_MODEL cannot be empty."
            )

        if self.timeout_seconds <= 0:
            raise ValueError(
                "OLLAMA_TIMEOUT must be greater than zero."
            )

    @property
    def generate_url(self) -> str:
        return f"{self.host}/api/generate"

    @property
    def tags_url(self) -> str:
        return f"{self.host}/api/tags"

    def is_available(self) -> bool:
        """
        Check whether the Ollama server is reachable.
        """

        try:
            response = requests.get(
                self.tags_url,
                timeout=5,
            )

            return response.status_code == 200

        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        """
        Return the names of locally installed Ollama models.
        """

        try:
            response = requests.get(
                self.tags_url,
                timeout=10,
            )

            response.raise_for_status()

            data = response.json()

        except (
            requests.RequestException,
            ValueError,
        ):
            return []

        models = data.get("models", [])

        if not isinstance(models, list):
            return []

        return [
            str(model.get("name", "")).strip()
            for model in models
            if isinstance(model, dict)
            and str(model.get("name", "")).strip()
        ]

    def is_model_available(
        self,
        model: str | None = None,
    ) -> bool:
        """
        Check whether the configured model is installed locally.
        """

        requested_model = (
            model or self.model
        ).strip()

        installed_models = self.list_models()

        return requested_model in installed_models

    def ask(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: Mapping[str, Any] | None = None,
        model: str | None = None,
        think: bool | None = None,
        temperature: float | None = None,
        keep_alive: str | None = None,
        additional_options: Mapping[str, Any] | None = None,
    ) -> OllamaResponse:
        """
        Send one non-streaming generation request to Ollama.

        When response_schema is supplied, Ollama is instructed to
        return JSON matching that schema. The parsed JSON is returned
        in OllamaResponse.structured_response.
        """

        cleaned_prompt = str(
            prompt or ""
        ).strip()

        if not cleaned_prompt:
            return self._error_response(
                model=model or self.model,
                error="Prompt cannot be empty.",
            )

        requested_model = (
            model or self.model
        ).strip()

        requested_think = (
            self.think
            if think is None
            else think
        )

        requested_temperature = (
            self.temperature
            if temperature is None
            else temperature
        )

        options: dict[str, Any] = {
            "temperature": requested_temperature,
            "num_predict": 220,
            "top_p": 0.8,
            "repeat_penalty": 1.05,
        }

        if additional_options:
            options.update(
                dict(additional_options)
            )

        payload: dict[str, Any] = {
            "model": requested_model,
            "prompt": cleaned_prompt,
            "stream": False,
            "think": requested_think,
            "keep_alive": (
                keep_alive
                or self.keep_alive
            ),
            "options": options,
        }

        cleaned_system_prompt = str(
            system_prompt or ""
        ).strip()

        if cleaned_system_prompt:
            payload["system"] = (
                cleaned_system_prompt
            )

        if response_schema is not None:
            payload["format"] = dict(
                response_schema
            )

        try:
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=self.timeout_seconds,
            )

            response.raise_for_status()

            data = response.json()

        except requests.Timeout:
            return self._error_response(
                model=requested_model,
                error=(
                    "Ollama request timed out after "
                    f"{self.timeout_seconds} seconds."
                ),
            )

        except requests.ConnectionError:
            return self._error_response(
                model=requested_model,
                error=(
                    "Cannot connect to the local Ollama "
                    f"server at {self.host}."
                ),
            )

        except requests.RequestException as exc:
            return self._error_response(
                model=requested_model,
                error=(
                    "Ollama HTTP request failed: "
                    f"{exc}"
                ),
            )

        except ValueError as exc:
            return self._error_response(
                model=requested_model,
                error=(
                    "Ollama returned invalid JSON: "
                    f"{exc}"
                ),
            )

        response_text = str(
            data.get(
                "response",
                "",
            )
        ).strip()

        structured_response: dict[str, Any] = {}

        if response_schema is not None:
            try:
                parsed_response = json.loads(
                    response_text
                )

                if not isinstance(
                    parsed_response,
                    dict,
                ):
                    raise ValueError(
                        "Structured response must "
                        "be a JSON object."
                    )

                structured_response = (
                    parsed_response
                )

            except (
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                return OllamaResponse(
                    success=False,
                    model=requested_model,
                    response=response_text,
                    raw_response=data,
                    response_time_ms=(
                        self._nanoseconds_to_milliseconds(
                            data.get("total_duration")
                        )
                    ),
                    load_time_ms=(
                        self._nanoseconds_to_milliseconds(
                            data.get("load_duration")
                        )
                    ),
                    prompt_token_count=(
                        self._optional_integer(
                            data.get(
                                "prompt_eval_count"
                            )
                        )
                    ),
                    output_token_count=(
                        self._optional_integer(
                            data.get("eval_count")
                        )
                    ),
                    thinking=str(
                        data.get(
                            "thinking",
                            "",
                        )
                    ),
                    error=(
                        "The model did not return valid "
                        f"structured JSON: {exc}"
                    ),
                )

        return OllamaResponse(
            success=True,
            model=str(
                data.get(
                    "model",
                    requested_model,
                )
            ),
            response=response_text,
            raw_response=data,
            response_time_ms=(
                self._nanoseconds_to_milliseconds(
                    data.get("total_duration")
                )
            ),
            load_time_ms=(
                self._nanoseconds_to_milliseconds(
                    data.get("load_duration")
                )
            ),
            prompt_token_count=(
                self._optional_integer(
                    data.get(
                        "prompt_eval_count"
                    )
                )
            ),
            output_token_count=(
                self._optional_integer(
                    data.get("eval_count")
                )
            ),
            thinking=str(
                data.get(
                    "thinking",
                    "",
                )
            ),
            structured_response=(
                structured_response
            ),
            error=None,
        )

    @staticmethod
    def _nanoseconds_to_milliseconds(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value) / 1_000_000

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _optional_integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _error_response(
        *,
        model: str,
        error: str,
    ) -> OllamaResponse:
        return OllamaResponse(
            success=False,
            model=model,
            response="",
            raw_response={},
            response_time_ms=None,
            load_time_ms=None,
            prompt_token_count=None,
            output_token_count=None,
            thinking="",
            structured_response={},
            error=error,
        )
