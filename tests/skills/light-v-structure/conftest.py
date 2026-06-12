"""Fixtures for light-v-structure skill tests.

Parametrized ``light_v_project`` fixture wraps ``instrumented_project`` with
one of two starting states:

* ``empty``   — no ``docs/`` directory at all.
* ``partial`` — sentinel-bearing files pre-seeded under ``docs/`` so the
  "do not overwrite existing files" rule from scaffold mode can be
  verified.

Canonical-structure inventory and seed content live in ``_helpers.py``.
"""

from __future__ import annotations

import pytest

from _helpers import PARTIAL_SEEDS


@pytest.fixture(params=["empty", "partial"], ids=["empty", "partial"])
async def light_v_project(request, instrumented_project):
    """Yield ``(project_dir, query_fn, start_state, preserved_files)``.

    * ``start_state`` is the param id (``"empty"`` or ``"partial"``).
    * ``preserved_files`` is ``{relpath: sentinel_text}``; empty for the
      ``"empty"`` start state.
    """
    project, query_fn = instrumented_project
    start_state = request.param

    preserved: dict[str, str] = {}
    if start_state == "partial":
        for relpath, content in PARTIAL_SEEDS.items():
            target = project / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            preserved[relpath] = content

    yield project, query_fn, start_state, preserved
