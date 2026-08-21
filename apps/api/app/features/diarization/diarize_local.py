"""Local speaker diarization via pyannote, returning non-overlapping turns."""

import logging
import threading
from pathlib import Path

from app import constants
from app.config import Settings
from app.shared.errors import DiarizationError
from app.shared.models import Turn

log = logging.getLogger(__name__)

MODEL_ID = "pyannote/speaker-diarization-community-1"

_pipeline = None
_lock = threading.Lock()


class LocalDiarizer:
    """Separates speakers locally with pyannote into exclusive turns.

    torchaudio.load decodes the full waveform into RAM by design; the memory
    cost is constants.DIARIZATION_RAM_BYTES_PER_SECOND per second of audio
    (about 230 MB/hour at 16 kHz mono float32). This is the one intentional
    whole-file-in-memory case, documented in README and DECISIONS.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def diarize(self, wav_path: Path) -> list[Turn]:
        pipeline = self._load()
        waveform, sample_rate = _load_waveform(wav_path)
        output = pipeline({"waveform": waveform, "sample_rate": sample_rate})
        return _turns_from(output)

    def _load(self):
        global _pipeline
        if _pipeline is not None:
            return _pipeline
        with _lock:
            if _pipeline is None:
                _pipeline = _build_pipeline(self._settings)
        return _pipeline


def _build_pipeline(settings: Settings):
    from pyannote.audio import Pipeline  # lazy import keeps startup fast

    kwargs = {"token": settings.hf_token} if settings.hf_token else {}
    try:
        pipeline = Pipeline.from_pretrained(MODEL_ID, **kwargs)
    except Exception as exc:
        raise DiarizationError("diarize.skipped", f"pipeline load: {exc}") from exc
    log.info("Diarization pipeline loaded: %s", MODEL_ID)
    return pipeline


def _load_waveform(wav_path: Path):
    """Decode the pipeline-made 16 kHz mono WAV without torchaudio.

    torchaudio 2.11 decodes via torchcodec, whose binary needs system libs this
    slim image does not ship. to_wav16k_mono always writes 16-bit PCM, so the
    stdlib reader plus an int16 -> float32 rescale is exact.
    """
    import wave

    import torch

    try:
        with wave.open(str(wav_path), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise DiarizationError(
                    "diarize.skipped",
                    f"unexpected wav format: {wav.getnchannels()}ch/{wav.getsampwidth()}B",
                )
            raw = wav.readframes(wav.getnframes())
            sample_rate = wav.getframerate()
        # torch needs a writable tensor: bytes are read-only, so stage via bytearray
        samples = torch.frombuffer(bytearray(raw), dtype=torch.int16)
        return samples.float().div_(32768.0).unsqueeze(0), sample_rate
    except DiarizationError:
        raise
    except Exception as exc:
        raise DiarizationError("diarize.skipped", f"waveform load: {exc}") from exc


def _turns_from(output) -> list[Turn]:
    annotation = getattr(output, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = output.speaker_diarization
    return [
        Turn(start=round(turn.start, 3), end=round(turn.end, 3), speaker=speaker)
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]


def estimated_ram_bytes(duration_s: float) -> int:
    """RAM the diarizer needs for a clip of this length (float32 16 kHz mono)."""
    return int(duration_s * constants.DIARIZATION_RAM_BYTES_PER_SECOND)
