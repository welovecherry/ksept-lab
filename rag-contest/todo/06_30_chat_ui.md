# 채팅 UI 개선 — 예쁜 서식 + 근거·비용 메타 (대회 UX·인용·Cost 배점)

> 🛩️ 대회가 채점하는 **채팅 화면**(rag-starter 프론트)을 개선. 실험 대시보드가 아니라 *심판이 실제로 보는 UI*. 배점: UX 10 · Clarity 10 · Citations 25 · Cost 15 · Robustness 10.
> 하네스(검색 최적화)는 → [`06_30_act1_harness.md`](06_30_act1_harness.md). 이 문서는 **답변을 보여주는 껍데기**.

## 사용자 시나리오 (가장 먼저 읽힌다)

- **누가**: 홍정민 + 대회 심판. FAA 질문을 채팅에 넣고 답을 보는 사람.
- **언제**: 질문 입력 후, 답변과 그 근거·비용을 한눈에 확인할 때.
- **어떻게**:
  1. 질문 입력 (예: "day VFR 연료 규정?")
  2. 답변이 **깔끔한 서식**으로 뜸 (문단·굵기·목록·조항번호 강조 — 마크다운 렌더). 원하면 **좌우 이중언어**(🇺🇸\|🇰🇷) — *설명 문장만* 나뉨.
  3. 답변 아래 **공유 footer(사실은 한 번만)**: 🤖 모델 · 🔢 토큰 + **~$비용** · 🔍 검색(방식·K) · **Sources 카드**(§ 클릭 시 근거 펼침). *(근거 배지는 정신없어 제외 — 인용 [n] 자체가 근거 신호)*
  4. 헤더 **언어 토글** `EN + 한` / `EN` — 대회 심판은 순수 영어, 사용자는 이중언어.
  5. **UX**: 검색먼저 표시(0.1s) → 답변 **스트리밍**(체감 속도) → 답 아래 **후속질문 칩**. 후속질문은 이전 문맥 유지.
- **결과**: 답이 *전문적·친근*(UX 10), *조항 인용 명확*(인용 25), *$비용 투명*(Cost 15)하게 드러남.
- **범위밖/실패**: "근처 맛집?" → "출처에 없음" 거부(환각 없음, Robustness) — *그 상황에서만* 표시(평상시 화면엔 없음).

> 비유: 항공 **섹셔널 차트** 옆의 친근한 참조 카드 — 따뜻하되 근거(§)·비용($)이 투명해 신뢰가 간다.
> **확정 디자인**: D 섹셔널(크림+teal), 인용=terracotta, 데이터=mono. 시스템 원천 → [`DESIGN.md`](../DESIGN.md), 목업 → `~/.gstack/.../designs/chat_ui_D_bilingual.html`.

## 배경

- 스타터 프론트(`App.jsx`)는 답변을 **날것 텍스트**로 출력(마크다운 안 먹음), Sources는 `[n] 라벨`만. 못생기고 정보가 빈약.
- 백엔드(`app.py`)는 `{reply, citations}`만 반환 — **모델·토큰·검색설정 메타가 없음**. 메타 패널을 그리려면 백엔드가 먼저 실어 보내야 함.
- 단계 5(파이프라인)에서 `§91.151 (Part 91)` 인용 label은 이미 내려옴 → 여기선 *예쁘게 그리기*.

## 목표

1. 답변을 **마크다운 렌더**로 읽기 편하게 출력.
2. 응답에 **메타(model·tokens_in/out·retrieval)** 를 실어, 프론트에 **메타 패널** 표시.
3. **Sources 카드**(조항 클릭 → 근거 펼침) + **범위밖 거부 카드**.
4. **[DESIGN.md] D 섹셔널 디자인 시스템** 적용(크림+teal, 인용=terracotta, 데이터=mono).
5. **요청 처리 중(~10초) 추가 제출 차단** — 더블클릭으로 API 중복 호출·비용 낭비 방지.
6. **$ 비용** 표시(토큰 옆 `~$0.006`) — Cost 15 시각화. *(근거 배지는 제외 — 정신없음, 인용 [n]이 근거)*
7. **좌우 이중언어**(EN\|한) + 헤더 언어 토글 — 설명만 분할, 사실(§·비용·Sources)은 공유.
8. **UX 3종**(UX 10): ①검색먼저 표시 ②답변 스트리밍(체감속도·first-token) ③후속질문 칩 + 멀티턴 문맥.

> 📌 **범위 밖(생성 단계 H5/실험6)**: *답변이 짧다 → 완전성·종합 부족*은 **화면이 아니라 생성 프롬프트** 문제(Answer Quality 30점). "day+night 모두·예외·여러 조항 종합" 지시를 프롬프트에 넣는 건 생성 단계에서. 한국어 번역도 생성이 함께 내보내면 프론트는 표시만.

