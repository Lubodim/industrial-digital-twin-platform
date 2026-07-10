from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        RESEARCH = "RESEARCH", "External research"
        ANALYZE = "ANALYZE", "Internal analysis"
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        EXPORT = "EXPORT", "Export"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100, blank=True)

    details = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    computer_name = models.CharField(
        max_length=255,
        blank=True,
    )

    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "action"]),
        ]

    def __str__(self):
        return f"{self.created_at} - {self.user} - {self.action}"
