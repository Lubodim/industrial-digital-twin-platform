from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0

    readonly_fields = (
        "role",
        "content",
        "metadata",
        "created_at",
    )

    can_delete = False

    ordering = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "owner",
        "conversation_type",
        "status",
        "updated_at",
    )

    list_filter = (
        "conversation_type",
        "status",
        "created_at",
    )

    search_fields = (
        "title",
        "owner__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    inlines = [
        MessageInline,
    ]

    ordering = (
        "-updated_at",
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    list_display = (
        "conversation",
        "role",
        "short_content",
        "created_at",
    )

    list_filter = (
        "role",
        "created_at",
    )

    search_fields = (
        "content",
        "conversation__title",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    def short_content(self, obj):
        if len(obj.content) <= 80:
            return obj.content
        return obj.content[:80] + "..."

    short_content.short_description = "Message"
