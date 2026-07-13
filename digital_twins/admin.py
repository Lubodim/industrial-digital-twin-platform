from django.contrib import admin

from .models import (
    DigitalTwin,
    DigitalTwinFile,
    MaterialCatalog,
    TechnologyCatalog,
)


@admin.register(MaterialCatalog)
class MaterialCatalogAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "density_kg_m3",
        "price_per_kg",
        "yield_strength_mpa",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "name",
    )


@admin.register(TechnologyCatalog)
class TechnologyCatalogAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "machine_hour_rate",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "description",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "name",
    )


class DigitalTwinFileInline(admin.TabularInline):
    model = DigitalTwinFile
    extra = 1

    fields = (
        "file_type",
        "file",
        "description",
        "uploaded_by",
    )


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = (
        "part_number",
        "name",
        "material",
        "technology",
        "display_effective_mass_kg",
        "display_estimated_total_cost",
        "display_estimated_selling_price",
        "created_by",
        "created_at",
        "is_active",
    )

    search_fields = (
        "part_number",
        "name",
        "description",
    )

    list_filter = (
        "material",
        "technology",
        "is_active",
        "created_at",
    )

    readonly_fields = (
        "calculated_mass_kg",
        "effective_mass_kg",
        "estimated_material_cost",
        "estimated_machine_cost",
        "estimated_direct_cost",
        "estimated_defect_cost",
        "estimated_total_cost",
        "estimated_selling_price",
        "estimated_profit",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "General information",
            {
                "fields": (
                    "name",
                    "part_number",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "Engineering data",
            {
                "fields": (
                    "material",
                    "technology",
                    "cad_file",
                    "image_file",
                    "volume_m3",
                    "mass_kg",
                    "production_time_minutes",
                )
            },
        ),
        (
            "Economic data",
            {
                "fields": (
                    "labor_cost",
                    "energy_cost",
                    "defect_rate_percent",
                    "desired_profit_margin_percent",
                )
            },
        ),
        (
            "Calculated values",
            {
                "fields": (
                    "calculated_mass_kg",
                    "effective_mass_kg",
                    "estimated_material_cost",
                    "estimated_machine_cost",
                    "estimated_direct_cost",
                    "estimated_defect_cost",
                    "estimated_total_cost",
                    "estimated_selling_price",
                    "estimated_profit",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Audit information",
            {
                "fields": (
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    inlines = (
        DigitalTwinFileInline,
    )

    ordering = (
        "name",
    )

    @admin.display(
        description="Mass, kg",
        ordering="mass_kg",
    )
    def display_effective_mass_kg(self, obj):
        return obj.effective_mass_kg

    @admin.display(description="Total cost")
    def display_estimated_total_cost(self, obj):
        return obj.estimated_total_cost

    @admin.display(description="Selling price")
    def display_estimated_selling_price(self, obj):
        return obj.estimated_selling_price

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not change and obj.created_by_id is None:
            obj.created_by = request.user

        obj.updated_by = request.user

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

        for instance in instances:
            if (
                isinstance(instance, DigitalTwinFile)
                and instance.uploaded_by_id is None
            ):
                instance.uploaded_by = request.user

            instance.save()

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        formset.save_m2m()


@admin.register(DigitalTwinFile)
class DigitalTwinFileAdmin(admin.ModelAdmin):
    list_display = (
        "digital_twin",
        "file_type",
        "description",
        "uploaded_by",
        "uploaded_at",
    )

    search_fields = (
        "digital_twin__part_number",
        "digital_twin__name",
        "description",
    )

    list_filter = (
        "file_type",
        "uploaded_at",
    )

    readonly_fields = (
        "uploaded_at",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if obj.uploaded_by_id is None:
            obj.uploaded_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )