"""
Web views for Digital Twin management.

The views are responsible for:

- processing HTTP requests;
- preparing forms and template context;
- calling the DigitalTwinService;
- displaying success and error messages;
- redirecting users after successful operations.

Business logic remains inside digital_twins.services.
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
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    DetailView,
    FormView,
    ListView,
)

from digital_twins.forms import (
    DigitalTwinDeleteForm,
    DigitalTwinFilterForm,
    DigitalTwinForm,
)
from digital_twins.models import DigitalTwin
from digital_twins.services import (
    DigitalTwinDeleteError,
    DigitalTwinNotFoundError,
    DigitalTwinService,
    DigitalTwinServiceError,
)


def get_request_metadata(
    request: HttpRequest,
) -> dict[str, str | None]:
    """
    Extract audit-related metadata from an HTTP request.

    Proxy headers are considered before REMOTE_ADDR because the project
    may later run behind a local reverse proxy.
    """

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.META.get(
            "REMOTE_ADDR"
        )

    computer_name = (
        request.META.get(
            "HTTP_X_COMPUTER_NAME",
            "",
        )
        or request.META.get(
            "REMOTE_HOST",
            "",
        )
    )

    user_agent = request.META.get(
        "HTTP_USER_AGENT",
        "",
    )

    return {
        "ip_address": ip_address,
        "computer_name": str(
            computer_name or ""
        ).strip(),
        "user_agent": str(
            user_agent or ""
        ).strip(),
    }


class DigitalTwinObjectMixin:
    """
    Shared object lookup for Digital Twin views.
    """

    model = DigitalTwin
    context_object_name = "digital_twin"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        """
        Return the optimized service queryset.
        """

        return DigitalTwinService.base_queryset()

    def get_object(self, queryset=None) -> DigitalTwin:
        """
        Return the Digital Twin selected by the URL UUID.
        """

        queryset = (
            queryset
            if queryset is not None
            else self.get_queryset()
        )

        twin_id = self.kwargs.get(
            self.pk_url_kwarg
        )

        try:
            return queryset.get(pk=twin_id)
        except (
            DigitalTwin.DoesNotExist,
            ValueError,
            TypeError,
        ) as error:
            raise Http404(
                "Digital Twin was not found."
            ) from error


class DigitalTwinListView(
    LoginRequiredMixin,
    ListView,
):
    """
    Display the searchable and filterable Digital Twin list.
    """

    model = DigitalTwin
    template_name = (
        "digital_twins/digital_twin_list.html"
    )
    context_object_name = "digital_twins"
    paginate_by = 20

    def get_filter_form(
        self,
    ) -> DigitalTwinFilterForm:
        """
        Return the bound filter form for the current query string.
        """

        if not hasattr(
            self,
            "_filter_form",
        ):
            self._filter_form = (
                DigitalTwinFilterForm(
                    data=self.request.GET or None
                )
            )

        return self._filter_form

    def get_queryset(self):
        """
        Apply validated search and filtering parameters.
        """

        queryset = (
            DigitalTwinService.base_queryset()
        )

        form = self.get_filter_form()

        if not form.is_valid():
            return queryset.order_by(
                "name",
                "part_number",
            )

        cleaned_data = form.cleaned_data

        return DigitalTwinService.search(
            queryset=queryset,
            query=cleaned_data.get(
                "query",
                "",
            ),
            material=cleaned_data.get(
                "material"
            ),
            technology=cleaned_data.get(
                "technology"
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
        Add filters and list statistics to the template context.
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
                    DigitalTwinService
                    .get_statistics(
                        filtered_queryset
                    )
                ),
                "page_title": (
                    "Digital Twins"
                ),
            }
        )

        return context


class DigitalTwinDetailView(
    LoginRequiredMixin,
    DigitalTwinObjectMixin,
    DetailView,
):
    """
    Display one Digital Twin and its calculated values.
    """

    template_name = (
        "digital_twins/digital_twin_detail.html"
    )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add engineering calculations and related history.
        """

        context = super().get_context_data(
            **kwargs
        )

        twin = self.object

        source_experiments = getattr(
            twin,
            "experiments",
            None,
        )

        result_experiments = getattr(
            twin,
            "result_experiments",
            None,
        )

        context.update(
            {
                "cost_summary": (
                    DigitalTwinService
                    .get_cost_summary(twin)
                ),
                "files": twin.files.all(),
                "source_experiments": (
                    source_experiments.all()
                    if source_experiments is not None
                    else ()
                ),
                "result_experiments": (
                    result_experiments.all()
                    if result_experiments is not None
                    else ()
                ),
                "page_title": (
                    f"{twin.part_number} - "
                    f"{twin.name}"
                ),
            }
        )

        return context


