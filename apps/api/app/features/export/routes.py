import uuid

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

from app import constants
from app.api.deps import MessageError, get_job, registry_of
from app.api.limiter import limiter
from app.features.export import docx_build
from app.features.export.service import build_export, export_filename
from app.shared.models import JobStatus, MeetingJob

router = APIRouter()


def _require_done(job: MeetingJob) -> None:

    if job.status is not JobStatus.DONE:
        raise MessageError(409, "audio.not_ready")


def _attachment(filename: str) -> str:
    return f'attachment; filename="{filename}"'


@router.get("/meetings/{job_id}/export/json")
@limiter.limit("30/minute")
def export_json(request: Request, job_id: str) -> Response:

    job = get_job(request, job_id)
    _require_done(job)
    body = build_export(job).model_dump_json().encode("utf-8")
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": _attachment(export_filename("json", job.id))},
    )


@router.get("/meetings/{job_id}/export/docx")
@limiter.limit("10/minute")
def export_docx(request: Request, job_id: str) -> FileResponse:

    job = get_job(request, job_id)
    _require_done(job)
    path = registry_of(request).job_dir(job.id) / "export.docx"

    tmp = path.with_name(f"export.{uuid.uuid4().hex}.docx.tmp")
    docx_build.build(build_export(job)).save(tmp)
    tmp.replace(path)
    return FileResponse(
        path,
        media_type=constants.DOCX_MEDIA_TYPE,
        filename=export_filename("docx", job.id),
    )
