"""
Web views for Experiment management.

The views process HTTP requests, prepare template context and delegate
all business operations to ExperimentService.
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import (
    DetailView,
    FormView,
    ListView,
)

from core.request import (
    get_client_computer_name,
    get_client_ip,
    get_user_agent,
)
from experiments.forms import (
    ExperimentDeleteForm,
    ExperimentFilterForm,
    ExperimentForm,
)
from experiments.models import Experiment
from experiments.services import (
    ExperimentDeleteError,
    ExperimentService,
    ExperimentServiceError,
    ExperimentUpdateError,
)


def get_request_metadata(
    request: HttpRequest,
) -> dict[str, str | None]:
    """
    Return audit metadata in the format expected by ExperimentService.
    """

    return {
        "ip_address": get_client_ip(request),
        "computer_name": (
            get_client_computer_name(request)
        ),
        "user_agent": get_user_agent(request),
    }


class ExperimentObjectMixin:
    """
    Shared Experiment object lookup.
    """

    model = Experiment
    context_object_name = "experiment"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        """
        Return the optimized Experiment queryset.
        """

        return ExperimentService.base_queryset()

    def get_object(
        self,
        queryset=None,
    ) -> Experiment:
        """
        Return the Experiment selected by the URL UUID.
        """

        queryset = (
            queryset
            if queryset is not None
            else self.get_queryset()
        )

        experiment_id = self.kwargs.get(
            self.pk_url_kwarg
        )

        try:
            return queryset.get(
                pk=experiment_id
            )
        except (
            Experiment.DoesNotExist,
            ValueError,
            TypeError,
        ) as error:
            raise Http404(
                "Experiment was not found."
            ) from error


class ExperimentListView(
    LoginRequiredMixin,
    ListView,
):
    """
    Display searchable and filterable Experiments.
    """

    model = Experiment
    template_name = (
        "experiments/experiment_list.html"
    )
    context_object_name = "experiments"
    paginate_by = 20

    def get_filter_form(
        self,
    ) -> ExperimentFilterForm:
        """
        Return the filter form for the current query string.
        """

        if not hasattr(
            self,
            "_filter_form",
        ):
            self._filter_form = (
                ExperimentFilterForm(
                    data=self.request.GET or None
                )
            )

        return self._filter_form

    def get_queryset(self):
        """
        Apply validated search and filter values.
        """

        queryset = (
            ExperimentService.base_queryset()
        )

        form = self.get_filter_form()

        if not form.is_valid():
            return queryset.order_by(
                "-created_at"
            )

        cleaned_data = form.cleaned_data

        return ExperimentService.search(
            queryset=queryset,
            query=cleaned_data.get(
                "query",
                "",
            ),
            digital_twin=cleaned_data.get(
                "digital_twin"
            ),
            status=cleaned_data.get(
                "status",
                "",
            ),
        )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add filters and Experiment statistics.
        """

        context = super().get_context_data(
            **kwargs
        )

        filtered_queryset = self.get_queryset()

        context.update(
            {
                "filter_form": (
                    self.get_filter_form()
                ),
                "statistics": (
                    ExperimentService
                    .get_statistics(
                        filtered_queryset
                    )
                ),
                "page_title": "Experiments",
            }
        )

        return context


class ExperimentDetailView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    DetailView,
):
    """
    Display one Experiment and its related engineering information.
    """

    template_name = (
        "experiments/experiment_detail.html"
    )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add related records and available actions.
        """

        context = super().get_context_data(
            **kwargs
        )

        experiment = self.object

        context.update(
            {
                "chat_messages": (
                    experiment
                    .chat_messages
                    .all()
                    .order_by("created_at")
                ),
                "proposals": (
                    experiment
                    .proposals
                    .all()
                    .order_by("sequence")
                ),
                "can_update": (
                    experiment.status
                    in ExperimentService
                    .EDITABLE_STATUSES
                    and experiment
                    .result_twin_id
                    is None
                ),
                "can_delete": (
                    experiment.status
                    == Experiment.Status.DRAFT
                ),
                "can_archive": (
                    experiment.status
                    != Experiment.Status.ARCHIVED
                ),
                "page_title": experiment.name,
            }
        )

        return context


class ExperimentCreateView(
    LoginRequiredMixin,
    FormView,
):
    """
    Create a new Experiment.
    """

    template_name = (
        "experiments/experiment_form.html"
    )
    form_class = ExperimentForm

    def get_initial(
        self,
    ) -> dict[str, Any]:
        """
        Optionally preselect a Digital Twin from the query string.
        """

        initial = super().get_initial()

        digital_twin_id = self.request.GET.get(
            "digital_twin"
        )

        if digital_twin_id:
            initial["digital_twin"] = (
                digital_twin_id
            )

        return initial

    def get_success_url(self) -> str:
        """
        Redirect to the created Experiment.
        """

        return reverse(
            "experiments:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )

    def form_valid(
        self,
        form: ExperimentForm,
    ) -> HttpResponse:
        """
        Delegate Experiment creation to the service layer.
        """

        try:
            self.object = (
                ExperimentService.create(
                    form=form,
                    user=self.request.user,
                    **get_request_metadata(
                        self.request
                    ),
                )
            )
        except ExperimentServiceError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Experiment '{self.object.name}' "
                "was created successfully."
            ),
        )

        return HttpResponseRedirect(
            self.get_success_url()
        )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add creation form context.
        """

        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "page_title": (
                    "Create Experiment"
                ),
                "submit_label": "Create",
                "cancel_url": reverse(
                    "experiments:list"
                ),
                "is_update": False,
            }
        )

        return context


