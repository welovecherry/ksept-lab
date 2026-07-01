# DESIGN.md — FAA RAG Chat

> 디자인 시스템 원천. 채팅 UI(`rag-starter/frontend`)의 색·타이포·컴포넌트 기준.
> 목업: `~/.gstack/projects/welovecherry-ksept-lab/designs/chat_ui_D_bilingual.html`

## 기억에 남길 한 가지 (memorable thing)

> "이건 **믿을 수 있고 친근한 항공 도우미**다." — 항공 섹셔널 차트처럼 따뜻하되, 근거(§)와 비용($)이 투명해 신뢰가 간다.

## 미학 논지 (aesthetic thesis)

**섹셔널 차트(sectional chart)** 방향 — 항공 지도의 크림 배경 + 차분한 teal. 딱딱한 법전이 아니라 *조종사 옆의 친근한 참조 도구*. 따뜻하지만 정밀하다.

## 색 (tokens)

| 역할 | 값 | 용도 |
|---|---|---|
| bg | `#ece5d6` (크림) | 페이지 배경 |
| paper / paper2 | `#fbf8f1` / `#f1ebdd` | 카드·footer |
| line | `#ddd3bf` | 테두리 |
| ink / ink-strong | `#2b2a26` / `#161512` | 본문·강조 텍스트 |
| muted | `#7a7466` | 보조 텍스트·메타 |
| **teal (accent)** | `#2e7d6b` | 버튼·링크·질문 버블·약어풀이 |
| teal-soft | `#e3efe9` | 한국어 패널 배경 |
| **terracotta (citation)** | `#b5651d` | **조항번호·인용 전용** (눈이 근거로 가게) |
| good | `#3d8b5f` | 근거 배지 |

> 규칙: **terracotta는 인용(§)에만.** 색이 "여기가 근거다"를 말하게.

## 타이포

- 본문: sans (`Segoe UI`/system). 한국어도 동일 sans.
- **데이터·조항번호·메타: mono** (`ui-monospace`) — 토큰·§가 *계기 판독값*처럼 정밀해 보이게.
- 라운드 카드(반경 14~18px), 넉넉한 여백.

## 컴포넌트

- **질문 버블**: 우측, teal 배경/흰 글씨, 반경 `16 16 5 16`.
- **답변 카드**: paper 배경, 마크다운 렌더(굵기·목록). 조항=terracotta mono, 약어풀이 `VFR (Visual Flight Rules)`=teal.
- **이중언어**: 답변 카드 안에서 **설명 문장만** 좌우 분할 — 🇺🇸 왼쪽 / 🇰🇷 오른쪽(teal-soft 배경). 조항·비용·근거·Sources는 *언어무관 사실*이라 아래에 **공유(한 번만)**. 좁은 화면(<640px)은 위아래로.
- **헤더 언어 토글**: `EN + 한` / `EN` — 대회 심판용은 순수 영어, 사용자용은 이중언어.
- **근거 배지**: `✓ 근거 확인 · all claims cited` (good 색 pill) — 인용 신뢰 신호(25점).
- **메타 칩(공유 footer)**: `● 모델` · `🔢 토큰 in/out · ~$비용` · `🔍 방식·K`. mono, 담백.
- **Sources 카드**: `[1] §91.151 (Part 91)` terracotta, 클릭 시 근거 원문(mono) 펼침.
- **입력창**: 흰 배경, teal 전송 버튼. 요청 중엔 버튼 잠금(스피너).

## 안티-슬롭 (금지)

보라 그라데이션, 3열 아이콘 그리드, 가운데 정렬 히어로, 장식용 블롭, 과한 그림자. 정보는 *필요한 판독값만* — 거부 카드처럼 가끔 쓰는 상태는 해당 상황에서만 나타난다(평상시 화면엔 없음).
