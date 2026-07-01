"""Parameterized retrieval for the grid (H3a, R3): vector / BM25 / hybrid.

    retrieve(query, records, method="vector", k=5, alpha=0.5, embed_model="minilm")

One interface so the orchestrator (H3b) can sweep the retrieval axis on a single
index. vector = meaning (embeddings), bm25 = word overlap, hybrid = min-max
normalize both then alpha * vector + (1 - alpha) * bm25.

NOTE (efficiency, for H3b): BM25 is rebuilt on every call to keep this interface
simple. When scoring many holdout questions against one index, build BM25 once
and reuse it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rag-starter"))
from indexer import cosine_distance, embed  # noqa: E402

from rank_bm25 import BM25Okapi  # noqa: E402


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _minmax(scores: list[float]) -> list[float]:
    """Scale to [0, 1] so vector and BM25 scores can be blended; flat -> zeros."""
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [0.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


def _vector_scores(query: str, records: list[dict], embed_model: str) -> list[float]:
    [qv] = embed([query], embed_model, is_query=True)
    # similarity (higher = better) = 1 - cosine distance
    return [1.0 - cosine_distance(r["embedding"], qv) for r in records]


def _bm25_scores(query: str, records: list[dict]) -> list[float]:
    bm25 = BM25Okapi([_tokenize(r["text"]) for r in records])
    return list(bm25.get_scores(_tokenize(query)))


def retrieve(query: str, records: list[dict], method: str = "vector",
             k: int = 5, alpha: float = 0.5,
             embed_model: str = "minilm") -> list[dict]:
    """Top-k records for `query` under the chosen retrieval method."""
    if method == "vector":
        scores = _vector_scores(query, records, embed_model)
    elif method == "bm25":
        scores = _bm25_scores(query, records)
    elif method == "hybrid":
        vec = _minmax(_vector_scores(query, records, embed_model))
        bm = _minmax(_bm25_scores(query, records))
        scores = [alpha * v + (1 - alpha) * b for v, b in zip(vec, bm)]
    else:
        raise ValueError(f"unknown method: {method!r}")

    # Rank by index, not by zipping (score, record) — ties would compare dicts.
    order = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)
    return [records[i] for i in order[:k]]
