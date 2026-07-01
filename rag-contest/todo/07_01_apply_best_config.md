# 3막 (아침) 실행 — 지금까지의 챔피언을 챗봇에 반영 → 출전

> ⚠️ **평행 계획 아님.** 3막의 권위 있는 설계는 [`STRATEGY.md` §8.5~8.7](../STRATEGY.md)·[`EXPERIMENTS.md` §5.1·§6](../EXPERIMENTS.md)에 있다. 여기는 그걸 **손으로 돌릴 체크리스트 + 코드 델타**만. 흐름·용어·비용가드는 STRATEGY §8.7을 따른다.

## 사용자 시나리오 (가장 먼저 읽힌다)

- **누가**: 홍정민 — 아침. 밤새 돌아간 실험 결과를 받아, *제일 잘 답하는 설정*을 챗봇에 심어 대회에 내보내는 사람.
- **언제**: 밤샘 그리드가 `runs.jsonl`을 채운(부분 완주) 직후.
- **어떻게**:
  1. **검색 성적표(리더보드)** 를 봐서 잘 물어오는 검색설정 **후보 2개**를 추린다.
  2. 그 후보들로 **홀드아웃 질문에 실제 답변을 생성**해본다(프롬프트 톤도 몇 개 시험 — 놀이터 `try_prompt.py`).
  3. **자동 채점(인용검증) + Claude 심판**으로 점수를 매겨 순위표를 만든다.
  4. **1등 설정**(검색방식·모델·K·프롬프트)을 챗봇(`app.py`)에 심는다.
  5. **연습문제 5개 + 비밀 시험지(final)** 로 눈검증하고, 문제없으면 **출전**.
- **결과**: "감"이 아니라 *홀드아웃 점수로 고른* 최적 설정이 챗봇에 반영돼, 처음 보는 질문에도 잘 답하는 출전본 완성.
- **잘 안 될 때**: 1·2등 점수가 근소하면 → *더 싸고 단순한* 쪽 선택(비용·안정성).

> 비유: 밤새 예선(여러 레시피 시식)을 돌려 **우승 레시피**를 데이터로 가렸으니, 아침에 그 레시피로 *본선 요리*를 실제로 차려 내보내는 단계.

## 배경

- **밤샘 그리드가 메모리 스와핑으로 중단(kill)됨** — char 청킹(5495조각) × 큰 모델(bge/e5/gte)이 16GB로 부풀어 스왑 thrash. **완주분**: `section × {minilm·bge·e5·gte}`(4모델 전부!) + `char/minilm` = **495 run**.
- **챔피언은 이 부분결과에서 뽑아도 충분** — 가장 중요한 *임베딩 비교(실험2)* 가 section에서 4모델 다 됐다. `char×큰모델`은 미완이나 덜 중요(section이 §인용에 유리, char는 메모리 과다).
- app.py는 지금 `search()`(vector·minilm) → 종합질문에서 정답 조항 놓침(오늘 실측). `retrieve(method="hybrid")` + 균형 프롬프트 = **답변품질 30점의 레버**.

## 목표

1. 부분결과 리더보드로 **챔피언(+2등 finalist) 검색설정 확정**.
2. `app.py`가 챔피언(인덱스·검색방식·K·모델)으로 검색하게.
3. `app.py` SYSTEM_PROMPT를 **균형톤**으로.
4. **연습 5 + holdout final** 눈검증 → 출전.

## 변경 대상 파일

### 신규
- `harness/leaderboard.py` — `runs.jsonl` → 설정별 순위표(STRATEGY §8.7 `leaderboard.md` 자동생성부).

### 수정
- `rag-starter/indexer.py` — (챔피언이 현재와 다르면) 챔피언 임베딩으로 재색인해 `index.pkl` 교체.
- `rag-starter/backend/app.py` — `search()` → `harness.retrieval.retrieve(method,k,embed_model,bm25)`; SYSTEM_PROMPT 균형톤.

### 참조
- STRATEGY §8.5~8.7(3막·심판·비용가드), EXPERIMENTS §5.1·§6, 놀이터 `harness/try_prompt.py`.

---

## 중요 규칙

- **부분결과라도 신뢰 가능**: section×4모델은 완주 → 임베딩·검색·K 비교는 유효. char×큰모델 미완은 리더보드에 "미측정"으로 표기(속이지 않음).
- **품질만 보지 말고 비용도**: coverage 근소차(12문제서 1문제≈8%)면 *더 싸고 단순한* 설정([수정4]③·EXPERIMENTS §5.1).
- **[동시 세션]** `06_30_chat_ui.md` 세션도 `app.py`(meta) 건드림 → 순서 합의(한쪽 먼저 커밋→rebase), 코드 즉시 커밋.
- 각 단계 끝: **검증 → `/simplify` → 커밋 브리핑 → 커밋**. 체크박스 `[ ]→[x]`는 **그 커밋에 같이**.

