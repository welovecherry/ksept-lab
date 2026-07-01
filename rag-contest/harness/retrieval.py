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


def build_bm25(records: list[dict]) -> BM25Okapi:
    """Build a reusable BM25 index once (the orchestrator reuses it per question)."""
    return BM25Okapi([_tokenize(r["text"]) for r in records])


def format_context(hits: list[dict]) -> str:
    """Number retrieved chunks for the prompt's CONTEXT block: '[1] ...\\n\\n[2] ...'.

    One definition for app.py, streamlit_app.py, gen_answers.py, and try_prompt.py
    so the citation numbering can't drift between the live app and the harness.
    """
    return "\n\n".join(f"[{i + 1}] {h['text']}" for i, h in enumerate(hits))


# ── Query-based sub-chunk rerank (todo/07_01_cap_context_tokens.md, A′) ───────
# Section chunks vary wildly (median ~1k, max ~200k chars). An uncapped K=5 of
# huge §-sections blows past 15k input tokens. Front-N truncation would drop the
# answer when it sits in a late subsection like (a)(1)(iv) — and CONTEST practice
# Q1 (§61.109 private-pilot experience) is exactly that shape. So instead of
# cutting by position, we split big hits into windows and keep the ones most
# similar to the QUERY, up to a char budget. Same token budget, better recall,
# no re-index (runs at request time on the already-loaded local model).
_META_KEYS = ("section", "part", "source", "chunk_index")

DEFAULT_WINDOW_CHARS = 500     # sub-chunk size (tuned in step 2)
# Total chars kept for CONTEXT. 5000 (~1,250 input tok) measured better than 6500:
# tighter context → more relevant windows → the model writes MORE complete answers
# on detail/multi-part questions while total tokens drop (input↓, substance output↑).
DEFAULT_CONTEXT_BUDGET = 5000


def _windows(text: str, size: int) -> list[str]:
    """Split text into ~size-char windows, preferring paragraph boundaries."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    windows: list[str] = []
    cur = ""
    for p in paras:
        # A single oversized paragraph is char-windowed on its own.
        if len(p) > size:
            if cur:
                windows.append(cur)
                cur = ""
            windows += [p[i:i + size] for i in range(0, len(p), size)]
        elif cur and len(cur) + 2 + len(p) > size:
            windows.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        windows.append(cur)
    return windows or ([text] if text else [])


def select_context(query: str, hits: list[dict], embed_model: str,
                   window_chars: int = DEFAULT_WINDOW_CHARS,
                   char_budget: int = DEFAULT_CONTEXT_BUDGET) -> list[dict]:
    """Rerank sub-chunks of `hits` by query similarity, keep up to char_budget.

    Returns window-sized "hits" each carrying the parent's section/part/source so
    citations still resolve. Best-first order. Falls back to `hits` if empty.
    """
    windows = [
        {**{k: h.get(k) for k in _META_KEYS}, "text": w}
        for h in hits for w in _windows(h["text"], window_chars)
    ]
    if not windows:
        return hits
    qv = embed([query], embed_model, is_query=True)[0]
    wv = embed([w["text"] for w in windows], embed_model, is_query=False)
    # Pair each window with its vector, sort by distance (lower = closer to query).
    ranked = [w for w, _ in sorted(zip(windows, wv),
                                   key=lambda p: cosine_distance(p[1], qv))]
    kept: list[dict] = []
    total = 0
    for w in ranked:
        if kept and total + len(w["text"]) > char_budget:
            break
        kept.append(w)
        total += len(w["text"])
    return kept


def _bm25_scores(query: str, records: list[dict], bm25: BM25Okapi | None = None) -> list[float]:
    bm25 = bm25 or build_bm25(records)
    return list(bm25.get_scores(_tokenize(query)))


def retrieve(query: str, records: list[dict], method: str = "vector",
             k: int = 5, alpha: float = 0.5,
             embed_model: str = "minilm", bm25: BM25Okapi | None = None) -> list[dict]:
    """Top-k records for `query` under the chosen retrieval method.

    Pass a prebuilt `bm25` (from build_bm25) to avoid rebuilding it per query.
    """
    if method == "vector":
        scores = _vector_scores(query, records, embed_model)
    elif method == "bm25":
        scores = _bm25_scores(query, records, bm25)
    elif method == "hybrid":
        vec = _minmax(_vector_scores(query, records, embed_model))
        bm = _minmax(_bm25_scores(query, records, bm25))
        scores = [alpha * v + (1 - alpha) * b for v, b in zip(vec, bm)]
    else:
        raise ValueError(f"unknown method: {method!r}")

    # Rank by index, not by zipping (score, record) — ties would compare dicts.
    order = sorted(range(len(records)), key=lambda i: scores[i], reverse=True)
    return [records[i] for i in order[:k]]
