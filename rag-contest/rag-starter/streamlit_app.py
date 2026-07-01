"""Streamlit chat UI for the FAA RAG contest — chat + champion retrieval + meta/sources.

Serves the SAME champion retrieval as the Flask backend (harness.retrieval +
indexer CHAMPION_* constants + the self-describing index.meta.json), but calls
Anthropic directly so later stages can stream natively and we never edit app.py.

Run from rag-starter/:  streamlit run streamlit_app.py

[E1] SYSTEM_PROMPT is copied here TEMPORARILY. Importing app.py would fire its
module-level side effects (load_index, Anthropic(), Flask). Once the output
session extracts the prompt to backend/prompts.py, replace the constant below
with:  from prompts import SYSTEM_PROMPT
"""
import re
from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from indexer import (
    CHAMPION_K,
    CHAMPION_METHOD,
    embed,
    load_index,
    load_index_embed_model,
)
from harness.retrieval import build_bm25, format_context, retrieve

load_dotenv(Path(__file__).parent / ".env")  # ANTHROPIC_API_KEY (shared class key)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
AVATARS = {"user": "🧑", "assistant": "🛩️"}

# (input, output) USD per million tokens, keyed by model so the cost badge stays
# correct if the champion model changes. Unknown model → $0 (badge shows ~$0).
PRICES = {"claude-sonnet-4-6": (3.0, 15.0)}

# Empty-state example questions (from CONTEST.md practice set) — one click to ask.
EXAMPLES = [
    "What are the fuel-reserve requirements for VFR flight, day versus night?",
    "What aeronautical experience is required for a private pilot certificate (airplane single-engine)?",
    "How do operating requirements differ between Class B and Class C airspace?",
]

# [E1 TEMP] verbatim copy of backend/app.py SYSTEM_PROMPT. Swap for an import once
# backend/prompts.py exists so the output session's prompt edits flow in for free.
SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
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


@st.cache_resource
def get_index():
    """Load the champion index once per process, mirroring app.py.

    Returns (index, embed_model, bm25). embed_model comes from the index's own
    index.meta.json (A1 single source of truth) so queries use the SAME model the
    vectors were built with. A dimension probe fails loud on mismatch — the
    "no error, meaningless results" trap A1 guards against. BM25 is built once and
    only when the champion method needs it (pure-vector champions skip it).
    """
    index = load_index()
    embed_model = load_index_embed_model()
    probe_dim = len(embed(["dimension probe"], embed_model, is_query=True)[0])
    if probe_dim != len(index[0]["embedding"]):
        raise RuntimeError(
            f"embed model {embed_model!r} is {probe_dim}-dim but index is "
            f"{len(index[0]['embedding'])}-dim — rebuild the index or fix the model."
        )
    bm25 = build_bm25(index) if CHAMPION_METHOD in ("bm25", "hybrid") else None
    return index, embed_model, bm25


@st.cache_resource
def get_client():
    return Anthropic()


