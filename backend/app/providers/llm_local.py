"""Minutes extraction against a local Ollama server (offline fallback).

Reuses the shared OpenAI-compatible transport (providers/llm_transport), so the
request bytes, the include_reasoning handling, the Retry-After retries, the
reply cleaning, the schema retry, the Arabic-output guard, the token budgets,
and the map-reduce window path are exactly the cloud extractor's. What differs
is only the wiring: no API key and no /models preflight, because the compose
"local" service pulls the configured model at startup and serves without auth.
The label and the error-key prefix ("local_llm") route failures to the local
Arabic copy instead of the Groq one.
"""

import logging

from backend.app.config import Settings
from backend.app.providers.llm_groq import GroqMinutesExtractor
from backend.app.providers.llm_transport import ChatProviderTransport, LocalChatConfig

log = logging.getLogger(__name__)


class LocalMinutesExtractor(GroqMinutesExtractor):
    """Minutes from the local LLM, inheriting every guard; skips key and preflight."""

    def __init__(self, settings: Settings) -> None:
        # A local endpoint never forwards include_reasoning, so no flag cell.
        super().__init__(
            settings,
            transport=ChatProviderTransport(LocalChatConfig(settings)),
        )

    def _require_key(self) -> None:
        pass  # a local server needs no key

    def _assert_model_available(self) -> None:
        # The compose "local" service pulls LOCAL_LLM_MODEL at startup; a live
        # /models preflight against the local endpoint would add a failure mode
        # for no information, so it is deliberately skipped.
        return None
