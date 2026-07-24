from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import Truncator

from conversation.enums import (
    ConversationStatus,
    ConversationType,
    MessageRole,
)
from conversation.models import Conversation, Message


User = get_user_model()


class ConversationService:
    """
    Управлява създаването и основните действия върху разговорите.

    View слоят не трябва директно да създава Conversation и Message,
    а да използва този service.
    """

    DEFAULT_TITLE = "New conversation"

    @classmethod
    @transaction.atomic
    def create_conversation(
        cls,
        *,
        owner: User,
        conversation_type: str = ConversationType.GLOBAL,
        title: str | None = None,
    ) -> Conversation:
        """
        Създава нов разговор.
        """

        if owner is None:
            raise ValidationError("Conversation owner is required.")

        if conversation_type not in ConversationType.values:
            raise ValidationError(
                f"Unsupported conversation type: {conversation_type}"
            )

        normalized_title = cls._normalize_title(title)

        conversation = Conversation.objects.create(
            owner=owner,
            title=normalized_title,
            conversation_type=conversation_type,
            status=ConversationStatus.ACTIVE,
        )

        return conversation

    @classmethod
    def create_global_conversation(
        cls,
        *,
        owner: User,
        title: str | None = None,
    ) -> Conversation:
        """
        Създава разговор за глобалния AI Assistant.
        """

        return cls.create_conversation(
            owner=owner,
            title=title,
            conversation_type=ConversationType.GLOBAL,
        )

    @classmethod
    def create_experiment_conversation(
        cls,
        *,
        owner: User,
        title: str | None = None,
    ) -> Conversation:
        """
        Създава разговор, предназначен за конкретен експеримент.

        Връзката с Experiment ще бъде добавена от experiments приложението.
        """

        return cls.create_conversation(
            owner=owner,
            title=title,
            conversation_type=ConversationType.EXPERIMENT,
        )

    @classmethod
    def create_research_conversation(
        cls,
        *,
        owner: User,
        title: str | None = None,
    ) -> Conversation:
        """
        Създава разговор или лог за AI Research процес.
        """

        return cls.create_conversation(
            owner=owner,
            title=title,
            conversation_type=ConversationType.RESEARCH,
        )

    @classmethod
    @transaction.atomic
    def add_message(
        cls,
        *,
        conversation: Conversation,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Добавя съобщение към активен разговор.
        """

        if conversation is None:
            raise ValidationError("Conversation is required.")

        if conversation.status != ConversationStatus.ACTIVE:
            raise ValidationError(
                "Messages can only be added to an active conversation."
            )

        if role not in MessageRole.values:
            raise ValidationError(f"Unsupported message role: {role}")

        normalized_content = cls._normalize_content(content)

        message = Message.objects.create(
            conversation=conversation,
            role=role,
            content=normalized_content,
            metadata=metadata or {},
        )

        cls._update_automatic_title(
            conversation=conversation,
            message=message,
        )

        return message

    @classmethod
    def add_engineer_message(
        cls,
        *,
        conversation: Conversation,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Добавя съобщение от инженера.
        """

        return cls.add_message(
            conversation=conversation,
            role=MessageRole.ENGINEER,
            content=content,
            metadata=metadata,
        )

    @classmethod
    def add_ai_message(
        cls,
        *,
        conversation: Conversation,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Добавя отговор от AI асистента.
        """

        return cls.add_message(
            conversation=conversation,
            role=MessageRole.AI,
            content=content,
            metadata=metadata,
        )

    @classmethod
    def add_system_message(
        cls,
        *,
        conversation: Conversation,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Добавя системно съобщение.
        """

        return cls.add_message(
            conversation=conversation,
            role=MessageRole.SYSTEM,
            content=content,
            metadata=metadata,
        )

    @staticmethod
    def rename(
        *,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """
        Променя заглавието на разговор.
        """

        normalized_title = ConversationService._normalize_title(title)

        conversation.title = normalized_title
        conversation.save(update_fields=["title", "updated_at"])

        return conversation

    @staticmethod
    def close(
        *,
        conversation: Conversation,
    ) -> Conversation:
        """
        Затваря разговор.

        След затваряне не могат да се добавят нови съобщения.
        """

        conversation.status = ConversationStatus.CLOSED
        conversation.save(update_fields=["status", "updated_at"])

        return conversation

    @staticmethod
    def archive(
        *,
        conversation: Conversation,
    ) -> Conversation:
        """
        Архивира разговор.
        """

        conversation.status = ConversationStatus.ARCHIVED
        conversation.save(update_fields=["status", "updated_at"])

        return conversation

    @staticmethod
    def reopen(
        *,
        conversation: Conversation,
    ) -> Conversation:
        """
        Активира повторно затворен или архивиран разговор.
        """

        conversation.status = ConversationStatus.ACTIVE
        conversation.save(update_fields=["status", "updated_at"])

        return conversation

    @staticmethod
    def _normalize_title(title: str | None) -> str:
        """
        Почиства и валидира заглавието.
        """

        if title is None:
            return ConversationService.DEFAULT_TITLE

        normalized_title = " ".join(title.split())

        if not normalized_title:
            return ConversationService.DEFAULT_TITLE

        return Truncator(normalized_title).chars(255)

    @staticmethod
    def _normalize_content(content: str) -> str:
        """
        Почиства и валидира съдържанието на съобщение.
        """

        if content is None:
            raise ValidationError("Message content is required.")

        normalized_content = content.strip()

        if not normalized_content:
            raise ValidationError("Message content cannot be empty.")

        return normalized_content

    @staticmethod
    def _update_automatic_title(
        *,
        conversation: Conversation,
        message: Message,
    ) -> None:
        """
        Използва първото инженерно съобщение за автоматично заглавие,
        когато разговорът все още е с началното заглавие.
        """

        if message.role != MessageRole.ENGINEER:
            return

        if conversation.title != ConversationService.DEFAULT_TITLE:
            return

        conversation.title = Truncator(message.content).chars(70)
        conversation.save(update_fields=["title", "updated_at"])
