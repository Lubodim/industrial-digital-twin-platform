from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls, ),
    path("", include("accounts.urls"), ),
    path("digital-twins/", include("digital_twins.urls"), ),
    path("experiments/", include("experiments.urls"), ),
    path("conversations/", include("conversation.urls"),),
    ]
if settings.DEBUG:
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, )