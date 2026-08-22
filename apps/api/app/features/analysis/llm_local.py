import logging

from app.config import Settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.analysis.llm_transport import ChatProviderTransport, LocalChatConfig

log = logging.getLogger(__name__)


class LocalMinutesExtractor(GroqMinutesExtractor):
    def __init__(self, settings: Settings) -> None:

        super().__init__(
            settings,
            transport=ChatProviderTransport(LocalChatConfig(settings)),
        )

    def _require_key(self) -> None:
        pass

    def _assert_model_available(self) -> None:

        return None
