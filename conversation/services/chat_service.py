from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from ai_engine.local_ai.engineering_chat import (
    AssistantResponse,
    EngineeringAssistant,
)
from conversation.enums import (
    ConversationStatus,
    ConversationType,
    MessageRole,
)
from conversation.models import Conversation, Message
from conversation.services.conversation_service import (
    ConversationService,
)


class GlobalChatService:
    """
    Свързва глобалния разговор с локалния EngineeringAssistant.

    Отговорностите на service слоя са:

    1. Записване на съобщението на инженера.
    2. Зареждане на предишната история от базата данни.
    3. Изпращане на съобщението към локалния Ollama модел.
    4. Записване на AI отговора или върнатата грешка.
    """

    MAX_HISTORY_MESSAGES = 8

    @classmethod
    @transaction.atomic
    def send_message(
        cls,
        *,
        conversation: Conversation,
        content: str,
    ) -> AssistantResponse:
        """
        Изпраща съобщение в глобалния локален чат.
        """

        cls._validate_conversation(conversation)

        engineer_message = ConversationService.add_engineer_message(
            conversation=conversation,
            content=content,
        )

        try:
            assistant = EngineeringAssistant()

            prompt = cls._build_prompt(
                conversation=conversation,
                current_message=engineer_message.content,
                excluded_message_id=engineer_message.id,
            )

            response = assistant.ask(
                prompt,
                page_title="Глобален инженерeн асистент",
                page_name="global_chat",
                page_url="/conversations/",
                page_description=(
                    "Локален чат за навигация, помощ и кратки "
                    "обяснения в Industrial Digital Twin Platform."
                ),
                available_actions=[
                    "Помощ при работа с платформата",
                    "Обяснение на страници и полета",
                    "Насочване към подходяща функция",
                    "Кратки отговори за работния процес",
                ],
                context={
                    "platform": "Industrial Digital Twin Platform",
                    "assistant_role": "UI and navigation assistant",
                }
            )

        except Exception as error:
            response = AssistantResponse(
                success=False,
                text="",
                model="unknown",
                response_time_ms=None,
                error_message=(
                    "Local AI Assistant configuration error: "
                    f"{type(error).__name__}: {error}"
                ),
                metadata={
                    "provider": "OLLAMA_LOCAL",
                    "stage": "assistant_initialization",
                    "error_type": type(error).__name__,
                },
            )

        if response.success:
            cls._save_ai_response(
                conversation=conversation,
                response=response,
            )
        else:
            cls._save_error_response(
                conversation=conversation,
                response=response,
            )

        return response

    @classmethod
    def _build_prompt(
        cls,
        *,
        conversation: Conversation,
        current_message: str,
        excluded_message_id: int | None = None,
    ) -> str:
        """
        Изгражда текстов prompt с ограничена история на разговора.
        """

        history = cls._build_history_text(
            conversation=conversation,
            excluded_message_id=excluded_message_id,
        )

        sections: list[str] = []

        if history:
            sections.append(
                "Предишна история на разговора:\n"
                f"{history}"
            )

        sections.append(
            "Текущо съобщение на инженера:\n"
            f"{current_message.strip()}"
        )

        sections.append(
            "Отговори само на текущото съобщение, като използваш "
            "историята единствено за контекст."
        )

        return "\n\n".join(sections)

    @classmethod
    def _build_history_text(
        cls,
        *,
        conversation: Conversation,
        excluded_message_id: int | None = None,
    ) -> str:
        """
        Преобразува записаните съобщения в кратка текстова история.
        """

        messages = conversation.messages.order_by(
            "-created_at",
            "-id",
        )

        if excluded_message_id is not None:
            messages = messages.exclude(
                id=excluded_message_id,
            )

        messages = list(
            messages[: cls.MAX_HISTORY_MESSAGES]
        )

        messages.reverse()

        history_lines: list[str] = []

        for message in messages:
            if not message.content.strip():
                continue

            role_name = cls._map_message_role(
                message.role,
            )

            if role_name is None:
                continue

            history_lines.append(
                f"{role_name}: {message.content.strip()}"
            )

        return "\n".join(history_lines)

    @staticmethod
    def _map_message_role(
        role: str,
    ) -> str | None:
        """
        Преобразува вътрешната роля в четим етикет.
        """

        role_mapping = {
            MessageRole.ENGINEER: "Инженер",
            MessageRole.AI: "Асистент",
        }

        return role_mapping.get(role)

    @staticmethod
    def _save_ai_response(
        *,
        conversation: Conversation,
        response: AssistantResponse,
    ) -> Message:
        """
        Записва успешния локален AI отговор.
        """

        response_metadata = response.metadata or {}

        metadata: dict[str, Any] = {
            "provider": response_metadata.get(
                "provider",
                "OLLAMA_LOCAL",
            ),
            "model": response.model,
            "response_time_ms": response.response_time_ms,
            "success": True,
            **response_metadata,
        }

        return ConversationService.add_ai_message(
            conversation=conversation,
            content=response.text,
            metadata=metadata,
        )

    @staticmethod
    def _save_error_response(
        *,
        conversation: Conversation,
        response: AssistantResponse,
    ) -> Message:
        """
        Записва грешката като системно съобщение.
        """

        error_text = response.error_message or (
            "Локалният AI асистент върна неизвестна грешка."
        )

        response_metadata = response.metadata or {}

        metadata: dict[str, Any] = {
            "provider": response_metadata.get(
                "provider",
                "OLLAMA_LOCAL",
            ),
            "model": response.model,
            "response_time_ms": response.response_time_ms,
            "success": False,
            **response_metadata,
        }

        return ConversationService.add_system_message(
            conversation=conversation,
            content=error_text,
            metadata=metadata,
        )

    @staticmethod
    def _validate_conversation(
        conversation: Conversation,
    ) -> None:
        """
        Проверява дали разговорът може да използва глобалния асистент.
        """

        if conversation is None:
            raise ValidationError(
                "Conversation is required."
            )

        if (
            conversation.conversation_type
            != ConversationType.GLOBAL
        ):
            raise ValidationError(
                "GlobalChatService supports only "
                "GLOBAL conversations."
            )

        if (
            conversation.status
            != ConversationStatus.ACTIVE
        ):
            raise ValidationError(
                "The conversation must be active."
            )
