# Setup — 내가 직접 하며 배운 것

## 포트 5000이 막혔던 일
- macOS에선 **AirPlay 수신기**가 5000번을 이미 쓰고 있었다.
- 증상: Flask가 `Address already in use`로 안 뜨고, `curl`은 `Server: AirTunes` 응답을 줬다.
- 해결: 백엔드 포트를 **5001**로 바꾸고, `vite.config.js` 프록시도 5001로 맞췄다.
- 교훈: "서버가 안 뜬다"면 **포트를 누가 쓰고 있는지** 먼저 의심하자.

## venv (가상환경)
- `python3 -m venv .venv` = 이 프로젝트 전용 파이썬 서랍.
- `pip install`은 시스템이 아니라 `.venv` 안에만 깔린다 → 다른 프로젝트와 안 꼬임.

## 한 줄 요약
설치는 `brew install node` 같은 패키지 매니저로, 백엔드는 venv 안에서 돌린다.
