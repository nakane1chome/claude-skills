"""Review-skill specific fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "review_skill"


@pytest.fixture
async def review_skill_project(instrumented_project):
    """Instrumented project with the flawed-skill fixture copied in."""
    project, query_fn = instrumented_project

    dest = project / "flawed-skill"
    shutil.copytree(FIXTURES_DIR / "flawed-skill", dest)

    yield project, query_fn
