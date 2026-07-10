from django.contrib import admin

from .models import (
    ExternalResearchRequest,
    InternalAnalysis,
    ProviderResponse,
    ValidatedResearchPackage,
)


@admin.register(ExternalResearchRequest)
class ExternalResearchRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "experiment", "status", "requested_by", "created_at")
    list_filter = ("status",)


@admin.register(ProviderResponse)
class ProviderResponseAdmin(admin.ModelAdmin):
    list_display = (
        "research_request",
        "provider",
        "model_name",
        "status",
        "response_time_ms",
        "created_at",
    )
    list_filter = ("provider", "status")


@admin.register(ValidatedResearchPackage)
class ValidatedResearchPackageAdmin(admin.ModelAdmin):
    list_display = ("research_request", "validation_status", "validated_at")
    list_filter = ("validation_status",)


@admin.register(InternalAnalysis)
class InternalAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "experiment",
        "local_model_name",
        "confidence_percent",
        "created_by",
        "created_at",
    )
