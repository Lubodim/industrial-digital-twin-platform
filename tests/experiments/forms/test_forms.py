from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from digital_twins.models import DigitalTwin
from experiments.forms import (
    ExperimentDeleteForm,
    ExperimentFilterForm,
    ExperimentForm,
)
from experiments.models import Experiment


User = get_user_model()


class ExperimentFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="experiment-form-user",
            password="test-password",
        )

        self.active_twin = DigitalTwin.objects.create(
            name="Active Shaft",
            part_number="ACTIVE-SHAFT-001",
            created_by=self.user,
            updated_by=self.user,
            is_active=True,
        )

        self.second_active_twin = (
            DigitalTwin.objects.create(
                name="Active Housing",
                part_number="ACTIVE-HOUSING-002",
                created_by=self.user,
                updated_by=self.user,
                is_active=True,
            )
        )

        self.inactive_twin = (
            DigitalTwin.objects.create(
                name="Inactive Bracket",
                part_number="INACTIVE-BRACKET-003",
                created_by=self.user,
                updated_by=self.user,
                is_active=False,
            )
        )

        self.valid_data = {
            "digital_twin": str(
                self.active_twin.pk
            ),
            "name": "Weight reduction",
            "description": (
                "Investigate alternative geometry."
            ),
            "objective": (
                "Reduce mass without unacceptable "
                "loss of strength."
            ),
        }

    def test_valid_form(self):
        form = ExperimentForm(
            data=self.valid_data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_name_is_required(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "name": "",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "name",
            form.errors,
        )

    def test_digital_twin_is_required(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "digital_twin": "",
            }
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "digital_twin",
            form.errors,
        )

    def test_form_normalizes_name(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "name": (
                    "   Weight    reduction   "
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["name"],
            "Weight reduction",
        )

    def test_form_trims_description(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "description": (
                    "   Description text.   "
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["description"],
            "Description text.",
        )

    def test_form_trims_objective(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "objective": (
                    "   Reduce manufacturing cost.   "
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data["objective"],
            "Reduce manufacturing cost.",
        )

    def test_description_may_be_empty(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "description": "",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_objective_may_be_empty(self):
        form = ExperimentForm(
            data={
                **self.valid_data,
                "objective": "",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_only_active_twins_are_available_on_create(
        self,
    ):
        form = ExperimentForm()

        queryset = form.fields[
            "digital_twin"
        ].queryset

        self.assertIn(
            self.active_twin,
            queryset,
        )

        self.assertIn(
            self.second_active_twin,
            queryset,
        )

        self.assertNotIn(
            self.inactive_twin,
            queryset,
        )

    def test_form_saves_experiment(self):
        form = ExperimentForm(
            data=self.valid_data
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        experiment = form.save(
            commit=False
        )

        experiment.created_by = self.user
        experiment.save()

        self.assertEqual(
            experiment.digital_twin,
            self.active_twin,
        )

        self.assertEqual(
            experiment.name,
            "Weight reduction",
        )

        self.assertEqual(
            experiment.status,
            Experiment.Status.DRAFT,
        )

    def test_update_form_uses_existing_instance(self):
        experiment = Experiment.objects.create(
            digital_twin=self.active_twin,
            name="Original experiment",
            created_by=self.user,
        )

        form = ExperimentForm(
            data={
                **self.valid_data,
                "name": "Updated experiment",
            },
            instance=experiment,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        updated_experiment = form.save()

        self.assertEqual(
            updated_experiment.pk,
            experiment.pk,
        )

        self.assertEqual(
            updated_experiment.name,
            "Updated experiment",
        )

    def test_digital_twin_is_disabled_during_update(
        self,
    ):
        experiment = Experiment.objects.create(
            digital_twin=self.active_twin,
            name="Existing experiment",
            created_by=self.user,
        )

        form = ExperimentForm(
            instance=experiment
        )

        self.assertTrue(
            form.fields[
                "digital_twin"
            ].disabled
        )

    def test_update_cannot_change_digital_twin(self):
        experiment = Experiment.objects.create(
            digital_twin=self.active_twin,
            name="Existing experiment",
            created_by=self.user,
        )

        form = ExperimentForm(
            data={
                **self.valid_data,
                "digital_twin": str(
                    self.second_active_twin.pk
                ),
                "name": "Changed experiment",
            },
            instance=experiment,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        updated_experiment = form.save()

        self.assertEqual(
            updated_experiment.digital_twin,
            self.active_twin,
        )

    def test_current_inactive_twin_is_available_on_update(
        self,
    ):
        experiment = Experiment.objects.create(
            digital_twin=self.inactive_twin,
            name="Historical experiment",
            created_by=self.user,
        )

        form = ExperimentForm(
            instance=experiment
        )

        queryset = form.fields[
            "digital_twin"
        ].queryset

        self.assertIn(
            self.inactive_twin,
            queryset,
        )


class ExperimentFilterFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="experiment-filter-user",
            password="test-password",
        )

        self.twin = DigitalTwin.objects.create(
            name="Filter Twin",
            part_number="FILTER-TWIN-001",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_empty_filter_form_is_valid(self):
        form = ExperimentFilterForm(
            data={}
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_filter_form_accepts_all_values(self):
        form = ExperimentFilterForm(
            data={
                "query": "weight",
                "digital_twin": str(
                    self.twin.pk
                ),
                "status": (
                    Experiment.Status.DRAFT
                ),
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        self.assertEqual(
            form.cleaned_data[
                "digital_twin"
            ],
            self.twin,
        )

        self.assertEqual(
            form.cleaned_data["status"],
            Experiment.Status.DRAFT,
        )

    def test_filter_form_contains_all_statuses(self):
        form = ExperimentFilterForm()

        choices = dict(
            form.fields[
                "status"
            ].choices
        )

        self.assertIn(
            Experiment.Status.DRAFT,
            choices,
        )

        self.assertIn(
            Experiment.Status.COMPLETED,
            choices,
        )

        self.assertIn(
            Experiment.Status.ARCHIVED,
            choices,
        )


class ExperimentDeleteFormTests(TestCase):
    def test_confirmation_is_required(self):
        form = ExperimentDeleteForm(
            data={}
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "confirm",
            form.errors,
        )

    def test_confirmed_form_is_valid(self):
        form = ExperimentDeleteForm(
            data={
                "confirm": True,
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_form_accepts_experiment_instance(self):
        form = ExperimentDeleteForm(
            experiment=None
        )

        self.assertIsNone(
            form.experiment
        )
