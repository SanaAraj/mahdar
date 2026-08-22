import re

from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from app import constants

_RTL_CHARS = constants.ARABIC_RTL_RANGES
_RTL_RUN_RE = re.compile(rf"[{_RTL_CHARS}]+[^{_RTL_CHARS}A-Za-z0-9]*")
_LTR_RUN_RE = re.compile(rf"[^{_RTL_CHARS}]+")

DOCX_FONT_NAME = "Arial"
STYLE_TOKENS: dict[str, tuple[float, bool]] = {
    "title": (24, True),
    "heading": (15, True),
    "subheading": (13, True),
    "body": (12, False),
    "meta": (12, False),
    "transcript": (11, False),
}


RPR_ORDER = (
    "w:rStyle",
    "w:rFonts",
    "w:b",
    "w:bCs",
    "w:i",
    "w:iCs",
    "w:caps",
    "w:smallCaps",
    "w:strike",
    "w:dstrike",
    "w:outline",
    "w:shadow",
    "w:emboss",
    "w:imprint",
    "w:noProof",
    "w:snapToGrid",
    "w:vanish",
    "w:webHidden",
    "w:color",
    "w:spacing",
    "w:w",
    "w:kern",
    "w:position",
    "w:sz",
    "w:szCs",
    "w:highlight",
    "w:u",
    "w:effect",
    "w:bdr",
    "w:shd",
    "w:fitText",
    "w:vertAlign",
    "w:rtl",
    "w:cs",
    "w:em",
    "w:lang",
    "w:eastAsianLayout",
    "w:specVanish",
    "w:oMath",
)


def split_directional(text: str) -> list[tuple[str, bool]]:

    parts: list[tuple[str, bool]] = []
    cursor = 0
    while cursor < len(text):
        rtl = _RTL_RUN_RE.match(text, cursor)
        if rtl:
            parts.append((rtl.group(0), True))
            cursor = rtl.end()
            continue
        ltr = _LTR_RUN_RE.match(text, cursor)
        if ltr is None:
            break
        parts.append((ltr.group(0), False))
        cursor = ltr.end()
    return parts


def add_mixed_runs(paragraph: Paragraph, text: str) -> list[Run]:

    runs: list[Run] = []
    for segment, is_rtl in split_directional(text):
        run = paragraph.add_run(segment)
        if is_rtl:
            set_run_rtl(run)
        runs.append(run)
    return runs


def set_run_rtl(run: Run) -> None:

    insert_ordered(run._element.get_or_add_rPr(), OxmlElement("w:rtl"), RPR_ORDER)


def insert_ordered(parent, element, order: tuple[str, ...]) -> None:

    tag = _local_name(element.tag)
    my_index = order.index(tag)
    for child in parent:
        child_tag = _local_name(child.tag)
        if child_tag in order and order.index(child_tag) > my_index:
            child.addprevious(element)
            return
    parent.append(element)


def _local_name(tag: str) -> str:

    name = tag.split("}")[-1] if "}" in tag else tag
    return name if name.startswith("w:") else "w:" + name
