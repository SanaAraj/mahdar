import json
import re

from pydantic import ValidationError

from app import constants
from app.shared.errors import AnalysisError
from app.shared.models import (
    Analysis,
    Decision,
    Directive,
    DueDate,
    TaskItem,
    Topic,
)

_SCHEMA_FIELDS: frozenset[str] = frozenset(
    name
    for model in (Analysis, Topic, Decision, Directive, TaskItem, DueDate)
    for name in model.model_fields
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


_ARABIC_RE = re.compile(f"[{constants.ARABIC_RTL_RANGES}]")


def strip_reasoning(content: str) -> str:

    return _THINK_RE.sub("", content)


def has_arabic_output(analysis: Analysis) -> bool:

    surfaces = [analysis.title, *(topic.summary for topic in analysis.topics)]
    return any(_ARABIC_RE.search(surface) for surface in surfaces)


def content_from(resp) -> str:
    try:
        payload = resp.json()
    except ValueError as exc:
        raise AnalysisError("analysis.failed", "invalid json envelope") from exc
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise AnalysisError("analysis.failed", "missing choices content") from exc


def normalize_schema_keys(value: object) -> object:

    if isinstance(value, dict):
        renamed: dict = {}
        for key, item in value.items():
            new_key = key
            if (
                isinstance(key, str)
                and key not in _SCHEMA_FIELDS
                and key.lower() in _SCHEMA_FIELDS
                and key.lower() not in value
            ):
                new_key = key.lower()
            renamed[new_key] = normalize_schema_keys(item)
        return renamed
    if isinstance(value, list):
        return [normalize_schema_keys(item) for item in value]
    return value


def json_object(content: str) -> dict:

    text = strip_reasoning(content)
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValidationError.from_exception_data(
            "Analysis",
            [{"type": "missing", "loc": (), "input": content[: constants.ERROR_SNIPPET_CHARS]}],
        )
    try:
        return normalize_schema_keys(json.loads(text[start : end + 1]))
    except (ValueError, TypeError) as exc:
        raise ValidationError.from_exception_data(
            "Analysis",
            [
                {
                    "type": "value_error",
                    "loc": (),
                    "input": text[start : start + constants.ERROR_SNIPPET_CHARS],
                }
            ],
        ) from exc
