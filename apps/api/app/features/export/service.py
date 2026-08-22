from app import constants
from app.shared.models import ExportMeeting, ExportMeta, MeetingJob


def build_export(job: MeetingJob) -> ExportMeeting:

    return ExportMeeting(
        meta=ExportMeta(
            id=job.id,
            created_at=job.created_at,
            date_gregorian=job.date_gregorian,
            date_hijri=job.date_hijri,
            duration_s=job.duration_s,
        ),
        speakers=list(job.speakers),
        sentences=list(job.sentences),
        analysis=job.analysis,
    )


def export_filename(kind: str, job_id: str) -> str:

    template = (
        constants.DOCX_FILENAME_TEMPLATE if kind == "docx" else constants.JSON_FILENAME_TEMPLATE
    )
    return template.format(job_id=job_id)
