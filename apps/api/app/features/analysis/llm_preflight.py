import logging

import httpx

from app import constants
from app.config import Settings

log = logging.getLogger(__name__)

_models_cache: frozenset[str] | None = None


_CHAT_PREFIXES = ("openai/", "meta-llama/", "qwen/", "allam", "groq/compound")


def available_models(settings: Settings) -> frozenset[str]:

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
        resp.raise_for_status()
        ids = {m["id"] for m in resp.json().get("data", []) if "id" in m}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("Groq /models preflight failed, skipping check: %s", exc)
        return frozenset()
    _models_cache = frozenset(ids)
    log.info("Groq /models preflight: %d model(s) available", len(_models_cache))
    return _models_cache


def suggest_models(available: frozenset[str]) -> list[str]:

    chat = sorted(m for m in available if m.startswith(_CHAT_PREFIXES))
    if not chat:
        chat = list(constants.FALLBACK_CHAT_MODELS)
    return chat[: constants.CHAT_MODEL_SUGGESTION_COUNT]
