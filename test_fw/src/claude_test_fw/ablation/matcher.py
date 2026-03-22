"""Greedy cosine similarity matching between input and output concept units."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .chunker import ConceptUnit


@dataclass
class Match:
    """A matched pair of input and output concept units."""

    input_unit: ConceptUnit
    output_unit: ConceptUnit
    similarity: float


@dataclass
class MatchResult:
    """Result of matching input concepts to output concepts."""

    matches: list[Match]
    unmatched_inputs: list[ConceptUnit]
    similarity_matrix: NDArray[np.float64]


def cosine_similarity_matrix(
    a: NDArray[np.float64], b: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Compute pairwise cosine similarity between row vectors of a and b."""
    # Normalize rows
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)

    # Avoid division by zero for empty vectors
    a_norm = np.where(a_norm == 0, 1, a_norm)
    b_norm = np.where(b_norm == 0, 1, b_norm)

    a_normalized = a / a_norm
    b_normalized = b / b_norm

    return a_normalized @ b_normalized.T


def greedy_match(
    input_units: list[ConceptUnit],
    output_units: list[ConceptUnit],
    input_embeddings: NDArray[np.float64],
    output_embeddings: NDArray[np.float64],
    threshold: float = 0.1,
) -> MatchResult:
    """Greedy matching: each input concept maps to the best-matching output concept.

    Multiple inputs can map to the same output (consolidation is valid).
    Inputs below the similarity threshold are left unmatched.
    """
    sim_matrix = cosine_similarity_matrix(input_embeddings, output_embeddings)
    matches: list[Match] = []
    unmatched: list[ConceptUnit] = []

    for i, input_unit in enumerate(input_units):
        if len(output_units) == 0:
            unmatched.append(input_unit)
            continue

        best_j = int(np.argmax(sim_matrix[i]))
        best_sim = float(sim_matrix[i, best_j])

        if best_sim >= threshold:
            matches.append(
                Match(
                    input_unit=input_unit,
                    output_unit=output_units[best_j],
                    similarity=best_sim,
                )
            )
        else:
            unmatched.append(input_unit)

    return MatchResult(
        matches=matches,
        unmatched_inputs=unmatched,
        similarity_matrix=sim_matrix,
    )
