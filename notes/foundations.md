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

## 첫 API 호출 — 손으로 직접 해보기

이 슬라이드 하나만 제대로 잡으면 챗 앱은 그냥 "이걸 웹으로 감싼 것"이에요. 그래서 **개념 → 준비물 → 진짜 1파일 실행 → 한 줄씩 해부 → 에러 대처** 순서로 천천히 갑니다.

### 0단계 · "API 호출"이 대체 뭔가
**비유 — 식당 주방에 주문서 넣기.** 내 코드는 손님이고, Anthropic 서버는 주방이에요. 정해진 양식의 **주문서(요청)**를 창구에 넣으면, 주방이 **요리(응답)**해서 돌려줘요. 주방이 *어떻게* 요리하는지는 몰라도 됩니다 — 양식만 맞으면 돼요.

**기술적으로는:** 내 컴퓨터 → 인터넷 → Anthropic 서버의 주소 한 곳(`https://api.anthropic.com/v1/messages`)으로 **HTTPS 요청**을 보내는 것. `anthropic` SDK가 이 복잡한 과정을 **함수 한 번**(`client.messages.create(...)`)으로 감싸줘요.

### 1단계 · 준비물 3가지
1. **API 키** — `console.anthropic.com`에서 발급. `sk-ant-...` 형태의 문자열. **내 신분증 + 결제수단**이라 남에게 노출 금지.
2. **anthropic 패키지** — 터미널에서 `pip install anthropic python-dotenv`.
3. **키를 둘 `.env` 파일** — 키를 코드에 직접 박지 않고 파일에 둠. git에는 절대 안 올림(`.gitignore`).

### 2단계 · 키는 어디 두고, 코드가 어떻게 찾나
- 프로젝트 폴더에 **`.env`** 파일을 만들고 딱 한 줄:
```
ANTHROPIC_API_KEY=sk-ant-여기에_내_키
```
- `Anthropic()`을 만들 때 **환경변수 `ANTHROPIC_API_KEY`를 자동으로 읽어요.** 그래서 코드에 키를 안 써도 됩니다.
- 단, `.env` 파일의 값을 환경변수로 "올려주는" 한 줄이 필요해요 → `load_dotenv()`. (이게 없으면 `.env`는 그냥 텍스트 파일일 뿐.)

### 3단계 · 진짜로 돌려보는 1파일 (여기가 핵심)
폴더 아무 데나 **`hello_claude.py`** 파일 하나를 만들고 아래를 **그대로 복붙**하면 끝이에요.
```python
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()                 # .env의 키를 환경변수로 올림
client = Anthropic()          # ANTHROPIC_API_KEY 자동 로드

resp = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=256,
    messages=[{"role": "user", "content": "한 문장으로 자기소개 해줘"}],
)
print(resp.content[0].text)   # 돌아온 답 출력
```
**실행:** 같은 폴더에서 터미널에 →
```
python hello_claude.py
```
화면에 Claude의 답 한 줄이 찍히면 성공. **이게 "API 콜"의 전부예요.**

### 4단계 · 한 줄씩 — 무슨 일이 일어나나
1. `import ...` — SDK를 불러옴.
2. `load_dotenv()` — `.env`의 키를 **메모리(환경변수)**로 올림.
3. `Anthropic()` — 키를 들고 서버와 통신할 준비가 된 **클라이언트 객체**.
4. `client.messages.create(...)` — **바로 이 줄에서 실제 인터넷 요청이 나가요.** 코드가 여기서 잠깐 멈추고(서버 기다림) 답이 오면 다음 줄로.
5. `resp.content[0].text` — 돌아온 답을 꺼냄.

### 5단계 · 주문서의 재료 4개
1. **model** — 어느 Claude를 쓸지. (`claude-opus-4-8` = 최강·기본 추천.)
2. **max_tokens** — 답 길이 상한(**필수**). 답이 중간에 끊기면 이 값을 올린다.
3. **system** — Claude의 역할·규칙(예: `"You are a tax advisor..."`). 선택.
4. **messages** — 실제 대화. `{"role": "user", "content": "..."}` 리스트.

### 6단계 · 돌아온 응답은 어떻게 생겼나
- `resp`는 객체이고, `resp.content`는 **블록들의 리스트**예요. 보통 `[TextBlock(text="...")]` 하나 → 그래서 `resp.content[0].text`.
- **왜 리스트?** 답이 글 + 이미지 + 도구호출처럼 **여러 블록**일 수 있어서. 지금은 글 한 덩어리니 `[0]`만 보면 됨.
- `messages`도 리스트인 이유: API는 **stateless**(직전 대화를 기억 못 함) → 대화를 이어가려면 **매 요청마다 전체 히스토리를 다시 보냄**.

### 7단계 · 자주 나는 에러 & 해결
1. **`ModuleNotFoundError: anthropic`** → `pip install anthropic python-dotenv` 안 함.
2. **401 `authentication_error`** → 키가 틀렸거나 안 읽힘. `.env` 위치 + `load_dotenv()` 호출 + 키 오타 확인.
3. **답이 중간에 잘림** → `max_tokens`를 올린다. (`resp.stop_reason`이 `"max_tokens"`면 길이 때문.)

### 8단계 · 이걸 "앱"으로 (슬라이드 15·17과 연결)
위 1파일 실험의 `messages.create(...)` 호출이 **그대로** `backend/app.py`의 `/api/chat` 안으로 들어가요. 딱 하나만 바뀝니다 — **"고정 질문" 대신 프론트가 보낸 질문**(`request.json["message"]`)을 `content`에 넣는 것. 즉 **13번을 이해하면 17번은 거의 다 한 거예요.**

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
