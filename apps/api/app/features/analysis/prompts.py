import math
import re

from app import constants
from app.shared.errors import AnalysisError
from app.shared.models import MeetingMeta, Sentence, Speaker

_SCHEMA_EXAMPLE = """{
  "title": "نص",
  "attendees": ["اسم"],
  "topics": [{"title": "نص", "summary": "نص", "segment_ids": ["s1"]}],
  "decisions": [{"text": "نص", "segment_ids": ["s2"]}],
  "directives": [{"text": "نص", "segment_ids": ["s3"]}],
  "tasks": [{
    "description": "نص",
    "owner": "اسم أو null",
    "due": {"raw": "العبارة كما قيلت أو null", "gregorian": "2026-01-31 أو null"},
    "priority": "عالية أو متوسطة أو منخفضة أو null",
    "segment_ids": ["s4"]
  }]
}"""

SYSTEM_PROMPT = (
    """You are an Arabic meeting-minutes extractor that reads a transcript of
spoken Arabic. The user message begins with a header carrying the Gregorian
meeting date, the Hijri meeting date, the duration, and the speaker names, then
the transcript one sentence at a time. Each sentence is prefixed by its id in
square brackets such as [s3], followed by the speaker name and its start time.

Follow these rules strictly:

1. Extract only what is actually said in the transcript. Never add information
   of your own, even when it seems likely from context.
2. Every item (topic, decision, directive, task) must carry in segment_ids the
   ids of the sentences it rests on. An item with no source sentence is never
   accepted: if you find no sentence to ground it in, drop the item. The
   wording of each item must stay faithful and close to the words of the
   sentences it cites; when in doubt, drop the item rather than invent it.
3. If no decisions were taken, return an empty decisions list. Do not invent a
   decision. The same rule applies to every list: if it is empty, return an
   empty list and invent nothing.
4. Tasks include statements that are not phrased as imperatives. For example,
   «نحتاج إلى رفع التقرير قبل نهاية الشهر» is a task even though it has no
   imperative verb and names no owner.
5. owner is null unless the name is spoken or the assignment is explicit in the
   dialogue; never assign an owner by inferring it from who spoke most.
6. priority is set only when something signals it explicitly, such as «عاجل»
   (urgent), «فورًا» (immediately), «عالية» (high), or a pressing deadline;
   otherwise it is null. Stay within the three values عالية, متوسطة, منخفضة.
7. Dates: each task has a due object with raw and gregorian. Put in raw the
   phrase exactly as spoken in the transcript, and normalize it to an ISO
   Gregorian date such as 2026-08-18 in gregorian, anchored to the meeting date
   in the header; leave gregorian null if normalization is not possible. If no
   date is spoken for the task, set raw to null. Normalize relative phrases
   such as «غدًا» (tomorrow), «بعد غد» (the day after tomorrow), and Hijri
   phrases such as «15 شعبان 1448» against that meeting date.
8. attendees: the speaker names given in the header, then any name spoken in
   the dialogue as present, without duplicates.
9. title is a short descriptive Arabic phrase that names the subject of the
   meeting itself; not a single word and not a generic label such as «اجتماع»
   (meeting) or «مناقشة» (discussion).
10. Each topic has a short title and a summary confined to what was said, no
    longer than two sentences.
11. A decision is what the participants agreed on or explicitly settled. A
    directive is general guidance or a follow-up request that is not a specific
    task with a date.
12. Return JSON only, matching the schema below, with no text outside the
    object and no code fences.

Hard rule on language: every JSON string VALUE must be written in Arabic,
except proper nouns and technical terms kept exactly as spoken. The field
names stay English per the schema. For example, a topic summary, a decision
text, a task description, an owner name, and the raw date phrase are all
Arabic; an English product name or a URL spoken in the meeting is kept as
spoken. Never translate an Arabic value to English.

"""
    + _SCHEMA_EXAMPLE
)


def estimate_tokens(text: str) -> int:

    return math.ceil(len(text) / constants.CHARS_PER_TOKEN)


def ensure_within_budget(user_message: str) -> None:

    tokens = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(user_message)
    if tokens > constants.MAX_PROMPT_TOKENS:
        raise AnalysisError(
            "analysis.too_long", f"prompt ~{tokens} tokens > {constants.MAX_PROMPT_TOKENS}"
        )