---

## 실행계획

### 각 단계 요약 (쉽게 + 무엇이 바뀌나)

- **단계 1 — 성적표 만들기**: 밤새 쌓인 495줄을 설정별 순위표로. UI: 변화 없음(터미널 표).
- **단계 2 — 챔피언을 챗봇에 심기(검색)**: 챗봇이 vector→챔피언(hybrid 등)으로 검색. UI: 답이 더 정확해짐(특히 종합질문).
- **단계 3 — 말투 개선(프롬프트)**: 딱딱→친절+완전+그라운딩. UI: 답변이 읽기 좋아짐.
- **단계 4 — 시식(눈검증)**: 연습 5 + 비밀 시험지로 확인 후 출전. UI: 대회 출전본 확정.

---

### [x] 단계 1: `leaderboard.py` 만들기 → 챔피언 확정
**띵크**: think — `runs.jsonl` 그룹집계+정렬(가벼운 판단). 새 알고리즘 아님.

**변경 파일**: `harness/leaderboard.py`(신규)

**변경 내용**:
- `runs.jsonl`을 (chunking·embed·method·K)로 그룹 → 평균 **coverage·recall·MRR** + **비용프록시(K × 평균 청크길이)** 순위표.
- 상위 **2개(finalist)** 표시. coverage 근소차면 싼 쪽 힌트.

- **[리뷰 T1] `test_leaderboard.py`**: 가짜 runs 몇 줄 → 그룹집계·순위·비용프록시가 맞는지 단위테스트.

**통과 기준**:
- `python harness/leaderboard.py` → 순위표 출력(495줄 기반), 1·2등 설정 명확, 비용프록시 열 존재.
- section×4모델이 표에 다 뜸(char×큰모델은 없음 — 미측정).
- `pytest harness/tests/test_leaderboard.py -q` 통과.

**검증 통과 시 커밋**: `feat(harness): leaderboard.py — rank configs by coverage/MRR + cost proxy (with tests)`

---

### [x] 단계 2: app.py를 챔피언으로 (검색 교체)
**띵크**: think hard — 임베딩 일치·BM25 startup·regression 등 회귀 민감. 조용한 버그 위험.

**변경 파일**: `rag-starter/indexer.py`(재색인 필요시), `rag-starter/backend/app.py`

**변경 내용**:
- 챔피언 임베딩이 현재(minilm)와 다르면 `build_index(chunker, embed)` → `save_index`로 `index.pkl` 교체.
  - **[리뷰 A2] 재색인은 section 계열만** — char×큰모델은 어젯밤 메모리 폭발 지점(5495청크). section+bge(2184)는 완주됐으니 안전. 챔피언이 char×큰모델이면 재색인하지 말고 다음 순위(section)로.
- `from indexer import search` → `from harness.retrieval import retrieve, build_bm25`.
- **[R3] startup 1회 BM25**: `INDEX=load_index()` 옆 `BM25=build_bm25(INDEX)`. `/api/chat`은 `retrieve(q, INDEX, method=<챔피언>, k=<챔피언>, embed_model=<챔피언>, bm25=BM25)`. (요청마다 재빌드 금지 — 지연↑=UX 손해)
- **[R2·리뷰 A1] 쿼리 임베딩 = 인덱스 임베딩 (단일 진실원)**: index.pkl엔 모델 정보가 없어 조용한 불일치 위험. **인덱스 빌드와 app.py가 같은 상수 하나**(예: `EMBED = "bge"`)를 참조하게 하거나, `save_index`가 embed_model을 함께 저장. bge 인덱스에 minilm 쿼리 = 에러 없이 무의미 결과.

**통과 기준**:
- 종합질문(H10류)이 이제 정답 조항 물어와 실제로 답함(vector 때 실패 → 개선 확인).
- 요청당 지연이 BM25 재빌드로 안 늘어남. 기존 채팅 regression 없음.

**검증 통과 시 커밋**: `feat(backend): retrieve with champion config (bm25 built once at startup)`

---

### [x] 단계 3: SYSTEM_PROMPT 균형톤 — 프롬프트 리더보드(3막 풀버전)
**띵크**: think — 생성 하네스 + 심판 루브릭(로직은 가볍고, 출력 판단이 핵심).

> **[확장 결정 2026-07-01]** 놀이터 눈검증(라이트 갈음) 대신 **STRATEGY §8.7 3막 풀버전**을 돌린다: 프롬프트 후보를 실제 생성→프로그램 인용검증→LLM 심판(루브릭)→**프롬프트 리더보드**. 검색 리더보드(단계1)와 같은 구조. 사용자 요청.

