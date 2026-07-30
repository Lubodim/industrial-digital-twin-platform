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
from django.core.paginator import Paginator
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

from ai_engine.local_ai.engineering_agent import (
    EngineeringAgent,
    EngineeringAgentError,
)
from ai_engine.experiment_research_service import (
    ExperimentResearchService,
)
from ai_engine.provider_factory import (
    ProviderFactory,
)


from experiments.forms import (
    ExperimentDeleteForm,
    ExperimentFilterForm,
    ExperimentForm,
    ExperimentResearchQuestionForm,
    ProposalReviewForm,
)


from experiments.models import (
    Experiment,
    ExperimentChatMessage,
    ExperimentProposal,
)

from experiments.locking import (
    ExperimentLockError,
    ExperimentLockService,
)

from experiments.services import (
    ExperimentDeleteError,
    ExperimentService,
    ExperimentServiceError,
    ExperimentUpdateError,
)

from experiments.proposal_services import (
    ProposalReviewError,
    ProposalReviewService,
)

from experiments.twin_creation import (
    TwinCreationError,
    TwinCreationService,
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

class ExperimentLockRequiredMixin:
    """
    Require the current engineer to own the experiment lock.
    """

    def ensure_experiment_lock(
        self,
        *,
        request: HttpRequest,
        experiment: Experiment,
    ) -> HttpResponse | None:
        try:
            ExperimentLockService.assert_owned(
                experiment=experiment,
                user=request.user,
            )
        except ExperimentLockError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "experiments:detail",
                pk=experiment.pk,
            )

        ExperimentLockService.refresh(
            experiment=experiment,
            user=request.user,
        )

        return None

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
                "filter_form": (self.get_filter_form()),
                "statistics": (ExperimentService.get_statistics(filtered_queryset)),
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

        context = super().get_context_data(
            **kwargs
        )

        experiment = self.object

        chat_messages = list(
            experiment.chat_messages.all().order_by(
                "sequence"
            )
        )

        question_groups = []
        current_group = None

        for chat_message in chat_messages:
            if (
                chat_message.role
                == ExperimentChatMessage.Role.ENGINEER
            ):
                current_group = {
                    "question": chat_message,
                    "answers": [],
                }

                question_groups.append(
                    current_group
                )

            elif current_group is not None:
                current_group["answers"].append(
                    chat_message
                )

        question_groups.reverse()

        question_paginator = Paginator(
            question_groups,
            10,
        )

        question_page = (
            question_paginator.get_page(
                self.request.GET.get(
                    "questions_page"
                )
            )
        )

        context.update(
            {
                "question_page": question_page,
                "chat_message_count": len(
                    chat_messages
                ),
                "proposal_count": (
                    experiment.proposals.count()
                ),
                "pending_proposal_count": (
                    experiment.proposals.filter(
                        status=(
                            ExperimentProposal.Status.PENDING
                        )
                    ).count()
                ),
                "approved_proposal_count": (
                    experiment.proposals.filter(
                        status=(
                            ExperimentProposal.Status.APPROVED
                        )
                    ).count()
                ),
                "rejected_proposal_count": (
                    experiment.proposals.filter(
                        status=(
                            ExperimentProposal.Status.REJECTED
                        )
                    ).count()
                ),

                "research_question_form": (
                    ExperimentResearchQuestionForm()
                ),
                                "has_active_lock": (
                    experiment.has_active_lock
                ),
                "lock_owned_by_current_user": (
                    experiment.is_locked_by(
                        self.request.user
                    )
                ),
                "locked_by_another_user": (
                    experiment.is_locked_by_another_user(
                        self.request.user
                    )
                ),
                "is_read_only": (
                    not experiment.is_locked_by(
                        self.request.user
                    )
                ),
                
                "can_update": (
                    experiment.status
                    in ExperimentService.EDITABLE_STATUSES
                    and experiment.result_twin_id is None
                    and experiment.is_locked_by(self.request.user)),
                "can_delete": (
                    experiment.status
                    == Experiment.Status.DRAFT
                    and experiment.is_locked_by(self.request.user)),
                "can_archive": (
                    experiment.status
                    != Experiment.Status.ARCHIVED
                    and experiment.is_locked_by(self.request.user)),
                "page_title": experiment.name,
            }
        )

        return context

