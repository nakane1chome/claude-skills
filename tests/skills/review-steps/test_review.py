"""Test: review-steps skill preserves author vocabulary (ablation analysis).

Sends a structured draft to Claude for review (stages 0-2 of review-steps),
then runs the ablation detector on the input vs output to verify that
domain-specific vocabulary was preserved.

Uses multi-turn conversation to respond to the skill's stop-after-each-stage
pattern with approval messages, mimicking a real developer interaction.
"""

from pathlib import Path

import pytest
from claude_agent_sdk.types import ResultMessage

from claude_test_fw.ablation.chunker import chunk_markdown
from claude_test_fw.ablation.embedder import TfidfEmbedder
from claude_test_fw.ablation.matcher import greedy_match
from claude_test_fw.ablation.reporter import ablation_metrics
from claude_test_fw.ablation.scorer import score_document


REVIEW_PROMPT = """\
Review the document `draft.md` following the review-steps process.

Complete these stages, applying corrections directly to the file:

1. **Read and understand** — identify the document's function, audience, and goal
2. **Language and consistency** — fix spelling, grammar, punctuation; ensure \
consistent terminology and patterns
3. **Conceptual clarity** — fix incomplete sentences, unclear phrasing; expand \
acronyms on first use

Apply all corrections directly to `draft.md` and save the result.
"""

CONTINUE_PROMPT = "Please proceed as suggested."

MAX_FOLLOW_UPS = 5


def _run_ablation(input_text: str, output_text: str):
    """Run the ablation pipeline and return a DocumentScore."""
    input_units = chunk_markdown(input_text)
    output_units = chunk_markdown(output_text)

    embedder = TfidfEmbedder()
    all_texts = [u.text for u in input_units] + [u.text for u in output_units]
    embedder.fit(all_texts)

    input_emb = embedder.embed(input_units)
    output_emb = embedder.embed(output_units)

    match_result = greedy_match(input_units, output_units, input_emb, output_emb)
    return score_document(match_result, len(input_units), len(output_units))


async def test_review_preserves_vocabulary(
    review_project, steps, sdk, model, model_alias, report, audit,
):
    """Claude's review output should preserve domain-specific vocabulary."""
    project_dir, doc_path, query_fn = review_project
    input_text = doc_path.read_text(encoding="utf-8")

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        test_file=Path(__file__),
    )

    # Multi-turn: send initial prompt, then respond with approvals
    async with query_fn.conversation(max_turns=15) as conv:
        await conv.say(REVIEW_PROMPT)

        for _ in range(MAX_FOLLOW_UPS):
            if doc_path.read_text(encoding="utf-8") != input_text:
                break
            await conv.say(CONTINUE_PROMPT)

    all_messages = conv.messages
    results = [m for m in all_messages if isinstance(m, ResultMessage)]
    result = results[-1] if results else None

    # require_: session must complete
    steps.require_session_ok(all_messages, phase="Review")

    session_id = result.session_id

    # Finalize audit
    audit.finalize(project_dir, session_id)

    report.add(session_id, sdk.metrics(all_messages), phase="Review")
    sdk.log_phase("Review", all_messages, project_dir)

    # Read the modified document
    output_text = doc_path.read_text(encoding="utf-8")

    # expect_: prompt asked for review — document should be modified
    steps.expect("document modified", output_text != input_text,
                 session_id=session_id, phase="Review")

    # Run ablation analysis
    score = _run_ablation(input_text, output_text)

    # Attach ablation metrics to the shared report
    report.add_custom("ablation", ablation_metrics(score, "preserve"))

    # expect_: review should preserve vocabulary above thresholds
    steps.expect("coverage >= 0.7", score.coverage >= 0.7,
                 phase="Ablation",
                 detail=f"{score.coverage:.3f}")
    steps.expect("lexical overlap >= 0.4", score.mean_lexical_overlap >= 0.4,
                 phase="Ablation",
                 detail=f"{score.mean_lexical_overlap:.3f}")
    steps.expect("ablation risk < 0.35", score.mean_ablation_risk < 0.35,
                 phase="Ablation",
                 detail=f"{score.mean_ablation_risk:.3f}")

    # achieve_: higher-quality ablation thresholds
    steps.achieve("coverage >= 0.85", score.coverage >= 0.85,
                  difficulty="expected", phase="Ablation",
                  detail=f"{score.coverage:.3f}")
    steps.achieve("lexical overlap >= 0.6", score.mean_lexical_overlap >= 0.6,
                  difficulty="challenging", phase="Ablation",
                  detail=f"{score.mean_lexical_overlap:.3f}")
    steps.achieve("ablation risk < 0.15", score.mean_ablation_risk < 0.15,
                  difficulty="challenging", phase="Ablation",
                  detail=f"{score.mean_ablation_risk:.3f}")