## 변경 대상 파일

### 수정
- `rag-starter/backend/app.py` — `/api/chat` 응답에 `meta{model, tokens_in, tokens_out, cost_usd, retrieval{method,k}, grounding{n_claims,n_cited}}` 추가
- `rag-starter/frontend/src/App.jsx` — 마크다운 렌더 · 메타 패널(+배지+$) · Sources 카드 · 이중언어(EN\|한)+토글
- `rag-starter/frontend/src/index.css` — **DESIGN.md D 섹셔널 시스템**(크림+teal, terracotta 인용, mono 데이터)
- `rag-starter/frontend/package.json` — `react-markdown` 의존성 추가

### 참조
- `DESIGN.md` — 색·타이포·컴포넌트 원천(이번에 확정). index.css는 이걸 구현.

---

## 중요 규칙

- 각 단계를 통과(브라우저 눈확인)하지 않으면 다음 단계로 넘어가지 않는다.
- **기존 동작 보호**: 답변·인용이 계속 나와야 함(regression 확인). 백엔드 응답에 필드 *추가*만, 기존 `reply`/`citations` 유지.
- 핵심 로직만 간결하게, 방어 코드 최소화.
- **검증은 브라우저 눈확인 중심**: 자동 브라우저가 로컬 dev서버(격리)에 못 닿음 → `http://localhost:5173`을 사용자가 직접 확인. 코드 레벨은 `npm run build`(vite) 에러 0로 보강.
- 각 단계 끝 순서(의무): **검증 → `/simplify` → 커밋 브리핑(3섹션) → 커밋**.

---

## 실행계획

### 각 단계 요약 (쉽게 + UI 변화)

- **단계 1 — 백엔드 메타 실어보내기**: 답변 만들 때 쓴 *모델·토큰수·검색설정*을 응답에 같이 넣는다.
  UI: 변화 없음 (데이터만 준비 — 메타 패널의 연료).
- **단계 2 — 답변 마크다운 렌더**: 날것 텍스트를 *굵기·목록·문단* 있는 서식으로 그린다.
  UI: **답변이 깔끔해짐** (읽기 편한 출력).
- **단계 3 — 메타 패널 + $비용**: 답변 아래 🤖모델 · 🔢토큰+~$비용 · 🔍검색 칩 (근거배지 제외).
  UI: **답변 밑에 담백한 비용·검색 칩 줄** (Cost15 시각화).
- **단계 4 — Sources 카드 + 거부 카드**: 조항 클릭 시 근거 펼침, 범위밖은 차분한 거부 카드.
  UI: **출처가 접힌 카드로**, 범위밖 질문은 안내 카드.
- **단계 5 — D 섹셔널 디자인 적용**: [DESIGN.md] 크림+teal·terracotta 인용·mono 데이터로 전체 정돈.
  UI: **전체가 목업처럼 예뻐짐** (대회 제출 수준).
- **단계 6 — 로딩 중 중복 제출 차단**: 답 기다리는 동안 전송 버튼·입력 잠그고 로딩 표시.
  UI: **전송 중엔 버튼 회색+스피너**, 두 번 눌러도 요청 1건.
- **단계 7 — 좌우 이중언어 + 토글**: 설명 문장만 🇺🇸\|🇰🇷 좌우로, 사실(§·비용·Sources)은 아래 공유. 헤더 `EN+한`/`EN` 토글.
  UI: **답변이 두 언어 나란히**, 토글로 순수 영어 전환.
- **단계 8 — UX 3종**: 검색먼저 표시 · 답변 스트리밍(first-token) · 후속질문 칩 + 멀티턴 문맥.
  UI: **답이 즉시 뜨기 시작**(스트리밍), 아래 후속 칩. 후속질문이 문맥 유지.

```
UI 진행 한눈
─────────────────────────────────────────────
지금:   you: day VFR 연료?
        assistant: **§ 91.151(a)(1)**... 30 minutes [1]   ← 마크다운 날것
        Sources: [1] §91.151 (Part 91)
─────────────────────────────────────────────
단계2:  답변이 굵기·문단 살아난 깔끔한 서식으로
단계3:  ┌ 답변 카드 ───────────────────────┐
        │ Day VFR fuel: 30 minutes …       │
        │ 🤖 sonnet-4-6  🔢 1,240/180  🔍 hybrid·K5 │ ← 메타 패널
        └──────────────────────────────────┘
단계4:  Sources ▸ §91.151 (Part 91)  [클릭→근거 원문 펼침]
        범위밖 질문 → ⚠️ "출처에 없어 답변 못 함" 카드
단계5:  전체 버블·색·여백 정돈 → 대회 제출 화면
─────────────────────────────────────────────
```

