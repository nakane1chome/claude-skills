"""Static tests validating the review-steps ablation fixtures.

These tests verify the fixture files themselves produce the expected
ablation signals, without invoking Claude. They mirror the pattern
in tests/tools/ablation/test_integration.py.
"""

from pathlib import Path

import yaml

from claude_test_fw.ablation.chunker import chunk_markdown
from claude_test_fw.ablation.embedder import TfidfEmbedder
from claude_test_fw.ablation.matcher import greedy_match
from claude_test_fw.ablation.scorer import score_document

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "event-sourcing-draft"


def _run_comparison(input_path: Path, output_path: Path):
    """Run the full ablation pipeline on two files and return the document score."""
    input_text = input_path.read_text(encoding="utf-8")
    output_text = output_path.read_text(encoding="utf-8")

    input_units = chunk_markdown(input_text)
    output_units = chunk_markdown(output_text)

    embedder = TfidfEmbedder()
    all_texts = [u.text for u in input_units] + [u.text for u in output_units]
    embedder.fit(all_texts)

    input_emb = embedder.embed(input_units)
    output_emb = embedder.embed(output_units)

    match_result = greedy_match(input_units, output_units, input_emb, output_emb)
    return score_document(match_result, len(input_units), len(output_units))


def test_fixture_files_exist():
    """Verify all fixture files are present."""
    assert (FIXTURE_DIR / "input.md").exists()
    assert (FIXTURE_DIR / "expected-good.md").exists()
    assert (FIXTURE_DIR / "expected-ablated.md").exists()
    assert (FIXTURE_DIR / "manifest.yaml").exists()


def test_good_output_has_high_coverage():
    """Good review output should have high concept coverage (preserve mode)."""
    score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-good.md"
    )
    assert score.coverage >= 0.9, f"Coverage too low: {score.coverage:.3f}"


def test_ablated_output_has_coverage():
    """Ablated output should still have partial coverage (meaning preserved)."""
    score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-ablated.md"
    )
    assert score.coverage >= 0.5, f"Coverage too low: {score.coverage:.3f}"


def test_good_output_higher_lexical_overlap():
    """Good review output should have higher lexical overlap than ablated output."""
    good_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-good.md"
    )
    ablated_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-ablated.md"
    )
    assert good_score.mean_lexical_overlap > ablated_score.mean_lexical_overlap, (
        f"Good ({good_score.mean_lexical_overlap:.3f}) should have higher "
        f"lexical overlap than ablated ({ablated_score.mean_lexical_overlap:.3f})"
    )


def test_ablated_output_higher_ablation_risk():
    """Ablated output should have a higher ablation risk score."""
    good_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-good.md"
    )
    ablated_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-ablated.md"
    )
    assert ablated_score.mean_ablation_risk > good_score.mean_ablation_risk, (
        f"Ablated ({ablated_score.mean_ablation_risk:.3f}) should have higher "
        f"ablation risk than good ({good_score.mean_ablation_risk:.3f})"
    )


def test_manifest_expectations():
    """Verify scores align with the manifest's expected thresholds."""
    manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text())
    expected = manifest["expected"]

    good_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-good.md"
    )
    ablated_score = _run_comparison(
        FIXTURE_DIR / "input.md", FIXTURE_DIR / "expected-ablated.md"
    )

    # Good output checks
    good_exp = expected["good"]
    assert good_score.coverage >= good_exp["min_coverage"], (
        f"Good coverage {good_score.coverage:.3f} < {good_exp['min_coverage']}"
    )
    assert good_score.mean_lexical_overlap >= good_exp["min_lexical_overlap"], (
        f"Good lexical overlap {good_score.mean_lexical_overlap:.3f} < "
        f"{good_exp['min_lexical_overlap']}"
    )

    # Ablated output checks
    abl_exp = expected["ablated"]
    assert ablated_score.coverage >= abl_exp["min_coverage"], (
        f"Ablated coverage {ablated_score.coverage:.3f} < {abl_exp['min_coverage']}"
    )
    assert ablated_score.mean_lexical_overlap <= abl_exp["max_lexical_overlap"], (
        f"Ablated lexical overlap {ablated_score.mean_lexical_overlap:.3f} > "
        f"{abl_exp['max_lexical_overlap']}"
    )


def test_identical_file_no_ablation():
    """Comparing a file to itself should show no ablation."""
    score = _run_comparison(FIXTURE_DIR / "input.md", FIXTURE_DIR / "input.md")
    assert score.coverage == 1.0
    assert score.mean_lexical_overlap == 1.0
    assert score.mean_ablation_risk == 0.0