class ExperimentProposalListView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    DetailView,
):
    """
    Display the engineering proposals generated for one experiment.
    """

    template_name = (
        "experiments/proposal_list.html"
    )

    def get_context_data(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Add paginated proposals and proposal statistics.
        """

        context = super().get_context_data(
            **kwargs
        )

        experiment = self.object

        proposals_queryset = (
            experiment.proposals
            .select_related(
                "reviewed_by",
                "internal_analysis",
            )
            .order_by(
                "sequence"
            )
        )

        status_filter = self.request.GET.get(
            "status",
            "",
        )

        category_filter = self.request.GET.get(
            "category",
            "",
        )

        if status_filter in {
            choice[0]
            for choice in ExperimentProposal.Status.choices
        }:
            proposals_queryset = (
                proposals_queryset.filter(
                    status=status_filter
                )
            )

        if category_filter in {
            choice[0]
            for choice in ExperimentProposal.Category.choices
        }:
            proposals_queryset = (
                proposals_queryset.filter(
                    category=category_filter
                )
            )

        paginator = Paginator(
            proposals_queryset,
            10,
        )

        proposal_page = paginator.get_page(
            self.request.GET.get(
                "page"
            )
        )

        all_proposals = experiment.proposals.all()

        pending_count = all_proposals.filter(
            status=ExperimentProposal.Status.PENDING
        ).count()

        approved_count = all_proposals.filter(
            status=ExperimentProposal.Status.APPROVED
        ).count()

        can_create_result_twin = (
            experiment.status == Experiment.Status.APPROVED
            and experiment.result_twin_id is None
            and pending_count == 0
            and approved_count > 0
            and experiment.is_locked_by(
                self.request.user
            )
        )
        
        context.update(
            {
                "has_active_lock": (experiment.has_active_lock),
                "lock_owned_by_current_user": (experiment.is_locked_by(self.request.user)),
                "locked_by_another_user": (experiment.is_locked_by_another_user(
                        self.request.user)),
                "is_read_only": (not experiment.is_locked_by(self.request.user)),
                "proposal_page": proposal_page,
                "proposal_count": (all_proposals.count()),
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": (all_proposals.filter(status=(ExperimentProposal.Status.REJECTED)).count()),
                "status_choices": (ExperimentProposal.Status.choices),
                "category_choices": (ExperimentProposal.Category.choices),
                "selected_status": status_filter,
                "selected_category": category_filter,
                "page_title": (f"Engineering proposals – {experiment.name}"),
                "can_create_result_twin": can_create_result_twin,
            }
        )

        return context

class ExperimentProposalReviewView(
    LoginRequiredMixin,
    ExperimentLockRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    """
    Approve or reject one engineering proposal.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        experiment = self.get_object()

        lock_response = self.ensure_experiment_lock(
            request=request,
            experiment=experiment,
        )

        if lock_response is not None:
            return lock_response

        proposal = (
            ExperimentProposal.objects
            .filter(
                pk=kwargs.get("proposal_pk"),
                experiment=experiment,
            )
            .first()
        )

        if proposal is None:
            raise Http404(
                "Инженерното предложение не е намерено."
            )

        form = ProposalReviewForm(
            request.POST
        )

        if not form.is_valid():
            messages.error(
                request,
                "Подаденото инженерно решение е невалидно.",
            )

            return redirect(
                "experiments:proposals",
                pk=experiment.pk,
            )

        decision = form.cleaned_data[
            "decision"
        ]

        review_note = form.cleaned_data[
            "review_note"
        ]

        service = ProposalReviewService()

        try:
            if decision == "APPROVE":
                service.approve(
                    proposal=proposal,
                    reviewed_by=request.user,
                    note=review_note,
                )

                messages.success(
                    request,
                    (
                        f"Предложение №{proposal.sequence} "
                        "е одобрено."
                    ),
                )

            elif decision == "REJECT":
                service.reject(
                    proposal=proposal,
                    reviewed_by=request.user,
                    note=review_note,
                )

                messages.success(
                    request,
                    (
                        f"Предложение №{proposal.sequence} "
                        "е отхвърлено."
                    ),
                )

            else:
                messages.error(
                    request,
                    "Непознато инженерно решение.",
                )

        except ProposalReviewError as error:
            messages.error(
                request,
                str(error),
            )

        return redirect(
            "experiments:proposals",
            pk=experiment.pk,
        )

class ExperimentCreateResultTwinView(
    LoginRequiredMixin,
    ExperimentLockRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    """
    Create a derived Digital Twin from all approved proposals.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        experiment = self.get_object()

        lock_response = self.ensure_experiment_lock(
            request=request,
            experiment=experiment,
        )

        if lock_response is not None:
            return lock_response

        metadata = get_request_metadata(
            request
        )

        service = TwinCreationService()

        try:
            result = service.create(
                experiment=experiment,
                created_by=request.user,
                ip_address=metadata[
                    "ip_address"
                ],
                computer_name=(
                    metadata["computer_name"]
                    or ""
                ),
                user_agent=(
                    metadata["user_agent"]
                    or ""
                ),
            )

        except TwinCreationError as error:
            messages.error(
                request,
                str(error),
            )

            return redirect(
                "experiments:proposals",
                pk=experiment.pk,
            )

        messages.success(
            request,
            (
                "Резултатният цифров двойник "
                f"„{result.result_twin.name}“ "
                "е създаден успешно."
            ),
        )

        return redirect(
            "digital_twins:detail",
            pk=result.result_twin.pk,
        )

class ExperimentAcquireLockView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    """
    Lock one experiment for exclusive engineering work.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        experiment = self.get_object()

        try:
            ExperimentLockService.acquire(
                experiment=experiment,
                user=request.user,
            )
        except ExperimentLockError as error:
            messages.error(
                request,
                str(error),
            )
        else:
            messages.success(
                request,
                (
                    "Експериментът е заключен за работа от вас. "
                    "Заключването е валидно 30 минути и се "
                    "удължава при всяко действие."
                ),
            )

        return redirect(
            "experiments:detail",
            pk=experiment.pk,
        )
class ExperimentReleaseLockView(
    LoginRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    """
    Release the current experiment lock.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        experiment = self.get_object()

        try:
            ExperimentLockService.release(
                experiment=experiment,
                user=request.user,
                force=False,
            )
        except ExperimentLockError as error:
            messages.error(
                request,
                str(error),
            )
        else:
            messages.success(
                request,
                "Експериментът е освободен.",
            )

        return redirect(
            "experiments:detail",
            pk=experiment.pk,
        )
        
class ExperimentResearchQuestionView(
    LoginRequiredMixin,
    ExperimentLockRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    
    """
    Send one engineering question to all configured external
    AI research providers.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        """
        Validate the question and run the external research pipeline.
        """

        experiment = self.get_object()
        
        lock_response = self.ensure_experiment_lock(request=request, experiment=experiment,)

        if lock_response is not None:
            return lock_response

        form = ExperimentResearchQuestionForm(
            request.POST
        )

        if not form.is_valid():
            error_messages: list[str] = []

            for field_errors in form.errors.values():
                for error in field_errors:
                    error_messages.append(
                        str(error)
                    )

            messages.error(
                request,
                " ".join(error_messages)
                or "Инженерният въпрос е невалиден.",
            )

            return redirect(
                "experiments:detail",
                pk=experiment.pk,
            )

        configured_providers = (
            ProviderFactory.get_configured_providers()
        )

        if not configured_providers:
            messages.error(
                request,
                (
                    "Няма конфигурирани външни AI доставчици. "
                    "Проверете API ключовете в .env файла."
                ),
            )

            return redirect(
                "experiments:detail",
                pk=experiment.pk,
            )

        try:
            result = ExperimentResearchService().run_question(
                experiment=experiment,
                engineer_question=(
                    form.cleaned_data[
                        "engineer_question"
                    ]
                ),
                requested_by=request.user,
                provider_names=configured_providers,
            )

        except Exception as error:
            messages.error(
                request,
                (
                    "Външното AI проучване не можа да бъде "
                    "завършено: "
                    f"{type(error).__name__}: {error}"
                ),
            )

        else:
            successful_count = len(
                result.agent_result.successful_providers
            )

            failed_count = len(
                result.agent_result.failed_providers
            )

            if successful_count:
                messages.success(
                    request,
                    (
                        "Инженерният въпрос беше изпратен към "
                        f"{len(configured_providers)} външни AI "
                        "доставчици. "
                        f"Успешни отговори: {successful_count}. "
                        f"Неуспешни: {failed_count}."
                    ),
                )
            else:
                messages.error(
                    request,
                    (
                        "Нито един външен AI доставчик не върна "
                        "успешен структуриран резултат."
                    ),
                )

        return redirect(
            "experiments:detail",
            pk=experiment.pk,
        )


class ExperimentAnalyzeView(
    LoginRequiredMixin,
    ExperimentLockRequiredMixin,
    ExperimentObjectMixin,
    View,
):
    
    """
    Start the local engineering analysis for one Experiment.

    The analysis is executed synchronously by EngineeringAgent.
    The generated structured result, InternalAnalysis record and
    engineering proposals are persisted by the agent.
    """

    http_method_names = [
        "post",
    ]

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseRedirect:
        """
        Run the local Ollama engineering analysis.
        """

        experiment = self.get_object()

        try:
            result = EngineeringAgent().analyze(
                experiment=experiment,
                requested_by=request.user,
                persist=True,
            )

        except EngineeringAgentError as error:
            messages.error(
                request,
                (
                    "Локалният инженерeн анализ не можа "
                    f"да бъде завършен: {error}"
                ),
            )

        except Exception as error:
            messages.error(
                request,
                (
                    "Възникна неочаквана грешка при "
                    "локалния инженерeн анализ: "
                    f"{type(error).__name__}: {error}"
                ),
            )

        else:
            messages.success(
                request,
                (
                    "Локалният инженерeн анализ приключи успешно. "
                    f"Генерирани предложения: "
                    f"{result.proposal_count}."
                ),
            )

        return redirect(
            "experiments:detail",
            pk=experiment.pk,
        )

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
    ExperimentLockRequiredMixin,
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
        
        lock_response = self.ensure_experiment_lock(
            request=request,
            experiment=self.object,
        )

        if lock_response is not None:
            return lock_response

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
    ExperimentLockRequiredMixin,
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
        
        lock_response = self.ensure_experiment_lock(
            request=request,
            experiment=experiment,
        )

        if lock_response is not None:
            return lock_response

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
    ExperimentLockRequiredMixin,
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

        lock_response = self.ensure_experiment_lock(
            request=request,
            experiment=self.object,
        )

        if lock_response is not None:
            return lock_response

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
