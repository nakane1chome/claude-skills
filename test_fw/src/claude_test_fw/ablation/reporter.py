"""Output formatters for ablation detection results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .scorer import DocumentScore, PairScore


@dataclass(frozen=True)
class Thresholds:
    """All reporter thresholds in one place."""

    # Per-mode minimum coverage before flagging LOW COVERAGE
    coverage_compress: float = 0.6
    coverage_expand: float = 0.8
    coverage_preserve: float = 0.9

    # Ablation risk verdict boundaries
    ablation_detected: float = 0.3
    ablation_mild: float = 0.15

    # Summary row signal thresholds
    coverage_ok: float = 0.8
    similarity_ok: float = 0.3
    lexical_overlap_ok: float = 0.5
    freq_shift_warn: float = -500.0

    # Per-pair flagging threshold
    pair_flag: float = 0.15

    # Maximum flagged pairs to display
    max_flagged_pairs: int = 10

    def min_coverage(self, mode: str) -> float:
        if mode == "compress":
            return self.coverage_compress
        elif mode == "expand":
            return self.coverage_expand
        return self.coverage_preserve


DEFAULT_THRESHOLDS = Thresholds()


def _verdict(
    score: DocumentScore, mode: str, t: Thresholds
) -> tuple[str, str]:
    """Return (verdict_text, color) based on score and thresholds."""
    min_cov = t.min_coverage(mode)
    if score.coverage < min_cov:
        return f"LOW COVERAGE ({score.coverage:.0%})", "red"

    if score.mean_ablation_risk > t.ablation_detected:
        return "ABLATION DETECTED", "red"
    elif score.mean_ablation_risk > t.ablation_mild:
        return "MILD ABLATION", "yellow"
    else:
        return "CLEAN", "green"


def ablation_metrics(
    score: DocumentScore, mode: str, thresholds: Thresholds = DEFAULT_THRESHOLDS
) -> dict[str, Any]:
    """Build a flat dict of ablation metrics for ``report.add_custom()``."""
    verdict_text, _ = _verdict(score, mode, thresholds)
    return {
        "mode": mode,
        "verdict": verdict_text,
        "coverage": round(score.coverage, 4),
        "mean_lexical_overlap": round(score.mean_lexical_overlap, 4),
        "mean_ablation_risk": round(score.mean_ablation_risk, 4),
        "mean_semantic_similarity": round(score.mean_semantic_similarity, 4),
        "mean_freq_shift": round(score.mean_freq_shift, 2),
        "concepts": (
            f"{score.total_input_concepts} in / "
            f"{score.total_output_concepts} out / "
            f"{score.unmatched_count} unmatched"
        ),
    }


def report_terminal(
    score: DocumentScore, mode: str, thresholds: Thresholds = DEFAULT_THRESHOLDS
) -> None:
    """Rich terminal output."""
    t = thresholds
    console = Console()
    verdict_text, verdict_color = _verdict(score, mode, t)

    # Header
    console.print()
    console.print(
        Panel(
            Text(f"Ablation Analysis ({mode} mode)", style="bold"),
            subtitle=Text(verdict_text, style=f"bold {verdict_color}"),
        )
    )

    # Summary table
    summary = Table(title="Summary Metrics", show_header=True)
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", justify="right")
    summary.add_column("Signal", justify="center")

    # Coverage
    cov_ok = score.coverage >= t.coverage_ok
    cov_color = "green" if cov_ok else "red"
    summary.add_row(
        "Concept coverage",
        f"{score.coverage:.1%}",
        f"[{cov_color}]{'OK' if cov_ok else 'LOW'}[/]",
    )

    # Semantic similarity
    sim_ok = score.mean_semantic_similarity >= t.similarity_ok
    sim_color = "green" if sim_ok else "yellow"
    summary.add_row(
        "Mean semantic similarity",
        f"{score.mean_semantic_similarity:.3f}",
        f"[{sim_color}]{'OK' if sim_ok else 'LOW'}[/]",
    )

    # Lexical overlap
    lex_ok = score.mean_lexical_overlap >= t.lexical_overlap_ok
    lex_color = "green" if lex_ok else "yellow"
    summary.add_row(
        "Mean lexical overlap",
        f"{score.mean_lexical_overlap:.3f}",
        f"[{lex_color}]{'OK' if lex_ok else 'LOW'}[/]",
    )

    # Frequency shift
    freq_label = "toward common" if score.mean_freq_shift < 0 else "toward rare"
    freq_color = "yellow" if score.mean_freq_shift < t.freq_shift_warn else "green"
    summary.add_row(
        "Mean frequency shift",
        f"{score.mean_freq_shift:+.0f}",
        f"[{freq_color}]{freq_label}[/]",
    )

    # Ablation risk
    abl_color = (
        "green"
        if score.mean_ablation_risk < t.ablation_mild
        else "yellow" if score.mean_ablation_risk < t.ablation_detected else "red"
    )
    summary.add_row(
        "Mean ablation risk",
        f"{score.mean_ablation_risk:.3f}",
        f"[{abl_color}]{verdict_text}[/]",
    )

    summary.add_row(
        "Concepts",
        f"{score.total_input_concepts} in → {score.total_output_concepts} out",
        f"{score.unmatched_count} unmatched",
    )

    console.print(summary)

    # Per-pair detail (show worst offenders)
    if score.pair_scores:
        flagged = [p for p in score.pair_scores if p.ablation_risk > t.pair_flag]
        if flagged:
            flagged.sort(key=lambda p: p.ablation_risk, reverse=True)
            detail = Table(title="Flagged Concept Pairs", show_header=True)
            detail.add_column("Input (truncated)", max_width=40)
            detail.add_column("Output (truncated)", max_width=40)
            detail.add_column("Sim", justify="right")
            detail.add_column("LexOv", justify="right")
            detail.add_column("FreqΔ", justify="right")
            detail.add_column("Risk", justify="right")

            for p in flagged[: t.max_flagged_pairs]:
                risk_color = "yellow" if p.ablation_risk < t.ablation_detected else "red"
                detail.add_row(
                    p.input_text[:40],
                    p.output_text[:40],
                    f"{p.semantic_similarity:.2f}",
                    f"{p.lexical_overlap:.2f}",
                    f"{p.freq_shift:+.0f}",
                    f"[{risk_color}]{p.ablation_risk:.3f}[/]",
                )
            console.print(detail)

    console.print()


def _pair_to_dict(p: PairScore) -> dict[str, Any]:
    return {
        "input_text": p.input_text,
        "output_text": p.output_text,
        "semantic_similarity": round(p.semantic_similarity, 4),
        "lexical_overlap": round(p.lexical_overlap, 4),
        "freq_shift": round(p.freq_shift, 2),
        "ablation_risk": round(p.ablation_risk, 4),
    }


def report_json(
    score: DocumentScore, mode: str, thresholds: Thresholds = DEFAULT_THRESHOLDS
) -> str:
    """JSON output."""
    verdict_text, _ = _verdict(score, mode, thresholds)
    data = {
        "mode": mode,
        "verdict": verdict_text,
        "summary": {
            "coverage": round(score.coverage, 4),
            "mean_semantic_similarity": round(score.mean_semantic_similarity, 4),
            "mean_lexical_overlap": round(score.mean_lexical_overlap, 4),
            "mean_freq_shift": round(score.mean_freq_shift, 2),
            "mean_ablation_risk": round(score.mean_ablation_risk, 4),
            "unmatched_count": score.unmatched_count,
            "total_input_concepts": score.total_input_concepts,
            "total_output_concepts": score.total_output_concepts,
        },
        "pairs": [_pair_to_dict(p) for p in score.pair_scores],
    }
    return json.dumps(data, indent=2)


def report_markdown(
    score: DocumentScore, mode: str, thresholds: Thresholds = DEFAULT_THRESHOLDS
) -> str:
    """Markdown output."""
    t = thresholds
    verdict_text, _ = _verdict(score, mode, t)
    lines = [
        f"# Ablation Analysis ({mode} mode)",
        "",
        f"**Verdict: {verdict_text}**",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Concept coverage | {score.coverage:.1%} |",
        f"| Mean semantic similarity | {score.mean_semantic_similarity:.3f} |",
        f"| Mean lexical overlap | {score.mean_lexical_overlap:.3f} |",
        f"| Mean frequency shift | {score.mean_freq_shift:+.0f} |",
        f"| Mean ablation risk | {score.mean_ablation_risk:.3f} |",
        f"| Concepts | {score.total_input_concepts} in → {score.total_output_concepts} out ({score.unmatched_count} unmatched) |",
        "",
    ]

    flagged = [p for p in score.pair_scores if p.ablation_risk > t.pair_flag]
    if flagged:
        flagged.sort(key=lambda p: p.ablation_risk, reverse=True)
        lines.append("## Flagged Pairs")
        lines.append("")
        lines.append("| Input | Output | Sim | LexOv | FreqΔ | Risk |")
        lines.append("|-------|--------|-----|-------|-------|------|")
        for p in flagged[: t.max_flagged_pairs]:
            lines.append(
                f"| {p.input_text[:40]} | {p.output_text[:40]} "
                f"| {p.semantic_similarity:.2f} | {p.lexical_overlap:.2f} "
                f"| {p.freq_shift:+.0f} | {p.ablation_risk:.3f} |"
            )
        lines.append("")

    return "\n".join(lines)
