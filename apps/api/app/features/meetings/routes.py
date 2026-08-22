import uuid
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse

from app import constants
from app.api.deps import MessageError, get_job, pipeline_of, registry_of
from app.features.meetings.upload import extension_of, save_upload
from app.features.meetings.validation import SpeakersUpdate, validated_mapping
from app.shared.errors import UploadError
from app.shared.models import MeetingJob, Speaker

router = APIRouter()


@router.post("/meetings", status_code=201)
async def create_meeting(
    request: Request,
    audio: Annotated[UploadFile, File()],
) -> dict[str, str]:
    registry = registry_of(request)
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
    except UploadError:
        raise MessageError(413, "upload.file_too_large") from None
    if size == 0:
        original.unlink(missing_ok=True)
        raise MessageError(422, "audio.corrupt")
    registry.create(job_id)
    pipeline_of(request).start(job_id)
    return {"id": job_id}


@router.get("/meetings/{job_id}")
def get_meeting(request: Request, job_id: str) -> MeetingJob:
    return get_job(request, job_id)


@router.get("/meetings/{job_id}/audio")
def get_audio(request: Request, job_id: str) -> FileResponse:
    job = get_job(request, job_id)
    mp3 = registry_of(request).job_dir(job.id) / "audio.mp3"
    if not mp3.exists():
        raise MessageError(404, "audio.not_ready")
    return FileResponse(mp3, media_type="audio/mpeg", filename="meeting.mp3")


@router.patch("/meetings/{job_id}/speakers")
def update_speakers(request: Request, job_id: str, body: SpeakersUpdate) -> list[Speaker]:
    job = get_job(request, job_id)
    mapping = validated_mapping(body.speakers, job)
    registry_of(request).rename_speakers(job.id, mapping)
    return registry_of(request).get(job.id).speakers
