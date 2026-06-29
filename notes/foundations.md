# Foundations — 내 학습 노트

이 모듈에서 배운 것을 단계별로 정리한다.

## 진도 한눈에
- **1부 (슬라이드 1~8):** hello-world 앱 ✅ — 실행 + 도커 배포 + React 동작 퀴즈
- **2부 (슬라이드 9~24):** LLM 앱 — 진행 중
  1. 9~12 개념 ✅
  2. 10 단계별 심화 ✅
  3. 13 첫 API 호출 ✅
  4. **14~18 챗 앱 만들기 ← 지금 정리 중**

# 9~12 · LLM 개념

## LLM이란
- **Large Language Model** = 초강력 자동완성기. **다음 토큰**(단어/단어조각)을 앞 내용 보고 예측한다.
- 한 번에 한 토큰씩 생성하고, 매 토큰은 앞의 모든 것(프롬프트 + 시스템 + 지금까지의 출력)에 좌우된다.
- **컨텍스트가 답을 바꾼다.** `Mary had a little ___` → 보통 `lamb`, "재밌게 끝내줘" 맥락 → `llama`.

## 잘하는 것 / 못하는 것
**잘함**
1. 글·코드·요약 생성
2. 번역
3. 지저분한 글에서 정보 추출
4. 이미지 읽기 (OCR·해석)
5. 단계적 추론

**도움 없이는 못함**
1. 이전 대화 기억
2. 최신 정보 조회
3. 실제 행동 (메일 전송 등)
4. 코드 실행·도구 사용
5. 자기 답 검증

**📌 환각(hallucination):** 모르면서도 그럴듯하게 자신 있게 지어냄. → **믿을 자료(컨텍스트)를 주면** 품질이 올라간다.

## 챗 앱 vs 모델 API
- **챗 앱** (claude.ai 등): 완성품. 대화 기억·UI 다 해줌. 구독 과금. 일반 사용자용.
- **모델 API** (Anthropic 등): 날것. **매 요청마다 히스토리 직접 전송**. 토큰당 과금. 개발자용.
- 비유: 챗앱 = 완성된 자동차, API = 엔진만. **우리는 엔진으로 직접 앱을 만든다.**

# 10 · LLM이란? (단계별 심화)

### 1단계 · 토큰
- 토큰 = 단어 또는 **단어 조각**. `unbelievable` → `un` + `believ` + `able`.
- 영어 기준 **1토큰 ≈ 0.75단어**. "토큰당 과금"이 여기서 나온다.

### 2단계 · 다음 토큰 예측
- 본질은 하나: 지금까지의 토큰 → **다음 토큰 확률** 계산 → 하나 뽑고, 붙이고, 반복 (autoregressive).
- 비유: **세계 최강 끝말잇기.**

### 3단계 · 학습
- 수조 개 토큰으로 "다음 토큰 맞히기"를 반복 연습 → **파라미터**(수천억 개 숫자 다이얼)를 조금씩 조정.

### 4단계 · 컨텍스트가 답을 바꾼다
- 다음 토큰 확률은 **앞에 뭐가 있었는지에 전적으로 의존**. 그래서 lamb vs llama.

### 5단계 · 컨텍스트 윈도우
- 한 번에 볼 수 있는 토큰 수에 **상한**이 있다. 넘어간 앞부분은 못 본다 → **매번 히스토리를 재전송**하는 이유.

### 6단계 · 확률적
- 확률 분포에서 **뽑기** 때문에 같은 질문도 답이 조금씩 다름 (`temperature`). 창의성이자 환각의 원천.

**한 줄 요약:** LLM = **토큰 단위로 다음을 예측하는 거대한 확률 엔진**.

# 13 · 첫 API 호출

비유: Claude에게 **전화 한 통** 거는 것.

```python
from anthropic import Anthropic
client = Anthropic()                 # .env의 ANTHROPIC_API_KEY 자동 로드
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    system="You are a tax advisor...",
    messages=[{"role": "user", "content": "..."}],
)
print(resp.content[0].text)
```

## 재료 4개
1. **model** — 어느 Claude에게 물을지.
2. **max_tokens** — 답 길이 상한 (**필수**). 끊기면 올린다.
3. **system** — Claude의 역할·규칙.
4. **messages** — 실제 대화. `{"role": "user", "content": ...}`.

## 꼭 기억
- 응답은 문자열이 아니라 **블록 리스트** → `resp.content[0].text`.
- `messages`가 리스트인 이유: HTTP는 stateless → **매번 전체 대화를 재전송**.

# 14~18 · 작은 챗 앱 만들기

## 큰 그림 (슬라이드 15)
- 구조는 hello-world와 **똑같다.** "고정된 답" 자리에 Claude 호출이 들어갈 뿐.
- 흐름: **React(5173) → Flask `/api/chat` → Claude API → 다시 React.**
- 핵심 파일 2개:
  1. `backend/app.py` — 엔드포인트 하나, Claude 호출 (~15줄)
  2. `frontend/src/App.jsx` — 입력칸 + 메시지 목록 (~30줄)

## 백엔드 (슬라이드 17)
```python
from flask import Flask, request, jsonify
from flask_cors import CORS
from anthropic import Anthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))   # 상위 폴더로 올라가며 .env 찾기
app = Flask(__name__)
CORS(app)
client = Anthropic()

@app.route("/api/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You are a helpful assistant. Keep replies brief.",
        messages=[{"role": "user", "content": user_message}],
    )
    return jsonify({"reply": resp.content[0].text})
```
핵심 3단계:
1. `request.json["message"]` — 프론트가 POST로 보낸 사용자 메시지를 꺼낸다.
2. `messages.create(...)` — **슬라이드 13의 그 호출 그대로.** 고정 답 대신 Claude 답.
3. `jsonify({"reply": ...})` — hello-world의 `{"message": ...}` 자리에 Claude 답을 실어 보냄.

## 프론트 (슬라이드 18)
```jsx
const [messages, setMessages] = useState([])
const [input, setInput] = useState('')

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
핵심 3단계:
1. 보내자마자 **내 메시지를 먼저** 화면에 추가 (낙관적 업데이트).
2. `fetch('/api/chat', POST)` — hello-world의 GET과 달리 **데이터를 body에 실어** 보냄.
3. 답이 오면 `assistant` 메시지로 추가 → 대화가 쌓인다.

## 실행 (슬라이드 16)
1. 백엔드: venv 활성화 → `pip install -r requirements.txt` → `python app.py` (`.env`의 키를 읽음)
2. 프론트: `npm install` → `npm run dev` → http://localhost:5173

**⚠️ 모델 ID:** 슬라이드는 `claude-sonnet-4-6`. 현재 최신 = **`claude-opus-4-8`**(최강·기본 추천), `claude-sonnet-4-6`(균형), `claude-haiku-4-5`(빠르고 저렴). 직접 만들 땐 `claude-opus-4-8` 권장.

# 다음 할 일
- **B안: 직접 만들어 돌려보기** — `chat-app/` 폴더 생성 → 위 코드 작성 → `.env` 키 확인 → 실제 Claude와 채팅 확인.
