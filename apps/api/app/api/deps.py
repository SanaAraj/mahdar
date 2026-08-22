import re

from fastapi import Request

from app import constants
from app.pipeline.pipeline import Pipeline
from app.shared.jobs import JobRegistry
from app.shared.models import MeetingJob

JOB_ID_RE = re.compile(rf"^[0-9a-f]{{{constants.JOB_ID_LENGTH}}}$")


class MessageError(Exception):
    def __init__(self, status_code: int, message_key: str) -> None:
        super().__init__(message_key)
        self.status_code = status_code
        self.message_key = message_key


def not_found() -> MessageError:
    return MessageError(404, "job.not_found")


def registry_of(request: Request) -> JobRegistry:
    return request.app.state.registry


def pipeline_of(request: Request) -> Pipeline:
    return request.app.state.pipeline


def get_job(request: Request, job_id: str) -> MeetingJob:
    if not JOB_ID_RE.fullmatch(job_id):
        raise not_found()
    job = registry_of(request).get(job_id)
    if job is None:
        raise not_found()
    return job
