"""Parse and validate model answers before they become table rows."""

from __future__ import annotations

import json
import re

ICD10_PATTERN = re.compile(r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$")
ASSERTION_STATUSES = (
    "Present",
    "Absent",
    "Family",
    "Past",
    "Hypothetical",
    "Possible",
    "Conditional",
)
GENDERS = ("male", "female")


def parse_items(answer: str) -> list[dict]:
    """Parse a model answer that must be a JSON array of objects."""
    try:
        items = json.loads(answer)
    except json.JSONDecodeError as error:
        message = f"model answer is not JSON: {error.msg} at position {error.pos}"
        raise ValueError(message) from error
    if not isinstance(items, list):
        message = "model answer is not a JSON array"
        raise ValueError(message)
    return [item for item in items if isinstance(item, dict)]


def parse_object(answer: str) -> dict:
    """Parse a model answer that must be one JSON object."""
    try:
        item = json.loads(answer)
    except json.JSONDecodeError as error:
        message = f"model answer is not JSON: {error.msg} at position {error.pos}"
        raise ValueError(message) from error
    if not isinstance(item, dict):
        message = "model answer is not a JSON object"
        raise ValueError(message)
    return item


def _check_confidence(item: dict) -> str:
    confidence = item.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return "confidence is not a number"
    if not 0 <= float(confidence) <= 1:
        return "confidence is not between 0 and 1"
    return ""


def validate_icd10_item(item: dict) -> str:
    """Return the reason the coded indication is rejected, or "" when it is valid."""
    chunk = item.get("chunk")
    if not isinstance(chunk, str) or not chunk.strip():
        return "missing or empty chunk"
    code = item.get("icd10_code")
    if not isinstance(code, str) or not ICD10_PATTERN.match(code.strip()):
        return f"icd10_code {code!r} is not an ICD-10-CM code"
    hcc = item.get("hcc")
    if hcc is not None and (
        not isinstance(hcc, int) or isinstance(hcc, bool) or not 1 <= hcc <= 999
    ):
        return "hcc is not null or a number between 1 and 999"
    if item.get("assertion") not in ASSERTION_STATUSES:
        return f"assertion is not one of {ASSERTION_STATUSES}"
    return _check_confidence(item)


def validate_demographics_item(item: dict) -> str:
    """Return the reason the demographics answer is rejected, or "" when it is valid."""
    if item.get("gender") not in GENDERS:
        return f"gender is not one of {GENDERS}"
    age = item.get("age")
    if not isinstance(age, int) or isinstance(age, bool) or not 0 <= age <= 120:
        return "age is not a number between 0 and 120"
    return _check_confidence(item)
