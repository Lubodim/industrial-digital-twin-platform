from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from conversation.enums import (
    ConversationStatus,
    ConversationType,
    MessageRole,
)
from conversation.models import Conversation
from conversation.services.chat_service import GlobalChatService
from conversation.services.conversation_service import ConversationService


def _get_user_global_conversations(request: HttpRequest):
    """
    Връща само глобалните разговори на текущия потребител.
    """

    return (
        Conversation.objects
        .filter(
            owner=request.user,
            conversation_type=ConversationType.GLOBAL,
        )
        .order_by("-updated_at")
    )


def _get_user_conversation(
    *,
    request: HttpRequest,
    conversation_id,
) -> Conversation:
    """
    Зарежда глобален разговор, който принадлежи на текущия потребител.
    """

    return get_object_or_404(
        Conversation.objects.prefetch_related("messages"),
        id=conversation_id,
        owner=request.user,
        conversation_type=ConversationType.GLOBAL,
    )


@login_required
@require_GET
def global_chat_view(
    request: HttpRequest,
    conversation_id=None,
) -> HttpResponse:
    """
    Показва отделния прозорец на глобалния AI асистент.
    """

    conversations = _get_user_global_conversations(request)

    active_conversation = None

    if conversation_id is not None:
        active_conversation = _get_user_conversation(
            request=request,
            conversation_id=conversation_id,
        )

    elif conversations.exists():
        active_conversation = conversations.first()

    else:
        active_conversation = (
            ConversationService.create_global_conversation(
                owner=request.user,
            )
        )

        return redirect(
            "conversation:global_chat_detail",
            conversation_id=active_conversation.id,
        )

    context = {
        "page_title": "Global AI Assistant",
        "conversations": conversations,
        "active_conversation": active_conversation,
        "message_roles": MessageRole,
        "conversation_statuses": ConversationStatus,
    }

    return render(
        request,
        "conversation/global_chat.html",
        context,
    )


@login_required
@require_POST
def create_global_conversation_view(
    request: HttpRequest,
) -> HttpResponse:
    """
    Създава нов глобален разговор.
    """

    conversation = ConversationService.create_global_conversation(
        owner=request.user,
    )

    return redirect(
        "conversation:global_chat_detail",
        conversation_id=conversation.id,
    )


@login_required
@require_POST
def send_global_message_view(
    request: HttpRequest,
    conversation_id,
) -> JsonResponse:
    """
    Приема съобщение от интерфейса и го изпраща към Gemini.
    """

    conversation = _get_user_conversation(
        request=request,
        conversation_id=conversation_id,
    )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Невалидни данни в заявката.",
            },
            status=400,
        )

    content = str(payload.get("content", "")).strip()

    if not content:
        return JsonResponse(
            {
                "success": False,
                "error": "Съобщението не може да бъде празно.",
            },
            status=400,
        )

    try:
        response = GlobalChatService.send_message(
            conversation=conversation,
            content=content,
        )

    except ValidationError as error:
        return JsonResponse(
            {
                "success": False,
                "error": "; ".join(error.messages),
            },
            status=400,
        )

    except Exception as error:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Възникна неочаквана грешка при обработката "
                    f"на съобщението: {error}"
                ),
            },
            status=500,
        )

    conversation.refresh_from_db()

    latest_message = (
        conversation.messages
        .order_by("-created_at", "-id")
        .first()
    )

    return JsonResponse(
        {
            "success": response.success,
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "status": conversation.status,
            },
            "message": {
                "role": latest_message.role if latest_message else "",
                "content": latest_message.content if latest_message else "",
                "created_at": (
                    latest_message.created_at.isoformat()
                    if latest_message
                    else None
                ),
            },
            "provider_response": response.to_dict(),
        },
        status=200,
    )
