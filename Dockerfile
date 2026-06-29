# ─────────────────────────────────────────────────────────────
# stage 1 — build React to static files
# 큰 작업대(node 이미지)에서 React를 굽는다. 결과물은 dist/ 폴더.
# ─────────────────────────────────────────────────────────────
FROM node:20-slim AS web
WORKDIR /web

# package.json만 먼저 복사 -> 의존성 설치 (이 레이어는 소스가 바뀌어도 캐시됨)
COPY frontend/package*.json ./
RUN npm ci

# 나머지 소스 복사 후 정적 빌드
COPY frontend/ .
RUN npm run build          # -> /web/dist

# ─────────────────────────────────────────────────────────────
# stage 2 — Flask + nginx in one image
# 작은 서빙 접시(python 이미지)에 '구운 결과물'과 백엔드만 옮겨 담는다.
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# nginx 설치 (접수처 역할)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 의존성 (flask, flask-cors, gunicorn)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Flask 코드
COPY backend/ .

# stage 1에서 구운 React 정적 파일을 nginx 웹루트로
COPY --from=web /web/dist /usr/share/nginx/html

# nginx 설정 교체 (기본 사이트는 80 포트 충돌 방지로 제거)
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

EXPOSE 80

# Gunicorn(Flask 엔진)을 8000에서 띄우고, nginx를 전면(80)에서 띄운다.
# nginx는 foreground(daemon off)로 띄워야 컨테이너가 살아 있는다.
CMD gunicorn -w 4 -b 127.0.0.1:8000 app:app & \
    nginx -g 'daemon off;'
