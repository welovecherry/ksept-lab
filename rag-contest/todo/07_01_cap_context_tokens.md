# A′안 — 질의기반 하위청크 재랭크로 토큰 절감 (재색인 X)

> ⚡ **급행 플랜(A′).** 대회 임박 → **재색인 없이** 배포 답변 토큰을 ~18k → **~2,000대**로.
> 🔁 **A→A′ 전환(2026-07-01):** 초안의 front-N(앞-N 자르기)은 **CONTEST 연습문제 1번(§61.109)을 콕 집어 망가뜨림**(정답 표가 조항 뒤쪽에 흩어짐). 대신 **큰 청크를 ~500자 조각으로 쪼개 질문 유사도순으로 예산까지** 채운다(같은 토큰·같은 속도·품질 우위, 재색인 X). = B안(하위청킹 재색인)을 재색인 없이 80% 당김. 근본 수정(파서 괴물청크·영구 하위청킹)은 별도 B안.

## 사용자 시나리오 (먼저 읽힌다)

- **누가**: 홍정민 — 시간 없음. 답변 품질은 만족스러운데 큰 조항 질문(§61.109 등)이 18k 토큰을 써서, *지금 당장* 토큰을 대회 평균대(2,500~4,000) 아래로 낮추고 싶은 사람.
- **언제**: 챔피언 설정(bge/vector/K5 + B_balanced) 배포 직후, 큰-조항 질문에서 토큰 폭증을 확인한 지금.
- **어떻게**:
  1. 컨텍스트에 넣는 **각 청크를 일정 글자수로 상한** 처리(재색인 없이 생성 직전에 자름).
  2. **출력 상한(`max_tokens`)도 축소** + (이미 균형 프롬프트에 "CONCISE" 있음).
  3. 대표 대형질문(§61.109)으로 **총 토큰 ~2,000** + 답이 여전히 쓸만한지 확인.
- **결과**: 재색인·리더보드 재분석 없이 **10분 내** 토큰이 대회 평균 이하로. 챗봇 즉시 출전 가능.
- **잘 안 될 때**: 큰 조항이 잘려 답이 부실해지면 → 상한을 조금 올리거나(품질↔토큰 저울질), 여유 생길 때 B안(하위청킹)으로 근본 수정.

> 비유: 큰 접시(조항 전체)를 통째로 내던 걸, *제일 관련 있는 앞부분만 덜어* 내는 것. 빠르지만 뒷부분이 필요한 손님(질문)에겐 아쉬울 수 있음 → 그건 B안에서 "요리를 작은 코스로 재구성"해 해결.

## 배경

- 18,284 토큰 분해: **입력(검색 컨텍스트) ~15,800(87%) + 출력 ~2,500(13%)**. → **입력이 지배**, 출력만 줄여선 절대 2,000 불가.
- section 청킹이 §태그~다음 §태그를 통째로 자름 → §61.109(19,637자)·§61.129(21,673자) 같은 초대형 조항, 게다가 파싱 사고로 §25.1801(200,311자) 등 **괴물 청크** 존재. K5로 뽑히면 폭발.
- A안은 **컨텍스트 조립 시점**(`format_context`)에서 청크를 잘라 재색인 없이 즉시 상한. 괴물 청크도 자동 방어.
- 트레이드오프(정직): 큰 조항을 중간에 자르면 **정답 부분이 잘릴 수 있음** → 큰-조항 질문 완전성 리스크. (근본 해결은 B안)

## 목표

1. 배포 경로(`app.py`)에서 **청크당 글자 상한** 적용 → 컨텍스트 토큰 급감.
2. **`max_tokens` 축소**로 출력도 절감.
3. 대표 대형질문 **총 토큰 ~2,000** 달성 + 답 유효성 눈확인, 기존 회귀 없음.

## 변경 대상 파일

### 수정
- `harness/retrieval.py` — `format_context(hits, max_chars=DEFAULT_CONTEXT_CHARS)` **기본값=CAP**(공유 기본값 → app·streamlit 자동 적용, [리뷰 1A]). 잘리면 `…` 표시. `DEFAULT_CONTEXT_CHARS` 상수.
- `harness/gen_answers.py`·`harness/try_prompt.py` — `format_context(hits, max_chars=None)` **명시적 None**으로 실험 재현성 보존.
- `rag-starter/backend/app.py` — `max_tokens` 축소(1024→~700, [리뷰 3]). CAP은 공유 기본값이라 별도 인자 불필요.
- `harness/tests/test_retrieval.py` — `format_context` 상한 단위테스트([리뷰 4]): 상한→자름+`…`, None→그대로.

### 자동 적용 (수정 불필요)
- `rag-starter/streamlit_app.py` — 공유 기본값 CAP 상속 → **당신이 실제 테스트한 UI가 이번에 고쳐짐**([리뷰 1A]). 동시세션이지만 인자 전달 없이 자동 정합.

