"""End-to-end smoke for the grid orchestrator (H3b, R8).

Uses a fake in-memory index and BM25-only retrieval so no embedding model loads.
Redirects the holdout + runs.jsonl to tmp files so real experiment logs stay clean.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rag-starter"))

from harness import orchestrate, recorder  # noqa: E402


FAKE_INDEX = [
    {"chunk_id": 0, "source": "part91.md", "chunk_index": 0, "part": "part91",
     "text": "§ 91.151 Fuel requirements for flight in VFR conditions", "section": "§91.151"},
    {"chunk_id": 1, "source": "part61.md", "chunk_index": 0, "part": "part61",
     "text": "§ 61.57 Recent flight experience pilot in command", "section": "§61.57"},
    {"chunk_id": 2, "source": "part67.md", "chunk_index": 0, "part": "part67",
     "text": "§ 67.1 Medical standards applicability", "section": "§67.1"},
]


@pytest.fixture
def wired(tmp_path, monkeypatch):
    holdout = tmp_path / "holdout.jsonl"
    holdout.write_text(
        json.dumps({"id": "T1", "question": "fuel reserve VFR",
                    "expected_sections": ["§91.151"], "expect_refusal": False}) + "\n"
        + json.dumps({"id": "T2", "question": "restaurant nearby",
                      "expected_sections": [], "expect_refusal": True}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(orchestrate, "HOLDOUT", holdout)
    monkeypatch.setattr(orchestrate, "build_index",
                        lambda chunker, embed_model: list(FAKE_INDEX))
    runs = tmp_path / "runs.jsonl"
    manifest = tmp_path / "index_manifest.jsonl"
    monkeypatch.setattr(recorder, "RUNS_PATH", runs)
    monkeypatch.setattr(recorder, "MANIFEST_PATH", manifest)
    monkeypatch.setitem(recorder._STREAM_FOR_PREFIX, "r", runs)
    monkeypatch.setitem(recorder._STREAM_FOR_PREFIX, "idx", manifest)
    return runs


def test_grid_end_to_end_bm25(wired):
    # 1 chunker x 1 embed x 1 method x 2 K x 1 non-refusal question = 2 runs.
    n = orchestrate.run_grid(["section"], ["minilm"], ["bm25"], [3, 5])
    assert n == 2
    lines = [json.loads(x) for x in wired.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert all(r["question_id"] == "T1" for r in lines)  # refusal T2 not scored
    assert lines[0]["retrieval"]["recall"] == 1.0
    assert lines[0]["retrieval"]["topk_sections"][0] == "§91.151"


def test_resume_skips_completed(wired):
    orchestrate.run_grid(["section"], ["minilm"], ["bm25"], [3])
    n2 = orchestrate.run_grid(["section"], ["minilm"], ["bm25"], [3])  # same config again
    assert n2 == 0
    assert len(wired.read_text(encoding="utf-8").splitlines()) == 1  # no duplicate line
