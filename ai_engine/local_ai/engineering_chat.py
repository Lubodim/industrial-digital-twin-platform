from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from ai_engine.local_ai.chat_prompt import (
    build_assistant_system_prompt,
)
from ai_engine.local_ai.ollama_client import (
    OllamaClient,
)


@dataclass(slots=True)
class AssistantResponse:
    success: bool
    text: str
    model: str
    response_time_ms: float | None = None
    error_message: str | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "text": self.text,
            "model": self.model,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }

class EngineeringAssistant:
    """
    Local UI assistant powered by Ollama.
    """

    def __init__(self) -> None:

        self.client = OllamaClient(
            host=settings.OLLAMA_HOST,
            model=settings.OLLAMA_ASSISTANT_MODEL,
            timeout_seconds=settings.OLLAMA_ASSISTANT_TIMEOUT,
            think=settings.OLLAMA_THINK,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
            temperature=settings.OLLAMA_TEMPERATURE,
        )

    def ask(
        self,
        user_message: str,
        *,
        page_title: str | None = None,
        page_name: str | None = None,
        page_url: str | None = None,
        page_description: str | None = None,
        selected_object: str | None = None,
        available_actions: list[str] | None = None,
        context: dict | None = None,
    ) -> AssistantResponse:

        system_prompt = build_assistant_system_prompt(
            page_title=page_title,
            page_name=page_name,
            page_url=page_url,
            page_description=page_description,
            selected_object=selected_object,
            available_actions=available_actions,
            context=context,
        )

        response = self.client.ask(
            prompt=user_message,
            system_prompt=system_prompt,
            model=settings.OLLAMA_ASSISTANT_MODEL,
        )

        return AssistantResponse(
            success=response.success,
            text=response.response,
            model=response.model,
            response_time_ms=response.response_time_ms,
            error_message=response.error,
            metadata={
                "provider": "OLLAMA_LOCAL",
            },
        )
