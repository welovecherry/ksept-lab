"""Phase 0 smoke test — exercise the real /api/chat path once.

Reuses backend/app.py exactly (retrieval + Claude generation + [n] citation
parsing) via Flask's test client, so no server/port is needed.
Run from the rag-starter/ directory so load_dotenv() finds .env.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import app as backend  # noqa: E402  (triggers index load + Anthropic client)

QUESTION = "What was the goal of the Apollo 11 mission?"

client = backend.app.test_client()
resp = client.post("/api/chat", json={"message": QUESTION})
data = resp.get_json()

print(f"Q: {QUESTION}\n")
print("REPLY:\n" + data["reply"])
print("\nCITATIONS:")
for c in data["citations"]:
    print(f"  [{c['n']}] {c['source']} (chunk {c['chunk_index']})")
