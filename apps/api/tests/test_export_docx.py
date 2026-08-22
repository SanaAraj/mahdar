"""DOCX structure tests run by unzipping document.xml: no Word needed."""

import io
import zipfile

from lxml import etree

from app import strings
from app.features.export import docx_build
from app.shared.models import (
    Analysis,
    DueDate,
    ExportMeeting,
    ExportMeta,
    Sentence,
    Speaker,
    TaskItem,
    Topic,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}

FIXTURE_SENTENCES = [
    Sentence(
        id="s1",
        start=65.0,
        end=68.0,
        text="اعتمدنا تقرير KPI بـ 95% اليوم.",
        speaker="S0",
    ),
]

FIXTURE_ANALYSIS = Analysis(
    title="مراجعة خطة المشروع",
    attendees=["أحمد"],
    topics=[
        Topic(title="الخطة", summary="استعرضنا خطة العمل المرحلية.", segment_ids=["s1"]),
    ],
    decisions=[],  # the empty list must render its designed line
    directives=[],
    tasks=[
        TaskItem(
            description="رفع التقرير النهائي",
            owner=None,  # the null owner must use the quiet fallback
            due=DueDate(raw="غدًا", gregorian="2026-08-19", hijri="1448-03-06"),
            priority=None,
            segment_ids=["s1"],
        )
    ],
)


def _meeting(analysis=FIXTURE_ANALYSIS) -> ExportMeeting:
    return ExportMeeting(
        meta=ExportMeta(
            id="0123456789ab",
            created_at="2026-08-18T10:00:00",
            date_gregorian="2026-08-18",
            date_hijri="1448-03-05",
            duration_s=125.0,
        ),
        speakers=[Speaker(id="S0", label="أحمد", first_start=0.0)],
        sentences=FIXTURE_SENTENCES,
        analysis=analysis,
    )


def _document_root(meeting=None, **kwargs) -> etree._Element:
    buffer = io.BytesIO()
    docx_build.build(meeting or _meeting(), **kwargs).save(buffer)
    document = zipfile.ZipFile(io.BytesIO(buffer.getvalue())).read("word/document.xml")
    return etree.fromstring(document)


def _paragraph_text(paragraph) -> str:
    return "".join(t.text or "" for t in paragraph.iter(f"{{{W}}}t"))


def test_every_paragraph_is_rtl_and_right_aligned():
    root = _document_root()
    paragraphs = root.findall(".//w:body/w:p", NS) + root.findall(".//w:tc/w:p", NS)
    assert paragraphs, "the document has no paragraphs"
    for p in paragraphs:
        ppr = p.find("w:pPr", NS)
        assert ppr is not None, f"missing pPr on: {_paragraph_text(p)!r}"
        assert ppr.find("w:bidi", NS) is not None, f"missing bidi: {_paragraph_text(p)!r}"
        justify = ppr.find("w:jc", NS)
        assert justify is not None and justify.get(f"{{{W}}}val") == "right"


def test_table_is_bidi_visual_with_rtl_cell_paragraphs():
    root = _document_root()
    table = root.find(".//w:tbl", NS)
    assert table is not None
    tblpr = table.find("w:tblPr", NS)
    assert tblpr is not None and tblpr.find("w:bidiVisual", NS) is not None
    for cell_p in table.findall(".//w:tc/w:p", NS):
        ppr = cell_p.find("w:pPr", NS)
        assert ppr is not None and ppr.find("w:bidi", NS) is not None


def test_rtl_flag_on_arabic_runs_and_absent_on_latin_runs():
    root = _document_root()
    target = None
    for p in root.findall(".//w:body/w:p", NS):
        if "KPI" in _paragraph_text(p) and "95" in _paragraph_text(p):
            target = p
            break
    assert target is not None, "the mixed transcript line is missing"
    runs = target.findall("w:r", NS)
    for run in runs:
        text = "".join(t.text or "" for t in run.iter(f"{{{W}}}t"))
        has_rtl = run.find("w:rPr/w:rtl", NS) is not None
        if any("؀" <= ch <= "ۿ" for ch in text):
            assert has_rtl, f"Arabic run without w:rtl: {text!r}"
        else:
            assert not has_rtl, f"Latin run with w:rtl: {text!r}"


def test_mixed_sentence_run_order_is_preserved():
    root = _document_root()
    for p in root.findall(".//w:body/w:p", NS):
        text = _paragraph_text(p)
        if "KPI" not in text or "95" not in text:
            continue
        ordered = "".join(t.text or "" for t in p.iter(f"{{{W}}}t"))
        assert "KPI" in ordered and "95" in ordered
        # The Arabic frame surrounds the Latin term and digits, in source order.
        assert ordered.index("اعتمدنا") < ordered.index("KPI")
        assert ordered.index("KPI") < ordered.index("95")
        assert ordered.index("95") < ordered.index("اليوم")
        return
    raise AssertionError("no mixed-direction paragraph found")


