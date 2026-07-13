import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
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

    def clean(self) -> None:
        """
        Validate the main engineering and economic parameters.
        """

        super().clean()

        errors = {}

        non_negative_fields = {
            "volume_m3": self.volume_m3,
            "mass_kg": self.mass_kg,
            "production_time_minutes": self.production_time_minutes,
            "labor_cost": self.labor_cost,
            "energy_cost": self.energy_cost,
            "defect_rate_percent": self.defect_rate_percent,
            "desired_profit_margin_percent": (
                self.desired_profit_margin_percent
            ),
        }

        for field_name, value in non_negative_fields.items():
            if value is not None and value < 0:
                errors[field_name] = (
                    "Value cannot be negative."
                )

        if (
            self.defect_rate_percent is not None
            and self.defect_rate_percent > 100
        ):
            errors["defect_rate_percent"] = (
                "Defect rate cannot be greater than 100 percent."
            )

        if (
            self.desired_profit_margin_percent is not None
            and self.desired_profit_margin_percent >= 100
        ):
            errors["desired_profit_margin_percent"] = (
                "Profit margin must be lower than 100 percent."
            )

        if (
            self.mass_kg is not None
            and self.mass_kg > 0
            and self.material is None
        ):
            errors["material"] = (
                "A material is required when mass is specified."
            )

        if (
            self.production_time_minutes is not None
            and self.production_time_minutes > 0
            and self.technology is None
        ):
            errors["technology"] = (
                "A production technology is required when "
                "production time is specified."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def calculated_mass_kg(self) -> Decimal | None:
        """
        Calculate mass from volume and material density.

        The stored mass value remains authoritative when it is entered
        explicitly. This property provides an engineering estimate.
        """

        if (
            self.volume_m3 is None
            or self.material is None
            or self.material.density_kg_m3 is None
        ):
            return None

        return (
            Decimal(self.volume_m3)
            * Decimal(self.material.density_kg_m3)
        ).quantize(Decimal("0.001"))

    @property
    def effective_mass_kg(self) -> Decimal | None:
        """
        Return a positive manually entered mass or calculate it
        from volume and material density.
        """

        if (
            self.mass_kg is not None
            and Decimal(self.mass_kg) > Decimal("0")
        ):
            return Decimal(self.mass_kg)

        return self.calculated_mass_kg

    @property
    def estimated_material_cost(self) -> Decimal | None:
        """
        Estimate material cost from mass and price per kilogram.
        """

        mass = self.effective_mass_kg

        if (
            mass is None
            or self.material is None
            or self.material.price_per_kg is None
        ):
            return None

        return (
            mass * Decimal(self.material.price_per_kg)
        ).quantize(Decimal("0.01"))

    @property
    def estimated_machine_cost(self) -> Decimal | None:
        """
        Estimate machine cost from production time and hourly rate.
        """

        if (
            self.technology is None
            or self.technology.machine_hour_rate is None
            or self.production_time_minutes is None
        ):
            return None

        production_hours = (
            Decimal(self.production_time_minutes)
            / Decimal("60")
        )

        return (
            production_hours
            * Decimal(self.technology.machine_hour_rate)
        ).quantize(Decimal("0.01"))

    @property
    def estimated_direct_cost(self) -> Decimal:
        """
        Calculate material, machine, labor and energy costs.
        """

        material_cost = (
            self.estimated_material_cost
            or Decimal("0.00")
        )

        machine_cost = (
            self.estimated_machine_cost
            or Decimal("0.00")
        )

        labor_cost = Decimal(
            self.labor_cost or 0
        )

        energy_cost = Decimal(
            self.energy_cost or 0
        )

        return (
            material_cost
            + machine_cost
            + labor_cost
            + energy_cost
        ).quantize(Decimal("0.01"))

    @property
    def estimated_defect_cost(self) -> Decimal:
        """
        Estimate the cost impact of the expected defect rate.
        """

        defect_rate = Decimal(
            self.defect_rate_percent or 0
        ) / Decimal("100")

        return (
            self.estimated_direct_cost
            * defect_rate
        ).quantize(Decimal("0.01"))

    @property
    def estimated_total_cost(self) -> Decimal:
        """
        Return direct cost plus expected defect cost.
        """

        return (
            self.estimated_direct_cost
            + self.estimated_defect_cost
        ).quantize(Decimal("0.01"))

    @property
    def estimated_selling_price(self) -> Decimal | None:
        """
        Calculate a selling price from the desired profit margin.

        Margin is treated as profit divided by selling price.
        """

        margin = Decimal(
            self.desired_profit_margin_percent or 0
        ) / Decimal("100")

        if margin >= Decimal("1"):
            return None

        denominator = Decimal("1") - margin

        return (
            self.estimated_total_cost / denominator
        ).quantize(Decimal("0.01"))

    @property
    def estimated_profit(self) -> Decimal | None:
        """
        Calculate estimated profit per manufactured unit.
        """

        selling_price = self.estimated_selling_price

        if selling_price is None:
            return None

        return (
            selling_price
            - self.estimated_total_cost
        ).quantize(Decimal("0.01"))


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
