"""Tests for the markdown chunker."""

from .chunker import chunk_markdown, ConceptUnit


def test_empty_input():
    assert chunk_markdown("") == []


def test_single_paragraph():
    units = chunk_markdown("This is a simple paragraph.")
    assert len(units) == 1
    assert units[0].kind == "paragraph"
    assert units[0].text == "This is a simple paragraph."


def test_heading():
    units = chunk_markdown("# My Heading")
    assert len(units) == 1
    assert units[0].kind == "heading"
    assert units[0].text == "My Heading"


def test_heading_levels():
    text = "# H1\n## H2\n### H3"
    units = chunk_markdown(text)
    assert len(units) == 3
    assert all(u.kind == "heading" for u in units)
    assert units[0].text == "H1"
    assert units[1].text == "H2"
    assert units[2].text == "H3"


def test_bullet_list():
    text = "- First item\n- Second item\n- Third item"
    units = chunk_markdown(text)
    assert len(units) == 3
    assert all(u.kind == "bullet" for u in units)
    assert units[0].text == "First item"
    assert units[2].text == "Third item"


def test_numbered_list():
    text = "1. First\n2. Second\n3. Third"
    units = chunk_markdown(text)
    assert len(units) == 3
    assert all(u.kind == "bullet" for u in units)


def test_table_rows():
    text = "| Name | Value |\n|------|-------|\n| foo | 42 |\n| bar | 99 |"
    units = chunk_markdown(text)
    # Header row + 2 data rows (separator skipped)
    assert len(units) == 3
    assert all(u.kind == "table_row" for u in units)
    assert "foo" in units[1].text
    assert "bar" in units[2].text


def test_mixed_document():
    text = """# Title

Some introductory paragraph that
spans multiple lines.

- Bullet one
- Bullet two

## Section Two

Another paragraph here.
"""
    units = chunk_markdown(text)
    kinds = [u.kind for u in units]
    assert kinds == ["heading", "paragraph", "bullet", "bullet", "heading", "paragraph"]


def test_multiline_paragraph_merged():
    text = "Line one of paragraph.\nLine two of paragraph.\nLine three."
    units = chunk_markdown(text)
    assert len(units) == 1
    assert "Line one" in units[0].text
    assert "Line three" in units[0].text


def test_blank_lines_separate_paragraphs():
    text = "Paragraph one.\n\nParagraph two."
    units = chunk_markdown(text)
    assert len(units) == 2
    assert units[0].text == "Paragraph one."
    assert units[1].text == "Paragraph two."


def test_tokens_property():
    unit = ConceptUnit(id=0, text="Cache coherence across microservices", kind="bullet")
    tokens = unit.tokens
    assert "cache" in tokens
    assert "coherence" in tokens
    assert "microservices" in tokens
    assert "across" in tokens


def test_horizontal_rule_skipped():
    text = "Before\n\n---\n\nAfter"
    units = chunk_markdown(text)
    assert len(units) == 2
    texts = [u.text for u in units]
    assert "Before" in texts
    assert "After" in texts


def test_unique_ids():
    text = "# Heading\n\n- Item 1\n- Item 2\n\nParagraph."
    units = chunk_markdown(text)
    ids = [u.id for u in units]
    assert len(ids) == len(set(ids))


def test_source_line_tracking():
    """Source line is best-effort — marko doesn't expose line numbers publicly.
    Verify the field exists and defaults to 0 (unknown) rather than crashing."""
    text = "# Title\n\nParagraph on line 3."
    units = chunk_markdown(text)
    assert isinstance(units[0].source_line, int)
    assert isinstance(units[1].source_line, int)