### 참조
- 토큰 실측: 대표 질문으로 in/out 확인. (§5.1 — 입력이 비용 지배)

---

## 중요 규칙

- **재색인·그리드 재실행 없음** — A안의 존재 이유(속도).
- **상한값은 데이터로 확정**: 단계 2에서 대표 질문 토큰을 재보며 `CONTEXT_CHUNK_CAP` 조정(2,000 맞추되 과도한 잘림 회피).
- **품질 리스크 명시**: 큰-조항 답 일부 잘림 가능 → 근본은 B안. A는 임시 급행.
- **[리뷰 2A] 순진한 앞-N truncation 채택**: 정답이 조항 뒤쪽이면 놓칠 수 있음(silent). 급행이라 수용, 근본은 B안(하위청킹).
- **[리뷰 1A] CAP은 공유 기본값**: `format_context` 기본값으로 넣어 app·streamlit 자동 정합. 실험 하네스(gen_answers·try_prompt)만 `max_chars=None` 명시로 재현성 보존.
- **final holdout 재사용 금지**(과적합) — 검증은 tune·대표 질문으로.
- 각 단계 끝: **검증 → `/simplify` → 커밋 브리핑 → 커밋**. 체크박스 `[ ]→[x]`는 그 커밋에 같이.

---

## 실행계획

### 각 단계 요약
- **단계 1 — 청크 상한 기능**: `format_context`에 상한 옵션 + app.py 적용. UI: 큰 답이 짧아짐.
- **단계 2 — 상한값·출력 튜닝**: 대표 질문 토큰 재보며 CAP·max_tokens 확정(~2,000).
- **단계 3 — 회귀·눈검증 + 커밋**: tune 질문 품질 유지·토큰 하락 확인.

---

### [x] 단계 1: `select_context` 질의기반 재랭크 + app.py 적용
**띵크**: think — 런타임 재랭크(임베딩·예산·인용메타), 로직 중간 난이도.

**변경 파일**: `harness/retrieval.py`, `rag-starter/backend/app.py`, `harness/tests/test_retrieval.py`

**변경 내용(완료)**:
- `retrieval.py`: `_windows(text, size)`(문단우선 분할) + `select_context(query, hits, embed_model, window_chars=500, char_budget=6500)` — 큰 청크를 창으로 쪼개 질문 유사도(cosine)순으로 예산까지. 각 창은 부모 §메타(section/part/source/chunk_index) 상속 → 인용 유지. `format_context`는 순수 포맷터로 복귀(front-N 제거).
- `app.py`: `retrieve()` 뒤 `hits = select_context(user_message, hits, EMBED)` 한 줄. 인용도 이 창-hits로.
- `test_retrieval.py`: `_windows` 분할, `select_context` 랭킹·예산·메타(embed monkeypatch) — 5 신규 테스트.
- 하네스(gen_answers·try_prompt)는 재랭크 미적용(재현성).

**통과 기준(달성)**:
- ✅ CONTEST Q1(§61.109): raw 15,482tok → 재랭크 **1,625tok**, §61.109가 최다(5)창·top-1. 정답 조각 생존.
- ✅ 하네스 49개 테스트 통과.

**검증 통과 시 커밋**: `feat(retrieval): query-based sub-chunk rerank (select_context) to cap context tokens`

---

### [x] 단계 2: 상한값 + `max_tokens` 확정 (토큰 ~2,000)
**띵크**: think — 품질↔토큰 저울질(출력 판단).

**변경 파일**: `rag-starter/backend/app.py`

**변경 내용**:
- 대표 대형질문(§61.109류)으로 `DEFAULT_CONTEXT_CHARS` 후보(예: 1,200 / 1,500) 실측 → **총 토큰 ~2,000** 지점 선택.
  - 대략식: 총 ≈ (K × CAP/4) + 출력. K=5, CAP=1,300 → 입력 ~1,600 + 출력 → CAP 근방에서 조정.
- `max_tokens` 1024 → **~700**([리뷰 3]: 500은 §61.109 표류 좋은 긴 답을 자를 수 있음). 균형 프롬프트가 CONCISE라 대부분 그 아래.

**통과 기준**:
- 대표 대형질문 **총 토큰 ~2,000**(≤ 대회 평균 2,500~4,000).
- 답이 여전히 정답 조항 요지를 담음(핵심 잘림 없음 — 눈확인).

**검증 통과 시 커밋**: `feat(backend): cap context+output tokens (~2k) for contest budget`

---

### [x] 단계 3: 회귀·눈검증 + 마감
**띵크**: default — 실행·확인.

**변경 파일**: 없음(확인만)

**변경 내용**:
- tune 질문 몇 개로 답 품질 유지 확인 + 토큰 하락 확인. startup 가드/기존 채팅 회귀 없음.
- `/simplify` → 커밋.

