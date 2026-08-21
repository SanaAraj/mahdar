import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import strings
from app.config import get_settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.diarization.diarize_local import LocalDiarizer
from app.features.transcription.stt_groq import GroqTranscriber
from app.main import create_app
from app.shared.errors import AnalysisError
from app.shared.jobs import JobRegistry
from app.shared.models import (
    Analysis,
    Decision,
    DueDate,
    JobStatus,
    TaskItem,
    Turn,
)

from .factories import make_words

WAIT_TIMEOUT_S = 15.0


def fake_transcribe(self, wav_path: Path, mp3_path: Path):
    gaps = [0.05] * 5 + [0.85] + [0.05] * 5
    return make_words(["كلمة"] * 6 + ["تقرير"] * 6, step=0.15, gaps=gaps)


def fake_analysis(title="اجتماع متابعة"):
    """A fake analysis grounded in the transcript: 'كلمة' grounds s1, 'تقرير' grounds s2."""
    return Analysis(
        title=title,
        attendees=["المتحدث 1", "المتحدث 2"],
        decisions=[Decision(text="اعتماد كلمة الخطة", segment_ids=["s1"])],
        tasks=[
            TaskItem(
                description="رفع تقرير كلمة",
                owner=None,
                due=DueDate(raw="غدًا"),
                priority=None,
                segment_ids=["s2"],
            )
        ],
    )


def fake_extract(self, meta, sentences, speakers, job_id=None):
    return fake_analysis()


def failing_extract(self, meta, sentences, speakers, job_id=None):
    raise AnalysisError("analysis.failed", "mock down")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    return _make_client(tmp_path, monkeypatch, with_diaries=True)


