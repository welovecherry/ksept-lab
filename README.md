# ksept-lab

A minimal hello-world full-stack app: a Flask API and a React (Vite) frontend.

```
ksept-lab/
├── backend/      Flask API  (GET /api/hello)
├── frontend/     React + Vite single page
└── README.md     you are here
```

## Quick start (two terminals)

Dependencies are **not** installed yet — install them first (see each
sub-README for details).

### Terminal 1 — backend

```bash
# from project root
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
python app.py                      # serves http://localhost:5001
```

### Terminal 2 — frontend

```bash
cd frontend
npm install
npm run dev                        # serves http://localhost:5173
```

Open **http://localhost:5173**. The page calls `/api/hello`, which Vite
proxies to the Flask server, and shows **"Hello from Flask"**.
