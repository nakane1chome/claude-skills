"""Split markdown into concept units for comparison.

Uses the marko parser (with GFM extension for table support) to build a
proper AST, then walks block-level elements to extract concept units.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from marko.block import (
    BlankLine,
    Heading,
    List,
    ListItem,
    Paragraph,
    ThematicBreak,
)
from marko.ext.gfm import gfm as gfm_parser
from marko.ext.gfm.elements import Table, TableRow


@dataclass
class ConceptUnit:
    """A single concept extracted from a markdown document."""

    id: int
    text: str
    kind: str  # "paragraph", "bullet", "table_row", "heading"
    source_line: int = 0

    @property
    def tokens(self) -> set[str]:
        """Lowercase word tokens, stripping markdown punctuation."""
        return set(re.findall(r"[a-z][a-z''-]+", self.text.lower()))


def _extract_text(node) -> str:
    """Recursively extract plain text from a marko AST node."""
    if isinstance(node, str):
        return node
    if hasattr(node, "children"):
        if isinstance(node.children, str):
            return node.children
        if isinstance(node.children, list):
            return "".join(_extract_text(c) for c in node.children)
    return ""


def _source_line(node) -> int:
    """Best-effort source line from a marko node (1-indexed, 0 if unknown)."""
    # marko block elements have a _source attribute set during parsing
    # that records (line, col) — but it's not public API and may not
    # always be present. Fall back to 0.
    if hasattr(node, "_source"):
        src = node._source
        if isinstance(src, tuple) and len(src) >= 1:
            return src[0] + 1  # marko uses 0-indexed lines
    return 0


def chunk_markdown(text: str) -> list[ConceptUnit]:
    """Split markdown text into concept units using the marko parser.

    Strategy:
    - Headings become their own units
    - List items become individual units (kind="bullet" for both ordered/unordered)
    - Table rows become individual units (cells joined with spaces)
    - Paragraphs become units (multi-line paragraphs are merged naturally by the parser)
    - Blank lines, thematic breaks, and other structural elements are skipped
    """
    doc = gfm_parser.parse(text)
    units: list[ConceptUnit] = []
    uid = 0

    def add(text: str, kind: str, node) -> None:
        nonlocal uid
        cleaned = text.strip()
        if cleaned:
            units.append(
                ConceptUnit(id=uid, text=cleaned, kind=kind, source_line=_source_line(node))
            )
            uid += 1

    for child in doc.children:
        if isinstance(child, (BlankLine, ThematicBreak)):
            continue

        if isinstance(child, Heading):
            add(_extract_text(child), "heading", child)

        elif isinstance(child, Paragraph):
            # Replace soft line breaks with spaces for a clean single-line text
            para_text = _extract_text(child).replace("\n", " ")
            add(para_text, "paragraph", child)

        elif isinstance(child, List):
            for item in child.children:
                if isinstance(item, ListItem):
                    item_text = _extract_text(item).replace("\n", " ")
                    add(item_text, "bullet", item)

        elif isinstance(child, Table):
            for row in child.children:
                if isinstance(row, TableRow):
                    cells = [_extract_text(cell).strip() for cell in row.children]
                    row_text = " ".join(cells)
                    add(row_text, "table_row", row)

        else:
            # Catch-all for other block types (code blocks, quotes, etc.)
            block_text = _extract_text(child)
            if block_text.strip():
                add(block_text, "paragraph", child)

    return units
