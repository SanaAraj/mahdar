"""Build the meeting-minutes DOCX from the canonical export document.

This module holds the document sections: title, meta block, the analysis
sections (topics, decisions, directives, the tasks table), and the optional
transcript appendix. The paragraph and element primitives it composes live in
docx_primitives.py; directionality comes from docx_rtl.py, layout and copy from
strings.py. Every paragraph is RTL and right-aligned, every table is bidiVisual,
and all body text flows through add_mixed_runs so embedded Latin terms and
numbers keep their shape inside the RTL stream.
"""

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.table import Table, _Cell

from backend.app import constants, strings
from backend.app.core.models import ExportMeeting, Sentence, TaskItem
from backend.app.processing.docx_primitives import (
    bidi_visual,
    rtl_paragraph,
    setup_styles,
)
from backend.app.providers.prompts import format_clock

__all__ = ["build", "rtl_paragraph"]


def build(meeting: ExportMeeting, include_transcript: bool | None = None) -> DocumentObject:
    """Render the whole document; the flag overrides the default appendix."""
    if include_transcript is None:
        include_transcript = constants.INCLUDE_TRANSCRIPT_IN_DOCX
    doc = Document()
    setup_styles(doc)
    _title(doc, meeting)
    _meta(doc, meeting)
    if meeting.analysis is None:
        rtl_paragraph(doc, strings.resolve("export.no_analysis"), style_name="body")
    else:
        _analysis_sections(doc, meeting)
    if include_transcript and meeting.sentences:
        _transcript(doc, meeting)
    return doc


# ---- document sections ----


def _title(doc: DocumentObject, meeting: ExportMeeting) -> None:
    prefix = strings.resolve("export.title_prefix")
    title = meeting.analysis.title if meeting.analysis else ""
    text = f"{prefix}: {title}" if title else prefix
    rtl_paragraph(doc, text, style_name="title")


def _meta(doc: DocumentObject, meeting: ExportMeeting) -> None:
    meta = meeting.meta
    lines = [f"{strings.resolve('export.date')}: {_date_line(meta)}"]
    if meta.duration_s is not None:
        lines.append(f"{strings.resolve('export.duration')}: {format_clock(meta.duration_s)}")
    attendees = (meeting.analysis.attendees if meeting.analysis else None) or [
        sp.label for sp in meeting.speakers
    ]
    if attendees:
        lines.append(
            f"{strings.resolve('export.attendees')}: "
            f"{strings.resolve('export.attendees_separator').join(attendees)}"
        )
    for line in lines:
        rtl_paragraph(doc, line, style_name="meta")


def _date_line(meta) -> str:
    parts = []
    if meta.date_gregorian:
        parts.append(f"{strings.resolve('export.date_gregorian')}: {meta.date_gregorian}")
    if meta.date_hijri:
        parts.append(f"{strings.resolve('export.date_hijri')}: {meta.date_hijri}")
    return " | ".join(parts)


def _analysis_sections(doc: DocumentObject, meeting: ExportMeeting) -> None:
    analysis = meeting.analysis
    _topics(doc, analysis.topics)
    _string_list(
        doc, "export.decisions", [d.text for d in analysis.decisions], "export.decisions_empty"
    )
    _string_list(
        doc,
        "export.directives",
        [d.text for d in analysis.directives],
        "export.directives_empty",
    )
    _tasks(doc, analysis.tasks)


def _topics(doc: DocumentObject, topics: list) -> None:
    rtl_paragraph(doc, strings.resolve("export.topics"), style_name="heading")
    if not topics:
        rtl_paragraph(doc, strings.resolve("export.topics_empty"), style_name="body")
        return
    for index, topic in enumerate(topics, start=1):
        rtl_paragraph(doc, f"{index}. {topic.title}", style_name="subheading")
        rtl_paragraph(doc, topic.summary, style_name="body")


def _string_list(doc: DocumentObject, heading_key: str, items: list[str], empty_key: str) -> None:
    rtl_paragraph(doc, strings.resolve(heading_key), style_name="heading")
    if not items:
        rtl_paragraph(doc, strings.resolve(empty_key), style_name="body")
        return
    for index, text in enumerate(items, start=1):
        rtl_paragraph(doc, f"{index}. {text}", style_name="body")


def _tasks(doc: DocumentObject, tasks: list[TaskItem]) -> None:
    rtl_paragraph(doc, strings.resolve("export.tasks"), style_name="heading")
    if not tasks:
        rtl_paragraph(doc, strings.resolve("export.tasks_empty"), style_name="body")
        return
    columns = (
        strings.resolve("export.col_task"),
        strings.resolve("export.col_owner"),
        strings.resolve("export.col_due"),
        strings.resolve("export.col_priority"),
    )
    table = doc.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.RIGHT
    bidi_visual(table)
    for cell, label in zip(table.rows[0].cells, columns, strict=True):
        rtl_paragraph(cell, label, bold=True)
    for task in tasks:
        _task_row(table, task)


def _task_row(table: Table, task: TaskItem) -> None:
    cells = table.add_row().cells
    owner = task.owner or strings.resolve("export.owner_unknown")
    values = (task.description, owner, None, task.priority or "")
    for cell, value in zip(cells, values, strict=True):
        if value is None:
            _due_cell(cell, task)
        else:
            rtl_paragraph(cell, value)


def _due_cell(cell: _Cell, task: TaskItem) -> None:
    due = task.due
    if not (due.gregorian or due.hijri or due.raw):
        rtl_paragraph(cell, strings.resolve("export.no_due"))
        return
    # All three lines share one style so the cell does not mix font sizes.
    if due.gregorian:
        rtl_paragraph(cell, due.gregorian, style_name="transcript")
    if due.hijri:
        rtl_paragraph(cell, due.hijri, style_name="transcript")
    if due.raw:
        rtl_paragraph(cell, due.raw, style_name="transcript")


def _transcript(doc: DocumentObject, meeting: ExportMeeting) -> None:
    rtl_paragraph(doc, strings.resolve("export.transcript"), style_name="heading")
    labels = {sp.id: sp.label for sp in meeting.speakers}
    for sentence in meeting.sentences:
        rtl_paragraph(doc, _transcript_line(sentence, labels), style_name="transcript")


def _transcript_line(sentence: Sentence, labels: dict[str, str]) -> str:
    speaker = labels.get(sentence.speaker) or strings.resolve("export.speaker_unknown")
    return f"[{format_clock(sentence.start)}] {speaker}: {sentence.text}"
