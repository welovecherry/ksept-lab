"""Context Management RAG starter — extended chat backend.

This is the Foundations chat backend with stubs for retrieval-augmented generation.

TODO:
  1. Update SYSTEM_PROMPT with citation rules.
  2. In /api/chat: retrieve top-K chunks for the user's question.
  3. Format chunks as a numbered context block.
  4. Build the user_content with CONTEXT + QUESTION.
  5. Parse citation numbers from the answer; return them to the frontend.
"""
import re
import sys
from pathlib import Path

# rag-starter/ (for indexer) and rag-contest/ (for the harness package) on path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from indexer import (
    CHAMPION_K,
    CHAMPION_METHOD,
    embed,
    load_index,
    load_index_embed_model,
)

from harness.retrieval import build_bm25, format_context, retrieve, select_context

load_dotenv()  # ANTHROPIC_API_KEY from .env

app = Flask(__name__)
CORS(app)
client = Anthropic()

# Load the index once at startup. Fails fast if no index — run `python indexer.py` first.
INDEX = load_index()
# Query with the SAME model the index was built with (A1 single source of truth).
EMBED = load_index_embed_model()
# BM25 is only needed by bm25/hybrid retrieval; build it ONCE, not per request
# ([R3]), and skip the work entirely for pure-vector champions.
BM25 = build_bm25(INDEX) if CHAMPION_METHOD in ("bm25", "hybrid") else None
print(f"Loaded {len(INDEX)} chunks (embed={EMBED}, method={CHAMPION_METHOD}, k={CHAMPION_K})")

# Fail loud if the query model's dimension doesn't match the stored vectors — a
# mismatched-dim query returns silently wrong neighbors (zip truncates), which is
# exactly the "no error, meaningless results" trap A1 warns about.
_probe_dim = len(embed(["dimension probe"], EMBED, is_query=True)[0])
if _probe_dim != len(INDEX[0]["embedding"]):
    raise SystemExit(
        f"embed model {EMBED!r} is {_probe_dim}-dim but index is "
        f"{len(INDEX[0]['embedding'])}-dim — re-run `python indexer.py`."
    )


# ════════════════════════════════════════════════════════════════
# TODO — update SYSTEM_PROMPT with citation rules.
# Suggestions:
#   - Answer ONLY from the provided context.
#   - Cite each factual claim with [n] using the numbers in the context.
#   - If the context doesn't contain the answer, say so explicitly.
# ════════════════════════════════════════════════════════════════

GROUNDING_RULES = """You are a helpful assistant that answers questions using ONLY the \
sources provided in the CONTEXT block of each message.

Rules:
- Base every statement strictly on the provided context. Do not use outside knowledge, \
and do not guess or infer beyond what the sources state.
- Cite each factual claim with a bracketed source number, e.g. [1] or [2][3], using the \
numbers shown in the context. Place the citation immediately after the claim it supports.
- Only use citation numbers that appear in the context. Never invent a number.
- If the context does not contain enough information to answer, say so explicitly \
(e.g. "The provided sources don't contain an answer to that.") and do not fabricate one.
- If only part of the question is supported, answer that part and clearly state what the \
sources do not cover.
- When you first use an acronym or abbreviation, spell it out once — e.g., \
"VFR (Visual Flight Rules)"."""

# Answer style — won the prompt leaderboard (harness/prompt_leaderboard.py): B_balanced
# beat A_current (too terse) and C_warm (verbose → truncated at max_tokens). Single
# source of truth; harness/try_prompt.py imports this instead of re-pasting it ([C2]).
BALANCED_STYLE = (
    "\n\nHow to write: clear and helpful like a good instructor, but CONCISE. "
    "Lead with a one-line direct answer, then only the specifics the sources "
    "support. Cover all relevant cases (e.g. day/night, airplane/rotorcraft) "
    "without padding. Cite every claim [n]; use ONLY the sources."
)

SYSTEM_PROMPT = GROUNDING_RULES + BALANCED_STYLE


@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]

    # Retrieve the top-K most relevant chunks with the champion config, then
    # augment the prompt with a numbered context block so the model can ground
    # its answer and cite sources.
    hits = retrieve(user_message, INDEX, method=CHAMPION_METHOD, k=CHAMPION_K,
                    embed_model=EMBED, bm25=BM25)
    # Rerank sub-chunks by query similarity and keep within the token budget, so a
    # huge §-section (e.g. §61.109) contributes only its relevant windows, not all
    # ~20k chars. Citations still resolve — windows carry their parent § metadata.
    hits = select_context(user_message, hits, EMBED)
    user_content = f"CONTEXT:\n{format_context(hits)}\n\nQUESTION:\n{user_message}"

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    answer = resp.content[0].text

    # ────────────────────────────────────────────────────────────
    # TODO — citation extraction
    #
    # Parse [n] markers from the answer. Drop invented ones.
    # For each valid citation, return its source filename and chunk index
    # so the frontend can display them.
    # ────────────────────────────────────────────────────────────

    citations = _build_citations(answer, hits)

    return jsonify({"reply": answer, "citations": citations})


def _build_citations(answer: str, hits: list[dict]) -> list[dict]:
    """Return one citation entry per unique valid [n] used in the answer.

    Starter implementation: extract the numbers, drop out-of-range, return
    the matching hit's filename + chunk_index. Improve as you like.
    """
    used = [int(n) for n in re.findall(r"\[(\d+)\]", answer)]
    seen: set[int] = set()
    citations: list[dict] = []
    for n in used:
        if n in seen or n < 1 or n > len(hits):
            continue
        seen.add(n)
        h = hits[n - 1]
        citations.append({
            "n": n,
            "source": h["source"],
            "chunk_index": h["chunk_index"],
            "section": h.get("section"),
            "part": h.get("part"),
            "label": _citation_label(h),
        })
    return citations


def _citation_label(hit: dict) -> str:
    """'§91.151 (Part 91)' for FAA chunks; fall back to the filename otherwise."""
    section, part = hit.get("section"), hit.get("part")
    if section and part:
        return f"{section} (Part {part.removeprefix('part')})"
    return hit["source"]


if __name__ == "__main__":
    app.run(port=5000, debug=True)
