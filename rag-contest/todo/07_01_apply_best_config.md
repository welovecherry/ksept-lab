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

### [ ] 단계 1: `leaderboard.py` 만들기 → 챔피언 확정
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

### [ ] 단계 2: app.py를 챔피언으로 (검색 교체)
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

### [ ] 단계 3: SYSTEM_PROMPT 균형톤
**띵크**: think — 프롬프트 문자열 추가 + 놀이터로 몇 문항 검증(로직 아님, 출력 판단).

**변경 파일**: `rag-starter/backend/app.py`

**변경 내용**:
- SYSTEM_PROMPT에 B(균형) 규칙: *직답 한 줄 → 필요한 특정만 → 관련 경우 다 커버(군더더기 없이) → 전부 [n] 인용 → 출처 밖 지식 금지.*
  - **[리뷰 C2] 균형 프롬프트 문구는 한 곳에** — `try_prompt.py`와 `app.py`에 중복 복붙 금지. 공유 상수/모듈로 두거나, 놀이터에서 확정한 문구를 app.py로 *한 번* 옮기고 놀이터는 그걸 import.
- **[리뷰 완전성] 라이트 갈음의 한계 명시**: STRATEGY §8.7 전체 3막(생성→LLM 심판)을 놀이터로 대체하면 **프롬프트 선택이 심판으로 검증되진 않음**(놀이터 눈검증 수준). 여유·예산 되면 finalist × 프롬프트를 실제 생성→심판으로 확정([수정3]).

**통과 기준**:
- `try_prompt.py`로 연습문제 몇 개 → 현재보다 명확·완전하되 토큰 안 폭증, 출처밖 상식 없음.

**검증 통과 시 커밋**: `feat(backend): balanced answer prompt (helpful, complete, grounded)`

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

## GSTACK REVIEW REPORT

| Run | Status | Findings |
|---|---|---|
| plan-eng-review (focused) | applied | **A1**(인덱스 임베딩 단일 진실원·🔴P1), **A2**(section-only 재색인, char×큰모델 메모리·🔴P1), **T1**(leaderboard 단위테스트·🟡P2), **C2**(균형 프롬프트 DRY·🟡P2), 완전성(3막 심판을 놀이터로 갈음한 한계 명시) — 전부 문서 반영 |
| plan-design-review | N/A | 백엔드/설정 계획 — UI scope 없음(자체 종료 대상) |
| codex outside voice | skipped | 시간·규모 고려 생략(단발 4단계 계획) |

**VERDICT:** 계획 방향 정상. **구현 전 필수 P1 2건** — A1(임베딩 상수 단일화로 조용한 불일치 차단)·A2(재색인은 section만, char×큰모델 메모리 회피). 앞선 리뷰 R1~R5 + 이번 A1/A2/T1/C2 모두 반영됨. 검색설정→답변품질(30점) 레버 방향 유효(오늘 실측 근거).

NO UNRESOLVED DECISIONS