---

### [ ] 단계 1: 백엔드가 답변 메타를 응답에 실어보내기

**변경 파일**: `rag-starter/backend/app.py`

**변경 내용**:
- `/api/chat`에서 `resp.usage.input_tokens`·`output_tokens`, `model`, 검색설정(`method`,`k`)을 모아 응답에 `meta` 추가.
- **`cost_usd`**: 토큰 × 모델 단가(sonnet in ~$3/M, out ~$15/M)로 계산해 실어보냄(Cost 배지용).
- **`grounding{n_claims,n_cited}`**: 답변의 `[n]` 인용 수 / 문장 수 등으로 "모든 주장 인용됨" 판정 근거(근거 배지용). (H4 인용검증기 붙으면 verified로 승급)
- 기존 `reply`·`citations`는 그대로 두고 **필드 추가만** (regression 방지).

**통과 기준**:
- `curl … /api/chat …` → `meta.model`·`meta.tokens_out`·`meta.cost_usd`·`meta.retrieval`·`meta.grounding` 존재, `reply`·`citations` 그대로.
- 기존 채팅 여전히 동작(regression).

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(backend): return answer meta (model, token usage, retrieval config)`

---

### [ ] 단계 2: 답변 마크다운 렌더 (사람이 읽기 편하게)

**변경 파일**: `rag-starter/frontend/src/App.jsx`, `package.json`

**변경 내용**:
- `react-markdown` 추가, 답변 텍스트를 `<ReactMarkdown>`으로 렌더 (굵기·목록·문단·인라인코드).
- 사용자 메시지는 평문 유지(마크다운 렌더는 assistant 답변만).

**통과 기준**:
- `npm run build` 에러 0.
- 브라우저(`localhost:5173`)에서 답변의 `**§ 91.151**`이 **굵게**, 목록이 들여쓰기로 보임(날것 아님).
- 기존 답변·Sources 계속 표시(regression).

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(frontend): render answer markdown for readable output`

---

### [ ] 단계 3: 메타 패널 + $ 비용

**변경 파일**: `rag-starter/frontend/src/App.jsx`, `src/index.css`

**변경 내용**:
- assistant 답변 아래 **공유 footer**(mono 칩, 담백): 🤖`meta.model` · 🔢`tokens_in/out` + **`~$cost_usd`** · 🔍`retrieval.method·K`.
- ~~근거 배지~~ 제외(사용자 피드백: 정신없음). 근거 신호는 인용 `[n]` 자체로 충분.
- `meta` 없으면 패널 숨김(구버전/에러 방어 1줄).

**통과 기준**:
- `npm run build` 에러 0.
- 브라우저에서 답변 아래에 **모델 + 토큰/$ + 검색**이 실제 값으로 보임.

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(frontend): meta panel (model, tokens, cost estimate, retrieval)`

---

### [ ] 단계 4: Sources 카드 + 범위밖 거부 카드

**변경 파일**: `rag-starter/frontend/src/App.jsx`, `src/index.css`

**변경 내용**:
- Sources를 접힌 카드로: `§91.151 (Part 91)` 클릭 → 그 인용의 근거 원문(청크 text) 펼침. (백엔드 citation에 `text` 스니펫 추가 필요 시 소폭 수정)
- `citations`가 비고 답이 "출처에 없음"류면 **차분한 거부 카드**(⚠️ 아이콘 + 안내문)로 표시.

**통과 기준**:
- 브라우저에서 조항 클릭 → 근거 펼침/접힘.
- 범위밖 질문("best restaurant near the airport?") → 거부 카드(환각 없음).
- `npm run build` 에러 0.

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(frontend): expandable source cards + out-of-scope refusal card`

---

### [ ] 단계 5: D 섹셔널 디자인 시스템 적용 ([DESIGN.md])

**변경 파일**: `rag-starter/frontend/src/index.css`

**변경 내용**:
- [`DESIGN.md`](../DESIGN.md) 토큰 구현: bg `#ece5d6`(크림)·paper `#fbf8f1`·teal `#2e7d6b`(액센트)·**terracotta `#b5651d`(인용 전용)**·mono(데이터). 라운드 카드·넉넉한 여백.
- 목업(`chat_ui_D_bilingual.html`)을 참조 구현으로.

**통과 기준**:
- 브라우저 전체 화면이 **목업과 동일한 인상**(크림+teal, 인용=terracotta).
- 데스크톱·좁은 폭 모두 깨짐 없음.

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `style(frontend): apply D sectional design system (cream + teal, terracotta citations)`

---

### [ ] 단계 6: 로딩 중 중복 제출 차단 [사용자 요청 — 실제 버그]