class DigitalTwinCreateView(
    LoginRequiredMixin,
    FormView,
):
    """
    Create a new Digital Twin.
    """

    template_name = (
        "digital_twins/digital_twin_form.html"
    )
    form_class = DigitalTwinForm

    def get_success_url(self) -> str:
        """
        Redirect to the newly created Digital Twin.
        """

        return reverse(
            "digital_twins:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )

    def form_valid(
        self,
        form: DigitalTwinForm,
    ) -> HttpResponse:
        """
        Delegate creation to the service layer.
        """

        try:
            self.object = (
                DigitalTwinService.create(
                    form=form,
                    user=self.request.user,
                    **get_request_metadata(
                        self.request
                    ),
                )
            )
        except DigitalTwinServiceError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                "Digital Twin "
                f"'{self.object.part_number}' "
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
        Add common form template information.
        """

        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "page_title": (
                    "Create Digital Twin"
                ),
                "submit_label": "Create",
                "cancel_url": reverse(
                    "digital_twins:list"
                ),
                "is_update": False,
            }
        )

        return context


class DigitalTwinUpdateView(
    LoginRequiredMixin,
    DigitalTwinObjectMixin,
    FormView,
):
    """
    Update an existing Digital Twin.
    """

    template_name = (
        "digital_twins/digital_twin_form.html"
    )
    form_class = DigitalTwinForm

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Load the Digital Twin once for the complete request.
        """

        self.object = self.get_object()

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(
        self,
    ) -> dict[str, Any]:
        """
        Bind the form to the selected Digital Twin.
        """

        kwargs = super().get_form_kwargs()

        kwargs["instance"] = self.object

        return kwargs

    def get_success_url(self) -> str:
        """
        Redirect to the updated Digital Twin.
        """

        return reverse(
            "digital_twins:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )

    def form_valid(
        self,
        form: DigitalTwinForm,
    ) -> HttpResponse:
        """
        Delegate the update operation to the service.
        """

        try:
            self.object = (
                DigitalTwinService.update(
                    twin=self.object,
                    form=form,
                    user=self.request.user,
                    **get_request_metadata(
                        self.request
                    ),
                )
            )
        except DigitalTwinServiceError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                "Digital Twin "
                f"'{self.object.part_number}' "
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
        Add update-related template information.
        """

        context = super().get_context_data(
            **kwargs
        )

        context.update(
            {
                "digital_twin": self.object,
                "page_title": (
                    "Update Digital Twin"
                ),
                "submit_label": "Save changes",
                "cancel_url": reverse(
                    "digital_twins:detail",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "is_update": True,
            }
        )

        return context


class DigitalTwinActivateView(
    LoginRequiredMixin,
    DigitalTwinObjectMixin,
    View,
):
    """
    Activate a Digital Twin through a POST request.
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
        Activate the selected Digital Twin.
        """

        twin = self.get_object()

        try:
            updated_twin = (
                DigitalTwinService.activate(
                    twin=twin,
                    user=request.user,
                    **get_request_metadata(
                        request
                    ),
                )
            )
        except DigitalTwinServiceError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "digital_twins:detail",
                pk=twin.pk,
            )

        messages.success(
            request,
            (
                "Digital Twin "
                f"'{updated_twin.part_number}' "
                "was activated successfully."
            ),
        )

        return redirect(
            "digital_twins:detail",
            pk=updated_twin.pk,
        )


class DigitalTwinDeactivateView(
    LoginRequiredMixin,
    DigitalTwinObjectMixin,
    View,
):
    """
    Deactivate a Digital Twin through a POST request.
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
        Deactivate the selected Digital Twin.
        """

        twin = self.get_object()

        try:
            updated_twin = (
                DigitalTwinService.deactivate(
                    twin=twin,
                    user=request.user,
                    **get_request_metadata(
                        request
                    ),
                )
            )
        except DigitalTwinServiceError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "digital_twins:detail",
                pk=twin.pk,
            )

        messages.success(
            request,
            (
                "Digital Twin "
                f"'{updated_twin.part_number}' "
                "was deactivated successfully."
            ),
        )

        return redirect(
            "digital_twins:detail",
            pk=updated_twin.pk,
        )


class DigitalTwinDeleteView(
    LoginRequiredMixin,
    DigitalTwinObjectMixin,
    FormView,
):
    """
    Permanently delete an unused Digital Twin.
    """

    template_name = (
        "digital_twins/"
        "digital_twin_confirm_delete.html"
    )
    form_class = DigitalTwinDeleteForm
    success_url = reverse_lazy(
        "digital_twins:list"
    )

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """
        Load the selected object before GET or POST processing.
        """

        self.object = self.get_object()

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(
        self,
    ) -> dict[str, Any]:
        """
        Provide the selected Digital Twin to the confirmation form when
        supported by the form constructor.
        """

        kwargs = super().get_form_kwargs()

        try:
            kwargs["digital_twin"] = self.object

            self.form_class(**kwargs)
        except TypeError:
            kwargs.pop(
                "digital_twin",
                None,
            )

        return kwargs

    def form_valid(
        self,
        form: DigitalTwinDeleteForm,
    ) -> HttpResponse:
        """
        Permanently delete the Digital Twin when deletion is safe.
        """

        part_number = self.object.part_number

        try:
            DigitalTwinService.delete(twin=self.object,
                                      user=self.request.user,
                                      **get_request_metadata(self.request),)
        except DigitalTwinDeleteError as error:
            form.add_error(None,str(error),)

            return self.form_invalid(form)
        except DigitalTwinServiceError as error:
            form.add_error(None,str(error),)

            return self.form_invalid(form)

        messages.success(self.request,("Digital Twin "f"'{part_number}' ""was deleted permanently."),)

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self,**kwargs: Any,) -> dict[str, Any]:
        
        """
        Add delete confirmation context.
        """

        context = super().get_context_data(**kwargs)

        context.update(
            {
                "digital_twin": self.object,
                "page_title": ("Delete Digital Twin"),
                "cancel_url": reverse("digital_twins:detail",kwargs={"pk": self.object.pk,},),
            }
        )

        return context
