"""Append-only JSONL logger for RAG experiment records.

Two record streams live under rag-contest/experiments/:
  - index_manifest.jsonl : one line per index build
  - runs.jsonl           : one line per (config x question) run

The contract this module enforces (see todo/06_30_phase0_1.md, 단계 2):

  1. append-only, one line == one execution — a run that dies overnight leaves
     every already-written line intact.
  2. record success AND failure — status in {ok, failed, error} + error message.
     recall=0, broken extraction, low judge scores are NEVER deleted; they are
     the dashboard's most useful signal.
  3. self-describing — each line inlines its whole config, readable on its own.
  4. flat, dashboard-friendly field paths (config.*, retrieval.recall, ...).
  5. stable ids (run_id / build_id / question_id) to join source and derived data.

Atomicity: a record is written as a single `json.dumps(...) + "\n"` write to a
file opened with mode "a" (O_APPEND). On POSIX a single append-write of < 4096B
(PIPE_BUF) is atomic, so 2막's parallel writers can't interleave a line. We fail
loud if a record would exceed that budget rather than risk a torn line.
"""
from __future__ import annotations

import json
from pathlib import Path

# Absolute, repo-anchored so callers can run from rag-starter/ or anywhere.
EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "experiments"
RUNS_PATH = EXPERIMENTS_DIR / "runs.jsonl"
MANIFEST_PATH = EXPERIMENTS_DIR / "index_manifest.jsonl"

# POSIX PIPE_BUF: a single append-write below this stays atomic across writers.
_MAX_LINE_BYTES = 4096

# Which stream each id prefix counts against, so new_id() stays monotonic.
_STREAM_FOR_PREFIX = {"r": RUNS_PATH, "idx": MANIFEST_PATH}


def _append(path: Path, record: dict) -> None:
    """Append one record as a single atomic JSONL line.

    Raises before touching the file if the record is not a dict, is not
    JSON-serializable, or would exceed the atomic-write budget — so a bad
    record can never leave a torn or partial line behind.
    """
    if not isinstance(record, dict):
        raise TypeError(f"record must be a dict, got {type(record).__name__}")

    # json.dumps raises TypeError on non-serializable values (e.g. a set) —
    # that is our defined "malformed input" behavior: raise, write nothing.
    line = json.dumps(record, ensure_ascii=False) + "\n"
    encoded = line.encode("utf-8")
    if len(encoded) > _MAX_LINE_BYTES:
        raise ValueError(
            f"record serializes to {len(encoded)}B > {_MAX_LINE_BYTES}B; "
            "trim large fields (e.g. `text`) before logging to keep the "
            "append atomic under parallel writers"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def log_run(record: dict) -> None:
    """Append one (config x question) run to runs.jsonl."""
    _append(RUNS_PATH, record)


def log_index_build(record: dict) -> None:
    """Append one index build to index_manifest.jsonl."""
    _append(MANIFEST_PATH, record)


def new_id(prefix: str) -> str:
    """Return the next zero-padded id for a stream, e.g. 'r0007', 'idx0003'.

    Derived from the number of lines already in the matching file rather than an
    in-memory counter, so ids keep incrementing across process restarts. Note:
    this races under truly parallel writers (two readers can see the same count);
    for 2막 fan-out, hand ids down from the orchestrator instead.
    """
    path = _STREAM_FOR_PREFIX.get(prefix)
    if path is not None and path.exists():
        with path.open("r", encoding="utf-8") as f:
            n = sum(1 for line in f if line.strip())
    else:
        n = 0
    return f"{prefix}{n + 1:04d}"
