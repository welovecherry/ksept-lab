"""Generation prompt playground (실험 6 seed).

Run ONE question through several prompt tones and print each answer with token
cost. Retrieval uses hybrid by default (the config that reliably fetches the
right §), so output quality isn't gated by weak retrieval. Read-only on app.py —
does NOT modify SYSTEM_PROMPT; a good place to iterate before committing a prompt.

    python harness/try_prompt.py "What are the day VFR fuel reserves?"
    python harness/try_prompt.py "..." --method vector --k 8 --only B_balanced

Costs real API calls (one per variant). sonnet pricing ~$3/M in, ~$15/M out.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
sys.path.insert(0, str(ROOT / "rag-starter" / "backend"))
import app  # noqa: E402  — SYSTEM_PROMPT, client, INDEX
from harness.retrieval import format_context, retrieve  # noqa: E402

IN_PRICE, OUT_PRICE = 3 / 1e6, 15 / 1e6  # sonnet, USD per token

# Each variant is an ADDITION appended to app.GROUNDING_RULES. "" = grounding-only
# baseline; B_balanced is the deployed winner, imported from app (not re-pasted, [C2]).
VARIANTS = {
    "A_current": "",
    "B_balanced": app.BALANCED_STYLE,
    "C_warm": (
        "\n\nHow to write: like a friendly flight instructor — warm, plain language, "
        "thorough. Direct one-line answer first, then the specifics, then a brief "
        "practical takeaway that STAYS WITHIN the sources. Cover every relevant case. "
        "Cite [n]; use ONLY the provided sources — no outside aviation knowledge."
    ),
}

DEFAULT_Q = "What are the fuel-reserve requirements for VFR flight, day versus night?"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default=DEFAULT_Q)
    ap.add_argument("--method", default=app.CHAMPION_METHOD, help="vector | bm25 | hybrid")
    ap.add_argument("--k", type=int, default=app.CHAMPION_K)
    ap.add_argument("--only", default=None, help="run a single variant by name")
    args = ap.parse_args()

    # Query with the index's own model (A1) — never a hardcoded minilm against bge.
    hits = retrieve(args.question, app.INDEX, method=args.method, k=args.k, embed_model=app.EMBED)
    user_content = f"CONTEXT:\n{format_context(hits)}\n\nQUESTION:\n{args.question}"

    print(f"Q: {args.question}")
    print(f"retrieval: {args.method} K={args.k} → {[h.get('section') for h in hits]}\n")

    variants = {args.only: VARIANTS[args.only]} if args.only else VARIANTS
    for name, extra in variants.items():
        resp = app.client.messages.create(
            model="claude-sonnet-4-6", max_tokens=800,
            system=app.GROUNDING_RULES + extra,
            messages=[{"role": "user", "content": user_content}])
        tin, tout = resp.usage.input_tokens, resp.usage.output_tokens
        cost = tin * IN_PRICE + tout * OUT_PRICE
        print(f"═══════ {name} · in {tin} / out {tout} · ~${cost:.4f} ═══════")
        print(resp.content[0].text, "\n")


if __name__ == "__main__":
    main()
