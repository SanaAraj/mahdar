from fastapi import APIRouter, Request

from app.api.deps import MessageError, get_job, pipeline_of
from app.api.limiter import limiter
from app.shared.models import JobStatus

router = APIRouter()


@router.post("/meetings/{job_id}/analyze", status_code=202)
@limiter.limit("5/minute;30/hour")
def reanalyze(request: Request, job_id: str) -> dict[str, str]:

    job = get_job(request, job_id)
    if not job.sentences:
        raise MessageError(409, "analysis.transcript_missing")
    if job.status is JobStatus.ANALYZING:
        return {"id": job.id}
    if job.status is not JobStatus.DONE:
        raise MessageError(409, "analysis.transcript_missing")
    if not pipeline_of(request).start_analysis(job.id):
        raise MessageError(503, "server.busy")
    return {"id": job.id}
