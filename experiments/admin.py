from django.contrib import admin

from .models import Experiment


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "digital_twin",
        "status",
        "created_by",
        "created_at",
    )
    search_fields = ("name", "digital_twin__name", "digital_twin__part_number")
    list_filter = ("status", "created_at")