def test_empty_decisions_render_the_designed_line():
    root = _document_root()
    wanted = strings.resolve("export.decisions_empty").split()
    texts = [_paragraph_text(p) for p in root.findall(".//w:body/w:p", NS)]
    line = next((t for t in texts if "قرارات" in t and "الاجتماع" in t), "")
    for word in wanted:
        assert word in line, f"missing {word!r} in the empty-decisions line"


def test_null_owner_uses_the_quiet_fallback():
    root = _document_root()
    all_text = "".join(t.text or "" for t in root.iter(f"{{{W}}}t"))
    assert strings.resolve("export.owner_unknown") in all_text


def test_due_cell_layers_dates_above_the_raw_phrase():
    root = _document_root()
    due_cell = None
    for cell in root.findall(".//w:tc", NS):
        text = "".join(t.text or "" for t in cell.iter(f"{{{W}}}t"))
        if "1448-03-06" in text:
            due_cell = cell
            break
    assert due_cell is not None, "no cell holds the hijri date"
    paras = due_cell.findall("w:p", NS)
    lines = ["".join(t.text or "" for t in p.iter(f"{{{W}}}t")) for p in paras]
    assert lines == ["2026-08-19", "1448-03-06", "غدًا"]


def test_no_analysis_keeps_meta_and_transcript_with_one_note():
    root = _document_root(_meeting(analysis=None))
    all_text = "".join(t.text or "" for t in root.iter(f"{{{W}}}t"))
    assert strings.resolve("export.no_analysis") in all_text
    assert "2026-08-18" in all_text  # meta still exported
    assert "اعتمدنا" in all_text  # transcript appendix still rendered
    # And none of the analysis section headings appear.
    assert strings.resolve("export.topics") not in all_text
    assert strings.resolve("export.decisions") not in all_text


def test_transcript_appendix_flag_drops_the_section():
    root = _document_root(include_transcript=False)
    all_text = "".join(t.text or "" for t in root.iter(f"{{{W}}}t"))
    assert strings.resolve("export.transcript") not in all_text
    assert "اعتمدنا" not in all_text
    # The analysis sections are still present without the appendix.
    assert strings.resolve("export.topics") in all_text


def test_bytes_are_a_valid_docx_package():
    buffer = io.BytesIO()
    docx_build.build(_meeting()).save(buffer)
    data = buffer.getvalue()
    assert data[:2] == b"PK"
    archive = zipfile.ZipFile(io.BytesIO(data))
    assert "word/document.xml" in archive.namelist()


def test_rpr_children_are_in_schema_order():
    """w:szCs precedes w:rtl in every run, per ECMA-376 CT_RPr."""
    root = _document_root()
    for rpr in root.iter(f"{{{W}}}rPr"):
        children = [c.tag.split("}")[-1] for c in rpr]
        if "rtl" in children and "szCs" in children:
            assert children.index("szCs") < children.index("rtl"), f"szCs after rtl: {children}"


def test_ppr_children_are_in_schema_order():
    """w:bidi precedes w:jc in every paragraph, per ECMA-376 CT_PPr."""
    root = _document_root()
    for ppr in root.iter(f"{{{W}}}pPr"):
        children = [c.tag.split("}")[-1] for c in ppr]
        if "bidi" in children and "jc" in children:
            assert children.index("bidi") < children.index("jc"), f"bidi after jc: {children}"


def test_empty_topics_render_the_designed_line_not_an_orphan_heading():
    root = _document_root(_meeting(analysis=Analysis(title="مراجعة", attendees=[])))
    all_text = "".join(t.text or "" for t in root.iter(f"{{{W}}}t"))
    assert strings.resolve("export.topics_empty")[:6] in all_text


def test_due_cell_uses_one_style_for_dates_and_raw_phrase():
    root = _document_root()
    for cell in root.findall(".//w:tc", NS):
        text = "".join(t.text or "" for t in cell.iter(f"{{{W}}}t"))
        if "1448-03-06" in text:
            sizes = [
                run.find("w:rPr/w:szCs", NS).get(f"{{{W}}}val")
                for p in cell.findall("w:p", NS)
                for run in p.findall("w:r", NS)
                if run.find("w:rPr/w:szCs", NS) is not None
            ]
            assert len(set(sizes)) == 1, f"mixed sizes in due cell: {sizes}"
            return
    raise AssertionError("no due cell found")
