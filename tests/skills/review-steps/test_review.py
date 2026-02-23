"""Test: review-steps skill preserves author vocabulary (ablation analysis).

Sends a structured draft to Claude for review (stages 0-2 of review-steps),
then runs the ablation detector on the input vs output to verify that
domain-specific vocabulary was preserved.
"""

from pathlib import Path

import pytest

from tools.ablation.chunker import chunk_markdown
from tools.ablation.embedder import TfidfEmbedder
from tools.ablation.matcher import greedy_match
from tools.ablation.reporter import ablation_metrics
from tools.ablation.scorer import score_document


REVIEW_PROMPT = """\
Review the document `draft.md` following the review-steps process.

Complete these stages, applying corrections directly to the file:

1. **Read and understand** — identify the document's function, audience, and goal
2. **Language and consistency** — fix spelling, grammar, punctuation; ensure \
consistent terminology and patterns
3. **Conceptual clarity** — fix incomplete sentences, unclear phrasing; expand \
acronyms on first use

Apply all corrections directly to `draft.md` and save the result.
Do not wait for approval between stages — proceed through all three and save \
the final version.
"""


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
    review_project, claude_query, sdk, model, model_alias, report,
):
    """Claude's review output should preserve domain-specific vocabulary."""
    project_dir, doc_path = review_project
    input_text = doc_path.read_text(encoding="utf-8")

    report.configure(
        project_dir=project_dir, model=model, model_alias=model_alias,
        title="Review-Steps Ablation Test", test_file=Path(__file__),
    )

    messages = await claude_query(
        REVIEW_PROMPT,
        max_turns=15,
    )

    result = sdk.result(messages)
    assert result is not None, "No ResultMessage from review session"
    assert not result.is_error, (
        f"Review session ended with error: {sdk.text(messages)[-500:]}"
    )

    session_id = result.session_id
    report.add(session_id, sdk.metrics(messages), phase="Review")
    sdk.log_phase("Review", messages, project_dir)

    # Read the modified document
    output_text = doc_path.read_text(encoding="utf-8")
    assert output_text != input_text, "Document was not modified by review"

    # Run ablation analysis
    score = _run_ablation(input_text, output_text)

    # Attach ablation metrics to the shared report
    report.add_custom("ablation", ablation_metrics(score, "preserve"))

    # Preserve mode: review should fix language without replacing vocabulary.
    # Thresholds are slightly relaxed vs the static fixture tests because
    # Claude may restructure sentences more than the hand-crafted expected-good.
    assert score.coverage >= 0.7, (
        f"Coverage too low: {score.coverage:.3f} (expected >= 0.7). "
        f"Review may have restructured too aggressively."
    )
    assert score.mean_lexical_overlap >= 0.4, (
        f"Lexical overlap too low: {score.mean_lexical_overlap:.3f} "
        f"(expected >= 0.4). "
        f"Review may have replaced domain-specific vocabulary."
    )
    assert score.mean_ablation_risk < 0.35, (
        f"Ablation risk too high: {score.mean_ablation_risk:.3f} "
        f"(expected < 0.35). "
        f"Review output shows signs of vocabulary flattening."
    )
