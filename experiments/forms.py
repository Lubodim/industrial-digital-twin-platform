"""
Forms for creating, editing, filtering and deleting experiments.
"""

from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from digital_twins.models import DigitalTwin
from experiments.models import Experiment


class ExperimentForm(forms.ModelForm):
    """
    Create or edit the user-controlled Experiment fields.

    Lifecycle state, snapshots, AI results and approval information are
    intentionally excluded. They are managed by application services.
    """

    class Meta:
        model = Experiment

        fields = (
            "digital_twin",
            "name",
            "description",
            "objective",
        )

        labels = {
            "digital_twin": "Цифров двойник",
            "name": "Наименование на експеримента",
            "description": "Описание",
            "objective": "Цел на експеримента",
        }

        help_texts = {
            "digital_twin": (
                "Изберете изходния цифров двойник, върху който "
                "ще се извършва експериментът."
            ),
            "name": (
                "Кратко и ясно наименование на инженерния експеримент."
            ),
            "objective": (
                "Опишете очаквания резултат или инженерния проблем, "
                "който трябва да бъде изследван."
            ),
        }

        widgets = {
            "digital_twin": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Например: Намаляване на масата"
                    ),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Допълнително описание на експеримента"
                    ),
                }
            ),
            "objective": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Например: Намаляване на масата с 10% "
                        "без недопустима загуба на якост"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs,):
        super().__init__(*args, **kwargs)

        digital_twin_queryset = (
            DigitalTwin.objects.filter(is_active=True).order_by("name", "part_number", )
            )

        if (self.instance is not None and self.instance.pk and self.instance.digital_twin_id):
            digital_twin_queryset = (
                DigitalTwin.objects.filter(
                    Q(is_active=True)
                    | Q(
                        pk=self.instance.digital_twin_id
                        )).distinct().order_by("name", "part_number",)
            )

            self.fields["digital_twin"].disabled = True

            self.fields["digital_twin"].help_text = (
                "Изходният цифров двойник не може да бъде "
                "променян след създаването на експеримента."
            )

        self.fields["digital_twin"].queryset = digital_twin_queryset

        self.fields["digital_twin"].empty_label = "Изберете цифров двойник"

    def clean_name(self) -> str:
        """
        Normalize and validate the experiment name.
        """

        name = str(self.cleaned_data.get("name", "", )).strip()

        name = " ".join(name.split())

        if not name:
            raise ValidationError("Наименованието на експеримента е задължително.")

        return name

    def clean_description(self) -> str:
        """
        Normalize optional description whitespace.
        """

        description = str(self.cleaned_data.get("description", "", ) or "").strip()

        return description

    def clean_objective(self) -> str:
        """
        Normalize optional experiment objective.
        """

        objective = str(self.cleaned_data.get("objective", "", ) or "").strip()

        return objective

    def clean(self):
        """
        Protect the source Digital Twin during updates.
        """

        cleaned_data = super().clean()

        if (self.instance is not None and self.instance.pk):
            stored_experiment = (Experiment.objects.filter(pk=self.instance.pk).only("digital_twin_id").first())

            if stored_experiment is not None:
                cleaned_data["digital_twin"] = (self.instance.digital_twin)

        return cleaned_data


class ExperimentFilterForm(forms.Form):
    """
    Search and filter the experiment list.
    """

    query = forms.CharField(
        required=False,
        label="Търсене",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": ("Име, описание, цел или цифров двойник"),}
            ),
        )

    digital_twin = forms.ModelChoiceField(
        required=False,
        queryset=DigitalTwin.objects.none(),
        label="Цифров двойник",
        empty_label="Всички цифрови двойници",
        widget=forms.Select(attrs={"class": "form-select", }), )

    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=(("", "Всички статуси", ), *Experiment.Status.choices,),
        widget=forms.Select(attrs={"class": "form-select",}), )

    def __init__(self, *args, **kwargs, ):
        super().__init__(*args, **kwargs)

        self.fields["digital_twin"].queryset = (DigitalTwin.objects.order_by("name", "part_number", ))


class ExperimentDeleteForm(forms.Form):
    """
    Require explicit confirmation before permanent deletion.
    """

    confirm = forms.BooleanField(
        required=True,
        label=("Потвърждавам, че желая експериментът да бъде изтрит окончателно."),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", }),
        error_messages={"required": ("Трябва да потвърдите окончателното изтриване."), }, )

    def __init__(self, *args, experiment: Experiment | None = None, **kwargs, ):
        super().__init__(*args, **kwargs, )

        self.experiment = experiment
