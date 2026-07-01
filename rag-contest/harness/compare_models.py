"""Side-by-side embedding-model comparison for the demo (best vs worst).

Shows WHY the champion embedding matters: the same query retrieves different §
sections under different models. bge (champion) vs minilm (starter default) is
the starkest contrast — bge tends to find the answer section, minilm often lands
on unrelated ones. Retrieval-only by default: free (local), and the difference is
clearest at the retrieval stage. streamlit_app.py can import compare_retrieval()
to render two columns without touching the deployed single-shot path.

    python harness/compare_models.py build          # build the non-deployed indexes
    python harness/compare_models.py "your question" # print side-by-side sections
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
sys.path.insert(0, str(ROOT))

from indexer import (  # noqa: E402
    CHAMPION_CHUNKER,
    INDEX_PATH,
    build_index,
    load_index,
    load_index_embed_model,
)
from harness.retrieval import retrieve  # noqa: E402

# Best vs worst — the starkest contrast for the demo. Order = display order.
COMPARE_MODELS = ["bge", "minilm"]


def _cmp_path(model: str) -> Path:
    """Dedicated compare-index file, kept separate from the deployed index.pkl."""
    return INDEX_PATH.parent / f"index.cmp.{model}.pkl"


def load_compare_index(model: str) -> list[dict]:
    """Load a model's section index. Reuses the live index.pkl when it already
    IS this model (the champion), so only the non-deployed models need building."""
    if model == load_index_embed_model():
        return load_index()
    path = _cmp_path(model)
    if not path.exists():
        raise FileNotFoundError(
            f"No compare index for {model!r}. Run: python harness/compare_models.py build")
    with path.open("rb") as f:
        return pickle.load(f)


def build_compare_indexes() -> None:
    """Build a section index for each compare model except the deployed one."""
    deployed = load_index_embed_model()
    for m in COMPARE_MODELS:
        if m == deployed:
            print(f"  {m}: reusing deployed index.pkl (skip build)")
            continue
        print(f"  {m}: building section index…")
        records = build_index(CHAMPION_CHUNKER, m)
        with _cmp_path(m).open("wb") as f:
            pickle.dump(records, f)
        print(f"  {m}: saved {_cmp_path(m).name} ({len(records)} chunks)")


def compare_retrieval(query: str, k: int = 5) -> dict[str, list[dict]]:
    """{model: top-k hits} for each compare model — retrieval only, free.

    Each model queries its OWN index with its OWN prefix (A1), so the comparison
    is apples-to-apples. streamlit renders one column per model from the hits.
    """
    return {
        m: retrieve(query, load_compare_index(m), method="vector", k=k, embed_model=m)
        for m in COMPARE_MODELS
    }


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_compare_indexes()
        return
    q = (sys.argv[1] if len(sys.argv) > 1
         else "recent flight experience day vs night to carry passengers")
    print(f"Q: {q}\n")
    for model, hits in compare_retrieval(q).items():
        print(f"  {model:<7}: {[h.get('section') for h in hits]}")


if __name__ == "__main__":
    main()
