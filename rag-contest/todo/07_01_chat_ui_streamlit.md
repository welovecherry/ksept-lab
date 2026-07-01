# 채팅 UI (Streamlit 버전) — 가벼운 4단계로 같은 목표

> 🛩️ `06_30_chat_ui.md`(React 8단계)를 **Streamlit로 다시 짠 경량판**. 목표(마크다운·메타·$비용·Sources·거부·스트리밍·멀티턴)는 그대로, 프레임워크 싸움을 내장 기능으로 대체해 **단계·코드·세션 충돌을 대폭 축소**.
> React 원본은 폴백으로 보존 → [`06_30_chat_ui.md`](06_30_chat_ui.md). **둘 중 하나만 최종 제출.**
> **확정 목업**: [`mockups/chat_ui_streamlit.html`](../mockups/chat_ui_streamlit.html) — 크림+teal·terracotta 인용·mono 데이터, 검색먼저 줄·후속칩·조용한 비용 footer. Streamlit이 실제로 그릴 수 있는 선에서의 상한선.

## 왜 Streamlit인가 (피로 감소 근거)

- 지금 계획이 무거운 이유 = React + Flask + 빌드. 단계 2·4·6·8이 대부분 "프레임워크와 싸우는 일".
- Streamlit은 그걸 **내장**으로 공짜로 줌: 마크다운·접힘카드·중복제출잠금·스트리밍·멀티턴.
- `indexer.py`가 이미 파이썬 → 궁합 좋음. **채팅 UI가 파이썬 파일 1개**로 끝.

> 용어: **Streamlit** = 파이썬 몇 줄로 웹 UI를 만드는 도구(JS·빌드·별도 서버 없음). `st.write_stream`=토큰 스트리밍 내장, `st.expander`=접힘 카드 내장, `st.session_state`=대화 히스토리 저장소.

## 배점 관점 (왜 지금 합리적)

- 내용 승부처가 무거움: **Citations 25 · Cost 15 · Answer Quality 30 = 70점**.
- 껍데기(브랜딩)는 **UX 10 + Clarity 10 = 20점**.
- Streamlit은 내용 로직을 공짜로 주고 **껍데기 감성만 일부 손해** → 지금 트레이드로 유리.

## ⚠️ 대가 (정직하게)

1. **D 섹셔널 목업 100% 재현은 포기.** Streamlit 테마는 색 몇 개+폰트만. terracotta 인용·mono·라운드 브랜드 카드는 CSS 억지 주입이라 잘 깨짐 → "크림+teal 인상"까지만 목표.
2. **대회 규정 리스크(단계 0에서 먼저 해소).** 콘테스트가 "주어진 rag-starter(React) 개선"을 필수로 요구하면 프레임워크 교체가 감점/금지일 수 있음.

---

## 🎁 공짜로 얻는 것 (React 대비)

| 06_30(React) 단계 | Streamlit에서는 |
|---|---|
| 2 마크다운 렌더 (react-markdown 의존성) | `st.markdown` **내장 · 의존성 0** |
| 4 Sources 접힘 카드 | `st.expander` **내장** |
| 6 중복제출 차단 | 실행모델상 `st.chat_input` **자동 잠금** |
| 8c SSE 스트리밍 (Flask SSE + EventSource) | `st.write_stream()` **내장** |
| 8a 멀티턴 | `st.session_state.messages` |
| (인용 text 스니펫 위해 백엔드 수정) | 파이썬에서 `search` hit의 `text` **직접 접근 — 백엔드 수정 불필요** |
| Flask · CORS · `npm run build` | **전부 삭제** |

## 🤝 세션 조율 — 이 버전의 최대 장점

- Streamlit 앱은 **Anthropic을 직접 호출**하고 메타/비용을 스스로 계산 → `app.py`에 **meta 필드를 추가할 필요가 없음**.
- `SYSTEM_PROMPT`는 `app.py`에서 **읽기 전용 import**(`from app import SYSTEM_PROMPT`) → 출력 세션이 프롬프트를 개선하면 **자동 반영**, 나는 app.py를 **한 줄도 안 씀**.
- 결과: **출력 세션과 백엔드 충돌 = 제로.** (React 계획은 app.py를 4번 터치했음 → 여기선 0번.)
- 커밋은 내 파일만: `streamlit_app.py`, `.streamlit/config.toml`. `git add .` 금지.

