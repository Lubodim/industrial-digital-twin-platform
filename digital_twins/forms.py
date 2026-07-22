"""
Forms for creating, editing and filtering Digital Twins.
"""

from __future__ import annotations

from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from digital_twins.models import (
    DigitalTwin,
    MaterialCatalog,
    TechnologyCatalog,
)


class DigitalTwinForm(forms.ModelForm):
    """
    Create and edit a Digital Twin.

    The form performs user-facing normalization and validation, while
    the model remains responsible for the core engineering rules.
    """

    class Meta:
        model = DigitalTwin

        fields = (
            "name",
            "part_number",
            "description",
            "material",
            "technology",
            "cad_file",
            "image_file",
            "volume_m3",
            "mass_kg",
            "production_time_minutes",
            "labor_cost",
            "energy_cost",
            "defect_rate_percent",
            "desired_profit_margin_percent",
            "is_active",
        )

        labels = {
            "name": "Наименование",
            "part_number": "Номер на изделието",
            "description": "Описание",
            "material": "Материал",
            "technology": "Технология",
            "cad_file": "CAD файл",
            "image_file": "Изображение",
            "volume_m3": "Обем, m³",
            "mass_kg": "Маса, kg",
            "production_time_minutes": (
                "Производствено време, min"
            ),
            "labor_cost": "Разход за труд",
            "energy_cost": "Разход за енергия",
            "defect_rate_percent": "Процент брак",
            "desired_profit_margin_percent": (
                "Желан марж на печалба"
            ),
            "is_active": "Активен",
        }

        help_texts = {
            "part_number": (
                "Уникален вътрешен номер на изделието."
            ),
            "volume_m3": (
                "Използва се за автоматично изчисляване "
                "на масата, когато е известна плътността."
            ),
            "mass_kg": (
                "Когато е въведена положителна стойност, "
                "тя има предимство пред изчислената маса."
            ),
            "defect_rate_percent": (
                "Допустима стойност между 0 и 100."
            ),
            "desired_profit_margin_percent": (
                "Допустима стойност от 0 до под 100."
            ),
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: Редукторен вал",
                }
            ),
            "part_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Например: SHAFT-001",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "material": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "technology": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "cad_file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".step,.stp,.iges,.igs,.stl,"
                        ".obj,.dxf,.dwg,.zip"
                    ),
                }
            ),
            "image_file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "volume_m3": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.00000001",
                    "min": "0",
                }
            ),
            "mass_kg": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.001",
                    "min": "0",
                }
            ),
            "production_time_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "labor_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "energy_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "defect_rate_percent": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "desired_profit_margin_percent": (
                forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "step": "0.01",
                        "min": "0",
                        "max": "99.99",
                    }
                )
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    CAD_FILE_EXTENSIONS = {
        ".step",
        ".stp",
        ".iges",
        ".igs",
        ".stl",
        ".obj",
        ".dxf",
        ".dwg",
        ".zip",
    }

    IMAGE_FILE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
    }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["material"].queryset = (
            MaterialCatalog.objects.filter(
                is_active=True
            ).order_by("name")
        )

        self.fields["technology"].queryset = (
            TechnologyCatalog.objects.filter(
                is_active=True
            ).order_by("name")
        )

        self.fields["material"].empty_label = (
            "Изберете материал"
        )

        self.fields["technology"].empty_label = (
            "Изберете технология"
        )

        self.fields["is_active"].initial = True

    def clean_name(self) -> str:
        """
        Normalize the Digital Twin name.
        """

        name = str(
            self.cleaned_data.get("name", "")
        ).strip()

        if not name:
            raise ValidationError(
                "Наименованието е задължително."
            )

        return " ".join(name.split())

    def clean_part_number(self) -> str:
        """
        Normalize and validate a case-insensitive part number.
        """

        part_number = str(
            self.cleaned_data.get(
                "part_number",
                "",
            )
        ).strip().upper()

        part_number = " ".join(
            part_number.split()
        )

        if not part_number:
            raise ValidationError(
                "Номерът на изделието е задължителен."
            )

        queryset = DigitalTwin.objects.filter(
            part_number__iexact=part_number
        )

        if self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise ValidationError(
                "Вече съществува цифров двойник "
                "с този номер на изделието."
            )

        return part_number

    def clean_cad_file(self):
        """
        Validate the CAD file extension.
        """

        cad_file = self.cleaned_data.get(
            "cad_file"
        )

        if not cad_file:
            return cad_file

        extension = Path(
            cad_file.name
        ).suffix.lower()

        if extension not in self.CAD_FILE_EXTENSIONS:
            raise ValidationError(
                "Неподдържан CAD файлов формат."
            )

        return cad_file

    def clean_image_file(self):
        """
        Validate the image extension.
        """

        image_file = self.cleaned_data.get(
            "image_file"
        )

        if not image_file:
            return image_file

        extension = Path(
            image_file.name
        ).suffix.lower()

        if extension not in self.IMAGE_FILE_EXTENSIONS:
            raise ValidationError(
                "Неподдържан формат на изображението."
            )

        return image_file

    def clean(self):
        """
        Add form-level engineering validation.

        The model's clean() method will also run automatically during
        ModelForm validation.
        """

        cleaned_data = super().clean()

        mass_kg = cleaned_data.get(
            "mass_kg"
        )

        material = cleaned_data.get(
            "material"
        )

        production_time = cleaned_data.get(
            "production_time_minutes"
        )

        technology = cleaned_data.get(
            "technology"
        )

        if (
            mass_kg is not None
            and mass_kg > 0
            and material is None
        ):
            self.add_error(
                "material",
                (
                    "Изберете материал, когато "
                    "е въведена маса."
                ),
            )

        if (
            production_time is not None
            and production_time > 0
            and technology is None
        ):
            self.add_error(
                "technology",
                (
                    "Изберете технология, когато "
                    "е въведено производствено време."
                ),
            )

        return cleaned_data


class DigitalTwinFilterForm(forms.Form):
    """
    Search and filter the Digital Twin list.
    """

    query = forms.CharField(
        required=False,
        label="Търсене",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Име, номер на изделие или описание"
                ),
            }
        ),
    )

    material = forms.ModelChoiceField(
        queryset=MaterialCatalog.objects.none(),
        required=False,
        label="Материал",
        empty_label="Всички материали",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    technology = forms.ModelChoiceField(
        queryset=TechnologyCatalog.objects.none(),
        required=False,
        label="Технология",
        empty_label="Всички технологии",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=(
            ("", "Всички"),
            ("active", "Активни"),
            ("inactive", "Неактивни"),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["material"].queryset = (
            MaterialCatalog.objects.filter(
                is_active=True
            ).order_by("name")
        )

        self.fields["technology"].queryset = (
            TechnologyCatalog.objects.filter(
                is_active=True
            ).order_by("name")
        )


class DigitalTwinDeleteForm(forms.Form):
    """
    Confirmation form for deleting or deactivating a Digital Twin.
    """

    confirmation = forms.BooleanField(
        required=True,
        label=(
            "Потвърждавам изтриването "
            "на цифровия двойник"
        ),
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )
