"""
Common constants shared across the entire platform.

This module intentionally contains only immutable values.
"""

from __future__ import annotations


# ------------------------------------------------------------------
# Pagination
# ------------------------------------------------------------------

DEFAULT_PAGE_SIZE = 20

SMALL_PAGE_SIZE = 10

LARGE_PAGE_SIZE = 50


# ------------------------------------------------------------------
# Date / Time
# ------------------------------------------------------------------

DISPLAY_DATE_FORMAT = "%d.%m.%Y"

DISPLAY_DATETIME_FORMAT = "%d.%m.%Y %H:%M"


# ------------------------------------------------------------------
# Session
# ------------------------------------------------------------------

DEFAULT_SESSION_TIMEOUT_MINUTES = 30


# ------------------------------------------------------------------
# Experiment
# ------------------------------------------------------------------

MAX_ENGINEERING_QUESTION_LENGTH = 5000

MAX_CHAT_MESSAGE_LENGTH = 8000


# ------------------------------------------------------------------
# File upload
# ------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB = 50


# ------------------------------------------------------------------
# AI Providers
# ------------------------------------------------------------------

SUPPORTED_AI_PROVIDERS = (
    "OPENAI",
    "GEMINI",
    "CLAUDE",
    "GROK",
)

DEFAULT_EXTERNAL_PROVIDER = "OPENAI"

DEFAULT_CHAT_PROVIDER = "GEMINI"


# ------------------------------------------------------------------
# User Roles
# ------------------------------------------------------------------

ROLE_ADMIN = "Administrator"

ROLE_ENGINEER = "Engineer"

ROLE_VIEWER = "Viewer"


# ------------------------------------------------------------------
# HTTP
# ------------------------------------------------------------------

HTTP_GET = "GET"

HTTP_POST = "POST"

HTTP_PUT = "PUT"

HTTP_DELETE = "DELETE"
