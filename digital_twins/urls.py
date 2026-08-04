"""
URL configuration for Digital Twin management.
"""

from django.urls import path

from digital_twins.views import (
    DigitalTwinActivateView,
    DigitalTwinCreateView,
    DigitalTwinDeactivateView,
    DigitalTwinDeleteView,
    DigitalTwinDetailView,
    DigitalTwinFileCreateView,
    DigitalTwinListView,
    DigitalTwinUpdateView,
)


app_name = "digital_twins"


urlpatterns = [
    path("", DigitalTwinListView.as_view(), name="list", ),
    path("create/", DigitalTwinCreateView.as_view(), name="create", ),
    path("<uuid:pk>/", DigitalTwinDetailView.as_view(), name="detail", ),
    path("<uuid:pk>/files/add/", DigitalTwinFileCreateView.as_view(), name="file_create", ),
    path("<uuid:pk>/update/", DigitalTwinUpdateView.as_view(), name="update", ),
    path("<uuid:pk>/activate/", DigitalTwinActivateView.as_view(), name="activate", ),
    path("<uuid:pk>/deactivate/", DigitalTwinDeactivateView.as_view(), name="deactivate", ),
    path("<uuid:pk>/delete/", DigitalTwinDeleteView.as_view(), name="delete", ),
]
