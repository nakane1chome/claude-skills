"""Word frequency lookup from bundled TSV data."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
FREQ_FILE = DATA_DIR / "word_freq_en.tsv"

# Rank assigned to words not in the frequency list (very rare)
DEFAULT_RANK = 100_000


@lru_cache(maxsize=1)
def load_frequency_table() -> dict[str, int]:
    """Load word frequency ranks from the bundled TSV.

    Returns a dict mapping lowercase word → rank (1 = most common).
    """
    table: dict[str, int] = {}
    if not FREQ_FILE.exists():
        return table
    with open(FREQ_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) >= 2:
                word = row[0].lower().strip()
                try:
                    rank = int(row[1])
                except ValueError:
                    continue
                table[word] = rank
    return table


def word_rank(word: str) -> int:
    """Return the frequency rank of a word (1 = most common)."""
    table = load_frequency_table()
    return table.get(word.lower(), DEFAULT_RANK)


def mean_frequency_rank(tokens: set[str]) -> float:
    """Return the mean frequency rank for a set of tokens."""
    if not tokens:
        return float(DEFAULT_RANK)
    return sum(word_rank(t) for t in tokens) / len(tokens)


def frequency_shift(input_tokens: set[str], output_tokens: set[str]) -> float:
    """Compute the frequency shift between input and output token sets.

    Returns the difference in mean rank: output_mean - input_mean.
    Negative values indicate a shift toward more common (lower rank) words,
    which is an ablation signal.
    """
    input_mean = mean_frequency_rank(input_tokens)
    output_mean = mean_frequency_rank(output_tokens)
    return output_mean - input_mean