**변경 파일**: `harness/gen_answers.py`(신규), `harness/prompt_leaderboard.py`(신규), `harness/try_prompt.py`(DRY·팔로업 수정), `rag-starter/backend/app.py`(우승 프롬프트 반영)

**설계**:
- **후보 3프롬프트** = `try_prompt.VARIANTS`(단일 진실원, [C2 DRY]): `A_current`(현행)·`B_balanced`·`C_warm`. 각자 `app.SYSTEM_PROMPT`(그라운딩 base)에 붙는 add-on.
- **질문 = tune 5개**(H01·H03·H06·H09·H14 — 다조항/단일/거부 혼합). **final 제외**(단계4 전용, §수정6 과적합 방지).
- **생성**(공용 API, sonnet): `gen_answers.py`가 3×5=15 호출 → `prompt_runs.jsonl`(답변·토큰·인용). **[§5.1] system에 `cache_control`**.
- **프로그램 검증**(무료 코드): 인용 [n] 유효성 + 인용된 청크가 정답 § 커버(`score._matches` 재사용).
- **LLM 심판**(무료, 이 세션 opus): 답변별 루브릭 1~5(도움됨·완전함·그라운딩) → `judge_scores.jsonl`. **생성=sonnet / 심판=opus 분리**(자기편향↓, §8.5).
- **`prompt_leaderboard.py`**: 프롬프트별 평균 심판점수 + 인용정합률 + 평균토큰 → `prompt_leaderboard.md`. 우승 프롬프트를 app.py에 반영.
  - **[팔로업]** `try_prompt.py`의 `embed_model="minilm"` → `app.EMBED`(bge 정합).

**비용 가드**: 생성만 공용키(≈$0.15). 심판·검증 0원. final 미사용.

**통과 기준**:
- `prompt_leaderboard.md`에 3프롬프트 순위(심판·인용·토큰) 명확, 우승 프롬프트 확정.
- 우승 프롬프트 반영 후 답: 명확·완전, 토큰 안 폭증, 출처밖 상식 없음, H14 인젝션 거부.

**검증 통과 시 커밋**: `feat(backend): balanced answer prompt won by prompt leaderboard (gen+judge)`

---

### [ ] 단계 4: 눈검증 → 출전
**띵크**: default — 채팅 UI에서 눈확인(기계적).

**변경 파일**: 없음(실행·확인만)

**변경 내용**:
- 연습 5문항(§9 체온계, 하드코딩 금지) + holdout `split:"final"` 3~4개를 채팅 UI(`localhost:5173`)로 확인. 범위밖 거부 확인.

**통과 기준**:
- 5문제 다 옳은 §인용 + 완전한 답. final holdout도 무너지지 않음(과적합 아님). 범위밖 거부.

**검증 통과 시 커밋**: `chore(app): verify champion config on practice + final holdout`

---

## 실험 로그

- **밤샘 그리드 중단 (2026-07-01):** `char × 큰모델(bge/e5/gte)`이 5495청크 임베딩으로 프로세스가 **16GB로 부풀어 스왑 thrash**(uninterruptible I/O, CPU 0.3~24% 요동) → 사용자가 PID kill. 완주 = `section×{minilm,bge,e5,gte}` + `char/minilm` = **495 run**. **교훈**: 큰 모델은 char 청킹에서 메모리 폭증 → 오케스트레이터가 (a)배치/스트리밍 임베딩 (b)모델 언로드 (c)char×큰모델 스킵 중 하나 필요. 챔피언은 부분결과(특히 section×4모델)로 충분.
- **토큰 실측 → K 결정 (2026-07-01):** 라이브 프롬프트 그대로 `sonnet-4-6` 실호출로 K별 usage 측정 — **K=3: 1,762 · K=5: 2,656 · K=8: 5,136 토큰** (in/out = 1660/102 · 2556/100 · 5042/94). 핵심 두 가지: ① **출력은 K와 무관하게 ~100토큰 고정** → *답변 간결화는 최대 ~50토큰 절약 = 무의미*. ② 토큰의 **91~96%가 입력(K × 문단)** — K8은 K5의 **약 2배**(마지막에 딸려오는 큰 § 문단이 원인)인데 coverage는 0.864→0.818로 근소차. **→ K=5 권장**(타 팀 평균 2,500~4,000대에 부합, 라이브 `search()` 기본값이 이미 k=5). *토큰 절약의 유일한 손잡이 = K 낮추기.* (부수 확인: SYSTEM_PROMPT의 VFR 약어 규칙 작동 — "VFR (Visual Flight Rules)" 출력됨.)

---