def build_user_message(
    meta: MeetingMeta, sentences: list[Sentence], speakers: list[Speaker]
) -> str:

    labels = {sp.id: sp.label for sp in speakers}
    header = [
        f"التاريخ الميلادي: {meta.date_gregorian}",
        f"التاريخ الهجري: {meta.date_hijri}",
        f"المدة: {format_duration(meta.duration_s)}",
        f"المتحدثون: {_speaker_names(speakers)}",
    ]
    lines = [_format_sentence(sentence, labels) for sentence in sentences]
    return "\n".join([*header, "", "التفريغ:", *lines])


def _format_sentence(sentence: Sentence, labels: dict[str, str]) -> str:
    stamp = format_clock(sentence.start)
    speaker = labels.get(sentence.speaker) if sentence.speaker else None
    if speaker:
        return f"[{sentence.id}] {speaker} ({stamp}): {sentence.text}"
    return f"[{sentence.id}] ({stamp}): {sentence.text}"


def _speaker_names(speakers: list[Speaker]) -> str:
    if not speakers:
        return "غير محددين (لم يجر فصل المتحدثين)"
    return "، ".join(sp.label for sp in speakers)


def format_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    if total >= 3600:
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
    return f"{total // 60:02d}:{total % 60:02d}"


def format_duration(duration_s: float | None) -> str:
    return "غير معروفة" if duration_s is None else format_clock(duration_s)


def build_correction_message(validation_errors: str) -> str:

    trimmed = re.sub(r"\s+", " ", validation_errors).strip()
    trimmed = trimmed[: constants.CORRECTION_ERRORS_TAIL_CHARS]
    return (
        "ردك السابق لا يطابق المخطط المطلوب. أعد إرسال JSON مصححًا فقط، "
        "بلا أي نص خارج الكائن. الأخطاء المرصودة: " + trimmed
    )


def build_arabic_output_message() -> str:

    return (
        "Your previous reply was valid JSON but its values are not Arabic. "
        "Resend the same JSON with every string value written in Arabic, "
        "keeping proper nouns and technical terms as spoken and the field "
        "names in English. JSON only, no text outside the object."
    )


WINDOW_SCOPE_LINE = (
    "This transcript is one portion of a longer meeting, split across "
    "consecutive parts; this message holds one of those parts. Extract only "
    "from the sentences shown here and cite only the ids shown here."
)


REDUCE_SYSTEM_PROMPT = (
    """You are an Arabic meeting-minutes reducer. The user message holds, one
block per portion of a longer meeting, the minutes extracted from each portion:
a title, the attendees, and the summaries of its topics, decisions, directives,
and tasks with the segment ids each rests on. No transcript lines are given.

Your job is to merge the portions into one Arabic minutes object. Rules:
1. Combine items from different portions that describe the same topic,
   decision, directive, or task into a single item, keeping the union of all
   their segment_ids. Do not merge items that merely share a theme while
   describing distinct content.
2. You may merge or drop duplicate items and rewrite one final title and the
   topic summaries in Arabic. Never rewrite the wording of a decision, a
   directive, or a task description: when duplicates are fused, keep one
   original wording verbatim and carry the union of the segment_ids.
3. attendees is the union of every portion's attendees, without duplicates.
4. Never introduce a topic, decision, directive, task, or attendee that no
   portion named. The union of the portions is the whole meeting.
5. Return JSON only, matching the schema below, with no text outside the
   object and no code fences. Every string value stays in Arabic, exactly as
   the portions carry it.
6. Field names are exactly the lowercase English names of the schema below.
   The uppercase markers of the portion blocks (TITLE, ATTENDEES, TOPIC,
   DECISION, DIRECTIVE, TASK) label the input and are never JSON keys. Every
   topic carries title, summary, and segment_ids; every decision and directive
   carries text and segment_ids; every task carries description and
   segment_ids.

"""
    + _SCHEMA_EXAMPLE
)


def build_reduce_message(window_summaries: list[str]) -> str:

    blocks = [f"[w{index + 1}]\n{summary}" for index, summary in enumerate(window_summaries)]
    message = "\n\n".join(blocks)
    tokens = estimate_tokens(message)
    if tokens > constants.REDUCE_TOKEN_BUDGET:
        raise AnalysisError(
            "analysis.too_long",
            f"reduce input ~{tokens} tokens > {constants.REDUCE_TOKEN_BUDGET}",
        )
    return message
