"""Test: light-v-structure scaffold mode creates the canonical project structure.

Two parametrized starting states (via ``light_v_project``):
* ``empty``   — no ``docs/`` directory exists.
* ``partial`` — sentinel-bearing files pre-seeded; the test asserts these
  survive the scaffold ("do not overwrite existing files").

The conversation follows the skill's stop-after-each-stage contract:
* Turn 1 (Propose) — invoke ``/light-v-structure scaffold``; model should
  produce a proposal and stop, **without** writing any new files.
* Turn 2 (Approve) — approve the proposal; model creates the canonical
  tree using the stub templates from ``scaffold.md``.

Out of scope for this first test: strict template fidelity against every
stub, and the ``check`` / ``explain`` modes (separate tests).
"""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk.types import ResultMessage

from _helpers import (
    assert_canonical_dirs_exist,
    assert_canonical_files_exist,
    assert_minimal_content_sanity,
    assert_preserved,
    docs_files_written,
)


PROMPT_PROPOSE = """\
Use the light-v-structure skill in scaffold mode: `/light-v-structure scaffold`.

Inventory the current `docs/` tree (if any), then propose the canonical
directory tree and the list of placeholder files you would create. Do **not**
create any files or directories yet — stop for developer review.
"""

PROMPT_APPROVE = """\
The proposal looks good. Proceed with stage 5 of scaffold: create the missing
directories and files using the stub templates in `scaffold.md`. Do not
overwrite any files that already exist.
"""


async def test_scaffold_creates_canonical_structure(
    light_v_project, steps, sdk, model, model_alias, report, audit,
):
    """Scaffold proposes, then on approval creates the canonical V-model tree."""
    project_dir, query_fn, start_state, preserved = light_v_project

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    async with query_fn.conversation(max_turns=30) as conv:
        # Stage 1 — propose only, no writes expected.
        propose_messages = await conv.say(PROMPT_PROPOSE)
        propose_results = [m for m in propose_messages
                           if isinstance(m, ResultMessage)]
        propose_session_id = (propose_results[-1].session_id
                              if propose_results else None)
        if propose_results:
            report.add(propose_results[-1].session_id,
                       sdk.metrics(propose_messages), phase="Propose")
        sdk.log_phase("Propose", propose_messages, project_dir)

        # Checkpoint behaviour: nothing under docs/ should have been written
        # yet (beyond the pre-seeded files in the "partial" variant).
        written_during_propose = docs_files_written(project_dir, preserved)
        steps.achieve(
            "propose stage created no files",
            passed=(len(written_during_propose) == 0),
            difficulty="expected",
            detail=("no writes" if not written_during_propose
                    else f"wrote: {written_during_propose[:5]}"),
            session_id=propose_session_id, phase="Propose",
        )

        # Stage 2 — approve; model creates files.
        approve_messages = await conv.say(PROMPT_APPROVE)

    all_messages = conv.messages
    result = steps.require_session_ok(all_messages, phase="Approve")
    session_id = result.session_id

    audit.finalize(project_dir, session_id)
    report.add(session_id, sdk.metrics(approve_messages), phase="Approve")
    sdk.log_phase("Approve", approve_messages, project_dir)

    assert_canonical_dirs_exist(steps, project_dir, session_id)
    assert_canonical_files_exist(steps, project_dir, session_id)
    assert_preserved(steps, project_dir, preserved, session_id)
    assert_minimal_content_sanity(steps, project_dir, session_id)