> **🤝 검색 계약 (2026-07-01 확정, apply_best_config 세션과)**
> - **계약 A**: `indexer.search(query, index, k)`를 **인자 없이** 부르면 항상 **챔피언 설정**(bge 등)을 반환. 출력/실험 세션이 `DEFAULT_MODEL`/search를 챔피언으로 맞춤 → 내 코드(`streamlit_app.answer`)는 **한 줄도 안 고치고 자동 상속**.
> - **A1 근본해결**: 인덱스가 **자기 `embed_model`을 스스로 기록** → streamlit 재개 시 질문 임베딩이 안 맞으면 **loud 실패**(조용한 임베딩 공간 불일치 차단). *(그 세션이 구현 중)*
> - **⏸️ 일시정지**: 그 세션이 `index.pkl`을 **재색인하는 동안 내 Streamlit 작업 정지**(공유 상태 보호). 재색인 완료 신호 오면 → **서버 재시작 → 무료 카나리(§91.151 최상위?) 확인 → 재개**.
> - 이로써 단계 5의 ⚠️정합성 플래그(minilm vs bge 불일치)도 **계약 A로 해소**.

---

## 변경 대상 파일

### 신규
- `rag-starter/streamlit_app.py` — 채팅 UI 전체(검색+생성+인용+메타+Sources+스트리밍+멀티턴)
- `rag-starter/.streamlit/config.toml` — 테마(크림+teal) + 크롬 숨김
- `rag-starter/requirements.txt` 또는 기존에 `streamlit` 추가

### 읽기 전용 재사용 (수정 금지)
- `indexer.py` — `load_index`, `search` (hit에 `text` 포함)
- `backend/prompts.py` — `SYSTEM_PROMPT` **import만** (아래 E1 참고: app.py에서 추출)

> **[E1] app.py를 직접 import하지 말 것.** `app.py`는 import 시 `load_dotenv()`·`Anthropic()`·`load_index()`·`print()`를 최상단에서 실행 → Streamlit이 import하면 **인덱스 이중 로드 + Flask 딸림**. 해결: 출력 세션과 조율해 `SYSTEM_PROMPT`를 **부작용 없는 `backend/prompts.py`로 추출**(3줄), `app.py`도 거기서 import. 그러면 단일 소스 유지 + 부작용 0. *(추출 전이면 임시로 streamlit_app에 프롬프트 상수를 두되, 추출 후 즉시 import로 교체.)*

---

## 중요 규칙

- 각 단계 통과(브라우저 눈확인) 전 다음 단계로 안 넘어감.
- **app.py는 절대 수정 안 함** — import만. 프롬프트 개선은 출력 세션 몫.
- 핵심 로직만 간결히, 방어 코드 최소.
- 검증: `streamlit run streamlit_app.py` → `localhost:8501` 사용자 눈확인.
- 각 단계 끝 순서(의무): **검증 → `/simplify` → 3섹션 커밋 브리핑 → 커밋.**
- 비용 정책: 로컬 검색 무료·마음껏, 생성 API 호출만 아낀다.

---

## 🔧 엔지니어링 리뷰 반영 (2026-07-01)

- **E1 import 부작용**: app.py 직접 import 금지 → `backend/prompts.py`로 `SYSTEM_PROMPT` 추출 후 import(위 변경대상 참고).
- **E2 멀티턴 비용**: 히스토리를 "그대로" 넘기지 말 것. 과거 CONTEXT 블록 재전송 금지 → **Q/A 텍스트만 유지, 최신 질문은 새로 검색**.
- **E3 인용/텍스트**: Sources 원문은 `search`의 `hits[n-1]['text']`에서 직접. 스트리밍 후 인용 파싱은 `get_final_message()` 완성 텍스트로.
- **E4 키**: streamlit_app도 `load_dotenv()`로 `ANTHROPIC_API_KEY` 로드(수업 공유키, 커밋 금지).
- **E5 테스트**: 비용 계산은 순수함수 → 작은 유닛테스트 값어치(선택).