def _cost_usd(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return tin / 1e6 * pin + tout / 1e6 * pout


def _citation_label(hit: dict) -> str:
    """'§91.151 (Part 91)' for FAA chunks; fall back to the source filename."""
    section, part = hit.get("section"), hit.get("part")
    if section and part:
        return f"{section} (Part {part.removeprefix('part')})"
    return hit.get("source", "source")


def _cited(answer_text: str, hits: list[dict]) -> list[dict]:
    """Parse the [n] markers the answer actually used, mapped to their hit.

    Deduped, in first-use order, out-of-range dropped — same rule as app.py's
    _build_citations, inlined to avoid importing app.py (its module-level side
    effects). Each entry carries the label + chunk text for the source card.
    """
    seen, out = set(), []
    for n in (int(m) for m in re.findall(r"\[(\d+)\]", answer_text)):
        if n in seen or not (1 <= n <= len(hits)):
            continue
        seen.add(n)
        h = hits[n - 1]
        out.append({"n": n, "label": _citation_label(h), "section": h.get("section"),
                    "text": h.get("text", "")})
    return out


def _looks_like_refusal(text: str) -> bool:
    """True if the answer explicitly declined for lack of grounding (per SYSTEM_PROMPT).

    Lets us show the out-of-scope card only on real refusals, not on any answer
    that merely happens to omit [n] markers.
    """
    low = text.lower()
    return "don't contain" in low or "do not contain" in low or "provided sources" in low


_SECTION_RE = re.compile(r"§\s?\d+\.\d+(?:\([a-z0-9]+\))*")


def _colorize(text: str) -> str:
    """Tint § regulation references with Streamlit's SAFE :orange markdown colorizer.

    Never unsafe_allow_html: the answer is model output, so injecting raw HTML into it
    would be a prompt-injection hole (Robustness). :orange is sanitized by Streamlit
    and reads as a warm terracotta-ish tone against the cream theme.
    """
    return _SECTION_RE.sub(lambda m: f":orange[{m.group(0)}]", text)


def _format_answer(text: str, citations: list[dict]) -> str:
    """Expand bare [n] markers to [n §xxx] (so the cited clause is visible inline
    without scrolling to the cards), then tint the § references. Markers whose hit
    has no section (non-FAA chunk) stay bare. Both passes are safe markdown, no HTML.
    """
    section = {c["n"]: c["section"] for c in citations if c.get("section")}
    text = re.sub(r"\[(\d+)\]",
                  lambda m: f"[{m.group(1)}] {section[int(m.group(1))]}"
                  if int(m.group(1)) in section else m.group(0),
                  text)
    return _colorize(text)


def stream_answer(question, hits, placeholder):
    """Stream the answer into `placeholder` token-by-token; return (text, meta).

    Raw tokens render live with a cursor for perceived speed; the caller swaps in
    the formatted answer (§ tint + [n] labels) once the text is complete. Usage/cost
    come from the final message — the "meta arrives at the end" contract (①) that
    stages 1-2 were built around, which is why streaming drops in without reshaping
    the message. `format_context` is the shared numbering helper app.py uses too.
    """
    user_content = f"CONTEXT:\n{format_context(hits)}\n\nQUESTION:\n{question}"
    full = ""
    with get_client().messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for chunk in stream.text_stream:
            full += chunk
            placeholder.markdown(full + " ▌")
        final = stream.get_final_message()
    meta = {
        "model": final.model,
        "tokens_in": final.usage.input_tokens,
        "tokens_out": final.usage.output_tokens,
        "cost_usd": _cost_usd(final.model, final.usage.input_tokens, final.usage.output_tokens),
        "method": CHAMPION_METHOD,
        "k": CHAMPION_K,
    }
    return full, meta


def render_footer(meta: dict | None, citations: list[dict], text: str) -> None:
    """Draw the quiet cost/model/retrieval chips + source cards under an answer.

    Shared by the live turn and the replay loop so history renders identically.
    No grounding badge (E2). § references are tinted by _colorize at render time.
    """
    if meta:
        # Uniform teal-soft pills. Headline = total tokens + cost; the in/out split
        # is on hover (title tooltip). Values are our own numbers (no user input),
        # so unsafe_allow_html is safe here.
        total = meta["tokens_in"] + meta["tokens_out"]
        chips = (
            f'<span class="chip" title="{meta["tokens_in"]:,} in · {meta["tokens_out"]:,} out">'
            f'{total:,} tok</span>'
            f'<span class="chip">~${meta["cost_usd"]:.4f}</span>'
            f'<span class="chip">{meta["method"]} · K{meta["k"]}</span>'
            f'<span class="chip">{meta["model"]}</span>'
        )
        st.markdown(f'<div class="meta-row">{chips}</div>', unsafe_allow_html=True)
    if citations:
        for c in citations:
            with st.expander(f"[{c['n']}] {c['label']}"):
                st.markdown(c["text"])
    elif _looks_like_refusal(text):
        # D3: calm out-of-scope card — shown only on a real refusal, not on every
        # uncited answer, and never the loud yellow st.warning.
        with st.container(border=True):
            st.markdown("⚠︎ Out of scope — I answer only from the indexed 14 CFR material.")


st.set_page_config(page_title="FAA RAG Chat", page_icon="🛩️")

# Theme polish (D6): serif headings for the sectional-chart warmth; mono footer chips.
st.markdown(
    """<style>
    /* Widen the centered column a bit — default ~730px felt too narrow on wide
       screens, but full-width would make legal-text lines too long to read. */
    .block-container{max-width:920px !important}
    h1{font-family:Georgia,"Times New Roman",serif;font-weight:600;letter-spacing:.2px}
    .meta-row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 2px;
      font-family:ui-monospace,Menlo,"SF Mono",monospace;font-size:12px}
    .meta-row .chip{background:#e4efe9;color:#3f4a45;padding:3px 11px;border-radius:13px}
    </style>""",
    unsafe_allow_html=True,
)

st.title("🛩️ FAA RAG Chat")
st.caption("Answers grounded in cited 14 CFR sources.")

index, embed_model, bm25 = get_index()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay the conversation so it survives Streamlit's rerun-on-every-interaction.
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
        st.markdown(_format_answer(m["text"], m.get("citations", []))
                    if m["role"] == "assistant" else m["text"])
        if m["role"] == "assistant":
            render_footer(m.get("meta"), m.get("citations", []), m["text"])

prompt = st.chat_input("Ask a question about 14 CFR…")

# Empty-state examples (D5): one click beats typing. Gone once a chat starts.
if not st.session_state.messages:
    st.caption("👋 New here? Try an example below — or ask your own question about 14 CFR.")
    for _q in EXAMPLES:
        if st.button(_q, use_container_width=True):
            prompt = _q

if prompt:
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        # 4b retrieval-first: show what we found before the answer starts generating.
        hits = retrieve(prompt, index, method=CHAMPION_METHOD, k=CHAMPION_K,
                        embed_model=embed_model, bm25=bm25)
        found = list(dict.fromkeys(h.get("section") or h.get("source") for h in hits))[:3]
        st.caption(f"🔍 Found {' · '.join(found)} · {CHAMPION_METHOD}·K{CHAMPION_K}")

        # 4a streaming: type the raw answer into a placeholder, then swap in the
        # formatted version (§ tint + [n] labels) once we have the full text.
        placeholder = st.empty()
        reply, meta = stream_answer(prompt, hits, placeholder)
        citations = _cited(reply, hits)
        placeholder.markdown(_format_answer(reply, citations))
        render_footer(meta, citations, reply)

    st.session_state.messages.append(
        {"role": "assistant", "text": reply, "meta": meta, "citations": citations})
