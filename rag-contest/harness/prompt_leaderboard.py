"""Prompt leaderboard: rank prompt variants from generation + judge (3막 §8.7).

Joins two free streams over experiments/:
  - prompt_runs.jsonl  : answers + tokens + program citation check (gen_answers.py)
  - judge_scores.jsonl : rubric 1-5 per run from the LLM judge (this session, opus)

and ranks each prompt by mean judge score, then cited-§ coverage, then tokens.
The judge stream is optional: without it the program metrics still rank, so you
can eyeball the table before judging. Writes prompt_leaderboard.md.

    python harness/prompt_leaderboard.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness.recorder import EXPERIMENTS_DIR  # noqa: E402

PROMPT_RUNS_PATH = EXPERIMENTS_DIR / "prompt_runs.jsonl"
JUDGE_SCORES_PATH = EXPERIMENTS_DIR / "judge_scores.jsonl"
LEADERBOARD_PATH = EXPERIMENTS_DIR / "prompt_leaderboard.md"

# Rubric axes the judge scores 1-5; "overall" is their mean.
RUBRIC = ("helpful", "complete", "grounded")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _mean(values: list[float]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def aggregate(runs: list[dict], judge_by_id: dict[str, dict]) -> list[dict]:
    """One row per prompt: mean judge axes, citation validity, coverage, tokens."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        groups[r["prompt"]].append(r)

    rows = []
    for prompt, rs in groups.items():
        judged = [judge_by_id[r["run_id"]] for r in rs if r["run_id"] in judge_by_id]
        axis_means = {ax: _mean([j["scores"].get(ax) for j in judged]) for ax in RUBRIC}
        overall = _mean([v for v in axis_means.values() if v is not None]) if judged else None
        rows.append({
            "prompt": prompt,
            "n": len(rs),
            **axis_means,
            "overall": overall,
            # program checks (free): fraction of answers with only valid [n],
            # and mean coverage of expected §s by the CITED chunks.
            "cite_valid": _mean([1.0 if not r["program_check"]["invalid_citations"]
                                 else 0.0 for r in rs]),
            "coverage": _mean([r["program_check"]["cited_coverage"] for r in rs]),
            "tok_in": _mean([r["tokens"]["in"] for r in rs]),
            "tok_out": _mean([r["tokens"]["out"] for r in rs]),
        })
    return rows


def rank(rows: list[dict]) -> list[dict]:
    """Best first: judge overall↓, then citation coverage↓, then input tokens↑."""
    def key(r: dict) -> tuple:
        return (-(r["overall"] or -1.0), -(r["coverage"] or -1.0), r["tok_in"] or 1e9)
    return sorted(rows, key=key)


def _fmt(v: float | None, nd: int = 2) -> str:
    return f"{v:.{nd}f}" if v is not None else "  -  "


def format_table(ranked: list[dict]) -> str:
    header = (f"{'#':>2}  {'prompt':<11} {'overall':>7} "
             + " ".join(f"{ax:>8}" for ax in RUBRIC)
             + f"  {'cite_ok':>7} {'cov':>5} {'tok_in':>7} {'tok_out':>7}  {'n':>2}")
    lines = [header, "-" * len(header)]
    for i, r in enumerate(ranked, start=1):
        lines.append(
            f"{i:>2}  {r['prompt']:<11} {_fmt(r['overall']):>7} "
            + " ".join(f"{_fmt(r[ax]):>8}" for ax in RUBRIC)
            + f"  {_fmt(r['cite_valid']):>7} {_fmt(r['coverage']):>5} "
            f"{_fmt(r['tok_in'], 0):>7} {_fmt(r['tok_out'], 0):>7}  {r['n']:>2}"
        )
    return "\n".join(lines)


def to_markdown(ranked: list[dict], judged: bool) -> str:
    champ = ranked[0]["prompt"] if ranked else "—"
    note = (f"Winner: **{champ}** — deployed in `rag-starter/backend/app.py` as "
            "`SYSTEM_PROMPT = GROUNDING_RULES + BALANCED_STYLE`." if judged
            else "⚠️ No judge scores yet — ranked by program metrics only.")
    cols = ["#", "prompt", "overall", *RUBRIC, "cite_ok", "cov", "tok_in", "tok_out", "n"]
    out = ["# Prompt leaderboard — answer quality (auto-generated)", "", note, "",
           "| " + " | ".join(cols) + " |",
           "|" + "|".join(["---"] * len(cols)) + "|"]
    for i, r in enumerate(ranked, start=1):
        out.append("| " + " | ".join([
            str(i), r["prompt"], _fmt(r["overall"]),
            *[_fmt(r[ax]) for ax in RUBRIC],
            _fmt(r["cite_valid"]), _fmt(r["coverage"]),
            _fmt(r["tok_in"], 0), _fmt(r["tok_out"], 0), str(r["n"]),
        ]) + " |")
    return "\n".join(out) + "\n"


def main() -> None:
    runs = load_jsonl(PROMPT_RUNS_PATH)
    if not runs:
        raise SystemExit(f"No runs at {PROMPT_RUNS_PATH}. Run gen_answers.py first.")
    judge_by_id = {j["run_id"]: j for j in load_jsonl(JUDGE_SCORES_PATH)}
    if judge_by_id and len(judge_by_id) < len(runs):
        print(f"⚠️  {len(runs) - len(judge_by_id)}/{len(runs)} runs unjudged — "
              "averages cover only the scored ones.\n")
    ranked = rank(aggregate(runs, judge_by_id))

    print(format_table(ranked))
    LEADERBOARD_PATH.write_text(to_markdown(ranked, bool(judge_by_id)), encoding="utf-8")
    print(f"\n→ {LEADERBOARD_PATH.relative_to(EXPERIMENTS_DIR.parent)}"
          + ("" if judge_by_id else "  (program-only — add judge_scores.jsonl)"))


if __name__ == "__main__":
    main()
