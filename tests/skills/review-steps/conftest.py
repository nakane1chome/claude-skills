"""Review-steps specific fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "event-sourcing-draft"


@pytest.fixture
async def review_project(sandbox_project):
    """Sandbox project with a test document placed for review."""
    project = sandbox_project

    # Copy the fixture input document into the project
    input_doc = FIXTURE_DIR / "input.md"
    target = project / "draft.md"
    target.write_text(input_doc.read_text(encoding="utf-8"), encoding="utf-8")

    yield project, target
