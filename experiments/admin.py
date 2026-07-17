from django.contrib import admin

from .models import (
    Experiment,
    ExperimentChatMessage,
    ExperimentProposal,
)


class ExperimentChatMessageInline(admin.TabularInline):
    model = ExperimentChatMessage

    extra = 1

    fields = (
        "sequence",
        "role",
        "provider",
        "content",
        "created_by",
        "created_at",
    )

    readonly_fields = (
        "sequence",
        "created_at",
    )

    ordering = (
        "sequence",
    )

class ExperimentProposalInline(admin.TabularInline):
    model = ExperimentProposal
    extra = 0

    fields = (
        "sequence",
        "category",
        "title",
        "parameter_name",
        "current_value",
        "proposed_value",
        "risk_level",
        "confidence_percent",
        "status",
        "reviewed_by",
        "reviewed_at",
    )

    readonly_fields = (
        "sequence",
        "created_at",
        "updated_at",
    )

    ordering = (
        "sequence",
    )

@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "digital_twin",
        "status",
        "display_message_count",
        "created_by",
        "created_at",
        "result_twin",
    )

    search_fields = (
        "name",
        "description",
        "objective",
        "digital_twin__name",
        "digital_twin__part_number",
    )

    list_filter = (
        "status",
        "digital_twin",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "analysis_started_at",
        "analysis_completed_at",
        "approved_at",
        "completed_at",
        "display_message_count",
        "display_can_request_analysis",
    )

    fieldsets = (
        (
            "Experiment",
            {
                "fields": (
                    "digital_twin",
                    "name",
                    "description",
                    "objective",
                    "status",
                )
            },
        ),
        (
            "Experiment data",
            {
                "fields": (
                    "base_snapshot",
                    "changed_parameters",
                    "experimental_values",
                    "calculated_results",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "AI results",
            {
                "fields": (
                    "external_results",
                    "local_analysis",
                    "display_can_request_analysis",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Result",
            {
                "fields": (
                    "result_twin",
                    "approved_by",
                    "approved_at",
                    "completed_at",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_by",
                    "ip_address",
                    "computer_name",
                    "created_at",
                    "updated_at",
                    "analysis_started_at",
                    "analysis_completed_at",
                    "display_message_count",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    inlines = (
            ExperimentChatMessageInline,
            ExperimentProposalInline,
        )

    @admin.display(description="Messages")
    def display_message_count(self, obj):
        if obj is None or obj.pk is None:
            return 0

        return obj.message_count

    @admin.display(
        description="Ready for local analysis",
        boolean=True,
    )
    def display_can_request_analysis(self, obj):
        if obj is None or obj.pk is None:
            return False

        return obj.can_request_analysis

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not change and obj.created_by_id is None:
            obj.created_by = request.user

        obj.full_clean()

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def save_formset(
        self,
        request,
        form,
        formset,
        change,
    ):
        instances = formset.save(commit=False)

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        for instance in instances:
            if (
                isinstance(
                    instance,
                    ExperimentChatMessage,
                )
                and instance.created_by_id is None
            ):
                instance.created_by = request.user

            instance.save()

        formset.save_m2m()

@admin.register(ExperimentProposal)
class ExperimentProposalAdmin(admin.ModelAdmin):
    list_display = (
        "experiment",
        "sequence",
        "category",
        "title",
        "risk_level",
        "confidence_percent",
        "status",
        "reviewed_by",
        "reviewed_at",
    )

    search_fields = (
        "experiment__name",
        "experiment__digital_twin__part_number",
        "title",
        "description",
        "parameter_name",
        "reason",
    )

    list_filter = (
        "status",
        "category",
        "risk_level",
        "requires_validation",
        "created_at",
    )

    readonly_fields = (
        "sequence",
        "created_at",
        "updated_at",
    )

    ordering = (
        "experiment",
        "sequence",
    )
    
@admin.register(ExperimentChatMessage)
class ExperimentChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "experiment",
        "sequence",
        "role",
        "provider",
        "created_by",
        "created_at",
    )

    search_fields = (
        "experiment__name",
        "experiment__digital_twin__part_number",
        "content",
    )

    list_filter = (
        "role",
        "provider",
        "created_at",
    )

    readonly_fields = (
        "sequence",
        "created_at",
    )

    ordering = (
        "experiment",
        "sequence",
    )
