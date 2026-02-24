"""Review-steps specific fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
async def review_project(instrumented_project):
    """Instrumented project with a test document placed for review."""
    project, query_fn = instrumented_project

    # Copy the fixture input document into the project
    input_doc = FIXTURE_DIR / "event-sourcing-draft" / "input.md"
    target = project / "draft.md"
    target.write_text(input_doc.read_text(encoding="utf-8"), encoding="utf-8")

    yield project, target, query_fn