## 🎨 디자인 리뷰 반영 (2026-07-01)

- **D1 크롬 숨김(필수)**: config `[client] toolbarMode="minimal"` + CSS로 Deploy/햄버거/"Made with Streamlit" 제거 → 프로토타입 티 제거.
- **D2 이모지 절제**: footer `🤖🔢🔍` 나열 금지(AI 슬롭) → 은은한 텍스트 라벨·구분점, 의미있는 1개만.
- **D3 거부 카드**: `st.warning`(노랑) 대신 **커스텀 차분 컨테이너**(팔레트 충돌 회피).
- **D4 데이터는 조연**: footer는 작게·mono·저채도로 답변을 안 가리게.
- **D5 첫인상**: 빈 화면 인사 + 항공 예시질문을 **단계 3으로 당김**(심판 첫 화면).
- **D6 폰트**: 제목 세리프 + 데이터 mono를 CSS `@import` → 색만으로 부족한 "섹셔널 인상" 보완.

## 실행계획 (4단계 + 규정 확인)

### [ ] 단계 0: 대회 규정 확인 (자고 일어나 제일 먼저)

**할 일**: 콘테스트가 "rag-starter(React) 프론트 개선"을 **필수**로 요구하는지 확인.
- `rag-contest/STRATEGY.md`·대회 안내문·채점 기준 확인.
- **프레임워크 교체 허용** → 이 계획 진행.
- **금지/감점** → [`06_30_chat_ui.md`](06_30_chat_ui.md)(React) 계획으로 복귀. (이 파일은 폐기 아닌 보류.)

**통과 기준**: 허용 여부에 대한 근거 한 줄을 이 문서 실험로그에 기록.

---

### [x] 단계 1: Streamlit 채팅 골격 (검색 + 생성 + 인용 + 마크다운) ✅

> 완료(2026-07-01): 마크다운·`[1]` 인용·멀티턴 브라우저 확인. `/simplify` 4각도 통과(MAX_TOKENS 상수화 1건 적용).
> **참고**: 다크모드 검정 이슈 때문에 **단계 3의 `config.toml` 테마 색만 앞당겨** 적용함(크림+teal 고정 + 크롬 숨김 + 파일감시기 off). terracotta 인용·폰트 등 나머지 CSS는 단계 3 그대로 남음.

**신규 파일**: `rag-starter/streamlit_app.py`

**변경 내용**:
- `from indexer import load_index, search`; `from app import SYSTEM_PROMPT, _build_citations`.
- 인덱스는 `@st.cache_resource`로 1회 로드.
- `st.session_state.messages`에 대화 저장, `st.chat_message`로 렌더(assistant는 `st.markdown` → 굵기·목록·§ 자동).
- `st.chat_input` 제출 → `search(q, index, k=5)` → CONTEXT 조립 → `client.messages.create(model, system=SYSTEM_PROMPT, ...)` → `_build_citations`로 인용.
- **영어 전용**(이중언어 없음 — 대회 토큰 절약, 심판은 EN만).

**통과 기준**:
- `streamlit run` → 질문하면 마크다운 서식으로 답 + `[n]` 인용 표시.
- 재실행(rerun) 후에도 이전 대화 유지(session_state).

**검증 통과 시 커밋**: `feat(streamlit): chat skeleton reusing indexer + app SYSTEM_PROMPT`

---

### [ ] 단계 2: 메타 footer + $비용 + Sources expander + 거부 카드

**변경 파일**: `rag-starter/streamlit_app.py`

**변경 내용**:
- 응답 `resp.usage`에서 `input_tokens`/`output_tokens`, `resp.model` → **비용 계산**.
  - `PRICES = {"claude-sonnet-4-6": (3, 15)}` (in/out $/M). 모델 키로 조회(하드코딩 회피).
  - footer 칩(`st.caption`, mono 느낌): 🤖 모델 · 🔢 tok_in/out · **~$cost** · 🔍 hybrid·K5.