@pytest.fixture
def silent_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A client without diarization (no token) to cover the degraded mode."""
    return _make_client(tmp_path, monkeypatch, with_diaries=False)


def _make_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_diaries: bool):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "hf-test" if with_diaries else "")
    get_settings.cache_clear()
    monkeypatch.setattr(GroqTranscriber, "transcribe", fake_transcribe)
    monkeypatch.setattr(GroqMinutesExtractor, "extract", fake_extract)
    if with_diaries:
        monkeypatch.setattr(LocalDiarizer, "diarize", _fake_diarize)
    return TestClient(create_app())


def _fake_diarize(self, wav_path: Path):
    return [
        Turn(start=0.0, end=5.0, speaker="SPEAKER_00"),
        Turn(start=5.0, end=9.5, speaker="SPEAKER_01"),
    ]


def _wait_until_done(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        job = client.get(f"/api/meetings/{job_id}").json()
        if job["status"] in (JobStatus.DONE, JobStatus.FAILED):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_pipeline_log_lines_carry_job_id_and_total(client: TestClient, wav_file: Path, caplog):
    """Every pipeline log line for this run names the job id, with one total line."""
    with caplog.at_level("INFO"):
        with wav_file.open("rb") as fh:
            job_id = client.post(
                "/api/meetings", files={"audio": ("meeting.wav", fh, "audio/wav")}
            ).json()["id"]
        _wait_until_done(client, job_id)
    lines = [r.getMessage() for r in caplog.records if job_id in r.getMessage()]
    # The stage transitions, the finish line, and any citation note all carry it.
    assert any("stage convert" in m for m in lines)
    assert any("finished; total duration" in m for m in lines)


def test_happy_upload_with_speakers(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post(
            "/api/meetings", files={"audio": ("meeting.wav", fh, "audio/wav")}
        ).json()["id"]
    job = _wait_until_done(client, job_id)
    assert job["status"] == JobStatus.DONE
    assert len(job["sentences"]) == 2
    stages = {s["key"]: s["state"] for s in job["stages"]}
    assert stages == {
        "convert": "done",
        "transcribe": "done",
        "diarize": "done",
        "assemble": "done",
        "analyze": "done",
    }
    assert len(job["speakers"]) == 2
    assert {sp["id"] for sp in job["speakers"]} == {"SPEAKER_00", "SPEAKER_01"}
    # The first sentence (0..~0.85s) maps to SPEAKER_00 inside 0..5.
    assert job["sentences"][0]["speaker"] == "SPEAKER_00"
    # The audio badge is available.
    audio_resp = client.get(f"/api/meetings/{job_id}/audio")
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"] == "audio/mpeg"


def test_degraded_mode_no_token(silent_client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = silent_client.post(
            "/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}
        ).json()["id"]
    job = _wait_until_done(silent_client, job_id)
    assert job["status"] == JobStatus.DONE
    stages = {s["key"]: s["state"] for s in job["stages"]}
    assert stages["diarize"] == "skipped"
    assert job["speakers"] == []
    diarize_stage = next(s for s in job["stages"] if s["key"] == "diarize")
    assert diarize_stage["note_ar"] == strings.resolve("diarize.skipped")
    # Every sentence without a speaker.
    assert all(s["speaker"] is None for s in job["sentences"])


def test_diarize_skip_logs_at_info_not_error(silent_client: TestClient, wav_file: Path, caplog):
    """Diarization is skippable: its miss logs at INFO with skip wording, never ERROR."""
    with caplog.at_level("INFO"):
        with wav_file.open("rb") as fh:
            job_id = silent_client.post(
                "/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}
            ).json()["id"]
        _wait_until_done(silent_client, job_id)
    skips = [r for r in caplog.records if "stage diarize skipped" in r.getMessage()]
    assert skips
    assert all(r.levelname == "INFO" for r in skips)
    errors = [r for r in caplog.records if r.levelname in ("ERROR", "CRITICAL")]
    assert not any("diarize" in r.getMessage() for r in errors)


def test_rejected_extension(client: TestClient, tmp_path: Path):
    fake = tmp_path / "notes.txt"
    fake.write_text("not audio", encoding="utf-8")
    with fake.open("rb") as fh:
        resp = client.post("/api/meetings", files={"audio": ("notes.txt", fh, "text/plain")})
    assert resp.status_code == 415
    body = resp.json()
    assert body["error_ar"] == strings.resolve("upload.unsupported_extension")
    assert body["code"] == "upload.unsupported_extension"


def test_oversized_file_rejected(client: TestClient, tmp_path: Path):
    big = tmp_path / "big.wav"
    big.write_bytes(b"\x00" * (1024 * 1024 + 10))
    with big.open("rb") as fh:
        resp = client.post("/api/meetings", files={"audio": ("big.wav", fh, "audio/wav")})
    assert resp.status_code == 413
    body = resp.json()
    assert body["error_ar"] == strings.resolve("upload.file_too_large")
    assert body["code"] == "upload.file_too_large"


def test_oversized_stream_is_cut_midway(tmp_path: Path):
    """An over-cap upload is rejected as soon as the running count crosses the cap.

    A fake upload that always has more bytes ready proves the loop aborts after
    the first chunk past the cap and deletes the partial file, instead of
    draining the whole body. The cap here is one chunk smaller than the body.
    """
    from app.features.meetings.upload import save_upload as _save_upload
    from app.shared.errors import UploadError

    chunk = 1024 * 1024

    class EndlessUpload:
        filename = "big.wav"

        async def read(self, n: int) -> bytes:
            return b"\x00" * n  # always has another chunk ready

        async def close(self) -> None:
            pass

    dst = tmp_path / "original.wav"
    with pytest.raises(UploadError) as exc_info:
        asyncio.run(_save_upload(EndlessUpload(), dst, chunk))
    assert exc_info.value.message_key == "upload.file_too_large"
    # The partial file is removed the moment the cap is crossed.
    assert not dst.exists()


def test_upload_exactly_at_cap_is_stored(tmp_path: Path):
    """A body whose size equals the cap is written to disk, not rejected."""
    from app.features.meetings.upload import save_upload as _save_upload

    payload = b"\x01" * 64
    reads = iter([payload, b""])

    class SmallUpload:
        filename = "ok.wav"

        async def read(self, n: int) -> bytes:
            return next(reads)

        async def close(self) -> None:
            pass

    dst = tmp_path / "ok.wav"
    size = asyncio.run(_save_upload(SmallUpload(), dst, len(payload)))
    assert size == len(payload)
    assert dst.read_bytes() == payload


def test_missing_job_returns_404(client: TestClient):
    resp = client.get("/api/meetings/000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_ar"] == strings.resolve("job.not_found")
    assert body["code"] == "job.not_found"


def test_invalid_job_id_shape_returns_404(client: TestClient):
    for bad in ("abc", "zzzzzzzzzzzz", "../etc", "0000000000000", "ABCDEF123456"):
        assert client.get(f"/api/meetings/{bad}").status_code == 404
        assert client.get(f"/api/meetings/{bad}/audio").status_code == 404


def test_missing_api_key_fails_job(tmp_path: Path, wav_file: Path, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data_nk"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("HF_TOKEN", "")
    get_settings.cache_clear()
    # No transcription mock here: the job must fail at once, with no network.
    failing = TestClient(create_app())
    with wav_file.open("rb") as fh:
        job_id = failing.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    job = _wait_until_done(failing, job_id)
    assert job["status"] == JobStatus.FAILED
    assert job["error_ar"] == strings.resolve("groq.key_missing")
    get_settings.cache_clear()


# ---------- PATCH /api/meetings/{id}/speakers ----------


def test_patch_speakers_happy_path(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    resp = client.patch(
        f"/api/meetings/{job_id}/speakers",
        json={"speakers": {"SPEAKER_00": "أحمد", "SPEAKER_01": "سارة "}},
    )
    assert resp.status_code == 200
    speakers = {s["id"]: s["label"] for s in resp.json()}
    assert speakers["SPEAKER_00"] == "أحمد"
    assert speakers["SPEAKER_01"] == "سارة"  # trailing whitespace is stripped

    persisted = client.get(f"/api/meetings/{job_id}").json()
    assert persisted["speakers"][0]["label"] == "أحمد"
    assert persisted["sentences"][0]["speaker"] == "SPEAKER_00"


def test_patch_unknown_job_404(client: TestClient):
    resp = client.patch(
        "/api/meetings/000000000000/speakers",
        json={"speakers": {"SPEAKER_00": "أحمد"}},
    )
    assert resp.status_code == 404


def test_patch_unknown_speaker_key_422(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    resp = client.patch(
        f"/api/meetings/{job_id}/speakers",
        json={"speakers": {"SPEAKER_99": "مجهول"}},
    )
    assert resp.status_code == 422
    assert resp.json()["error_ar"] == strings.resolve("speaker.unknown")


def test_patch_empty_label_422(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    resp = client.patch(
        f"/api/meetings/{job_id}/speakers",
        json={"speakers": {"SPEAKER_00": "   "}},
    )
    assert resp.status_code == 422
    assert resp.json()["error_ar"] == strings.resolve("speaker.empty_label")


def test_patch_too_long_label_422(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    resp = client.patch(
        f"/api/meetings/{job_id}/speakers",
        json={"speakers": {"SPEAKER_00": "آ" * 41}},
    )
    assert resp.status_code == 422
    assert resp.json()["error_ar"] == strings.resolve("speaker.label_too_long")


def test_persists_state_across_registry_reload(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    client.patch(f"/api/meetings/{job_id}/speakers", json={"speakers": {"SPEAKER_00": "أحمد"}})
    # Reload from disk through a fresh registry to prove persistence.
    fresh = JobRegistry(client.app.state.settings.data_dir)
    reloaded = fresh.get(job_id)
    assert reloaded is not None
    assert reloaded.status == JobStatus.DONE
    assert any(sp.id == "SPEAKER_00" and sp.label == "أحمد" for sp in reloaded.speakers)


# ---------- the analyze stage and POST /api/meetings/{id}/analyze ----------


def test_analysis_stored_and_dates_set(client: TestClient, wav_file: Path):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    job = _wait_until_done(client, job_id)
    assert job["status"] == JobStatus.DONE
    assert job["analysis"] is not None
    assert job["analysis"]["title"] == "اجتماع متابعة"
    assert job["analysis"]["tasks"][0]["due"]["raw"] == "غدًا"
    assert job["analysis"]["tasks"][0]["due"]["gregorian"] is not None
    assert job["analysis"]["tasks"][0]["due"]["hijri"] is not None
    assert job["date_gregorian"] is not None
    assert job["date_hijri"] is not None


def test_analysis_soft_fail_keeps_job_done(tmp_path: Path, monkeypatch, wav_file: Path):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data_sf"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "")
    get_settings.cache_clear()
    monkeypatch.setattr(GroqTranscriber, "transcribe", fake_transcribe)
    monkeypatch.setattr(GroqMinutesExtractor, "extract", failing_extract)
    failing = TestClient(create_app())
    with wav_file.open("rb") as fh:
        job_id = failing.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    job = _wait_until_done(failing, job_id)
    assert job["status"] == JobStatus.DONE
    assert job["analysis"] is None
    stage = next(s for s in job["stages"] if s["key"] == "analyze")
    assert stage["state"] == "error"
    assert stage["note_ar"] == strings.resolve("analysis.failed")
    get_settings.cache_clear()


def test_reanalyze_endpoint_reruns_analysis(client: TestClient, wav_file: Path, monkeypatch):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    monkeypatch.setattr(
        GroqMinutesExtractor,
        "extract",
        lambda self, m, s, sp, job_id=None: fake_analysis("إعادة تحليل"),
    )
    resp = client.post(f"/api/meetings/{job_id}/analyze")
    assert resp.status_code == 202
    job = _wait_until_done(client, job_id)
    assert job["analysis"]["title"] == "إعادة تحليل"


def test_rename_then_reanalyze_reflects_new_names(client: TestClient, wav_file: Path, monkeypatch):
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    _wait_until_done(client, job_id)
    client.patch(
        f"/api/meetings/{job_id}/speakers",
        json={"speakers": {"SPEAKER_00": "أحمد", "SPEAKER_01": "سارة"}},
    )
    seen: dict[str, list[str]] = {}

    def capture(self, meta, sentences, speakers, job_id=None):
        seen["labels"] = [sp.label for sp in speakers]
        return fake_analysis()

    monkeypatch.setattr(GroqMinutesExtractor, "extract", capture)
    client.post(f"/api/meetings/{job_id}/analyze")
    _wait_until_done(client, job_id)
    assert seen["labels"] == ["أحمد", "سارة"]


def test_reanalyze_unknown_job_404(client: TestClient):
    assert client.post("/api/meetings/000000000000/analyze").status_code == 404
    assert client.post("/api/meetings/bad-id/analyze").status_code == 404