**통과 기준**:
- tune 대표 질문 답 유효 + 토큰 이전보다 뚜렷이 감소. 회귀 없음.

**검증 통과 시 커밋**: `chore(app): verify capped-token answers on tune questions`

---

## 실험 로그

- **밸런스 튜닝 + primary-섹션 우선 (2026-07-01):** 사용자 QA로 큰 열거형 조항의 하위규칙 누락 반복 발견(§91.215 "10,000 MSL", §61.57 낮규칙, §61.109 세부). 원인: 섹션검색은 정상인데 **섹션 내부 창 재랭크가 하위항을 파편화**. ①입출력 밸런스: `DEFAULT_CONTEXT_BUDGET 6,500→5,000`(실측 Pareto — 입력↓·실속출력↑·총토큰↓). ②**타깃 개선 `select_context`**: 최고점 창이 속한 섹션(top HIT 아님 — vector가 §61.57을 4등으로 밀어서)의 창을 앞으로 모아 열거규칙 보존. 실측: **Mode C 10,000 ✅·§61.109 세부 ✅ 회복, 회귀 0, 토큰 ~2,100 유지**. **잔여 한계**: §61.57(6+하위항 최대조항)의 낮(a)규칙은 여전히 미흡(예산 올려도 안 잡힘) — §-opener 항상포함 휴리스틱은 부작용 위험으로 보류. 검색 방식은 vector가 리더보드 평균 최적이나 키워드 질문엔 hybrid가 우세(§61.57 vector 4등 vs hybrid 1등)로 기록.
- **단계2·3 + 에이전틱 검토 → 단일 RAG 확정 (2026-07-01):** `max_tokens 1024→700`(§61.109 표 안 잘림). 예산 `DEFAULT_CONTEXT_BUDGET=6,500` 확정(§61.109 총 **2,256tok**·H03 2,281·헤드라인 정확). **에이전틱(tool loop) 검토·실험** `harness/agent_rag.py`(search_cfr 툴 + 검색 하드캡 3): 광범위 질문 품질↑지만 **토큰 무제한 81,320 / 캡 15,954 / 구체질문 4,282**(단일의 2~27×). 단일 RAG가 이미 복잡질문(H06 2/2·§61.109·final holdout) 잘 풀고 루브릭 Cost(15)+UX(10)에 유리 → **단일 RAG 배포 확정, 에이전틱은 미배포 학습/폴백 아티팩트로 보존.** 버그 교훈: tool을 루프 중간에 제거하면 모델이 빈 턴 반환 → 툴 유지+"budget reached, 지금 답 써라" tool_result로 해결.
- **A→A′ 전환 + 단계1 (2026-07-01):** front-N이 CONTEST Q1(§61.109) 정답표를 날린다는 지적(동시세션) 확인 → 질의기반 재랭크로 교체. `select_context` 구현·검증: §61.109 질문에서 raw K5 **15,482tok → 1,625tok**(6,500자·13창), §61.109가 최다 5창·top-1로 정답 조각 생존. 하네스 49테스트 통과. front-N(`_truncate`) 제거, `format_context`는 순수 포맷터 복귀. **[리뷰 2A] 무효화**(재랭크가 위치가정 대체). 남은 근본이슈: 파서 괴물청크 §25.1801(200k)는 B안/파서수정.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Runs | Status | Findings |
|---|---|---|---|---|
| Eng Review | `/plan-eng-review` | 1 | issues_open→applied | 4 issues (P1×2, P2×2), 0 critical gaps |

**발견·반영:**
- **[1A·P1] 배포 UI 불일치** — 테스트한 UI는 streamlit인데 플랜은 app.py만 CAP → **CAP을 `format_context` 공유 기본값으로** 이동(app·streamlit 자동, 하네스만 None). *사용자 선택: 공유 기본값.*
- **[2A·P1] 앞-N truncation이 정답 뒤쪽을 놓칠 수 있음(silent)** — *사용자 선택: 급행이라 순진한 앞-N 수용, 근본은 B안.* 규칙에 리스크 명시.
- **[3·P2] `max_tokens` 500→~700** — §61.109 표류 좋은 긴 답 잘림 방지. 반영.
- **[4·P2] `format_context` 상한 무테스트** — 단위테스트 추가(상한·None). 반영.

**NOT in scope:** 스마트/의미기반 truncation, 하위청킹 재색인(=B안), 파서 괴물청크(§25.1801 200k 등) 수정.
**이미 존재:** `format_context`(step3 공유헬퍼) — 재구현 없이 확장.
**Outside voice(codex):** 급행·소규모(2파일) 고려 생략.

**VERDICT:** ENG CLEARED — P1 2건 모두 결정·반영(CAP 공유 기본값·truncation 리스크 문서화). 방향 유효(입력 토큰이 비용 지배, §5.1). 구현 준비 완료.

NO UNRESOLVED DECISIONS
