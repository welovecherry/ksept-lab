"""Grid orchestrator (H3b): sweep the free retrieval axes over the holdout and
append one runs.jsonl line per (config x question). Resumable by config content.

Loop shape ([수정2]) — rebuild the index only on the slow outer axes:

    for chunker:                      # outer: expensive (re-embed the corpus)
      for embed_model:
        index = build_index(...)      #   built once per (chunker, embed_model)
        bm25  = build_bm25(index)     #   built once, reused across questions
        for method:                   # inner: cheap (same index, query only)
          for k:
            for question in holdout:
              score -> log_run(...)

Only free axes (실험 0~4): no Claude calls. Generation (실험 5~6) is H5/main session.
Run:  python harness/orchestrate.py        (default overnight grid)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
from indexer import build_index  # noqa: E402

from harness import recorder  # noqa: E402
from harness.retrieval import build_bm25, retrieve  # noqa: E402
from harness.score import score_retrieval  # noqa: E402

HOLDOUT = ROOT / "holdout.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_holdout() -> list[dict]:
    """Non-refusal questions — retrieval is scored only where an answer exists."""
    rows = [json.loads(line) for line in HOLDOUT.open(encoding="utf-8") if line.strip()]
    return [r for r in rows if not r.get("expect_refusal")]


def _config_key(chunker: str, embed_model: str, method: str, k: int, qid: str) -> tuple:
    return (chunker, embed_model, method, k, qid)


def _seen_keys() -> set[tuple]:
    """Config keys already in runs.jsonl (R4: resume on CONTENT, not build_id)."""
    seen: set[tuple] = set()
    path = recorder.RUNS_PATH
    if not path.exists():
        return seen
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        c = r.get("config", {})
        seen.add(_config_key(c.get("chunking"), c.get("embed_model"),
                             c.get("retrieval"), c.get("topk"), r.get("question_id")))
    return seen


def run_grid(chunkers: list[str], embed_models: list[str], methods: list[str],
             ks: list[int], alpha: float = 0.5) -> int:
    """Run the grid, skipping (config x question) combos already logged. Returns
    the number of new run lines appended."""
    questions = _load_holdout()
    seen = _seen_keys()
    needs_bm25 = any(m in ("bm25", "hybrid") for m in methods)
    appended = 0

    for chunker in chunkers:
        for embed_model in embed_models:
            todo = [(m, k, q) for m in methods for k in ks for q in questions
                    if _config_key(chunker, embed_model, m, k, q["id"]) not in seen]
            if not todo:
                print(f"  skip {chunker}/{embed_model}: all {len(methods)*len(ks)*len(questions)} done")
                continue

            build_id = recorder.new_id("idx")
            print(f"▶ build {chunker}/{embed_model} (build_id={build_id}) ...", flush=True)
            records = build_index(chunker, embed_model)
            recorder.log_index_build({
                "kind": "index_build", "build_id": build_id, "ts": _now(),
                "config": {"chunking": chunker, "embed_model": embed_model, "corpus": "faa"},
                "result": {"status": "ok", "n_chunks": len(records),
                           "n_sections": sum(1 for r in records if r.get("section"))},
                "status": "ok", "error": None,
            })
            bm25 = build_bm25(records) if needs_bm25 else None

            for method, k, q in todo:
                hits = retrieve(q["question"], records, method=method, k=k,
                                alpha=alpha, embed_model=embed_model, bm25=bm25)
                sc = score_retrieval(hits, q["expected_sections"], k=k)
                recorder.log_run({
                    "kind": "run", "run_id": recorder.new_id("r"), "ts": _now(),
                    "build_id": build_id,
                    "config": {"chunking": chunker, "embed_model": embed_model,
                               "retrieval": method, "topk": k, "alpha": alpha},
                    "question_id": q["id"], "stage": "retrieval",
                    "retrieval": {"topk_sections": [h.get("section") for h in hits], **sc},
                    "status": "ok", "error": None,
                })
                seen.add(_config_key(chunker, embed_model, method, k, q["id"]))
                appended += 1
            print(f"  done {chunker}/{embed_model}: +{len(todo)} runs", flush=True)

    print(f"✓ grid complete: {appended} new runs → {recorder.RUNS_PATH.name}")
    return appended


# Overnight grid: section FIRST (most promising, lands early even if we run out of
# time), then char (slower, 2.5x chunks). "route" is omitted — for an all-§-tagged
# corpus it is identical to "section". 2 x 4 x 3 x 3 x 11 questions = 792 runs.
OVERNIGHT_GRID = dict(
    chunkers=["section", "char"],
    embed_models=["minilm", "bge", "e5", "gte"],
    methods=["vector", "bm25", "hybrid"],
    ks=[3, 5, 8],
)


def main() -> None:
    run_grid(**OVERNIGHT_GRID)


if __name__ == "__main__":
    main()
