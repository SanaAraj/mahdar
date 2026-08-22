from fastapi import APIRouter, Request

from app.api.deps import MessageError, get_job, pipeline_of
from app.shared.models import JobStatus

router = APIRouter()


@router.post("/meetings/{job_id}/analyze", status_code=202)
def reanalyze(request: Request, job_id: str) -> dict[str, str]:
    """Re-run analysis on the stored transcript without re-transcribing."""
    job = get_job(request, job_id)
    if not job.sentences:
        raise MessageError(409, "analysis.transcript_missing")
    if job.status is JobStatus.ANALYZING:
        return {"id": job.id}  # an analysis is already running; the request is a duplicate
    if job.status is not JobStatus.DONE:
        raise MessageError(409, "analysis.transcript_missing")
    pipeline_of(request).start_analysis(job.id)
    return {"id": job.id}
