"""Leaderboard: rank grid configs from runs.jsonl (3막 · STRATEGY §8.7).

Reads experiments/runs.jsonl (retrieval-stage rows), groups by
(chunking, embed_model, retrieval, topk), averages coverage / recall / MRR, adds
a cost proxy (K × mean chunk chars — the input-token driver, EXPERIMENTS §5.1),
ranks, prints the table, and writes leaderboard.md. The top 2 rows are the
finalists handed to generation (수정3).

Honesty rule: configs absent from runs.jsonl (char × big model — killed overnight
for memory) simply do not appear here. main() prints them as "미측정 (not
measured)" so a gap never reads as a zero-score config we secretly dropped.

    python harness/leaderboard.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import product
from pathlib import Path

# harness/ is importable as a package; rag-starter/ holds indexer (chunkers).
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "rag-starter"))
from harness.recorder import EXPERIMENTS_DIR, RUNS_PATH  # noqa: E402

LEADERBOARD_PATH = EXPERIMENTS_DIR / "leaderboard.md"

# The config axes, in the order they identify a group. A "config" is one tuple
# of these values; a "run" is one (config × question).
AXES = ("chunking", "embed_model", "retrieval", "topk")

# coverage gap treated as "the same" — 1 question out of ~11 ≈ 0.09. Within this
# band we prefer the cheaper config (EXPERIMENTS §5.1: recall동률 → 토큰 적은 쪽).
NEAR_TIE = 0.09

# Metrics we average across a config's questions. None (refusal questions with no
# expected §) is skipped so it can't drag a mean toward zero.
_METRICS = ("coverage", "recall", "mrr")


def load_runs(path: Path = RUNS_PATH) -> list[dict]:
    """Read runs.jsonl into a list of records (one line == one run)."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _mean(values: list[float]) -> float | None:
    """Mean over non-None values; None if there is nothing to average."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def aggregate(runs: list[dict]) -> list[dict]:
    """Fold runs into one row per config with averaged metrics + question count.

    Pure: no corpus, no torch. Returns dicts keyed by the AXES plus
    coverage/recall/mrr (means) and n (questions counted).
    """
    metrics: dict[tuple, dict[str, list]] = defaultdict(
        lambda: {m: [] for m in _METRICS} | {"n": 0}
    )
    for r in runs:
        cfg = r["config"]
        key = tuple(cfg[a] for a in AXES)
        bucket = metrics[key]
        ret = r.get("retrieval", {})
        for m in _METRICS:
            bucket[m].append(ret.get(m))
        bucket["n"] += 1

    rows: list[dict] = []
    for key, bucket in metrics.items():
        row = dict(zip(AXES, key))
        for m in _METRICS:
            row[m] = _mean(bucket[m])
        row["n"] = bucket["n"]
        rows.append(row)
    return rows


def rank(rows: list[dict], chunk_chars: dict[str, float]) -> list[dict]:
    """Attach a cost proxy and sort best-first.

    cost = K × mean chunk chars for that chunking — a stand-in for input tokens,
    which dominate the bill (EXPERIMENTS §5.1). Sort by coverage↓, then MRR↓
    (answers ranked earlier), then cost↑ so a cheaper config wins a true tie.
    A missing chunk length falls back to K alone rather than crashing.
    """
    for row in rows:
        row["cost"] = row["topk"] * chunk_chars.get(row["chunking"], 1.0)

    def sort_key(row: dict) -> tuple:
        # None coverage/mrr (all-refusal config) sorts last via -1.0.
        cov = row["coverage"] if row["coverage"] is not None else -1.0
        mrr = row["mrr"] if row["mrr"] is not None else -1.0
        return (-cov, -mrr, row["cost"])

    return sorted(rows, key=sort_key)


def mean_chunk_chars(chunking: str, docs_dir: Path | None = None) -> float:
    """Average chunk length (chars) if the corpus were chunked this way.

    Lazily imports indexer (pulls torch) so tests that only exercise
    aggregate()/rank() stay light. Mirrors build_index: char chunking applies to
    every doc, section chunking only yields chunks from §-tagged FAA docs.
    """
    from indexer import DOCS_DIR, _chunk  # noqa: E402 — heavy import, kept local

    docs_dir = docs_dir or DOCS_DIR
    lengths: list[int] = []
    for path in sorted(docs_dir.glob("*")):
        if path.is_dir() or path.suffix.lower() not in (".md", ".txt"):
            continue
        for piece in _chunk(path.read_text(), chunking):
            lengths.append(len(piece["text"]))
    return sum(lengths) / len(lengths) if lengths else 0.0


def missing_configs(rows: list[dict]) -> list[tuple]:
    """(chunking, embed_model) pairs in the axis cross-product with zero runs.

    The overnight grid killed char × {bge,e5,gte}; those pairs never reach
    runs.jsonl. We report them so a gap reads as 미측정, not a silent drop.
    """
    seen_pairs = {(r["chunking"], r["embed_model"]) for r in rows}
    chunkings = sorted({r["chunking"] for r in rows})
    embeds = sorted({r["embed_model"] for r in rows})
    return [pair for pair in product(chunkings, embeds) if pair not in seen_pairs]


def _fmt(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "  -  "


def format_table(ranked: list[dict]) -> str:
    """Fixed-width leaderboard for the terminal; rank 1 = champion."""
    header = (
        f"{'#':>2}  {'chunking':<8} {'embed':<6} {'retrieval':<9} {'K':>2}  "
        f"{'cov':>5} {'recall':>6} {'mrr':>5}  {'cost':>8}  {'n':>2}"
    )
    lines = [header, "-" * len(header)]
    for i, r in enumerate(ranked, start=1):
        lines.append(
            f"{i:>2}  {r['chunking']:<8} {r['embed_model']:<6} {r['retrieval']:<9} "
            f"{r['topk']:>2}  {_fmt(r['coverage'])} {_fmt(r['recall'])} "
            f"{_fmt(r['mrr'])}  {r['cost']:>8.0f}  {r['n']:>2}"
        )
    return "\n".join(lines)


def _label(r: dict) -> str:
    return f"{r['chunking']}/{r['embed_model']}/{r['retrieval']}/K{r['topk']}"


def recommend(ranked: list[dict]) -> dict:
    """The config to actually carry forward.

    Not simply rank 1: among every config whose coverage is within NEAR_TIE of
    the top (statistically the same on ~11 questions), take the cheapest, then
    the higher MRR. This is EXPERIMENTS §5.1 as code — "recall 동률 → 토큰 적은
    쪽" — so a K8 that edges out a K5 by half a question doesn't win when the K5
    is far cheaper and ranks answers earlier.
    """
    champ = ranked[0]
    top_cov = champ["coverage"] or 0.0
    band = [r for r in ranked if top_cov - (r["coverage"] or 0.0) <= NEAR_TIE]
    return min(band, key=lambda r: (r["cost"], -(r["mrr"] or 0.0)))


def finalist_note(ranked: list[dict]) -> str:
    """Call the champion (top coverage) vs the cost-aware recommended pick."""
    if not ranked:
        return "No configs measured."
    champ = ranked[0]
    pick = recommend(ranked)
    if pick is champ:
        return f"Champion {_label(champ)} — also cheapest within the near-tie band."
    gap = (champ["coverage"] or 0) - (pick["coverage"] or 0)
    saved = (1 - pick["cost"] / champ["cost"]) * 100
    return (
        f"Recommend {_label(pick)} (cov {pick['coverage']:.3f}, mrr "
        f"{pick['mrr']:.3f}): only {gap:.3f} behind top-coverage {_label(champ)} "
        f"but ~{saved:.0f}% cheaper and ranks answers earlier (§5.1)."
    )


def to_markdown(ranked: list[dict], missing: list[tuple]) -> str:
    """leaderboard.md — the human-facing 3막 artifact (STRATEGY §8.7)."""
    out = ["# Leaderboard — retrieval configs (auto-generated)", "",
           finalist_note(ranked), "",
           "| # | chunking | embed | retrieval | K | cov | recall | mrr | cost | n |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(ranked, start=1):
        out.append(
            f"| {i} | {r['chunking']} | {r['embed_model']} | {r['retrieval']} | "
            f"{r['topk']} | {_fmt(r['coverage'])} | {_fmt(r['recall'])} | "
            f"{_fmt(r['mrr'])} | {r['cost']:.0f} | {r['n']} |"
        )
    if missing:
        out += ["", "## 미측정 (not measured)",
                "Killed overnight (memory); never scored, never faked:", ""]
        out += [f"- {c} × {e}" for c, e in missing]
    return "\n".join(out) + "\n"


def main() -> None:
    runs = load_runs()
    rows = aggregate(runs)
    chunkings = {r["chunking"] for r in rows}
    chunk_chars = {c: mean_chunk_chars(c) for c in chunkings}
    ranked = rank(rows, chunk_chars)
    missing = missing_configs(rows)

    print(format_table(ranked))
    print()
    print(finalist_note(ranked))
    if missing:
        print(f"\n미측정 (not measured): {', '.join(f'{c}×{e}' for c, e in missing)}")

    LEADERBOARD_PATH.write_text(to_markdown(ranked, missing), encoding="utf-8")
    print(f"\n→ {LEADERBOARD_PATH.relative_to(EXPERIMENTS_DIR.parent)}")


if __name__ == "__main__":
    main()
