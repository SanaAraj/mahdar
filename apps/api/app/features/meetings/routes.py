import shutil
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse

from app import constants
from app.api.deps import MessageError, get_job, pipeline_of, registry_of
from app.api.limiter import limiter
from app.features.meetings.upload import extension_of, save_upload
from app.features.meetings.validation import SpeakersUpdate, validated_mapping
from app.shared.errors import UploadError
from app.shared.models import MeetingJob, Speaker

router = APIRouter()


@router.post("/meetings", status_code=201)
@limiter.limit("3/minute;20/hour")
async def create_meeting(
    request: Request,
    audio: Annotated[UploadFile, File()],
) -> dict[str, str]:
    registry = registry_of(request)
    pipeline = pipeline_of(request)
    if not pipeline.has_capacity():
        raise MessageError(503, "server.busy")
    max_bytes = request.app.state.settings.max_upload_bytes
    extension = extension_of(audio.filename or "")
    if extension not in constants.ALLOWED_EXTENSIONS:
        raise MessageError(415, "upload.unsupported_extension")
    job_id = uuid.uuid4().hex[: constants.JOB_ID_LENGTH]
    job_dir = registry.job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    original = job_dir / f"original.{extension}"
    try:
        size = await save_upload(audio, original, max_bytes)
    except UploadError as exc:
        status = 413 if exc.message_key == "upload.file_too_large" else 415
        raise MessageError(status, exc.message_key) from None
    if size == 0:
        original.unlink(missing_ok=True)
        raise MessageError(422, "audio.corrupt")
    registry.create(job_id)
    if not pipeline.start(job_id):
        shutil.rmtree(job_dir, ignore_errors=True)
        raise MessageError(503, "server.busy")
    return {"id": job_id}


@router.get("/meetings/{job_id}")
@limiter.limit("120/minute")
def get_meeting(request: Request, job_id: str) -> MeetingJob:
    return get_job(request, job_id)


@router.get("/meetings/{job_id}/audio")
@limiter.limit("30/minute")
def get_audio(request: Request, job_id: str) -> FileResponse:
    job = get_job(request, job_id)
    mp3 = registry_of(request).job_dir(job.id) / "audio.mp3"
    if not mp3.exists():
        raise MessageError(404, "audio.not_ready")
    return FileResponse(mp3, media_type="audio/mpeg", filename="meeting.mp3")


@router.patch("/meetings/{job_id}/speakers")
@limiter.limit("30/minute")
def update_speakers(request: Request, job_id: str, body: SpeakersUpdate) -> list[Speaker]:
    job = get_job(request, job_id)
    mapping = validated_mapping(body.speakers, job)
    registry_of(request).rename_speakers(job.id, mapping)
    return registry_of(request).get(job.id).speakers