- **Sources 접힘 카드**: 각 citation을 `st.expander(label)` → 안에 그 hit의 **`text` 스니펫**(파이썬에서 `search` 결과 직접 접근 → 백엔드 수정 불필요).
- **거부 카드**: `citations`가 비면 `st.warning("출처에 없어 답변 못 함")` (⑧ 리뷰: 문자열 매칭 말고 **빈 인용**으로 판정).
- **[리뷰 ②]** grounding 배지 없음(소비처 없어서 계산 안 함).

**통과 기준**:
- 답 아래 모델+토큰+$+검색 칩이 실제 값으로.
- § expander 클릭 → 근거 원문 펼침.
- 범위밖 질문("best restaurant near the airport?") → 거부 카드.

**검증 통과 시 커밋**: `feat(streamlit): meta footer (cost) + expandable sources + refusal card`

---

### [ ] 단계 3: 테마 정돈 (크림+teal 인상)

**신규 파일**: `rag-starter/.streamlit/config.toml`

**참조 목업**: [`mockups/chat_ui_streamlit.html`](../mockups/chat_ui_streamlit.html) (확정본) — 색·레이아웃·질감의 기준.

**변경 내용**:
- `[theme]` primaryColor=teal `#2e7d6b`, backgroundColor=크림 `#ece5d6`, secondaryBackgroundColor=paper `#fbf8f1`, font.
- 가능한 선의 최소 CSS 주입으로 **인용=terracotta `#b5651d`**, 데이터 칩=mono. (깨지면 색만이라도.)
- **[가독성 결정 2026-07-01] 색은 "중요"가 아니라 "종류"로**: terracotta는 **규정 참조 전용**(§조항·인용 `[n]`)만. 핵심 수치("**30 minutes**")는 색 대신 **굵게**. 나머지 본문 검정 → 색이 신호가 됨(하이라이터 수프 방지). 구현: 답변 렌더 후 `§\d+\.\d+`·`\[\d+\]`를 정규식으로 terracotta span 래핑(모델에 HTML 안 시킴 = unsafe_allow_html 최소).
- **D5 첫인상**: 빈 화면 인사 + 항공 예시질문(목업엔 미포함 상태지만 계획엔 남김).
- **대가 인정**: 목업 100% 재현 아님 → "크림+teal 섹셔널 인상"까지가 목표.

> **[가독성 — 불릿/번호는 프롬프트 = 출력 세션 담당]** 답변을 불릿·번호로 구조화하는 건 `SYSTEM_PROMPT`가 시키는 일(내 `st.markdown`은 이미 렌더함). `SYSTEM_PROMPT`는 출력 세션 소유(E1)라, "다항목 답변은 불릿/번호로 정리" 지시는 **출력 세션에 요청**. UI는 표시만.

**통과 기준**:
- 전체 화면이 크림 배경 + teal 액센트로 정돈된 인상.
- 좁은 폭에서도 안 깨짐.

**검증 통과 시 커밋**: `style(streamlit): cream + teal sectional theme`

---

### [ ] 단계 4: UX 3종 + 멀티턴 (스트리밍·검색먼저·후속칩)

**변경 파일**: `rag-starter/streamlit_app.py`

**변경 내용**:
- **① 검색먼저**: 생성 전 `st.status("🔍 §91.151·§91.167 찾음 · 0.1s")`로 즉시 반응.
- **② 스트리밍**: `with client.messages.stream(...) as s: st.write_stream(s.text_stream)`. usage는 스트림 종료 후 `s.get_final_message().usage`로 받아 메타 채움(**①계약: 메타는 끝에 도착** — Streamlit이 자연스럽게 처리).
- **③ 후속질문 칩**: 답 아래 `st.button` 줄. 빈 화면엔 예시 질문 인사.
- **멀티턴**: `st.session_state.messages` 히스토리를 `client.messages`에 그대로 전달 → "그럼 야간엔?" 후속 이해. (지금 app.py는 단일턴이지만 여기선 히스토리를 직접 실어 보냄.)

**통과 기준**:
- 검색먼저 줄 → 스트리밍으로 답 뜸 → 후속 칩. 후속질문이 이전 문맥 유지.
- 단일턴도 정상.

