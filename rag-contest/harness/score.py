"""Retrieval scoring for the experiment harness (H2).

    score_retrieval(hits, expected, k) -> {recall, coverage, mrr}

A retrieved chunk "matches" an expected § when (R1 — chunking-independent):
  - its `section` meta equals the expected §, OR
  - (no section meta, i.e. a char chunk) the expected § number appears in its text.
So section-chunked and char-chunked configs are scored on the same ruler; without
this, char chunks (section=None) would silently score 0 and slander a good config.

Metrics (R4):
  - recall   : 1 if ANY expected § is in top-k (coarse, kept for reference)
  - coverage : |expected §s found| / |expected| (honest for multi-answer questions)
  - mrr      : 1 / rank of the first matching hit (rewards putting answers early)
"""
from __future__ import annotations

import re


def _norm(section: str) -> str:
    """'§ 91.151' -> '§91.151' (whitespace-insensitive)."""
    return re.sub(r"\s+", "", section)


def _text_has_section(text: str, number: str) -> bool:
    # `number` like '91.151' — require the § glyph so bare numbers / cross-refs
    # like '191.151' or '91.1511' don't count.
    return re.search(rf"§\s*{re.escape(number)}(?!\d)", text) is not None


def _matches(hit: dict, expected_norm: set[str]) -> set[str]:
    """The expected §s this hit satisfies (R1)."""
    section = hit.get("section")
    if section:
        return {_norm(section)} & expected_norm
    text = hit.get("text", "")
    return {e for e in expected_norm if _text_has_section(text, e.lstrip("§"))}


def score_retrieval(hits: list[dict], expected: list[str], k: int = 5) -> dict:
    """Score top-k retrieval against the expected §s.

    Returns None metrics when `expected` is empty (e.g. refusal questions),
    which also guards the coverage division by zero (R5).
    """
    expected_norm = {_norm(e) for e in expected}
    if not expected_norm:
        return {"recall": None, "coverage": None, "mrr": None}

    found: set[str] = set()            # R5: a set dedupes repeated §s
    first_rank = 0
    for rank, hit in enumerate(hits[:k], start=1):
        matched = _matches(hit, expected_norm)
        if matched and first_rank == 0:
            first_rank = rank
        found |= matched

    return {
        "recall": 1.0 if found else 0.0,
        "coverage": len(found) / len(expected_norm),
        "mrr": (1.0 / first_rank) if first_rank else 0.0,
    }
