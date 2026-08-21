"""RTL and mixed-direction primitives for the DOCX export.

Every body paragraph in the exported document must declare itself RTL and
right-aligned, and every piece of text within it must be split into Arabic
runs (w:rtl set) versus Latin and digit runs (no w:rtl), so an English term
or a number inside an Arabic sentence keeps its internal order while the
sentence itself flows right to left. Styles are fixed Arial with matching
ascii and complex-script fonts: Arial is installed everywhere Word runs and
shapes Arabic correctly, so the export renders the same on any machine that
opens it, while embedding the vendored UI font would swell every file and
raise font-embedding license questions the document does not need.
"""

import re

from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from app import constants

# Arabic and friends, including presentation forms; everything else (Latin,
# digits, punctuation, spaces) goes to a non-RTL run. The character ranges are
# data held in constants (chartered); this module compiles the matchers.
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

# The ECMA-376 child order for w:rPr. Children must be inserted at the index
# their tag holds here, or a strict validator flags the run. python-docx has no
# managed accessor for w:rtl or w:szCs, so the export inserts them by schema
# position rather than via a raw (unordered) append.
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
    """Split text into (segment, is_rtl) parts, keeping intra-text order."""
    parts: list[tuple[str, bool]] = []
    cursor = 0
    while cursor < len(text):
        rtl = _RTL_RUN_RE.match(text, cursor)
        if rtl:
            parts.append((rtl.group(0), True))
            cursor = rtl.end()
            continue
        ltr = _LTR_RUN_RE.match(text, cursor)
        parts.append((ltr.group(0), False))  # every char falls in one class
        cursor = ltr.end()
    return parts


def add_mixed_runs(paragraph: Paragraph, text: str) -> list[Run]:
    """Append text as runs; returns them so the caller sets run properties once."""
    runs: list[Run] = []
    for segment, is_rtl in split_directional(text):
        run = paragraph.add_run(segment)
        if is_rtl:
            set_run_rtl(run)
        runs.append(run)
    return runs


def set_run_rtl(run: Run) -> None:
    """Insert w:rtl at its schema position so w:szCs stays before it."""
    insert_ordered(run._element.get_or_add_rPr(), OxmlElement("w:rtl"), RPR_ORDER)


def insert_ordered(parent, element, order: tuple[str, ...]) -> None:
    """Place an element before the first existing child with a later schema tag."""
    tag = _local_name(element.tag)
    my_index = order.index(tag)
    for child in parent:
        child_tag = _local_name(child.tag)
        if child_tag in order and order.index(child_tag) > my_index:
            child.addprevious(element)
            return
    parent.append(element)


def _local_name(tag: str) -> str:
    """Strip the namespace and re-add the w: prefix the order tables carry."""
    name = tag.split("}")[-1] if "}" in tag else tag
    return name if name.startswith("w:") else "w:" + name
