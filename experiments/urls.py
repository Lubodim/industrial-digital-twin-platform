"""
URL configuration for Experiment management.
"""

from django.urls import path

from experiments.views import (
    ExperimentAnalyzeView,
    ExperimentAcquireLockView,
    ExperimentArchiveView,
    ExperimentCreateView,
    ExperimentDeleteView,
    ExperimentDetailView,
    ExperimentListView,
    ExperimentProposalListView,
    ExperimentReleaseLockView,
    ExperimentResearchQuestionView,
    ExperimentUpdateView,
)


app_name = "experiments"


urlpatterns = [
    path("", ExperimentListView.as_view(), name="list", ),
    path("create/", ExperimentCreateView.as_view(), name="create", ),
    path("<uuid:pk>/", ExperimentDetailView.as_view(), name="detail", ),
    path("<uuid:pk>/lock/", ExperimentAcquireLockView.as_view(), name="acquire_lock", ),
    path("<uuid:pk>/unlock/", ExperimentReleaseLockView.as_view(), name="release_lock", ),
    path("<uuid:pk>/analyze/", ExperimentAnalyzeView.as_view(), name="analyze", ),
    path("<uuid:pk>/update/", ExperimentUpdateView.as_view(), name="update", ),
    path("<uuid:pk>/archive/", ExperimentArchiveView.as_view(), name="archive", ),
    path("<uuid:pk>/delete/", ExperimentDeleteView.as_view(), name="delete", ),
    path("<uuid:pk>/research/question/", ExperimentResearchQuestionView.as_view(), name="research_question", ),
    path("<uuid:pk>/proposals/", ExperimentProposalListView.as_view(), name="proposals", ),
]

