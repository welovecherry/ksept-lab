"""Context Management RAG starter — indexer.

Walks documents/, chunks each file, embeds chunks, persists the index to disk
so the chat backend can load it without re-indexing.

TODO: implement chunk_text(). The embedding and storage code is provided so
you can focus on the structure.
"""
from __future__ import annotations  # allow `X | None` annotations on Python 3.9

import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from sentence_transformers import SentenceTransformer

# Put rag-contest/ on the path so both `python indexer.py` and app.py's
# `from indexer import ...` can reach the shared harness package ([리뷰 T1]).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness.recorder import log_index_build, log_run, new_id

# Multilingual (50+ languages), 384-dim — same model as the /embedding project.
# Lets the corpus and the queries be in different languages and still match.
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_PATH = Path(__file__).parent / "index.pkl"
DOCS_DIR = Path(__file__).parent / "documents"


# ════════════════════════════════════════════════════════════════
# TODO — implement chunk_text
#
# Split `text` into overlapping chunks. A reasonable default:
#   - ~1000 characters per chunk
#   - ~100 characters of overlap
#   - try to break on paragraph boundaries (\n\n) when possible
#
# Return a list of non-empty strings.
# See the lecture slide on chunking for one working implementation.
# ════════════════════════════════════════════════════════════════

