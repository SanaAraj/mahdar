import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from backend.app import constants
from backend.app.core.errors import UploadError
from backend.app.core.export import build_export, export_filename
from backend.app.core.jobs import JobRegistry
from backend.app.core.models import JobStatus, MeetingJob, Speaker
from backend.app.core.pipeline import Pipeline
from backend.app.processing import docx_build

router = APIRouter()

JOB_ID_RE = re.compile(rf"^[0-9a-f]{{{constants.JOB_ID_LENGTH}}}$")


class MessageError(Exception):
    """An API-boundary error that the handler renders as {"error_ar", "code"}."""

    def __init__(self, status_code: int, message_key: str) -> None:
        super().__init__(message_key)
        self.status_code = status_code
        self.message_key = message_key


class SpeakersUpdate(BaseModel):
    speakers: dict[str, str] = Field(default_factory=dict)


def _not_found() -> MessageError:
    return MessageError(404, "job.not_found")


def _registry(request: Request) -> JobRegistry:
    return request.app.state.registry


def _pipeline(request: Request) -> Pipeline:
    return request.app.state.pipeline


def _get_job(request: Request, job_id: str) -> MeetingJob:
    if not JOB_ID_RE.fullmatch(job_id):
        raise _not_found()
    job = _registry(request).get(job_id)
    if job is None:
        raise _not_found()
    return job


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/meetings", status_code=201)
async def create_meeting(
    request: Request,
    audio: Annotated[UploadFile, File()],
) -> dict[str, str]:
    registry = _registry(request)
    max_bytes = request.app.state.settings.max_upload_bytes
    extension = _extension_of(audio.filename or "")
    if extension not in constants.ALLOWED_EXTENSIONS:
        raise MessageError(415, "upload.unsupported_extension")
    job_id = uuid.uuid4().hex[: constants.JOB_ID_LENGTH]
    job_dir = registry.job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    original = job_dir / f"original.{extension}"
    try:
        size = await _save_upload(audio, original, max_bytes)
    except UploadError:
        raise MessageError(413, "upload.file_too_large") from None
    if size == 0:
        original.unlink(missing_ok=True)
        raise MessageError(422, "audio.corrupt")
    registry.create(job_id)
    _pipeline(request).start(job_id)
    return {"id": job_id}


@router.get("/meetings/{job_id}")
def get_meeting(request: Request, job_id: str) -> MeetingJob:
    return _get_job(request, job_id)


@router.get("/meetings/{job_id}/audio")
def get_audio(request: Request, job_id: str) -> FileResponse:
    job = _get_job(request, job_id)
    mp3 = _registry(request).job_dir(job.id) / "audio.mp3"
    if not mp3.exists():
        raise MessageError(404, "audio.not_ready")
    return FileResponse(mp3, media_type="audio/mpeg", filename="meeting.mp3")


@router.patch("/meetings/{job_id}/speakers")
def update_speakers(request: Request, job_id: str, body: SpeakersUpdate) -> list[Speaker]:
    job = _get_job(request, job_id)
    mapping = _validated_mapping(body.speakers, job)
    _registry(request).rename_speakers(job.id, mapping)
    return _registry(request).get(job.id).speakers


@router.post("/meetings/{job_id}/analyze", status_code=202)
def reanalyze(request: Request, job_id: str) -> dict[str, str]:
    """Re-run analysis on the stored transcript without re-transcribing."""
    job = _get_job(request, job_id)
    if not job.sentences:
        raise MessageError(409, "analysis.transcript_missing")
    if job.status is JobStatus.ANALYZING:
        return {"id": job.id}  # an analysis is already running; the request is a duplicate
    if job.status is not JobStatus.DONE:
        raise MessageError(409, "analysis.transcript_missing")
    _pipeline(request).start_analysis(job.id)
    return {"id": job.id}


def _require_done(job: MeetingJob) -> None:
    """Exports exist only for a finished meeting; anything else is not ready."""
    if job.status is not JobStatus.DONE:
        raise MessageError(409, "audio.not_ready")


@router.get("/meetings/{job_id}/export/json")
def export_json(request: Request, job_id: str) -> Response:
    """The canonical public meeting document as a JSON attachment."""
    job = _get_job(request, job_id)
    _require_done(job)
    body = build_export(job).model_dump_json().encode("utf-8")
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": _attachment(export_filename("json", job.id))},
    )


@router.get("/meetings/{job_id}/export/docx")
def export_docx(request: Request, job_id: str) -> FileResponse:
    """Render the minutes DOCX on demand and serve it as an attachment."""
    job = _get_job(request, job_id)
    _require_done(job)
    path = _registry(request).job_dir(job.id) / "export.docx"
    # A unique temp name per request, so concurrent renders never collide on
    # the same .tmp file; each then atomically swaps into the shared path.
    tmp = path.with_name(f"export.{uuid.uuid4().hex}.docx.tmp")
    docx_build.build(build_export(job)).save(tmp)
    tmp.replace(path)
    return FileResponse(
        path,
        media_type=constants.DOCX_MEDIA_TYPE,
        filename=export_filename("docx", job.id),
    )


def _attachment(filename: str) -> str:
    return f'attachment; filename="{filename}"'


def _validated_mapping(raw: dict[str, str], job: MeetingJob) -> dict[str, str]:
    known = {s.id for s in job.speakers}
    mapping: dict[str, str] = {}
    for key, value in raw.items():
        if key not in known:
            raise MessageError(422, "speaker.unknown")
        label = value.strip()
        if not label:
            raise MessageError(422, "speaker.empty_label")
        if len(label) > constants.MAX_LABEL_LENGTH:
            raise MessageError(422, "speaker.label_too_long")
        mapping[key] = label
    return mapping


def _extension_of(filename: str) -> str:
    match = re.search(r"\.([A-Za-z0-9]+)$", filename)
    return match.group(1).lower() if match else ""


async def _save_upload(audio: UploadFile, dst: Path, max_bytes: int) -> int:
    """Stream the upload to disk in chunks; reject mid-stream when oversized.

    Reads at most one chunk past the cap, then deletes the partial file, so an
    over-cap body is never fully buffered (the with-block closes the handle).
    """
    size = 0
    with dst.open("wb") as fh:
        while chunk := await audio.read(constants.UPLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > max_bytes:
                dst.unlink(missing_ok=True)
                raise UploadError("upload.file_too_large", f"{size} bytes > {max_bytes}")
            fh.write(chunk)
    await audio.close()
    return size
