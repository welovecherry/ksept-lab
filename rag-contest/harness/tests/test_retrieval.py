"""Unit tests for H3a: prefix table, chunker axis, and BM25/hybrid retrieval.

Pure tests only — no model loading. Vector/hybrid embedding paths are covered by
a live smoke at build time, since they need a real embedding model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# rag-starter/ on path for the indexer helpers under test.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag-starter"))

from harness.retrieval import _minmax, retrieve  # noqa: E402
from indexer import _apply_prefix, _chunk  # noqa: E402


def test_prefix_bge_query_only():
    assert _apply_prefix(["fuel"], "bge", is_query=True)[0].startswith("Represent this sentence")
    assert _apply_prefix(["fuel"], "bge", is_query=False) == ["fuel"]  # doc side: none


def test_prefix_e5_both_sides():
    assert _apply_prefix(["q"], "e5", is_query=True) == ["query: q"]
    assert _apply_prefix(["d"], "e5", is_query=False) == ["passage: d"]


def test_prefix_none_for_minilm_and_gte():
    for model in ("minilm", "gte"):
        assert _apply_prefix(["x"], model, is_query=True) == ["x"]
        assert _apply_prefix(["x"], model, is_query=False) == ["x"]


def test_chunk_section_vs_char_differ():
    text = ("<!-- §1.1 | part1 -->\n§ 1.1 Definitions here\n"
            "<!-- §1.2 | part1 -->\n§ 1.2 Abbreviations here")
    section = _chunk(text, "section")
    char = _chunk(text, "char")
    assert len(section) == 2 and section[0]["section"] == "§1.1"
    assert all("section" not in c for c in char)  # char chunks carry no § meta


def test_chunk_unknown_raises():
    with pytest.raises(ValueError):
        _chunk("x", "nope")


def test_minmax_normalizes():
    assert _minmax([0.0, 5.0, 10.0]) == [0.0, 0.5, 1.0]


def test_minmax_flat_returns_zeros():
    assert _minmax([3.0, 3.0]) == [0.0, 0.0]


def test_bm25_ranks_by_word_overlap():
    recs = [{"text": "fuel reserve requirements for VFR", "section": "§91.151"},
            {"text": "medical certificate duration", "section": "§67.1"}]
    hits = retrieve("fuel reserve", recs, method="bm25", k=1)
    assert hits[0]["section"] == "§91.151"


def test_bm25_ties_do_not_crash():
    # No overlap -> all-zero scores -> must not try to compare record dicts.
    recs = [{"text": "alpha", "section": "§1.1"}, {"text": "beta", "section": "§2.2"}]
    assert len(retrieve("zzz", recs, method="bm25", k=2)) == 2


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        retrieve("q", [{"text": "a"}], method="nope")
