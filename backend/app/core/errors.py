"""One exception hierarchy for the whole backend.

Every layer raises a MahdarError subclass carrying a message_key that
strings.py maps to Arabic user-facing text. The pipeline and the API
boundary translate these to the user's language; nothing else in the
backend raises ad-hoc exceptions with user-facing text.
"""


class MahdarError(Exception):
    """Base for all expected failures; message_key resolves to Arabic copy."""

    def __init__(self, message_key: str, technical: str = "") -> None:
        super().__init__(message_key)
        self.message_key = message_key
        self.technical = technical

    def with_available(self, model_ids: list[str]) -> "MahdarError":
        """Attaches the available model IDs a deprecated-model error names."""
        self.available = ", ".join(model_ids)
        return self


class AudioError(MahdarError):
    """Audio conversion, probing, or splitting failed."""


class TranscriptionError(MahdarError):
    """The speech-to-text provider failed or returned nothing usable."""


class DiarizationError(MahdarError):
    """Speaker diarization failed or was skipped."""


class AnalysisError(MahdarError):
    """Minutes extraction failed or produced an unusable payload."""


class UploadError(MahdarError):
    """The uploaded file failed validation or could not be stored."""
