# Backend (Flask)

Single-file Flask API exposing one endpoint:

- `GET /api/hello` → `{"message": "Hello from Flask"}`

## Install

From the **project root** (`ksept-lab/`), create and activate a virtual
environment, then install the backend dependencies:

```bash
# from project root: ksept-lab/
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt
```

## Run

With the `.venv` active:

```bash
cd backend
python app.py
```

The server listens on **http://localhost:5001**.
Test it: `curl http://localhost:5001/api/hello`
