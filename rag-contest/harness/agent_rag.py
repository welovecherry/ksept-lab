"""Minimal AGENTIC RAG experiment — one search tool + a bounded agent loop.

Contrast with the deployed single-shot app.py (retrieve→stuff→one generation):
here the MODEL drives retrieval. It calls search_cfr(query) as many times as it
needs (capped), so a question that spans parts — e.g. airspace *operating* rules
live in Part 91, not the Part 71 designation stubs — can be recovered by a second
search the single-shot path can't issue.

    python harness/agent_rag.py "make a table covering all airspace classes"

Reuses app.py's index/model/prompt and harness retrieval — no duplication. Costs
real API (one call per loop turn); prints each search + total tokens so you can
weigh the Cost(15)/Quality(30) tradeoff against the single-shot baseline.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
sys.path.insert(0, str(ROOT / "rag-starter" / "backend"))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402 — INDEX, EMBED, BM25, client, prompts, _build_citations
from harness.retrieval import retrieve, select_context  # noqa: E402

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 4      # loop safety bound
MAX_SEARCHES = 3   # HARD cap on total searches — the real cost lever. Each search
                   # accumulates in the resent history, so unbounded searches blow
                   # up quadratically (13 searches = 81k tokens). 3 keeps a broad
                   # question near ~15k worst case; specifics use just 1.

SEARCH_TOOL = {
    "name": "search_cfr",
    "description": (
        "Search the 14 CFR corpus for passages relevant to a query. Returns "
        "numbered passages [n] you must cite. Call it MULTIPLE times with "
        "different queries to gather every part of a multi-topic question — e.g. "
        "airspace operating requirements are in Part 91 (§91.131 Class B, §91.130 "
        "Class C), NOT the Part 71 designation sections. Search again with a "
        "refined query whenever the results don't fully cover the question."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "search query"}},
        "required": ["query"],
    },
}

SYSTEM_PROMPT = app.SYSTEM_PROMPT + (
    "\n\nYou have a search_cfr tool. Search BEFORE answering, and issue extra "
    "searches (different queries) until you have every part the question needs. "
    "Then answer from the search results only, citing [n]."
)


def _run_search(query: str, registry: list[dict]) -> str:
    """Retrieve + rerank for `query`; append windows to the shared citation
    registry and return them numbered with GLOBAL indices so [n] stays unique
    across every search in the conversation."""
    hits = retrieve(query, app.INDEX, method=app.CHAMPION_METHOD, k=app.CHAMPION_K,
                    embed_model=app.EMBED, bm25=app.BM25)
    hits = select_context(query, hits, app.EMBED)
    start = len(registry)
    registry.extend(hits)
    # Number with GLOBAL indices (start+1..) so [n] is unique across all searches.
    return "\n\n".join(f"[{start + i + 1}] {h['text']}" for i, h in enumerate(hits))


def answer(question: str) -> dict:
    messages = [{"role": "user", "content": question}]
    registry: list[dict] = []           # every window seen, for citation resolve
    tin = tout = 0
    searches = 0
    # Keep the tool present EVERY turn — withdrawing it mid-task makes the model
    # return an empty turn. Instead, once the budget is spent the tool itself
    # returns a "stop and answer" result, which the model follows normally.
    for _turn in range(MAX_TURNS + 2):
        resp = app.client.messages.create(
            model=MODEL, max_tokens=900, system=SYSTEM_PROMPT,
            tools=[SEARCH_TOOL], messages=messages)
        tin += resp.usage.input_tokens
        tout += resp.usage.output_tokens

        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"answer": text, "citations": app._build_citations(text, registry),
                    "searches": searches, "tokens": {"in": tin, "out": tout}}

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type != "tool_use" or b.name != "search_cfr":
                continue
            if searches < MAX_SEARCHES:
                q = b.input["query"]
                print(f"  🔎 search_cfr({q!r})")
                content = _run_search(q, registry)
                searches += 1
            else:
                print(f"  ⛔ budget reached, skip {b.input.get('query')!r}")
                content = ("Search budget reached. STOP searching. Write your final "
                           "answer NOW from the passages already returned, citing [n].")
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": content})
        messages.append({"role": "user", "content": results})

    return {"answer": "", "citations": [], "searches": searches,
            "tokens": {"in": tin, "out": tout}}


def main() -> None:
    q = sys.argv[1] if len(sys.argv) > 1 else "make a table covering all airspace classes"
    print(f"Q: {q}\n")
    r = answer(q)
    t = r["tokens"]
    print(f"\n{'=' * 80}\nTOKENS in={t['in']} out={t['out']} total={t['in'] + t['out']} "
          f"| searches={r['searches']}\n{'=' * 80}")
    print(r["answer"])
    print("\nCitations:", [c["label"] for c in r["citations"]])


if __name__ == "__main__":
    main()