> 배경: 답변이 ~10초 걸리는데 그 사이 전송을 2번 누르면 API가 2번 호출됨(비용 낭비·중복 답변). UX + Cost 둘 다 관련.

**변경 파일**: `rag-starter/frontend/src/App.jsx`, `src/index.css`(스피너 소폭)

**변경 내용**:
- `isLoading` 상태: 요청 시작 시 `true`, 응답/에러 시 `false`.
- `isLoading`이면 **전송 버튼·입력·Enter 제출 비활성화**, 이미 요청 중이면 submit 무시(가드 1줄).
- 로딩 인디케이터(버튼 스피너 또는 "…") 표시.

**통과 기준**:
- 브라우저에서 질문 전송 → 답 오기 전 버튼 회색, **두 번 눌러도 Network 탭에 `/api/chat` 요청 1건**(중복 없음).
- 응답 후 버튼 다시 활성화. 에러 시에도 잠금 해제(안 멈춤).
- `npm run build` 에러 0.

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `fix(frontend): disable submit while a request is in flight (prevent double-send)`

---

### [ ] 단계 7: 좌우 이중언어 (EN|한) + 언어 토글

> 목적: 사용자는 두 언어를 한눈에, 심판은 순수 영어로. **설명 문장만** 나누고 사실(§·비용·근거·Sources)은 공유(한 번만).

**변경 파일**: `rag-starter/backend/app.py`(한국어 번역 동반 반환), `rag-starter/frontend/src/App.jsx`, `src/index.css`

**변경 내용**:
- **번역 출처(택1)**: (A) 생성이 답변을 EN+KO로 함께 내보냄(프롬프트에 "answer in English, then a Korean translation" — 생성단계와 연동, 정확도↑) / (B) 프론트에서 별도 번역. **권장 A** — 답변 근거·인용이 번역에도 일관.
- 답변 카드 안 **설명 문장만** 2열 그리드(🇺🇸\|🇰🇷, 한국어는 teal-soft 배경). 좁은 화면(<640px)은 위아래.
- footer(근거·비용·검색·Sources)는 **공유(한 번만)** — 언어무관 사실.
- 헤더 언어 토글 `EN + 한` / `EN`. 기본은 취향(대회 제출은 `EN` 권장).

**통과 기준**:
- 브라우저에서 답변이 EN\|한 좌우로, §·비용·Sources는 아래 1회만.
- 토글로 `EN` 선택 시 한국어 열 사라짐.
- 좁은 폭에서 위아래로 안 깨짐. `npm run build` 에러 0.

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(frontend): bilingual EN|KO answer with language toggle (shared facts)`

---

### [ ] 단계 8: UX 3종 (반응성·일관성·친절) — UX 10점

> 목업: `~/.gstack/.../designs/chat_ui_D_ux.html`. 세 아이디어가 UX 세 하위항목(속도·멀티턴·말투)을 각각 겨냥.

**UI 파트 (이 문서)** — `App.jsx`, `index.css`:
- **① 검색먼저 표시**: 답 생성 전에 `🔍 §91.151·§91.167 찾음 · 0.1s` 줄 → 즉시 반응.
- **② 스트리밍 렌더**: 답변을 토큰 단위로 그려 커서 표시. 메타에 `⚡ first token 0.4s`(전체시간 대신 첫글자 시간 — 느려 보이지 않게).
- **③ 후속질문 칩**: 답 아래 `🔗 IFR fuel?` 류 클릭 칩. 빈 화면엔 예시 질문 인사.

**백엔드/생성 파트 (의존성, 일부는 H5)** — `app.py`:
- **멀티턴 문맥**: `/api/chat`가 이전 대화(messages 히스토리)를 모델에 전달 → "그럼 야간엔?" 후속질문 이해. *(지금은 현재 메시지만 보냄 = 실제 구멍)*
- **SSE 스트리밍**: `client.messages.stream(...)` + 프론트 EventSource. (②의 백엔드)
- 후속질문 칩 문구는 생성이 함께 제안하면 정확도↑(H5 연동, 선택).

**통과 기준**:
- 브라우저: 검색먼저 줄 → 스트리밍으로 답 뜸 → 후속 칩. 후속질문이 이전 문맥 유지.
- `npm run build` 에러 0. 기존 단일턴도 정상(regression).

**마지막 — /simplify 후 커밋 (의무)**: 검증 → `/simplify` → 3섹션 브리핑 → 커밋.

**검증 통과 시 커밋**: `feat(chat): streaming + retrieval-first + follow-up chips + multi-turn context`

---

## 실험 로그

(작업 중 아래에 누적 — 예상과 다른 결과, 결정 변경 등)

- _(예: react-markdown이 §기호를 이스케이프 → rehype 설정으로 보정)_
