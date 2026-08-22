from docx.document import Document as DocumentObject
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.table import _Cell
from docx.text.paragraph import Paragraph

from app.features.export.docx_rtl import (
    DOCX_FONT_NAME,
    RPR_ORDER,
    STYLE_TOKENS,
    add_mixed_runs,
    insert_ordered,
)

_PPR_ORDER = (
    "w:pStyle",
    "w:keepNext",
    "w:keepLines",
    "w:pageBreakBefore",
    "w:framePr",
    "w:widowControl",
    "w:numPr",
    "w:suppressLineNumbers",
    "w:pBdr",
    "w:shd",
    "w:tabs",
    "w:suppressAutoHyphens",
    "w:kinsoku",
    "w:wordWrap",
    "w:overflowPunct",
    "w:topLinePunct",
    "w:autoSpaceDE",
    "w:autoSpaceDN",
    "w:bidi",
    "w:adjustRightInd",
    "w:snapToGrid",
    "w:spacing",
    "w:ind",
    "w:contextualSpacing",
    "w:mirrorIndents",
    "w:suppressOverlap",
    "w:jc",
    "w:textDirection",
    "w:textAlignment",
    "w:textboxTightWrap",
    "w:outlineLvl",
    "w:divId",
    "w:cnfStyle",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)


def rtl_paragraph(
    host: DocumentObject | _Cell,
    text: str = "",
    *,
    style_name: str = "body",
    bold: bool | None = None,
) -> Paragraph:

    size, style_bold = STYLE_TOKENS[style_name]
    paragraph = _paragraph_in(host)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_bidi(paragraph)
    add_mixed_runs(paragraph, text)
    for run in paragraph.runs:
        run.bold = style_bold if bold is None else bold
        run.font.size = Pt(size)
        run.font.name = DOCX_FONT_NAME
        rpr = run._element.get_or_add_rPr()
        _set_sz_cs(rpr, size)
        _rfonts(rpr).set(qn("w:cs"), DOCX_FONT_NAME)
    return paragraph


def _set_sz_cs(rpr, size: float) -> None:

    element = OxmlElement("w:szCs")
    element.set(qn("w:val"), str(int(size * 2)))
    insert_ordered(rpr, element, RPR_ORDER)


def _rfonts(rpr):
    element = rpr.find(qn("w:rFonts"))
    if element is None:
        element = OxmlElement("w:rFonts")
        rpr.append(element)
    return element


def _paragraph_in(host: DocumentObject | _Cell) -> Paragraph:

    if isinstance(host, _Cell):
        last = host.paragraphs[-1]
        if not last.runs and not last.text:
            return last
    return host.add_paragraph()


def _set_bidi(paragraph: Paragraph) -> None:

    insert_ordered(paragraph._p.get_or_add_pPr(), OxmlElement("w:bidi"), _PPR_ORDER)


def bidi_visual(table) -> None:
    table._tbl.tblPr.append(OxmlElement("w:bidiVisual"))


def setup_styles(doc: DocumentObject) -> None:

    for style in doc.styles:
        font = getattr(style, "font", None)
        if font is None:
            continue
        font.name = DOCX_FONT_NAME
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), DOCX_FONT_NAME)
        rfonts.set(qn("w:hAnsi"), DOCX_FONT_NAME)
        rfonts.set(qn("w:cs"), DOCX_FONT_NAME)
