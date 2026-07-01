"""H1: gather evidence to verify holdout `expected_sections` against the FAA index.

For each non-refusal question:
  - expected §s present -> for each §, show whether it exists in the index
    (R6: distinguish "missing from index" = extraction gap, from "present but the
    keywords don't land" = likely wrong label), its snippet, and keyword overlap.
  - expected §s empty   -> run search() and suggest candidate sections to fill in.

Read-only: this tool GATHERS evidence; a human confirms the labels in holdout.jsonl.
Run: python harness/verify_holdout.py   (from rag-contest/)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
from indexer import load_index, search  # noqa: E402

HOLDOUT = ROOT / "holdout.jsonl"

# Question words that carry no topical signal — dropped before keyword overlap.
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "what", "how", "does", "do", "must", "be", "with", "under", "which", "that",
    "this", "you", "your", "it", "its", "as", "at", "by", "from", "not", "can",
    "between", "differ", "require", "required", "requirements", "act", "acting",
}


def keywords(question: str) -> list[str]:
    words = re.findall(r"[a-z]+", question.lower())
    return [w for w in words if len(w) > 2 and w not in _STOP]


def _oneline(text: str, n: int) -> str:
    return re.sub(r"\s+", " ", text[:n]).strip()


def chunks_for_section(records: list[dict], section: str) -> list[dict]:
    return [r for r in records if r.get("section") == section]


def main() -> None:
    rows = [json.loads(l) for l in HOLDOUT.open() if l.strip()]
    records = load_index()
    print(f"Loaded {len(records)} chunks; verifying {len(rows)} holdout rows\n")

    for r in rows:
        rid, q = r["id"], r["question"]
        if r.get("expect_refusal"):
            print(f"═══ {rid} [refusal] ═══  거부가 정답 — § 검증 스킵\n")
            continue

        expected = r.get("expected_sections") or []
        kws = keywords(q)
        print(f"═══ {rid} [{r.get('type')}]  part={r.get('part')} ═══")
        print(f"  Q: {q}")
        print(f"  keywords: {kws}")

        if expected:
            for sec in expected:
                found = chunks_for_section(records, sec)
                if not found:
                    print(f"  🔴 {sec}: 인덱스에 없음 → [R6] 추출 누락 의심(파이프라인 확인)")
                    continue
                text = found[0]["text"]
                hit = [k for k in kws if k in text.lower()]
                dupe = f" (+{len(found) - 1} more chunks)" if len(found) > 1 else ""
                print(f"  ✅ {sec}: 인덱스 있음{dupe} · 키워드 {len(hit)}/{len(kws)} 적중: {hit}")
                print(f"     ↳ {_oneline(text, 220)}")
        else:
            print("  ⬜ 정답 비어있음 → search() 후보 top-5:")
            for h in search(q, records, k=5):
                print(f"     {h.get('section')} ({h.get('part')}) :: {_oneline(h['text'], 90)}")
        print()


if __name__ == "__main__":
    main()
