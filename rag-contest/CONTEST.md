# 🛩️ RAG-Chat Contest — 공식 설명

> Project · Contest — 주최측이 배포한 원문 기록. (전략·실행은 [STRATEGY.md](STRATEGY.md) · [EXPERIMENTS.md](EXPERIMENTS.md) 참조)

Point your RAG chat at a real, messy corpus: the **U.S. Federal Aviation Regulations (14 CFR)**. Tune it on the practice questions below — then go head-to-head on fresh questions, **tournament-style**.

---

## 📚 The corpus

Six PDFs from **14 CFR — Aeronautics & Space**, ~15 MB of dense legal text with cross-references, tables, and definitions:

| 파일 | 내용 |
|------|------|
| **Vol. 1 — FAA general (Parts 1–59)** | definitions, certification, airworthiness |
| **Part 61** | pilot certification |
| **Part 67** | medical standards |
| **Part 71 / 73** | airspace designations & special-use airspace |
| **Part 91** | general operating & flight rules |

⬇️ Download the corpus: `faa-rag-corpus.zip`

---

## ✍️ Practice with these 5

| # | Question | 정답 근거 |
|---|----------|-----------|
| 1 | What aeronautical experience is required for a private pilot certificate with an airplane single-engine rating? | **Part 61** |
| 2 | Which medical conditions disqualify an applicant for a first-class airman medical certificate? | **Part 67** |
| 3 | What are the fuel-reserve requirements for VFR flight, day versus night? | **Part 91** |
| 4 | How do operating requirements differ between Class B and Class C airspace? | **Parts 71 + 91** |
| 5 | What must a pilot do before operating in an active restricted area? | **Part 73** |

---

## 🏆 The tournament bracket

```
Entry 1 ─┐
         ├─ winner ─┐
Entry 2 ─┘          │
                    ├─ Champion
Entry 3 ─┐          │
         ├─ winner ─┘
Entry 4 ─┘
```

## ⚙️ How the contest works

1. Everyone builds a RAG chat over the FAA corpus and **tunes it on the 5 practice questions**.
2. On contest day a **fresh, unseen question** goes to two entries **head-to-head**.
3. The **better-grounded, better-cited** answer advances.
4. Repeat until **one remains** — the Champion.

---

## 📊 Contest Rubric

How head-to-head answers are scored. **100 points total** — *grounding and answer quality carry the weight.*

| Category | 배점 | Description |
|----------|:---:|-------------|
| **Answer Quality** | 30 | Factual accuracy (claims match sources, no hallucinations), relevance to the question, completeness, and **synthesis across sources** rather than text dumping. |
| **Citations & Grounding** | 25 | Claims are attributed to sources, citations point to the **actual supporting passage**, references resolve and are verifiable, and **no fabricated sources**. |
| **Cost Management** | 15 | Token-efficient: retrieves only what's needed and keeps prompts lean, reaching a correct, well-grounded answer with **as few tokens as possible**. |
| **Clarity & Communication** | 10 | Defines acronyms and jargon on first use, uses readable structure appropriate to the question, and avoids filler. |
| **User Experience** | 10 | Latency and responsiveness, **conversational coherence** across turns and follow-ups, and helpful tone. |
| **Robustness & Safety** | 10 | Handles ambiguous, adversarial, and out-of-scope queries gracefully, **flags or refuses** when appropriate, and **resists prompt injection** from retrieved content. |

> 💡 배점의 55%가 **답변 품질(30) + 인용·근거(25)** → 검색 정확도와 §조항 인용이 승부처. (배점은 앞서 확인한 대회 규정 기준; 원문 표엔 카테고리·설명만 표기되어 있었음.)
