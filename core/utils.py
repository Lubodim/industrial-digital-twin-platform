"""
General reusable utility helpers.

These helpers are intentionally framework-independent whenever possible.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def generate_uuid() -> str:
    """
    Return a random UUID4 string.
    """

    return str(uuid4())


def utc_timestamp() -> datetime:
    """
    Return current UTC datetime.
    """

    return datetime.utcnow()


def ensure_directory_exists(
    directory: str | Path,
) -> Path:
    """
    Create directory if necessary.
    """

    directory = Path(directory)

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def safe_filename(
    filename: str,
) -> str:
    """
    Remove characters that are unsafe for file systems.
    """

    invalid = '<>:"/\\|?*'

    for character in invalid:
        filename = filename.replace(
            character,
            "_",
        )

    return filename.strip()


def read_json_file(
    path: str | Path,
) -> dict[str, Any]:
    """
    Load JSON from disk.
    """

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def write_json_file(
    path: str | Path,
    data: dict[str, Any],
) -> None:
    """
    Save JSON using UTF-8.
    """

    path = Path(path)

    ensure_directory_exists(
        path.parent,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4,
        )


def is_json_serializable(
    value: Any,
) -> bool:
    """
    Check whether a value can be serialized as JSON.
    """

    try:

        json.dumps(
            value,
            ensure_ascii=False,
        )

        return True

    except TypeError:

        return False


def truncate_text(
    text: str,
    max_length: int,
) -> str:
    """
    Truncate long text.

    Ellipsis is appended when truncation occurs.
    """

    if len(text) <= max_length:
        return text

    if max_length <= 3:
        return text[:max_length]

    return text[: max_length - 3] + "..."


def format_bytes(
    size: int,
) -> str:
    """
    Human-readable file size.
    """

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    )

    value = float(size)

    for unit in units:

        if value < 1024:

            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PB"
