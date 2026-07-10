import uuid

from django.conf import settings
from django.db import models

from digital_twins.models import DigitalTwin


class Experiment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RESEARCHING = "RESEARCHING", "Researching"
        ANALYZED = "ANALYZED", "Analyzed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    digital_twin = models.ForeignKey(
        DigitalTwin,
        on_delete=models.CASCADE,
        related_name="experiments",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    objective = models.TextField(blank=True)

    changed_parameters = models.JSONField(default=dict, blank=True)
    base_snapshot = models.JSONField(default=dict, blank=True)
    experimental_values = models.JSONField(default=dict, blank=True)
    calculated_results = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_experiments",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_experiments",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    computer_name = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["digital_twin", "created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.digital_twin.name} - {self.name}"
