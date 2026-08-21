"""Reply-cleaning for the minutes extractor: reasoning blocks, code fences, and
the JSON object inside the model's envelope.

These helpers are pure functions of the model's raw content string, kept apart
from the transport and the two-call orchestration in llm_groq.py. The think-tag
strip and the fence extraction are lossy by design: the goal is the JSON object,
and anything outside it is the model's own narration, never shown to the user.
"""

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

# Every field name of the analysis schema, at every nesting level. Derived from
# the pydantic models so a schema change can never leave this set stale.
_SCHEMA_FIELDS: frozenset[str] = frozenset(
    name
    for model in (Analysis, Topic, Decision, Directive, TaskItem, DueDate)
    for name in model.model_fields
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

# Arabic detection for the output guard. The constant is a character-class body,
# not a full pattern (see processing/docx_rtl.py for the same wrapped usage), so
# it is compiled inside brackets; a bare compile would match a literal sequence.
_ARABIC_RE = re.compile(f"[{constants.ARABIC_RTL_RANGES}]")


def strip_reasoning(content: str) -> str:
    """Remove reasoning-model think blocks; the direct product of _THINK_RE."""
    return _THINK_RE.sub("", content)


def has_arabic_output(analysis: Analysis) -> bool:
    """True when the title or any topic summary carries an Arabic character.

    The output guard gates a reply that parsed cleanly but came back English.
    Checking the title plus every topic summary catches the common case of a
    model that translated its whole output; a grounded reply always names its
    topics in Arabic because the transcript it cites is Arabic.
    """
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
    """Rename keys whose lowercase form is a schema field name; values never change.

    A deterministic repair for a model that mirrors the uppercase markers of
    the reduce input (TITLE, SEGMENT_IDS) as JSON keys. A key is renamed only
    when its lowercase form is a known field and the dict does not already
    carry that exact field, so a correctly-cased reply passes through as is.
    """
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
    """Strips reasoning blocks and fences, then parses and key-repairs the object."""
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
