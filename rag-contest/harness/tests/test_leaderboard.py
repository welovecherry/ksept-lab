"""Unit tests for leaderboard aggregation + ranking ([리뷰 T1]).

These exercise the pure core (aggregate / rank / finalist_note / missing_configs)
on hand-written runs — no corpus, no torch — so the grouping, mean, cost-proxy,
and tiebreak logic is pinned independently of the 495-row overnight data.
"""
from harness.leaderboard import (
    NEAR_TIE,
    aggregate,
    finalist_note,
    missing_configs,
    rank,
)


def _run(chunking, embed, retrieval, k, coverage, recall, mrr):
    return {
        "config": {"chunking": chunking, "embed_model": embed,
                   "retrieval": retrieval, "topk": k, "alpha": 0.5},
        "retrieval": {"coverage": coverage, "recall": recall, "mrr": mrr},
    }


def test_aggregate_groups_and_averages():
    runs = [
        _run("section", "bge", "vector", 5, 1.0, 1.0, 1.0),
        _run("section", "bge", "vector", 5, 0.0, 0.0, 0.0),  # same config → averaged
        _run("section", "bge", "hybrid", 5, 0.5, 1.0, 0.5),  # different config
    ]
    rows = {tuple(r[a] for a in ("chunking", "embed_model", "retrieval", "topk")): r
            for r in aggregate(runs)}
    assert len(rows) == 2
    vec = rows[("section", "bge", "vector", 5)]
    assert vec["coverage"] == 0.5 and vec["recall"] == 0.5 and vec["n"] == 2


def test_aggregate_skips_none_metrics():
    # A refusal question logs None; it must not drag the mean toward zero.
    runs = [
        _run("section", "bge", "vector", 5, 1.0, 1.0, 1.0),
        _run("section", "bge", "vector", 5, None, None, None),
    ]
    [row] = aggregate(runs)
    assert row["coverage"] == 1.0  # averaged over the one real value, not 0.5
    assert row["n"] == 2           # but both runs are still counted


def test_rank_orders_by_coverage_then_mrr_then_cost():
    rows = [
        {"chunking": "section", "embed_model": "bge", "retrieval": "hybrid",
         "topk": 8, "coverage": 0.9, "recall": 0.9, "mrr": 0.5, "n": 11},
        {"chunking": "section", "embed_model": "bge", "retrieval": "vector",
         "topk": 5, "coverage": 0.9, "recall": 0.9, "mrr": 0.7, "n": 11},
    ]
    ranked = rank(rows, {"section": 100.0})
    # Same coverage → higher MRR (vector/K5) wins the tiebreak.
    assert ranked[0]["retrieval"] == "vector"
    # Cost proxy = K × chunk chars.
    assert ranked[0]["cost"] == 500.0 and ranked[1]["cost"] == 800.0


def test_rank_cost_breaks_true_ties():
    rows = [
        {"chunking": "section", "embed_model": "bge", "retrieval": "vector",
         "topk": 8, "coverage": 0.8, "recall": 0.8, "mrr": 0.6, "n": 11},
        {"chunking": "section", "embed_model": "bge", "retrieval": "vector",
         "topk": 3, "coverage": 0.8, "recall": 0.8, "mrr": 0.6, "n": 11},
    ]
    ranked = rank(rows, {"section": 100.0})
    assert ranked[0]["topk"] == 3  # equal cov & mrr → cheaper (smaller K) first


def test_finalist_note_prefers_cheaper_on_near_tie():
    rows = [
        {"chunking": "section", "embed_model": "bge", "retrieval": "hybrid",
         "topk": 8, "coverage": 0.86, "recall": 0.9, "mrr": 0.5, "n": 11},
        {"chunking": "section", "embed_model": "bge", "retrieval": "vector",
         "topk": 5, "coverage": 0.86 - NEAR_TIE, "recall": 0.9, "mrr": 0.7, "n": 11},
    ]
    ranked = rank(rows, {"section": 100.0})
    note = finalist_note(ranked)
    # K5 is within the near-tie band and cheaper → it's the recommended pick.
    assert "Recommend" in note and "vector/K5" in note


def test_missing_configs_flags_absent_pairs():
    runs = [
        _run("section", "bge", "vector", 5, 1.0, 1.0, 1.0),
        _run("section", "minilm", "vector", 5, 1.0, 1.0, 1.0),
        _run("char", "minilm", "vector", 5, 1.0, 1.0, 1.0),
    ]
    rows = aggregate(runs)
    # cross-product {section,char} × {bge,minilm} minus seen → char×bge missing.
    assert missing_configs(rows) == [("char", "bge")]
