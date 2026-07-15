from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max

from digital_twins.models import DigitalTwin


class Experiment(models.Model):
    """
    Engineering experiment performed on one digital twin.

    The original digital twin remains unchanged. The experiment stores
    its own snapshot, chat history, external research and local analysis.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CHATTING = "CHATTING", "Chatting"
        READY_FOR_ANALYSIS = (
            "READY_FOR_ANALYSIS",
            "Ready for analysis",
        )
        ANALYZING = "ANALYZING", "Analyzing"
        PROPOSALS_READY = (
            "PROPOSALS_READY",
            "Proposals ready",
        )
        PARTIALLY_APPROVED = (
            "PARTIALLY_APPROVED",
            "Partially approved",
        )
        APPROVED = "APPROVED", "Approved"
        TWIN_CREATED = "TWIN_CREATED", "Twin created"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"
        FAILED = "FAILED", "Failed"

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

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    objective = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    # Snapshot of the original twin when the experiment starts.
    # This protects the experiment history if the original twin is
    # modified later.
    base_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    # Kept from the first version of the project.
    # It can later store manually entered changes.
    changed_parameters = models.JSONField(
        default=dict,
        blank=True,
    )

    # Alternative values entered or generated during the experiment.
    experimental_values = models.JSONField(
        default=dict,
        blank=True,
    )

    # Engineering and economic calculation results.
    calculated_results = models.JSONField(
        default=dict,
        blank=True,
    )

    # Validated results returned by external AI providers.
    external_results = models.JSONField(
        default=dict,
        blank=True,
    )

    # Final structured analysis from the local AI engineer.
    local_analysis = models.JSONField(
        default=dict,
        blank=True,
    )

    # A new derived twin may be created at the end of the experiment.
    # The source twin is never replaced.
    result_twin = models.ForeignKey(
        DigitalTwin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_experiments",
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

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    analysis_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    analysis_completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def clean(self) -> None:
        """
        Validate important experiment relations and lifecycle rules.
        """

        super().clean()

        errors: dict[str, str] = {}

        if (
            self.result_twin_id is not None
            and self.result_twin_id == self.digital_twin_id
        ):
            errors["result_twin"] = (
                "The result twin must be a new derived twin, "
                "not the original digital twin."
            )

        if (
            self.status == self.Status.TWIN_CREATED
            and self.result_twin_id is None
        ):
            errors["result_twin"] = (
                "A result twin is required when the experiment "
                "status is Twin created."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def message_count(self) -> int:
        """
        Return the number of chat messages in the experiment.
        """

        if not self.pk:
            return 0

        return self.chat_messages.count()

    @property
    def engineer_message_count(self) -> int:
        """
        Return the number of questions/messages written by engineers.
        """

        if not self.pk:
            return 0

        return self.chat_messages.filter(
            role=ExperimentChatMessage.Role.ENGINEER
        ).count()

    @property
    def can_request_analysis(self) -> bool:
        """
        Analysis can start after at least one engineer question and
        one external assistant response have been saved.
        """

        if not self.pk:
            return False

        has_engineer_message = self.chat_messages.filter(
            role=ExperimentChatMessage.Role.ENGINEER
        ).exists()

        has_external_response = self.chat_messages.filter(
            role=ExperimentChatMessage.Role.ASSISTANT,
        ).exclude(
            provider=ExperimentChatMessage.Provider.LOCAL_AI,
        ).exists()

        return has_engineer_message and has_external_response

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=[
                    "digital_twin",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
        ]

    def __str__(self) -> str:
        return f"{self.digital_twin.name} - {self.name}"


class ExperimentChatMessage(models.Model):
    """
    One message in the engineering conversation of an experiment.

    The number of messages is unlimited. Their sequence preserves
    the complete conversation for later local AI analysis.
    """

    class Role(models.TextChoices):
        ENGINEER = "ENGINEER", "Engineer"
        ASSISTANT = "ASSISTANT", "Assistant"
        SYSTEM = "SYSTEM", "System"

    class Provider(models.TextChoices):
        NONE = "NONE", "None"
        OPENAI = "OPENAI", "OpenAI"
        GEMINI = "GEMINI", "Gemini"
        CLAUDE = "CLAUDE", "Claude"
        GROK = "GROK", "Grok"
        LOCAL_AI = "LOCAL_AI", "Local AI"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.NONE,
    )

    content = models.TextField()

    sequence = models.PositiveIntegerField(
        editable=False,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiment_chat_messages",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def clean(self) -> None:
        """
        Validate message role and provider combinations.
        """

        super().clean()

        errors: dict[str, str] = {}

        if not self.content or not self.content.strip():
            errors["content"] = "Message content cannot be empty."

        if (
            self.role == self.Role.ENGINEER
            and self.provider != self.Provider.NONE
        ):
            errors["provider"] = (
                "Engineer messages must not have an AI provider."
            )

        if (
            self.role == self.Role.ASSISTANT
            and self.provider == self.Provider.NONE
        ):
            errors["provider"] = (
                "Assistant messages must identify their provider."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        """
        Assign the next message sequence automatically.
        """

        if not self.sequence:
            latest_sequence = (
                ExperimentChatMessage.objects.filter(
                    experiment=self.experiment
                ).aggregate(
                    maximum=Max("sequence")
                )["maximum"]
                or 0
            )

            self.sequence = latest_sequence + 1

        self.full_clean()

        super().save(*args, **kwargs)

    class Meta:
        ordering = [
            "experiment",
            "sequence",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "experiment",
                    "sequence",
                ],
                name=(
                    "unique_experiment_chat_message_sequence"
                ),
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "experiment",
                    "sequence",
                ]
            ),
            models.Index(
                fields=[
                    "provider",
                    "created_at",
                ]
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.experiment.name} "
            f"#{self.sequence} - {self.get_role_display()}"
        )