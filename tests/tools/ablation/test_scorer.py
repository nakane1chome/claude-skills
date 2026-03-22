"""Tests for the scoring module."""

from .chunker import ConceptUnit
from .matcher import Match, MatchResult
from .scorer import lexical_overlap, ablation_risk, score_pair, score_document

import numpy as np


def _unit(text: str, uid: int = 0) -> ConceptUnit:
    return ConceptUnit(id=uid, text=text, kind="paragraph")


def test_lexical_overlap_identical():
    tokens = {"cache", "coherence", "microservices"}
    assert lexical_overlap(tokens, tokens) == 1.0


def test_lexical_overlap_disjoint():
    a = {"cache", "coherence", "tombstone"}
    b = {"update", "notification", "message"}
    assert lexical_overlap(a, b) == 0.0


def test_lexical_overlap_partial():
    a = {"cache", "coherence", "tombstone", "propagation"}
    b = {"cache", "consistency", "update", "propagation"}
    # 2 out of 4 input tokens present
    assert lexical_overlap(a, b) == 0.5


def test_lexical_overlap_empty_input():
    assert lexical_overlap(set(), {"foo", "bar"}) == 1.0


def test_ablation_risk_identical_text():
    # Same words → high lexical overlap → low risk
    risk = ablation_risk(semantic_sim=0.95, lex_overlap=0.9, freq_shift_val=0.0)
    assert risk < 0.15


def test_ablation_risk_word_replacement():
    # High similarity but low lexical overlap → ablation signal
    risk = ablation_risk(semantic_sim=0.8, lex_overlap=0.2, freq_shift_val=-500.0)
    assert risk > 0.3


def test_ablation_risk_frequency_shift_amplifies():
    # Negative frequency shift should increase risk
    risk_no_shift = ablation_risk(semantic_sim=0.8, lex_overlap=0.3, freq_shift_val=0.0)
    risk_with_shift = ablation_risk(
        semantic_sim=0.8, lex_overlap=0.3, freq_shift_val=-2000.0
    )
    assert risk_with_shift > risk_no_shift


def test_score_pair():
    inp = _unit("Cache coherence requires tombstone propagation")
    out = _unit("Cache consistency requires tombstone propagation")
    match = Match(input_unit=inp, output_unit=out, similarity=0.85)
    result = score_pair(match)
    assert result.semantic_similarity == 0.85
    assert 0.0 <= result.lexical_overlap <= 1.0
    assert isinstance(result.freq_shift, float)
    assert result.ablation_risk >= 0.0


def test_score_document_full_coverage():
    inp1 = _unit("Cache coherence", uid=0)
    out1 = _unit("Cache coherence across services", uid=0)
    match_result = MatchResult(
        matches=[Match(input_unit=inp1, output_unit=out1, similarity=0.9)],
        unmatched_inputs=[],
        similarity_matrix=np.array([[0.9]]),
    )
    doc = score_document(match_result, total_input=1, total_output=1)
    assert doc.coverage == 1.0
    assert doc.unmatched_count == 0


def test_score_document_partial_coverage():
    inp1 = _unit("Cache coherence", uid=0)
    inp2 = _unit("Tombstone propagation", uid=1)
    out1 = _unit("Cache coherence across services", uid=0)
    match_result = MatchResult(
        matches=[Match(input_unit=inp1, output_unit=out1, similarity=0.9)],
        unmatched_inputs=[inp2],
        similarity_matrix=np.array([[0.9], [0.05]]),
    )
    doc = score_document(match_result, total_input=2, total_output=1)
    assert doc.coverage == 0.5
    assert doc.unmatched_count == 1
