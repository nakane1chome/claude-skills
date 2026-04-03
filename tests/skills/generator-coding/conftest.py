"""Generator-coding test fixtures."""

from __future__ import annotations

import shutil

import pytest


@pytest.fixture
async def project_env(request, instrumented_project):
    """Instrumented project with or without generator-coding skill.

    Pass ``True`` (keep skill) or ``False`` (remove skill) via indirect parametrize.
    """
    project, query_fn = instrumented_project
    keep_skill = request.param

    if not keep_skill:
        skill_dir = project / ".claude" / "skills" / "generator-coding"
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)

    yield project, query_fn
