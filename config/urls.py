from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls, ),
    path("", include("accounts.urls"), ),
    path("digital-twins/", include("digital_twins.urls"), ),
    path("experiments/", include("experiments.urls"), ),
    ]
