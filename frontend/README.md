# Frontend (React + Vite)

Single-page React app (plain JavaScript) that fetches `/api/hello` on mount
and displays the returned message.

## Install

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Open **http://localhost:5173**.

Requests to `/api/*` are proxied to the Flask backend at
`http://localhost:5001` (see `vite.config.js`), so the backend must be
running for the message to appear.
