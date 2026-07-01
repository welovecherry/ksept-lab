"""Unit tests for the retrieval scorer (H2, 리뷰 R1·R5)."""
from __future__ import annotations

from harness.score import score_retrieval


def _hit(section=None, text=""):
    return {"section": section, "text": text}


def test_single_exact_match():
    s = score_retrieval([_hit("§91.151", "fuel...")], ["§91.151"], k=5)
    assert s == {"recall": 1.0, "coverage": 1.0, "mrr": 1.0}


def test_cross_question_half_coverage():
    # 2 expected, only one retrieved -> recall stays 1 but coverage is honest.
    hits = [_hit("§61.57"), _hit("§99.99"), _hit("§88.88")]
    s = score_retrieval(hits, ["§61.57", "§61.23"], k=5)
    assert s["recall"] == 1.0
    assert s["coverage"] == 0.5
    assert s["mrr"] == 1.0


def test_no_match():
    s = score_retrieval([_hit("§10.10"), _hit("§20.20")], ["§91.151"], k=5)
    assert s == {"recall": 0.0, "coverage": 0.0, "mrr": 0.0}


def test_mrr_reflects_rank():
    hits = [_hit("§1.1"), _hit("§2.2"), _hit("§91.151")]
    s = score_retrieval(hits, ["§91.151"], k=5)
    assert s["mrr"] == 1 / 3
    assert s["recall"] == 1.0


def test_r1_char_chunk_text_fallback():
    # No section meta (char chunk); the § number lives in the text.
    hits = [_hit(None, "... rules. § 91.151 Fuel requirements for flight in VFR ...")]
    s = score_retrieval(hits, ["§91.151"], k=5)
    assert s["recall"] == 1.0 and s["coverage"] == 1.0


def test_r1_text_fallback_avoids_longer_number():
    # '§91.1511' must NOT count as a match for expected '§91.151'.
    hits = [_hit(None, "see § 91.1511 for details")]
    s = score_retrieval(hits, ["§91.151"], k=5)
    assert s["recall"] == 0.0


def test_r5_empty_expected_guard():
    s = score_retrieval([_hit("§1.1")], [], k=5)
    assert s == {"recall": None, "coverage": None, "mrr": None}


def test_r5_dedupe_same_section():
    # Same § retrieved twice counts once toward coverage.
    hits = [_hit("§61.57"), _hit("§61.57")]
    s = score_retrieval(hits, ["§61.57", "§61.23"], k=5)
    assert s["coverage"] == 0.5


def test_normalizes_whitespace_in_meta():
    s = score_retrieval([_hit("§ 91.151")], ["§91.151"], k=5)
    assert s["recall"] == 1.0


def test_k_limits_considered_hits():
    # Match sits at rank 3 but k=2 -> not counted.
    hits = [_hit("§1.1"), _hit("§2.2"), _hit("§91.151")]
    s = score_retrieval(hits, ["§91.151"], k=2)
    assert s["recall"] == 0.0
