from pydantic import BaseModel, Field

from app import constants
from app.api.deps import MessageError
from app.shared.models import MeetingJob


class SpeakersUpdate(BaseModel):
    speakers: dict[str, str] = Field(default_factory=dict)


def validated_mapping(raw: dict[str, str], job: MeetingJob) -> dict[str, str]:
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
