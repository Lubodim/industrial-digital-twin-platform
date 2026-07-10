from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "action",
        "entity_type",
        "entity_id",
        "ip_address",
    )
    search_fields = ("entity_type", "entity_id", "user__username")
    list_filter = ("action", "created_at")
    readonly_fields = (
        "user",
        "action",
        "entity_type",
        "entity_id",
        "details",
        "ip_address",
        "computer_name",
        "user_agent",
        "created_at",
    )
