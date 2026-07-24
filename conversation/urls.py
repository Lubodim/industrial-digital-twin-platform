from django.urls import path

from conversation import views


app_name = "conversation"


urlpatterns = [
    path("global/", views.global_chat_view, name="global_chat",),
    path("global/new/", views.create_global_conversation_view, name="create_global_conversation",),
    path("global/<uuid:conversation_id>/", views.global_chat_view, name="global_chat_detail",),
    path("global/<uuid:conversation_id>/send/", views.send_global_message_view, name="send_global_message",),
]