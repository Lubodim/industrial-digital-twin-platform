"""
Local Bulgarian translation service for AI conversation messages.

The original English content remains unchanged in the database.
Bulgarian translations are stored in a filesystem cache.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings

from ai_engine.local_ai.ollama_client import OllamaClient


class TranslationError(Exception):
    """
    Raised when a local translation cannot be completed.
    """


class BulgarianTranslationService:
    """
    Translate AI messages to Bulgarian through local Ollama.

    Translations are stored outside the database under:
    data/translations/bg/
    """

    SYSTEM_PROMPT = """
You are a precise technical translator.

Translate the supplied engineering text from English to Bulgarian.

Rules:
- Return only the Bulgarian translation.
- Do not add comments, explanations or introductory text.
- Do not shorten, summarize or reinterpret the content.
- Preserve paragraph structure and lists.
- Preserve all numbers, formulas, units and technical codes.
- Preserve material codes such as S355, AL6082 and TI6AL4V.
- Preserve CAD, CNC, API, JSON, STEP, GLB and software identifiers.
- Translate ordinary technical terminology into natural Bulgarian.
""".strip()

    def __init__(
        self,
        *,
        client: OllamaClient | None = None,
    ) -> None:
        self.client = (
            client
            or OllamaClient(
                host=settings.OLLAMA_HOST,
                model=settings.OLLAMA_ANALYZER_MODEL,
                timeout_seconds=settings.OLLAMA_ANALYZER_TIMEOUT,
                think=False,
                keep_alive=settings.OLLAMA_KEEP_ALIVE,
                temperature=0.1,
                max_output_tokens=(
                    settings.OLLAMA_ANALYZER_MAX_OUTPUT_TOKENS
                ),
            )
        )

        self.cache_directory = (
            Path(settings.BASE_DIR)
            / "data"
            / "translations"
            / "bg"
        )

        self.cache_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_cached_translation(
        self,
        *,
        message_id: Any,
        content: str,
    ) -> str:
        """
        Return a valid cached translation or an empty string.
        """

        normalized_content = self._normalize_content(
            content
        )

        if not normalized_content:
            return ""

        cache_path = self._get_cache_path(
            message_id
        )

        if not cache_path.is_file():
            return ""

        try:
            cache_data = json.loads(
                cache_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return ""

        expected_hash = self._content_hash(
            normalized_content
        )

        if cache_data.get("original_hash") != expected_hash:
            return ""

        return str(
            cache_data.get(
                "translated_text",
                "",
            )
            or ""
        ).strip()

    def translate(
        self,
        *,
        message_id: Any,
        content: str,
        force: bool = False,
    ) -> str:
        """
        Translate one message and persist the translation in cache.
        """

        normalized_content = self._normalize_content(
            content
        )

        if not normalized_content:
            raise TranslationError(
                "Текстът за превод е празен."
            )

        if not force:
            cached_translation = (
                self.get_cached_translation(
                    message_id=message_id,
                    content=normalized_content,
                )
            )

            if cached_translation:
                return cached_translation

        response = self.client.ask(
            normalized_content,
            system_prompt=self.SYSTEM_PROMPT,
            think=False,
            temperature=0.1,
            additional_options={
                "top_p": 0.8,
                "repeat_penalty": 1.05,
            },
        )

        if not response.success:
            raise TranslationError(
                response.error
                or "Локалният преводач не върна успешен отговор."
            )

        translated_text = str(
            response.response or ""
        ).strip()

        if not translated_text:
            raise TranslationError(
                "Локалният преводач върна празен текст."
            )

        self._save_translation(
            message_id=message_id,
            original_content=normalized_content,
            translated_text=translated_text,
        )

        return translated_text

    def _save_translation(
        self,
        *,
        message_id: Any,
        original_content: str,
        translated_text: str,
    ) -> None:
        """
        Save one translation atomically.
        """

        cache_path = self._get_cache_path(
            message_id
        )

        temporary_path = cache_path.with_suffix(
            ".tmp"
        )

        payload = {
            "message_id": str(message_id),
            "original_hash": self._content_hash(
                original_content
            ),
            "translated_text": translated_text,
        }

        try:
            temporary_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                cache_path
            )
        except OSError as error:
            raise TranslationError(
                "Преводът е получен, но не може да бъде "
                "записан във файловия кеш."
            ) from error

    def _get_cache_path(
        self,
        message_id: Any,
    ) -> Path:
        safe_message_id = str(
            message_id
        ).strip()

        return (
            self.cache_directory
            / f"{safe_message_id}.json"
        )

    @staticmethod
    def _normalize_content(
        content: str,
    ) -> str:
        return str(
            content or ""
        ).strip()

    @staticmethod
    def _content_hash(
        content: str,
    ) -> str:
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()