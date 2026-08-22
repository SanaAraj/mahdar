import struct
import sys
import types
import wave
from pathlib import Path

import pytest

from app.features.diarization import diarize_local
from app.shared.errors import DiarizationError


class _FakeTensor:
    def __init__(self, values, dtype):
        scale = 32768.0 if dtype == "int16" else 1.0
        self._values = [v / scale for v in values] if dtype == "int16" else list(values)

    def float(self):
        return self

    def div_(self, scalar):
        return self

    def unsqueeze(self, dim):
        assert dim == 0
        return self

    @property
    def shape(self):
        return (1, len(self._values))

    def tolist(self):
        return self._values

    def abs(self):
        return _FakeTensor([abs(v) for v in self._values], "float32")

    def max(self):
        return _FakeTensor([max(self._values)], "float32")

    def item(self):
        return self._values[0]

    def __getitem__(self, i):
        return _FakeTensor(self._values, "float32") if i == 0 else None


def _fake_torch():
    mod = types.ModuleType("torch")
    mod.int16 = "int16"
    mod.frombuffer = lambda buf, dtype: _FakeTensor(
        struct.unpack(f"<{len(buf) // 2}h", bytes(buf)), dtype
    )
    return mod


@pytest.fixture(autouse=True)
def _no_torch(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch())
    yield
    monkeypatch.undo()


def _write_wav(path: Path, samples: list[int], channels: int = 1, rate: int = 16000) -> None:
    frames = struct.pack(f"<{len(samples)}h", *samples)
    if channels == 2:
        frames = b"".join(struct.pack("<hh", v, v) for v in samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def test_load_waveform_int16_full_scale(tmp_path: Path) -> None:
    wav = tmp_path / "tone.wav"
    _write_wav(wav, [0, 32767, -32768])
    waveform, rate = diarize_local._load_waveform(wav)
    assert rate == 16000
    assert tuple(waveform.shape) == (1, 3)
    values = waveform[0].tolist()
    assert values[0] == 0.0
    assert values[1] == pytest.approx(32767 / 32768.0)
    assert values[2] == -1.0


def test_load_waveform_silence_roundtrip(tmp_path: Path) -> None:
    wav = tmp_path / "quiet.wav"
    _write_wav(wav, [0] * 16000)
    waveform, rate = diarize_local._load_waveform(wav)
    assert rate == 16000
    assert waveform.abs().max().item() == 0.0


def test_load_waveform_rejects_corrupt_file(tmp_path: Path) -> None:
    bad = tmp_path / "garbage.wav"
    bad.write_bytes(b"not a wav at all")
    with pytest.raises(DiarizationError) as excinfo:
        diarize_local._load_waveform(bad)
    assert excinfo.value.message_key == "diarize.skipped"


def test_load_waveform_rejects_stereo(tmp_path: Path) -> None:
    stereo = tmp_path / "stereo.wav"
    _write_wav(stereo, [100, 200, 300], channels=2)
    with pytest.raises(DiarizationError) as excinfo:
        diarize_local._load_waveform(stereo)
    assert excinfo.value.message_key == "diarize.skipped"
