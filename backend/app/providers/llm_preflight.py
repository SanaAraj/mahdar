"""The Groq model-catalog preflight for the minutes extractor.

Fetched live once per process from GET /models so a retired configured model is
caught before any analysis call, with a curated chat-id suggestion list when the
live listing cannot be read. The module-level cache is process state by design;
tests reset it by patching this module's attribute.
"""

import logging

import httpx

from backend.app import constants
from backend.app.config import Settings

log = logging.getLogger(__name__)

_models_cache: frozenset[str] | None = None

# Chat-family model id prefixes; used when /models cannot be parsed into a
# helpful suggestion list (empty, unreachable, or a non-chat-only listing).
_CHAT_PREFIXES = ("openai/", "meta-llama/", "qwen/", "allam", "groq/compound")


def available_models(settings: Settings) -> frozenset[str]:
    """Live IDs once per process; empty set on any failure (no crash)."""
    global _models_cache
    if _models_cache is not None:
        return _models_cache
    if not settings.groq_api_key:
        return frozenset()
    url = constants.GROQ_API_BASE + constants.MODELS_API_PATH
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    try:
        with httpx.Client(timeout=constants.MODELS_TIMEOUT_S) as client:
            resp = client.get(url, headers=headers)
        ids = {m["id"] for m in resp.json().get("data", []) if "id" in m}
        _models_cache = frozenset(ids)
        log.info("Groq /models preflight: %d model(s) available", len(_models_cache))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("Groq /models preflight failed, skipping check: %s", exc)
        _models_cache = frozenset()
    return _models_cache


def suggest_models(available: frozenset[str]) -> list[str]:
    """Pick up to CHAT_MODEL_SUGGESTION_COUNT chat ids the user can switch to.

    Prefer current Groq chat models the account actually lists, and fall back
    to the curated constant when the listing is empty or unhelpful.
    """
    chat = sorted(m for m in available if m.startswith(_CHAT_PREFIXES))
    if not chat:
        chat = list(constants.FALLBACK_CHAT_MODELS)
    return chat[: constants.CHAT_MODEL_SUGGESTION_COUNT]
