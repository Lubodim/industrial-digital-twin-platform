from django.contrib import admin

from .models import (
    DigitalTwin,
    DigitalTwinFile,
    MaterialCatalog,
    TechnologyCatalog,
)


@admin.register(MaterialCatalog)
class MaterialCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "density_kg_m3", "price_per_kg", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(TechnologyCatalog)
class TechnologyCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "machine_hour_rate", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = (
        "part_number",
        "name",
        "material",
        "technology",
        "created_by",
        "created_at",
        "is_active",
    )
    search_fields = ("part_number", "name")
    list_filter = ("material", "technology", "is_active")


@admin.register(DigitalTwinFile)
class DigitalTwinFileAdmin(admin.ModelAdmin):
    list_display = ("digital_twin", "file_type", "uploaded_by", "uploaded_at")
    list_filter = ("file_type",)
