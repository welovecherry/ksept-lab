# 진도 한눈에

- **1부 (슬라이드 1~8):** hello-world 앱 ✅ — 실행 + 도커 배포 + React 동작 퀴즈
- **2부 (슬라이드 9~24):** LLM 앱 — 진행 중
  1. 9~12 개념 ✅
  2. 10 단계별 심화 ✅
  3. 13 첫 API 호출 ✅
  4. 15·17·18 챗 앱 코드 정리 ✅
  5. **다음: 직접 만들어 돌려보기**

@slide-9

## LLM 개념 요약 (9~12)

### LLM이란
- **Large Language Model** = 초강력 자동완성기. **다음 토큰**(단어/단어조각)을 앞 내용 보고 예측.
- 한 번에 한 토큰씩, 매 토큰은 앞의 모든 것(프롬프트 + 시스템 + 지금까지 출력)에 좌우.
- **컨텍스트가 답을 바꾼다.** `Mary had a little ___` → 보통 `lamb`, "재밌게" 맥락 → `llama`.

### 잘하는 것 / 못하는 것
**잘함:** 글·코드·요약 생성, 번역, 정보 추출, 이미지 읽기, 단계적 추론.
**못함(도움 없이는):** 이전 대화 기억, 최신 정보, 실제 행동, 코드 실행, 자기 답 검증.
**📌 환각:** 모르면서 그럴듯하게 지어냄 → **믿을 자료(컨텍스트)를 주면** 품질↑.

### 챗 앱 vs 모델 API
- **챗 앱**(claude.ai): 완성품, 기억·UI 다 해줌, 구독.
- **모델 API**(Anthropic): 날것, **매 요청마다 히스토리 전송**, 토큰당 과금.
- 비유: 챗앱 = 완성차, API = 엔진만. **우리는 엔진으로 앱을 만든다.**

@slide-10

## LLM이란? — 단계별로

### 1단계 · 토큰
- 토큰 = 단어 또는 **단어 조각**. `unbelievable` → `un`+`believ`+`able`.
- 영어 기준 **1토큰 ≈ 0.75단어**. 과금 단위.

### 2단계 · 다음 토큰 예측
- 본질은 하나: 지금까지 토큰 → **다음 토큰 확률** → 하나 뽑고 반복(autoregressive).
- 비유: **세계 최강 끝말잇기.**

### 3단계 · 학습
- 수조 개 토큰으로 "다음 토큰 맞히기" 반복 → **파라미터**(수천억 다이얼) 조정.

### 4단계 · 컨텍스트가 답을 바꾼다
- 다음 토큰 확률은 **앞 내용에 전적 의존**. lamb vs llama.

### 5단계 · 컨텍스트 윈도우
- 한 번에 볼 수 있는 토큰 수 **상한**. 넘으면 앞부분 못 봄 → **매번 히스토리 재전송** 이유.

### 6단계 · 확률적
- 확률에서 **뽑기** → 매번 조금 다름(`temperature`). 창의성이자 환각의 원천.

**한 줄 요약:** LLM = **토큰 단위로 다음을 예측하는 거대한 확률 엔진.**

@slide-13

## 첫 API 호출 — 코드 해부

비유: Claude에게 **전화 한 통**.

```python
from anthropic import Anthropic
client = Anthropic()              # .env의 ANTHROPIC_API_KEY 자동 로드
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    system="You are a tax advisor...",
    messages=[{"role": "user", "content": "..."}],
)
print(resp.content[0].text)
```

### 재료 4개
1. **model** — 어느 Claude.
2. **max_tokens** — 답 길이 상한(**필수**). 끊기면 올린다.
3. **system** — 역할·규칙.
4. **messages** — 실제 대화. `{"role":"user","content":...}`.

### 꼭 기억
- 응답은 **블록 리스트** → `resp.content[0].text`.
- `messages`가 리스트인 이유: stateless → **매번 전체 대화 재전송**.

@slide-15

## 큰 그림 — 챗 앱은 hello-world와 똑같다

- "고정된 답" 자리에 **Claude 호출**이 들어갈 뿐.
- 흐름: **React(5173) → Flask `/api/chat` → Claude API → 다시 React.**
- 핵심 파일 2개:
  1. `backend/app.py` — 엔드포인트 하나, Claude 호출 (~15줄)
  2. `frontend/src/App.jsx` — 입력칸 + 메시지 목록 (~30줄)

@slide-17

## 백엔드 해설

```python
@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]          # 1. 프론트가 보낸 메시지
    resp = client.messages.create(                  # 2. 슬라이드 13의 그 호출
        model="claude-sonnet-4-6", max_tokens=512,
        system="You are a helpful assistant. Keep replies brief.",
        messages=[{"role": "user", "content": user_message}],
    )
    return jsonify({"reply": resp.content[0].text}) # 3. 답을 프론트로
```

### 3단계
1. `request.json["message"]` — POST body에서 사용자 메시지 꺼냄.
2. `messages.create(...)` — **슬라이드 13 호출 그대로.** 고정 답 대신 Claude 답.
3. `jsonify({"reply": ...})` — hello-world의 `{"message": ...}` 자리.

**⚠️ 모델 ID:** 슬라이드는 `claude-sonnet-4-6`. 현재 최신 = **`claude-opus-4-8`**(최강·기본 추천) / `claude-sonnet-4-6`(균형) / `claude-haiku-4-5`(빠름). 직접 만들 땐 opus-4-8 권장.

@slide-18

## 프론트 해설

```jsx
async function send(e) {
  e.preventDefault()
  if (!input.trim()) return
  setMessages(m => [...m, { role: 'user', text: input }])   // 1. 내 말 먼저
  setInput('')
  const res = await fetch('/api/chat', {                    // 2. 백엔드로 POST
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: input }),
  })
  const data = await res.json()
  setMessages(m => [...m, { role: 'assistant', text: data.reply }])  // 3. 답 추가
}
```

### 3단계
1. 보내자마자 **내 메시지를 먼저** 표시(낙관적 업데이트).
2. `fetch('/api/chat', POST)` — GET과 달리 **데이터를 body에 실어** 보냄.
3. 답이 오면 `assistant`로 추가 → 대화가 쌓임.
