"""
Django settings for Industrial Digital Twin Platform.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def get_boolean_environment(
    name: str,
    default: bool = False,
) -> bool:
    """
    Read a Boolean value from an environment variable.
    """

    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_list_environment(
    name: str,
    default: str = "",
) -> list[str]:
    """
    Read a comma-separated environment variable.
    """

    raw_value = os.getenv(name, default)

    return [
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    ]


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-development-only-change-me",
)

DEBUG = get_boolean_environment(
    "DJANGO_DEBUG",
    default=True,
)

ALLOWED_HOSTS = get_list_environment(
    "DJANGO_ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
)

CSRF_TRUSTED_ORIGINS = get_list_environment(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)

# Enable only when requests pass through a controlled reverse proxy.
TRUST_X_FORWARDED_FOR = get_boolean_environment(
    "TRUST_X_FORWARDED_FOR",
    default=False,
)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "core",
    "accounts",
    "digital_twins",
    "experiments",
    "ai_engine",
    "audit",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


LANGUAGE_CODE = "bg"

TIME_ZONE = "Europe/Sofia"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGIN_URL = "accounts:login"

LOGIN_REDIRECT_URL = "accounts:home"

LOGOUT_REDIRECT_URL = "accounts:login"


SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"

SECURE_CONTENT_TYPE_NOSNIFF = True
