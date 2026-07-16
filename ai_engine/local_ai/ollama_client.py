"""
Ollama Client

Responsible only for communication with the local Ollama server.

The client does NOT know anything about:
- Digital Twins
- Experiments
- Engineering analysis
- Django models

Its only responsibility is to send prompts to Ollama
and return the generated response.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class OllamaResponse:
    """
    Response returned by the local Ollama server.
    """

    success: bool

    model: str

    response: str

    raw_response: dict

    response_time_ms: float | None

    error: str | None = None


class OllamaClient:
    """
    Client responsible for communication with Ollama.
    """

    def __init__(self) -> None:

        self.host = os.getenv(
            "OLLAMA_HOST",
            "http://localhost:11434",
        )

        self.model = os.getenv(
            "OLLAMA_MODEL",
            "qwen3.5:9b",
        )

        self.timeout = int(
            os.getenv(
                "OLLAMA_TIMEOUT",
                "300",
            )
        )

        self.think = (
            os.getenv(
                "OLLAMA_THINK",
                "false",
            ).lower()
            == "true"
        )

    # ---------------------------------------------------------

    @property
    def generate_url(self) -> str:

        return f"{self.host}/api/generate"

    # ---------------------------------------------------------

    def is_available(self) -> bool:
        """
        Checks whether Ollama is running.
        """

        try:

            response = requests.get(
                f"{self.host}/api/tags",
                timeout=5,
            )

            return response.status_code == 200

        except requests.RequestException:

            return False

    # ---------------------------------------------------------
    def ask(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict | None = None,
    ) -> OllamaResponse:
        """
        Sends a prompt to Ollama and returns the response.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        # Disable thinking mode if requested
        if not self.think:

            payload["think"] = False

        try:

            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            return OllamaResponse(
                success=True,
                model=self.model,
                response=data.get(
                    "response",
                    "",
                ),
                raw_response=data,
                response_time_ms=data.get(
                    "total_duration",
                    0,
                )
                / 1_000_000,
            )

        except Exception as ex:

            return OllamaResponse(
                success=False,
                model=self.model,
                response="",
                raw_response={},
                response_time_ms=None,
                error=str(ex),
            )