def chunk_text(text: str, target_chars: int = 1000, overlap_chars: int = 100) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Greedily packs paragraphs (split on blank lines) into chunks of up to
    ~target_chars. Each chunk carries ~overlap_chars of trailing context from
    the previous chunk so retrieval doesn't lose information across cut points.
    Paragraphs longer than target_chars are split by character window.
    """
    # Split on blank lines, keeping non-empty paragraphs.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Break up any single paragraph that exceeds the target size.
    pieces: list[str] = []
    for para in paragraphs:
        if len(para) <= target_chars:
            pieces.append(para)
        else:
            for start in range(0, len(para), target_chars):
                pieces.append(para[start:start + target_chars])

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + 2 + len(piece) > target_chars:
            chunks.append(current)
            # Carry the tail of the finished chunk as overlap context.
            tail = current[-overlap_chars:] if overlap_chars > 0 else ""
            current = (tail + "\n\n" + piece) if tail else piece
        else:
            current = (current + "\n\n" + piece) if current else piece

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


# ════════════════════════════════════════════════════════════════
# FAA chunking: one chunk per §-section, carrying its section/part meta.
# ════════════════════════════════════════════════════════════════

# Matches the tags that extract_faa.py inserted: "<!-- §91.151 | part91 -->".
_SECTION_TAG = re.compile(r"<!-- (§[\d.\w]+) \| (part\d+) -->")


def chunk_by_section(text: str) -> list[dict]:
    """Split §-tagged FAA markdown into one chunk per section.

    Each chunk spans from one `<!-- § … -->` tag to the next and carries the
    section/part parsed from that tag, so retrieval can cite the exact clause.
    """
    tags = list(_SECTION_TAG.finditer(text))
    pieces: list[dict] = []
    for i, m in enumerate(tags):
        end = tags[i + 1].start() if i + 1 < len(tags) else len(text)
        body = text[m.end():end].strip()
        if body:
            pieces.append({"section": m.group(1), "part": m.group(2), "text": body})
    return pieces


def pick_chunker(text: str) -> list[dict]:
    """Route §-tagged FAA text to section chunking, everything else to char
    chunking. Both return list[dict] with a "text" key so build_index is uniform."""
    if "<!-- §" in text:
        return chunk_by_section(text)
    return [{"text": chunk} for chunk in chunk_text(text)]


def _chunk(text: str, chunker: str) -> list[dict]:
    """Chunking axis for the grid: force section/char, or content-route (default)."""
    if chunker == "section":
        return chunk_by_section(text)
    if chunker == "char":
        return [{"text": chunk} for chunk in chunk_text(text)]
    if chunker == "route":
        return pick_chunker(text)
    raise ValueError(f"unknown chunker: {chunker!r}")


# ════════════════════════════════════════════════════════════════
# Provided: embedding (sentence-transformers, no API key required)
# ════════════════════════════════════════════════════════════════

# Candidate embedding models for the grid (실험2) + their retrieval prefixes.
# Each value: (hf_id, query_prefix, doc_prefix). bge instructs the query only;
# e5 prefixes BOTH sides ("query:"/"passage:"); minilm/gte need no prefix.
# Prefixes must be applied at index time (doc side) AND query time (query side).
EMBED_MODELS = {
    "minilm": (MODEL_NAME, "", ""),
    "bge": ("BAAI/bge-large-en-v1.5",
            "Represent this sentence for searching relevant passages: ", ""),
    "e5": ("intfloat/e5-large-v2", "query: ", "passage: "),
    "gte": ("thenlper/gte-large", "", ""),
}
DEFAULT_MODEL = "minilm"

_models: dict[str, SentenceTransformer] = {}


def get_model(name: str = DEFAULT_MODEL) -> SentenceTransformer:
    if name not in _models:
        model_id = EMBED_MODELS[name][0]
        print(f"Loading embedding model '{name}' ({model_id})...")
        _models[name] = SentenceTransformer(model_id)
    return _models[name]


def _apply_prefix(texts: list[str], model_name: str, is_query: bool) -> list[str]:
    _, query_prefix, doc_prefix = EMBED_MODELS[model_name]
    prefix = query_prefix if is_query else doc_prefix
    return [prefix + t for t in texts] if prefix else list(texts)


def embed(texts: list[str], model_name: str = DEFAULT_MODEL,
          is_query: bool = False) -> list[list[float]]:
    """Embed strings with the named model, applying its query/doc prefix."""
    payload = _apply_prefix(texts, model_name, is_query)
    vectors = get_model(model_name).encode(
        payload, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


# ════════════════════════════════════════════════════════════════
# Provided: build / save / load / search
# ════════════════════════════════════════════════════════════════

def build_index(chunker: str = "route", embed_model: str = DEFAULT_MODEL) -> list[dict]:
    """Walk DOCS_DIR, chunk each file, embed, return list of records.

    `chunker`/`embed_model` are the grid axes (실험1·2): default "route"+minilm
    reproduces the app's index. Subdirectories (e.g. _apollo_backup/) are skipped,
    so moving the starter's apollo docs there drops them without touching this code.
    """
    records: list[dict] = []
    chunk_id = 0
    for path in sorted(DOCS_DIR.glob("*")):
        if path.is_dir() or path.suffix.lower() not in (".md", ".txt"):
            continue
        pieces = _chunk(path.read_text(), chunker)
        if not pieces:
            continue
        vectors = embed([p["text"] for p in pieces], embed_model, is_query=False)
        for i, (piece, vec) in enumerate(zip(pieces, vectors)):
            records.append({
                "chunk_id": chunk_id,
                "source": path.name,
                "chunk_index": i,
                "text": piece["text"],
                "section": piece.get("section"),  # None for non-FAA (char) chunks
                "part": piece.get("part"),
                "embedding": vec,
            })
            chunk_id += 1
        print(f"  {path.name}: {len(pieces)} chunks")
    return records


def save_index(records: list[dict]) -> None:
    with INDEX_PATH.open("wb") as f:
        pickle.dump(records, f)


def load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"No index found at {INDEX_PATH}. Run `python indexer.py` from the project root first."
        )
    with INDEX_PATH.open("rb") as f:
        return pickle.load(f)


def cosine_distance(a: list[float], b: list[float]) -> float:
    # Both vectors are unit-normalized, so cosine distance == 1 - dot product.
    return 1.0 - sum(x * y for x, y in zip(a, b))


def search(query: str, records: list[dict], k: int = 5,
           model_name: str = DEFAULT_MODEL) -> list[dict]:
    """Embed the query (with the model's query prefix), return top-k by cosine."""
    [query_vec] = embed([query], model_name, is_query=True)
    scored = [(cosine_distance(r["embedding"], query_vec), r) for r in records]
    scored.sort(key=lambda x: x[0])
    return [r for _, r in scored[:k]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    print(f"Indexing documents from {DOCS_DIR}/")
    records = build_index()
    save_index(records)
    print(f"\n✓ Indexed {len(records)} chunks → {INDEX_PATH.name}")

    # Record the build (success or not) as one manifest line.
    build_id = new_id("idx")
    log_index_build({
        "kind": "index_build", "build_id": build_id, "ts": _now(),
        "config": {"chunking": "section", "embed_model": MODEL_NAME, "corpus": "faa"},
        "result": {
            "status": "ok",
            "n_chunks": len(records),
            "n_sections": sum(1 for r in records if r.get("section")),
            "n_docs": len({r["source"] for r in records}),
        },
        "status": "ok", "error": None,
    })

    # [리뷰 T5] End-to-end smoke: prove the runs.jsonl schema by writing a REAL
    # line from an actual retrieval, not a hand-declared example.
    question = "What are the day VFR fuel-reserve requirements for an airplane?"
    hits = search(question, records, k=5)
    top_sections = [h.get("section") for h in hits]
    log_run({
        "kind": "run", "run_id": new_id("r"), "ts": _now(), "build_id": build_id,
        "config": {"chunking": "section", "embed_model": MODEL_NAME,
                   "retrieval": "vector", "topk": 5},
        "question_id": "smoke_fuel", "stage": "retrieval",
        "retrieval": {"topk_sections": top_sections},
        "status": "ok", "error": None,
    })
    print(f"  smoke: top sections {top_sections}")


if __name__ == "__main__":
    main()
