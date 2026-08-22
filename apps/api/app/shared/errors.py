class MahdarError(Exception):
    def __init__(self, message_key: str, technical: str = "") -> None:
        super().__init__(message_key)
        self.message_key = message_key
        self.technical = technical

    def with_available(self, model_ids: list[str]) -> "MahdarError":

        self.available = ", ".join(model_ids)
        return self


class AudioError(MahdarError):
    pass


class TranscriptionError(MahdarError):
    pass


class DiarizationError(MahdarError):
    pass


class AnalysisError(MahdarError):
    pass


class UploadError(MahdarError):
    pass
