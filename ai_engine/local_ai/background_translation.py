"""Background translation scheduling for experiment AI messages."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any

from django.db import close_old_connections

from ai_engine.local_ai.translation_service import (
    BulgarianTranslationService,
    TranslationError,
)


_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="bg-translator",
)

_pending_message_ids: set[str] = set()
_pending_lock = Lock()


def schedule_translation(
    *,
    message_id: Any,
    content: str,
) -> bool:
    """
    Schedule one translation without blocking the HTTP request.

    Return True when a new background task is submitted.
    """

    normalized_id = str(message_id)
    normalized_content = str(content or "").strip()

    if not normalized_content:
        return False

    service = BulgarianTranslationService()

    if service.get_cached_translation(
        message_id=normalized_id,
        content=normalized_content,
    ):
        return False

    with _pending_lock:
        if normalized_id in _pending_message_ids:
            return False

        _pending_message_ids.add(normalized_id)

    _executor.submit(
        _translate_message,
        message_id=normalized_id,
        content=normalized_content,
    )

    return True


def _translate_message(*, message_id: str, content: str, ) -> None:
    """
    Execute one translation in the background.
    """

    close_old_connections()

    try:
        BulgarianTranslationService().translate(
            message_id=message_id,
            content=content,
        )
    except TranslationError:
        # The original English response remains available.
        pass
    finally:
        close_old_connections()

        with _pending_lock:
            _pending_message_ids.discard(message_id)
