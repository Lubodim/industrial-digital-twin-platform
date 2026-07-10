import uuid

from django.conf import settings
from django.db import models


class MaterialCatalog(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True)
    density_kg_m3 = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    price_per_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    yield_strength_mpa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Material"
        verbose_name_plural = "Materials"

    def __str__(self):
        return f"{self.code} - {self.name}"


class TechnologyCatalog(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True)
    machine_hour_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Technology"
        verbose_name_plural = "Technologies"

    def __str__(self):
        return f"{self.code} - {self.name}"


class DigitalTwin(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    material = models.ForeignKey(
        MaterialCatalog,
        on_delete=models.PROTECT,
        related_name="digital_twins",
        null=True,
        blank=True,
    )

    technology = models.ForeignKey(
        TechnologyCatalog,
        on_delete=models.PROTECT,
        related_name="digital_twins",
        null=True,
        blank=True,
    )

    cad_file = models.FileField(
        upload_to="digital_twins/cad/",
        null=True,
        blank=True,
    )

    image_file = models.FileField(
        upload_to="digital_twins/images/",
        null=True,
        blank=True,
    )

    volume_m3 = models.DecimalField(
        max_digits=14,
        decimal_places=8,
        null=True,
        blank=True,
    )

    mass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    production_time_minutes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    energy_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    defect_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    desired_profit_margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_digital_twins",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_digital_twins",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["part_number"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.part_number} - {self.name}"


class DigitalTwinFile(models.Model):
    class FileType(models.TextChoices):
        CAD = "CAD", "CAD"
        DRAWING = "DRAWING", "Drawing"
        IMAGE = "IMAGE", "Image"
        DOCUMENT = "DOCUMENT", "Document"

    digital_twin = models.ForeignKey(
        DigitalTwin,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
    )

    file = models.FileField(upload_to="digital_twins/files/")
    description = models.CharField(max_length=255, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_twin_files",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.digital_twin} - {self.file_type}"
