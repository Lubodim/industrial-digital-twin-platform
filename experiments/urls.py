"""
URL configuration for Experiment management.
"""

from django.urls import path

from experiments.views import (
    ExperimentArchiveView,
    ExperimentCreateView,
    ExperimentDeleteView,
    ExperimentDetailView,
    ExperimentListView,
    ExperimentUpdateView,
)

app_name = "experiments"

urlpatterns = [
    path("", ExperimentListView.as_view(), name="list", ),
    path("create/", ExperimentCreateView.as_view(), name="create", ),
    path("<uuid:pk>/", ExperimentDetailView.as_view(), name="detail", ),
    path("<uuid:pk>/update/", ExperimentUpdateView.as_view(), name="update", ),
    path("<uuid:pk>/archive/", ExperimentArchiveView.as_view(), name="archive", ),
    path("<uuid:pk>/delete/", ExperimentDeleteView.as_view(), name="delete", ),
]