**검증 통과 시 커밋**: `feat(streamlit): streaming + retrieval-first status + follow-up chips + multi-turn`

---

### [ ] 단계 5: 리더보드 사이드바 (실험 rigor 전시) [사용자 요청]

> 목적: `experiments/leaderboard.md`(retrieval 그리드 실험 결과)를 UI에 걸어 심판에게 "이 검색설정은 근거 있는 선택"임을 보여줌. footer의 `hybrid·K5` 숫자에 신뢰를 줌.

**변경 파일**: `rag-starter/streamlit_app.py`

**변경 내용 (내 의견 반영)**:
- **탑바 말고 사이드바**: `st.sidebar` + `st.expander("🏆 Retrieval leaderboard", expanded=False)`. 탑바는 채팅을 아래로 밀고 항상 보여 산만 → 사이드바는 접혀 있어 안 방해, 궁금한 심판만 펼침.
- **요약 먼저**: 58줄 전체 말고 **추천 한 줄 + 상위 ~5행**만. "전체 보기"는 링크/expander.
- 파일 읽기: `Path("../experiments/leaderboard.md")` (상대경로 주의 — 실행 위치 rag-starter 기준) 읽어 `st.markdown`.

**⚠️ 정합성 플래그 (별개 todo 연동)**: 리더보드 추천은 **section/bge/vector/K5**인데, 지금 앱은 `indexer` 기본값 **minilm/vector/K5**로 돌아감(챔피언 embed=bge 아님). footer가 "search"를 정직하게 표시하려면 앱이 **챔피언 설정으로 실행**돼야 함 → [`07_01_apply_best_config.md`](07_01_apply_best_config.md) 일. 그 전엔 리더보드와 실제 실행이 불일치하니, 사이드바에 "현재 실행 설정"도 같이 표기 권장.

**통과 기준**:
- 사이드바 펼치면 리더보드 요약+상위행 표시. 접힌 기본 상태에선 채팅 안 방해.
- `npm/build` 없음(streamlit). 파일 없으면 사이드바 숨김(방어 1줄).

**검증 통과 시 커밋**: `feat(streamlit): leaderboard sidebar (retrieval experiment results)`

---

## React ↔ Streamlit 매핑 (원본 추적용)

| 06_30 React 단계 | 이 문서 |
|---|---|
| 1 백엔드 meta | (불필요 — Streamlit이 직접 계산) |
| 2 마크다운 | 단계 1 |
| 3 메타패널+$ | 단계 2 |
| 4 Sources+거부 | 단계 2 |
| 5 디자인 | 단계 3 |
| 6 중복제출 | (거의 공짜 — 실행모델) |
| 7 이중언어 | 컷(영어 전용) |
| 8 UX 3종+멀티턴 | 단계 4 |

---

## 실험 로그

(작업 중 아래에 누적)

- _(단계 0: 대회 규정 — 프레임워크 교체 허용 여부 근거를 여기 기록)_

---

## GSTACK REVIEW REPORT

| Run | Status | Findings | 반영 |
|---|---|---|---|
| plan-eng-review | DONE | E1~E5 (5) | 전부 문서 반영 |
| plan-design-review | DONE | D1~D6 (6) | 전부 문서 반영 |

**주요 결정/미해결**
- **E1(코디네이션 필요)**: `SYSTEM_PROMPT`를 `backend/prompts.py`로 추출 — 출력 세션과 합의 필요(app.py 소유권). 추출 전엔 임시 상수 → 추출 후 import 교체.
- **단계 0 게이트**: 대회가 rag-starter(React) 개선을 필수로 요구하면 이 계획 전체 보류 → React(06_30)로 복귀.

**VERDICT**: 계획 승인 가능. 실행 전 딱 두 개만 확정 — ① 대회 규정(단계 0), ② prompts.py 추출을 출력 세션과 조율.

**UNRESOLVED DECISIONS:**
- 대회 프레임워크 교체 허용 여부 (단계 0에서 확인)
- `backend/prompts.py` 추출 여부 (출력 세션 조율)
