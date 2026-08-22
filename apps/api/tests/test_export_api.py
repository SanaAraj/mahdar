import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.transcription.stt_groq import GroqTranscriber
from app.main import create_app
from app.shared.errors import AnalysisError
from app.shared.models import (
    Analysis,
    Decision,
    DueDate,
    JobStatus,
    TaskItem,
)

from .test_api import fake_transcribe

WAIT_TIMEOUT_S = 15.0


def grounded_extract(self, meta, sentences, speakers, job_id=None):

    return Analysis(
        title="اجتماع متابعة",
        attendees=["المتحدث 1"],
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


def failing_extract(self, meta, sentences, speakers, job_id=None):
    raise AnalysisError("analysis.failed", "mock down")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("MAX_ACTIVE_JOBS", "8")
    get_settings.cache_clear()
    monkeypatch.setattr(GroqTranscriber, "transcribe", fake_transcribe)
    monkeypatch.setattr(GroqMinutesExtractor, "extract", grounded_extract)
    return TestClient(create_app())


def _done_job(client: TestClient, wav_file: Path) -> str:
    with wav_file.open("rb") as fh:
        job_id = client.post("/api/meetings", files={"audio": ("m.wav", fh, "audio/wav")}).json()[
            "id"
        ]
    deadline = time.monotonic() + WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        job = client.get(f"/api/meetings/{job_id}").json()
        if job["status"] in (JobStatus.DONE, JobStatus.FAILED):
            return job_id
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


def test_export_json_shape_and_headers(client: TestClient, wav_file: Path):
    job_id = _done_job(client, wav_file)
    resp = client.get(f"/api/meetings/{job_id}/export/json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.headers["content-disposition"] == f'attachment; filename="mahdar-{job_id}.json"'
    body = resp.json()
    assert set(body) == {"meta", "speakers", "sentences", "analysis"}
    assert set(body["meta"]) == {
        "id",
        "created_at",
        "date_gregorian",
        "date_hijri",
        "duration_s",
    }
    assert body["meta"]["id"] == job_id

    assert "stages" not in body and "status" not in body and "error_ar" not in body
    assert body["sentences"][0]["id"] == "s1"
    assert set(body["sentences"][0]) == {"id", "start", "end", "text", "speaker"}
    assert body["analysis"]["title"] == "اجتماع متابعة"


def test_export_docx_media_type_and_file(client: TestClient, wav_file: Path):
    job_id = _done_job(client, wav_file)
    resp = client.get(f"/api/meetings/{job_id}/export/docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert f"mahdar-{job_id}.docx" in resp.headers["content-disposition"]
    assert resp.content[:2] == b"PK"

    job_dir = client.app.state.settings.data_dir / job_id
    assert (job_dir / "export.docx").exists()

    assert not list(job_dir.glob("export.*.docx.tmp"))


def test_export_docx_is_writable_concurrently(client: TestClient, wav_file: Path):

    import threading

    job_id = _done_job(client, wav_file)
    results: list[bytes] = []
    errors: list[Exception] = []

    def fetch():
        try:
            results.append(client.get(f"/api/meetings/{job_id}/export/docx").content)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=fetch) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors

    assert all(b[:2] == b"PK" and b[-22:] != b"" for b in results)
    assert len(set(results)) == 1


def test_export_endpoints_guard_unknown_and_bad_ids(client: TestClient):
    for bad in ("000000000000", "bad-id", "../../../etc"):
        assert client.get(f"/api/meetings/{bad}/export/json").status_code == 404
        assert client.get(f"/api/meetings/{bad}/export/docx").status_code == 404


def test_export_after_failed_analysis_still_serves_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path
):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data_sf"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("MAX_ACTIVE_JOBS", "8")
    get_settings.cache_clear()
    monkeypatch.setattr(GroqTranscriber, "transcribe", fake_transcribe)
    monkeypatch.setattr(GroqMinutesExtractor, "extract", failing_extract)
    client = TestClient(create_app())
    job_id = _done_job(client, wav_file)
    resp = client.get(f"/api/meetings/{job_id}/export/json")
    assert resp.status_code == 200
    assert resp.json()["analysis"] is None
    assert len(resp.json()["sentences"]) == 2
    docx = client.get(f"/api/meetings/{job_id}/export/docx")
    assert docx.status_code == 200 and docx.content[:2] == b"PK"


def test_export_of_an_unfinished_job_is_rejected(client: TestClient):

    from app import strings

    client.app.state.registry.create("aaaabbbbcccc")
    for kind in ("json", "docx"):
        resp = client.get(f"/api/meetings/aaaabbbbcccc/export/{kind}")
        assert resp.status_code == 409
        assert resp.json()["error_ar"] == strings.resolve("audio.not_ready")
