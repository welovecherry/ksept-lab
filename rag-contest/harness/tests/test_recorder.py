"""Unit tests for the append-only JSONL recorder.

Covers the 단계 2 acceptance gate (todo/06_30_phase0_1.md, 리뷰 T3):
  1. write -> read roundtrip is identical
  2. a status:"failed" record still appends and parses
  3. malformed input has defined behavior (raises, writes nothing)

Each test redirects RUNS_PATH/MANIFEST_PATH to a tmp file so the real
experiments/ logs stay clean.
"""
from __future__ import annotations

import json

import pytest

from harness import recorder


@pytest.fixture
def runs_path(tmp_path, monkeypatch):
    p = tmp_path / "runs.jsonl"
    monkeypatch.setattr(recorder, "RUNS_PATH", p)
    return p


def _lines(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_roundtrip_identical(runs_path):
    rec = {
        "kind": "run",
        "run_id": "r_test",
        "config": {"embed_model": "bge-large-en-v1.5", "alpha": 0.5},
        "retrieval": {"topk_sections": ["§91.151"], "recall": 1.0},
        "status": "ok",
        "error": None,
    }
    recorder.log_run(rec)
    parsed = _lines(runs_path)
    assert len(parsed) == 1
    assert parsed[0] == rec  # deep equality: every field survives the roundtrip


def test_appends_do_not_overwrite(runs_path):
    recorder.log_run({"kind": "run", "run_id": "r1", "status": "ok"})
    recorder.log_run({"kind": "run", "run_id": "r2", "status": "ok"})
    parsed = _lines(runs_path)
    assert [r["run_id"] for r in parsed] == ["r1", "r2"]


def test_failed_record_roundtrips(runs_path):
    failed = {
        "kind": "run",
        "run_id": "r_fail",
        "status": "failed",
        "error": "recall=0 — bge lost the medical-standards table",
        "retrieval": {"recall": 0.0},
    }
    recorder.log_run(failed)
    recorder.log_run({"kind": "run", "run_id": "r_ok", "status": "ok"})
    parsed = _lines(runs_path)
    assert len(parsed) == 2
    assert parsed[0]["status"] == "failed"
    assert parsed[0]["error"].startswith("recall=0")


def test_non_dict_raises_and_writes_nothing(runs_path):
    with pytest.raises(TypeError):
        recorder.log_run(["not", "a", "dict"])
    assert not runs_path.exists()


def test_non_serializable_raises_and_writes_nothing(runs_path):
    with pytest.raises(TypeError):
        recorder.log_run({"kind": "run", "bad": {1, 2, 3}})  # a set is not JSON
    assert not runs_path.exists()


def test_oversized_record_rejected(runs_path):
    with pytest.raises(ValueError):
        recorder.log_run({"kind": "run", "text": "x" * 5000})
    assert not runs_path.exists()


def test_unicode_preserved(runs_path):
    recorder.log_run({"kind": "run", "note": "조항 §91.151 인용", "status": "ok"})
    parsed = _lines(runs_path)
    assert parsed[0]["note"] == "조항 §91.151 인용"
    # ensure_ascii=False keeps the raw bytes readable, not \uXXXX escaped.
    assert "§91.151" in runs_path.read_text(encoding="utf-8")


def test_new_id_increments_with_file(tmp_path, monkeypatch):
    p = tmp_path / "runs.jsonl"
    monkeypatch.setattr(recorder, "RUNS_PATH", p)
    monkeypatch.setitem(recorder._STREAM_FOR_PREFIX, "r", p)
    assert recorder.new_id("r") == "r0001"
    recorder.log_run({"kind": "run", "run_id": recorder.new_id("r"), "status": "ok"})
    assert recorder.new_id("r") == "r0002"
