"""Test: full document curation pipeline with cross-session memory recall.

Runs flesh-out → review-steps → strong-edit → agent-optimize on a document
with mempalace active, then tests that a fresh session can recall key concepts
from the document using only persistent memory.

The pipeline sessions populate mempalace via the skills' conditional
"if mempalace tools are available" instructions. The recall session has no
access to the document — only mempalace search.
"""

import re
from pathlib import Path

from claude_agent_sdk.types import ResultMessage


# ── prompts ──────────────────────────────────────────────────

FLESH_OUT_PROMPT = """\
Run /flesh-out on draft.md. Complete all stages, applying changes directly.
Approve all suggestions and proceed through every stage without stopping.
"""

REVIEW_PROMPT = """\
Run /review-steps on draft.md. Complete stages 0-3 (understand, language,
clarity, structure). Apply corrections directly. Skip stages 4-6.
Approve all suggestions and proceed without stopping.
"""

STRONG_EDIT_PROMPT = """\
Run /strong-edit on draft.md. Complete all stages through stage 5.
Apply agreed edits directly. Approve all critique points and proceed
without stopping.
"""

AGENT_OPTIMIZE_PROMPT = """\
Run /agent-optimize on draft.md. Complete all stages, applying changes
directly. Approve all suggestions and proceed without stopping.
"""

RECALL_PROMPT = """\
Using mempalace, search your persistent memory for information about
event sourcing in distributed systems. Do NOT read any files.

Based only on what you find in mempalace, answer these questions:
1. What pattern pairs naturally with event sourcing for separating reads and writes?
2. What handles long-running business processes that span multiple aggregates?
3. What captures events that repeatedly fail processing?
4. What enables distributed tracing across aggregate boundaries?

Report what you found in mempalace for each question.
"""

CONTINUE_PROMPT = "Approved. Please proceed through all remaining stages."

# Domain concepts the recall should surface
RECALL_TERMS = {
    "cqrs": r"(?i)cqrs|command.query.responsibility.segregation",
    "saga": r"(?i)saga|process.manager",
    "dead_letter": r"(?i)dead.letter",
    "correlation_id": r"(?i)correlation.id",
}

PIPELINE_STAGES = [
    ("Flesh-out", FLESH_OUT_PROMPT),
    ("Review", REVIEW_PROMPT),
    ("Strong-edit", STRONG_EDIT_PROMPT),
    ("Agent-optimize", AGENT_OPTIMIZE_PROMPT),
]

MAX_TURNS_PIPELINE = 30
MAX_TURNS_RECALL = 10


async def test_pipeline_memory_recall(
    pipeline_project, steps, sdk, model, model_alias, report, audit,
):
    """Pipeline populates mempalace; fresh session recalls key concepts."""
    project_dir, doc_path, query_fn, mempalace = pipeline_project

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    prev_text = doc_path.read_text(encoding="utf-8")

    # ── Pipeline phase ───────────────────────────────────────
    for phase_name, prompt in PIPELINE_STAGES:
        async with query_fn.conversation(
            max_turns=MAX_TURNS_PIPELINE,
            mcp_servers=mempalace,
        ) as conv:
            await conv.say(prompt)
            await conv.say(CONTINUE_PROMPT)

        messages = conv.messages
        results = [m for m in messages if isinstance(m, ResultMessage)]
        result = results[-1] if results else None

        steps.require_session_ok(messages, phase=phase_name)
        session_id = result.session_id

        audit.finalize(project_dir, session_id)
        report.add(session_id, sdk.metrics(messages), phase=phase_name)
        sdk.log_phase(phase_name, messages, project_dir)

        current_text = doc_path.read_text(encoding="utf-8")
        steps.expect(
            f"{phase_name}: document modified",
            current_text != prev_text,
            session_id=session_id,
            phase=phase_name,
        )
        prev_text = current_text

    # ── Recall phase ─────────────────────────────────────────
    recall_messages = await query_fn(
        RECALL_PROMPT,
        max_turns=MAX_TURNS_RECALL,
        mcp_servers=mempalace,
    )

    steps.require_session_ok(recall_messages, phase="Recall")
    recall_result = sdk.result(recall_messages)
    recall_session_id = recall_result.session_id

    report.add(recall_session_id, sdk.metrics(recall_messages), phase="Recall")
    sdk.log_phase("Recall", recall_messages, project_dir)

    recall_text = sdk.text(recall_messages)

    # expect_: recall should produce substantial output
    steps.expect_text_length(
        recall_text, 100,
        session_id=recall_session_id,
        phase="Recall",
    )

    # achieve_: check each domain concept in recall output
    found = 0
    for concept, pattern in RECALL_TERMS.items():
        matched = bool(re.search(pattern, recall_text))
        if matched:
            found += 1
        steps.achieve(
            f"recall: {concept}",
            matched,
            difficulty="challenging",
            phase="Recall",
            detail=f"{'found' if matched else 'missing'} in recall output",
        )

    # expect_: at least 2 of 4 concepts recalled
    steps.expect(
        "recall: >= 2 of 4 concepts found",
        found >= 2,
        session_id=recall_session_id,
        phase="Recall",
        detail=f"{found}/4 concepts",
    )
