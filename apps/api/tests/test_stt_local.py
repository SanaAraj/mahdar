import sys
import types
from pathlib import Path

import pytest

from app.config import Settings
from app.features.transcription import stt_local
from app.features.transcription.stt_local import LocalTranscriber
from app.shared.errors import TranscriptionError
from app.shared.models import Word


class _FakeWord:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.word = text


class _FakeSegment:
    def __init__(self, words) -> None:
        self.words = words


class _FakeModel:
    kwargs: dict = {}
    raise_on: str | None = None

    def __init__(self, model_name: str, **kwargs) -> None:
        type(self).kwargs = {"model_name": model_name, **kwargs}
        if type(self).raise_on == "init":
            raise RuntimeError("weights missing")

    def transcribe(self, path: str, **kwargs):
        type(self).transcribe_call = {"path": path, **kwargs}
        if type(self).raise_on == "transcribe":
            raise RuntimeError("decode failed")
        segments = [
            _FakeSegment([_FakeWord(0.0, 0.4, "مرحبا"), _FakeWord(0.4, 0.9, "بكم")]),
            _FakeSegment([_FakeWord(1.0, 1.5, "  ")]),
        ]
        return segments, object()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, local_stt_model="large-v3-turbo")


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):

    monkeypatch.setattr(stt_local, "_model", None)
    _FakeModel.raise_on = None
    fake = types.SimpleNamespace(WhisperModel=_FakeModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    yield


def test_transcribe_returns_word_models(settings, tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"wav")
    words = LocalTranscriber(settings).transcribe(wav, tmp_path / "a.mp3")
    assert words == [
        Word(start=0.0, end=0.4, text="مرحبا"),
        Word(start=0.4, end=0.9, text="بكم"),
    ]
    call = _FakeModel.transcribe_call
    assert call["path"] == str(wav)
    assert call["language"] == "ar"
    assert call["word_timestamps"] is True
    assert call["vad_filter"] is True


def test_model_is_built_for_cpu_int8_under_the_data_volume(settings, tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"wav")
    LocalTranscriber(settings).transcribe(wav, tmp_path / "a.mp3")
    kwargs = _FakeModel.kwargs
    assert kwargs["model_name"] == "large-v3-turbo"
    assert kwargs["device"] == "cpu"
    assert kwargs["compute_type"] == "int8"

    assert kwargs["download_root"] == str(tmp_path / "hf")


def test_model_load_failure_maps_to_local_stt_failed(settings, tmp_path):
    _FakeModel.raise_on = "init"
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"wav")
    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber(settings).transcribe(wav, tmp_path / "a.mp3")
    assert exc.value.message_key == "local_stt.failed"


def test_transcribe_failure_maps_to_local_stt_failed(settings, tmp_path):
    _FakeModel.raise_on = "transcribe"
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"wav")
    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber(settings).transcribe(wav, tmp_path / "a.mp3")
    assert exc.value.message_key == "local_stt.failed"


def test_empty_result_maps_to_transcription_empty(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(_FakeModel, "transcribe", lambda self, p, **k: ([], object()))
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"wav")
    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber(settings).transcribe(wav, tmp_path / "a.mp3")
    assert exc.value.message_key == "transcription.empty"
