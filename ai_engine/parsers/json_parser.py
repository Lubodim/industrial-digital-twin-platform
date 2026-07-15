from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JSONParseResult:
    """
    Result returned after attempting to parse an AI provider response.
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    cleaned_text: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "error_message": self.error_message,
        }


def _remove_markdown_code_fences(text: str) -> str:
    """
    Remove Markdown code fences such as:

    ```json
    {...}
    ```
    """

    cleaned = text.strip()

    fenced_pattern = re.compile(
        r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
        re.IGNORECASE | re.DOTALL,
    )

    match = fenced_pattern.match(cleaned)

    if match:
        return match.group(1).strip()

    return cleaned


def _extract_json_object(text: str) -> str | None:
    """
    Extract the first complete JSON object from surrounding text.

    The function respects quoted strings and escaped characters.
    """

    start_index = text.find("{")

    if start_index == -1:
        return None

    depth = 0
    inside_string = False
    escape_next = False

    for index in range(start_index, len(text)):
        character = text[index]

        if escape_next:
            escape_next = False
            continue

        if character == "\\" and inside_string:
            escape_next = True
            continue

        if character == '"':
            inside_string = not inside_string
            continue

        if inside_string:
            continue

        if character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                return text[start_index:index + 1]

    return None


def parse_json_response(raw_response: Any) -> JSONParseResult:
    """
    Parse an external AI response into a JSON dictionary.

    Supported situations:
    - plain JSON object;
    - JSON wrapped in Markdown code fences;
    - explanatory text around a JSON object;
    - UTF-8 BOM at the beginning of the response.

    The function does not validate the engineering schema.
    Schema validation is handled separately by validators.py.
    """

    if not isinstance(raw_response, str):
        return JSONParseResult(
            success=False,
            raw_text=str(raw_response),
            error_message="AI response must be a string.",
        )

    original_text = raw_response

    cleaned_text = raw_response.lstrip("\ufeff").strip()
    cleaned_text = _remove_markdown_code_fences(cleaned_text)

    if not cleaned_text:
        return JSONParseResult(
            success=False,
            raw_text=original_text,
            cleaned_text=cleaned_text,
            error_message="AI response is empty.",
        )

    try:
        parsed = json.loads(cleaned_text)

    except json.JSONDecodeError:
        extracted_json = _extract_json_object(cleaned_text)

        if extracted_json is None:
            return JSONParseResult(
                success=False,
                raw_text=original_text,
                cleaned_text=cleaned_text,
                error_message="No complete JSON object was found.",
            )

        try:
            parsed = json.loads(extracted_json)
            cleaned_text = extracted_json

        except json.JSONDecodeError as error:
            return JSONParseResult(
                success=False,
                raw_text=original_text,
                cleaned_text=extracted_json,
                error_message=(
                    "Invalid JSON response: "
                    f"{error.msg} at line {error.lineno}, "
                    f"column {error.colno}."
                ),
            )

    if not isinstance(parsed, dict):
        return JSONParseResult(
            success=False,
            raw_text=original_text,
            cleaned_text=cleaned_text,
            error_message="The top-level JSON value must be an object.",
        )

    return JSONParseResult(
        success=True,
        data=parsed,
        raw_text=original_text,
        cleaned_text=cleaned_text,
    )