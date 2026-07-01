"""Act-3 generation harness: prompt variants × holdout → prompt_runs.jsonl.

For each (prompt variant, tune question) it retrieves the champion context,
GENERATES an answer (sonnet — the only step that spends the shared key), then
PROGRAM-CHECKS the citations for free (valid [n]? do the cited chunks cover the
expected §?). Answers land in experiments/prompt_runs.jsonl for the LLM judge
(this Claude Code session, opus) and prompt_leaderboard.py to consume.

    python harness/gen_answers.py

Cost: 3 prompts × 5 questions = 15 sonnet calls (~$0.15). The system prompt
carries cache_control (§5.1), so questions 2..5 of each variant reuse it cheaply.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag-starter"))
sys.path.insert(0, str(ROOT / "rag-starter" / "backend"))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402 — SYSTEM_PROMPT, client, INDEX, EMBED, champion config
from harness.recorder import EXPERIMENTS_DIR  # noqa: E402
from harness.retrieval import format_context, retrieve  # noqa: E402
from harness.score import _matches, _norm  # noqa: E402
from try_prompt import VARIANTS  # noqa: E402 — the single source of prompt variants

PROMPT_RUNS_PATH = EXPERIMENTS_DIR / "prompt_runs.jsonl"

# tune split only (final is held out for step 4): comprehensive (H01, H06),
# single-clause (H03, H09), and a prompt-injection refusal (H14).
QUESTION_IDS = ["H01", "H03", "H06", "H09", "H14"]

GEN_MODEL = "claude-sonnet-4-6"


def load_questions() -> list[dict]:
    by_id = {}
    for line in (ROOT / "holdout.jsonl").open(encoding="utf-8"):
        q = json.loads(line)
        by_id[q["id"]] = q
    return [by_id[qid] for qid in QUESTION_IDS]


def program_check(answer: str, hits: list[dict], expected: list[str]) -> dict:
    """Free citation check: are [n] in range, and do cited chunks cover expected §?"""
    nums = [int(n) for n in re.findall(r"\[(\d+)\]", answer)]
    invalid = sorted({n for n in nums if not 1 <= n <= len(hits)})
    cited = {n for n in nums if 1 <= n <= len(hits)}
    exp_norm = {_norm(e) for e in expected}
    covered: set[str] = set()
    for n in cited:
        covered |= _matches(hits[n - 1], exp_norm)
    return {
        "n_citations": len(nums),
        "invalid_citations": invalid,          # invented numbers = ungrounded
        "cited_coverage": (len(covered) / len(exp_norm)) if exp_norm else None,
    }


def generate(system_prompt: str, user_content: str):
    """One sonnet call; cache the system block so repeats within a variant are cheap."""
    return app.client.messages.create(
        model=GEN_MODEL,
        max_tokens=800,
        system=[{"type": "text", "text": system_prompt,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )


def main() -> None:
    questions = load_questions()
    # Retrieve each question's context ONCE and reuse it across every prompt
    # variant — the query embedding is identical, so 5 retrievals, not 15.
    contexts = [(q, hits := retrieve(q["question"], app.INDEX,
                                     method=app.CHAMPION_METHOD, k=app.CHAMPION_K,
                                     embed_model=app.EMBED), format_context(hits))
                for q in questions]

    records = []
    for vi, (name, extra) in enumerate(VARIANTS.items()):
        # Build on grounding-only so A_current is the true baseline and B_balanced
        # applies app.BALANCED_STYLE exactly once (not doubled via SYSTEM_PROMPT).
        system_prompt = app.GROUNDING_RULES + extra
        for qi, (q, hits, ctx) in enumerate(contexts):
            # Prompt-major ids (p0001-05 = variant 1, ...) stay stable regardless
            # of loop order, so judge_scores.jsonl keeps mapping to the same runs.
            run_no = vi * len(contexts) + qi + 1
            user_content = f"CONTEXT:\n{ctx}\n\nQUESTION:\n{q['question']}"

            resp = generate(system_prompt, user_content)
            answer = resp.content[0].text
            u = resp.usage
            check = program_check(answer, hits, q.get("expected_sections") or [])
            records.append({
                "kind": "prompt_run", "run_id": f"p{run_no:04d}",
                "prompt": name, "question_id": q["id"],
                "answer": answer,
                "tokens": {"in": u.input_tokens, "out": u.output_tokens,
                           "cache_read": getattr(u, "cache_read_input_tokens", 0)},
                "program_check": check,
            })
            cov = check["cited_coverage"]
            print(f"  {name:<11} {q['id']}  in={u.input_tokens} out={u.output_tokens} "
                  f"cov={cov if cov is None else round(cov, 2)} "
                  f"bad_cites={check['invalid_citations']}")

    with PROMPT_RUNS_PATH.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n→ {PROMPT_RUNS_PATH.relative_to(ROOT)} ({len(records)} runs)")


if __name__ == "__main__":
    main()
