from django.conf import settings
from django.db import models

from experiments.models import Experiment


class ExternalResearchRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        PARTIAL = "PARTIAL", "Partial"
        FAILED = "FAILED", "Failed"

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="research_requests",
    )

    sanitized_query = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="external_research_requests",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Research request #{self.pk} for {self.experiment}"


class ProviderResponse(models.Model):
    class Provider(models.TextChoices):
        OPENAI = "OPENAI", "OpenAI"
        ANTHROPIC = "ANTHROPIC", "Anthropic Claude"
        GEMINI = "GEMINI", "Google Gemini"
        GROK = "GROK", "xAI Grok"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    research_request = models.ForeignKey(
        ExternalResearchRequest,
        on_delete=models.CASCADE,
        related_name="provider_responses",
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
    )

    model_name = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    raw_response = models.TextField(blank=True)
    structured_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["research_request", "provider"],
                name="unique_provider_per_research_request",
            )
        ]

    def __str__(self):
        return f"{self.provider} - {self.research_request_id}"


class ValidatedResearchPackage(models.Model):
    class ValidationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VALID = "VALID", "Valid"
        INVALID = "INVALID", "Invalid"

    research_request = models.OneToOneField(
        ExternalResearchRequest,
        on_delete=models.CASCADE,
        related_name="validated_package",
    )

    validated_data = models.JSONField(default=dict, blank=True)
    validation_status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
    )

    validation_errors = models.JSONField(default=list, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Validated package for request #{self.research_request_id}"


class InternalAnalysis(models.Model):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="internal_analyses",
    )

    research_package = models.ForeignKey(
        ValidatedResearchPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_analyses",
    )

    local_model_name = models.CharField(max_length=100, blank=True)

    twin_snapshot = models.JSONField(default=dict, blank=True)
    base_calculations = models.JSONField(default=dict, blank=True)
    experimental_calculations = models.JSONField(default=dict, blank=True)
    provider_comparison = models.JSONField(default=dict, blank=True)

    recommendation = models.TextField(blank=True)
    risks = models.JSONField(default=list, blank=True)

    confidence_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_internal_analyses",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Internal analysis for {self.experiment}"
