from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class PlatformAuthenticationForm(AuthenticationForm):
    """
    Authentication form used by the industrial platform.

    Authentication remains based on Django's standard and tested
    AuthenticationForm. This class adds user-facing labels and widget
    attributes without changing the security logic.
    """

    username = forms.CharField(
        label="Потребителско име",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Потребителско име",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Парола",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Парола",
                "autocomplete": "current-password",
            }
        ),
    )