"""Compute ablation metrics for matched concept pairs."""

from __future__ import annotations

from dataclasses import dataclass

from .matcher import Match, MatchResult
from .wordfreq import frequency_shift


@dataclass
class PairScore:
    """Ablation metrics for a single matched concept pair."""

    input_text: str
    output_text: str
    semantic_similarity: float
    lexical_overlap: float
    freq_shift: float
    ablation_risk: float


@dataclass
class DocumentScore:
    """Aggregate ablation metrics for an entire document comparison."""

    pair_scores: list[PairScore]
    coverage: float
    mean_semantic_similarity: float
    mean_lexical_overlap: float
    mean_freq_shift: float
    mean_ablation_risk: float
    unmatched_count: int
    total_input_concepts: int
    total_output_concepts: int


def lexical_overlap(input_tokens: set[str], output_tokens: set[str]) -> float:
    """Fraction of input tokens that appear in the output."""
    if not input_tokens:
        return 1.0
    return len(input_tokens & output_tokens) / len(input_tokens)


def ablation_risk(
    semantic_sim: float, lex_overlap: float, freq_shift_val: float
) -> float:
    """Composite ablation risk score.

    High risk = high semantic similarity (meaning preserved)
              × low lexical overlap (words replaced)
              × negative frequency shift (shifted toward common words)

    Returns a value in [0, 1] where higher = more ablation.
    """
    word_replacement = 1.0 - lex_overlap
    # Normalize freq shift: negative shift (toward common words) is the signal
    # Clamp to [0, 1] range using a sigmoid-like scaling
    freq_signal = max(0.0, -freq_shift_val) / (abs(freq_shift_val) + 1000.0)
    return semantic_sim * word_replacement * (1.0 + freq_signal)


def score_pair(match: Match) -> PairScore:
    """Compute all metrics for a single matched pair."""
    in_tokens = match.input_unit.tokens
    out_tokens = match.output_unit.tokens
    lex_ov = lexical_overlap(in_tokens, out_tokens)
    freq_sh = frequency_shift(in_tokens, out_tokens)
    abl_risk = ablation_risk(match.similarity, lex_ov, freq_sh)

    return PairScore(
        input_text=match.input_unit.text,
        output_text=match.output_unit.text,
        semantic_similarity=match.similarity,
        lexical_overlap=lex_ov,
        freq_shift=freq_sh,
        ablation_risk=abl_risk,
    )


def score_document(
    match_result: MatchResult,
    total_input: int,
    total_output: int,
) -> DocumentScore:
    """Compute aggregate ablation metrics for a full document comparison."""
    pair_scores = [score_pair(m) for m in match_result.matches]

    n_matched = len(pair_scores)
    coverage = n_matched / total_input if total_input > 0 else 0.0

    if n_matched > 0:
        mean_sim = sum(p.semantic_similarity for p in pair_scores) / n_matched
        mean_lex = sum(p.lexical_overlap for p in pair_scores) / n_matched
        mean_freq = sum(p.freq_shift for p in pair_scores) / n_matched
        mean_abl = sum(p.ablation_risk for p in pair_scores) / n_matched
    else:
        mean_sim = mean_lex = mean_abl = 0.0
        mean_freq = 0.0

    return DocumentScore(
        pair_scores=pair_scores,
        coverage=coverage,
        mean_semantic_similarity=mean_sim,
        mean_lexical_overlap=mean_lex,
        mean_freq_shift=mean_freq,
        mean_ablation_risk=mean_abl,
        unmatched_count=len(match_result.unmatched_inputs),
        total_input_concepts=total_input,
        total_output_concepts=total_output,
    )
