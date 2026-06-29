# Production — 도커로 배포하며 배운 것

## 개발 vs 프로덕션
- 개발: 서버 2개 (Vite 5173 + Flask 5001).
- 프로덕션: **포트 하나(80)**. Nginx가 화면(정적 파일)을 직접 주고, `/api/*`만 Gunicorn으로 넘김.
- 같은 출처(origin)라서 **CORS가 필요 없다**.

## 등장인물
- **Nginx** = 출입문. TLS 처리, 정적 파일 서빙, `/api/*` 전달(reverse proxy).
- **Gunicorn** = 엔진. Flask를 **워커 여러 개**로 돌려 동시 요청 처리 (Flask 내장 서버는 1명).

## multi-stage 빌드
- 1단계(node): React를 `dist/`로 굽기.
- 2단계(python): 그 결과물 + 백엔드만 옮겨 담기 → 이미지가 가벼워짐.

## 직접 확인한 것
- `docker run -p 8080:80` 후 `GET /` → 200, `GET /api/hello` → JSON.
- 로그에 gunicorn 워커 4개(pid)가 떴다.