class ExperimentUpdateView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    FormView,
):
    """
    Update an editable Experiment.
    """

    template_name = (
        "experiments/experiment_form.html"
    )
    form_class = ExperimentForm

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Load and validate the Experiment before processing the request.
        """

        self.object = self.get_object()

        try:
            ExperimentService.validate_before_update(
                self.object
            )
        except ExperimentUpdateError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "experiments:detail",
                pk=self.object.pk,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(
        self,
    ) -> dict[str, Any]:
        """
        Bind the form to the selected Experiment.
        """

        kwargs = super().get_form_kwargs()

        kwargs["instance"] = self.object

        return kwargs

    def get_success_url(self) -> str:
        """
        Redirect to the updated Experiment.
        """

        return reverse(
            "experiments:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )

    def form_valid(
        self,
        form: ExperimentForm,
    ) -> HttpResponse:
        """
        Delegate Experiment update to the service layer.
        """

        try:
            self.object = (
                ExperimentService.update(
                    experiment=self.object,
                    form=form,
                    user=self.request.user,
                    **get_request_metadata(
                        self.request
                    ),
                )
            )
        except ExperimentServiceError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Experiment '{self.object.name}' "
                "was updated successfully."
            ),
        )

        return HttpResponseRedirect(
            self.get_success_url()
        )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add update form context.
        """

        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "experiment": self.object,
                "page_title": (
                    "Update Experiment"
                ),
                "submit_label": (
                    "Save changes"
                ),
                "cancel_url": reverse(
                    "experiments:detail",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "is_update": True,
            }
        )

        return context


class ExperimentArchiveView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    """
    Archive an Experiment through a POST request.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Archive the selected Experiment.
        """

        experiment = self.get_object()

        try:
            archived_experiment = (
                ExperimentService.archive(
                    experiment=experiment,
                    user=request.user,
                    **get_request_metadata(
                        request
                    ),
                )
            )
        except ExperimentServiceError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "experiments:detail",
                pk=experiment.pk,
            )

        messages.success(
            request,
            (
                f"Experiment "
                f"'{archived_experiment.name}' "
                "was archived successfully."
            ),
        )

        return redirect(
            "experiments:detail",
            pk=archived_experiment.pk,
        )


class ExperimentDeleteView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    FormView,
):
    """
    Permanently delete an unused Draft Experiment.
    """

    template_name = (
        "experiments/"
        "experiment_confirm_delete.html"
    )
    form_class = ExperimentDeleteForm

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Load the Experiment once for the complete request.
        """

        self.object = self.get_object()

        try:
            ExperimentService.validate_before_delete(
                self.object
            )
        except ExperimentDeleteError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "experiments:detail",
                pk=self.object.pk,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(
        self,
    ) -> dict[str, Any]:
        """
        Supply the selected Experiment to the confirmation form.
        """

        kwargs = super().get_form_kwargs()

        kwargs["experiment"] = self.object

        return kwargs

    def form_valid(
        self,
        form: ExperimentDeleteForm,
    ) -> HttpResponse:
        """
        Delegate permanent deletion to the service layer.
        """

        experiment_name = self.object.name

        try:
            ExperimentService.delete(
                experiment=self.object,
                user=self.request.user,
                **get_request_metadata(
                    self.request
                ),
            )
        except ExperimentDeleteError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Experiment '{experiment_name}' "
                "was deleted successfully."
            ),
        )

        return redirect(
            "experiments:list"
        )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add deletion confirmation context.
        """

        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "experiment": self.object,
                "page_title": ("Delete Experiment"),
                "cancel_url": reverse("experiments:detail", kwargs={"pk": self.object.pk, }, ), 
                }
            )

        return context
