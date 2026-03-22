"""Pluggable embedding backends for concept units."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer

from .chunker import ConceptUnit


class Embedder(ABC):
    """Base class for embedding backends."""

    @abstractmethod
    def embed(self, units: list[ConceptUnit]) -> NDArray[np.float64]:
        """Return an (n_units, n_dims) matrix of embeddings."""


class TfidfEmbedder(Embedder):
    """TF-IDF embeddings using scikit-learn.

    Fits a joint vocabulary on all provided texts, then transforms each
    unit into a sparse TF-IDF vector (converted to dense for cosine math).
    """

    def __init__(self, max_features: int = 5000) -> None:
        self.max_features = max_features
        self._vectorizer: TfidfVectorizer | None = None

    def fit(self, texts: list[str]) -> None:
        """Fit the vectorizer on a combined corpus."""
        self._vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            stop_words="english",
            sublinear_tf=True,
        )
        self._vectorizer.fit(texts)

    def embed(self, units: list[ConceptUnit]) -> NDArray[np.float64]:
        if self._vectorizer is None:
            raise RuntimeError("Call fit() before embed()")
        texts = [u.text for u in units]
        sparse = self._vectorizer.transform(texts)
        return sparse.toarray().astype(np.float64)


def make_embedder(backend: str = "tfidf", **kwargs) -> Embedder:
    """Factory for embedding backends."""
    if backend == "tfidf":
        return TfidfEmbedder(**kwargs)
    raise ValueError(f"Unknown embedding backend: {backend}")