- **챔피언 확정 — leaderboard.py (2026-07-01):** 495줄(45설정×11문제)을 순위표로. **coverage 1등 = `section/bge/hybrid/K8`(0.864)**, 2·3등도 K8 hybrid(gte·minilm) 동률. 하지만 순위 규칙(coverage↓→MRR↓→비용↑)+근소차(±0.09) 밴드 최저비용 선택으로 **추천 = `section/bge/vector/K5`**(cov 0.818·**MRR 0.718**·비용 −38%). 근거: 11문제 중 0.046(≈½문제)차는 통계적 동점, K5가 실험 로그(토큰 실측) K=5 결정과 일치하고 정답을 더 위(MRR↑)에 놓음. **finalist 2개**(hybrid/K8 챔피언 + vector/K5 추천)를 단계 2로. char×큰모델 27개는 "미측정" 명시(속이지 않음). section 청킹이 상위 36개 독식(char는 37등부터).

- **챔피언 검색 반영 — app.py + 재색인 (2026-07-01):** `index.pkl`을 **section/bge(1024d)로 재색인**(bge 캐시됨, 2184청크, ~8분). `app.py`: `search()(vector/minilm)` → `retrieve(method=vector, k=5, embed_model=bge, bm25=None)`. **A1 해결**: `index.meta.json` 사이드카에 embed_model 기록 → app.py가 `load_index_embed_model()`로 읽어 같은 모델로 질의 + startup 차원가드(불일치 시 loud 실패). 근본수정으로 `search()` 기본 모델도 인덱스 스탬프로(streamlit·verify_holdout 자동 정합, 동시세션 파일 미변경). 검증(무료): H06 종합질문 §91.130+§91.131 **2/2**(옛 vector/minilm 실패분 개선), startup 가드 통과, 하네스 44테스트 통과. **팔로업**: try_prompt.py의 `embed_model="minilm"` 하드코딩은 단계3에서 정리.

- **프롬프트 리더보드 — 3막 풀버전 (2026-07-01):** 3프롬프트(A_current·B_balanced·C_warm) × tune 5문항(H01·H03·H06·H09·H14) = **15 생성**(sonnet, 공용키, system에 cache_control). 프로그램 인용검증(무료): 셋 다 인용오류 0·커버 0.88 동률. **LLM 심판(이 세션 opus, 무료)** 루브릭(도움됨·완전함·그라운딩 1~5) → **우승 B_balanced(4.93) > A_current(4.60) > C_warm(4.20)**. 변별점: 그라운딩은 셋 다 만점(인젝션 H14 모두 거부), **완전성에서 갈림** — C_warm은 장황해 out=800 상한에 3번 걸려 잘림, B는 다 덮고도 안 잘림. app.py `SYSTEM_PROMPT = GROUNDING_RULES + BALANCED_STYLE`(우승문구, 단일 진실원); try_prompt·gen_answers가 이를 공유([C2] DRY). 산출: `experiments/prompt_leaderboard.md`. 신규 하네스: `gen_answers.py`·`prompt_leaderboard.py`. /simplify 반영: 질문당 검색 1회·`retrieval.format_context()` 3파일 공유·심판누락 경고.

- **우승 프롬프트(배포본) — 명시:** `rag-starter/backend/app.py`의 `SYSTEM_PROMPT = GROUNDING_RULES + BALANCED_STYLE`. 우승 델타 `BALANCED_STYLE`(= 놀이터 `B_balanced`, 단일 진실원):
  ```text
  How to write: clear and helpful like a good instructor, but CONCISE. Lead with a
  one-line direct answer, then only the specifics the sources support. Cover all
  relevant cases (e.g. day/night, airplane/rotorcraft) without padding. Cite every
  claim [n]; use ONLY the sources.
  ```
  (앞의 `GROUNDING_RULES`는 기존 그라운딩·[n]인용·거부·약어풀이 규칙. 리더보드: `experiments/prompt_leaderboard.md`.)

## GSTACK REVIEW REPORT

| Run | Status | Findings |
|---|---|---|
| plan-eng-review (focused) | applied | **A1**(인덱스 임베딩 단일 진실원·🔴P1), **A2**(section-only 재색인, char×큰모델 메모리·🔴P1), **T1**(leaderboard 단위테스트·🟡P2), **C2**(균형 프롬프트 DRY·🟡P2), 완전성(3막 심판을 놀이터로 갈음한 한계 명시) — 전부 문서 반영 |
| plan-design-review | N/A | 백엔드/설정 계획 — UI scope 없음(자체 종료 대상) |
| codex outside voice | skipped | 시간·규모 고려 생략(단발 4단계 계획) |

**VERDICT:** 계획 방향 정상. **구현 전 필수 P1 2건** — A1(임베딩 상수 단일화로 조용한 불일치 차단)·A2(재색인은 section만, char×큰모델 메모리 회피). 앞선 리뷰 R1~R5 + 이번 A1/A2/T1/C2 모두 반영됨. 검색설정→답변품질(30점) 레버 방향 유효(오늘 실측 근거).

NO UNRESOLVED DECISIONS
