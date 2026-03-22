"""Dev-record specific fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
async def installed_project(instrumented_project):
    """Alias for instrumented_project — preserves existing test signatures."""
    yield instrumented_project
