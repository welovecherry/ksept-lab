"""Streamlit chat UI for the FAA RAG contest — stage 1 skeleton.

Reuses indexer.search (vector retrieval) and the same SYSTEM_PROMPT as the Flask
backend, but calls Anthropic directly so later stages can stream natively and we
never have to edit app.py (zero conflict with the output/prompt session).

Run from rag-starter/:  streamlit run streamlit_app.py

[E1] SYSTEM_PROMPT is copied here TEMPORARILY. Importing app.py would fire its
module-level side effects (load_index, Anthropic(), Flask). Once the output
session extracts the prompt to backend/prompts.py, replace the constant below
with:  from prompts import SYSTEM_PROMPT
"""
from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from indexer import load_index, search

load_dotenv(Path(__file__).parent / ".env")  # ANTHROPIC_API_KEY (shared class key)

MODEL = "claude-sonnet-4-6"
TOP_K = 5
MAX_TOKENS = 1024
AVATARS = {"user": "🧑", "assistant": "🛩️"}

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
    """Load the pickled index once per server process (heavy — cache it)."""
    return load_index()


@st.cache_resource
def get_client():
    return Anthropic()


def answer(question: str, index: list[dict]) -> tuple[str, list[dict]]:
    """Retrieve top-K chunks, build the numbered context block, generate an answer.

    Mirrors app.py's /api/chat so the two frontends behave identically. Returns
    the answer text and the hits (slimmed) so stage 2 can render source cards
    without re-searching.
    """
    hits = search(question, index, k=TOP_K)
    context = "\n\n".join(f"[{i + 1}] {h['text']}" for i, h in enumerate(hits))
    user_content = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    answer_text = resp.content[0].text
    # Slim the hits: drop the 384-dim embedding before it lands in session_state.
    slim = [{k: h.get(k) for k in ("source", "chunk_index", "section", "part", "text")}
            for h in hits]
    return answer_text, slim


st.set_page_config(page_title="FAA RAG Chat", page_icon="🛩️")
st.title("🛩️ FAA RAG Chat")

index = get_index()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay the conversation so it survives Streamlit's rerun-on-every-interaction.
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
        st.markdown(m["text"])

if prompt := st.chat_input("Ask a question about 14 CFR…"):
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.spinner("Searching + answering…"):
            reply, hits = answer(prompt, index)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "text": reply, "hits": hits})
