from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Shared infrastructure for the Industrial Digital Twin Platform.

    This application contains reusable components shared by all
    business modules.
    """

    default_auto_field = "django.db.models.BigAutoField"

    name = "core"

    verbose_name = "Core Infrastructure"
