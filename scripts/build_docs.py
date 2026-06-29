#!/usr/bin/env python3
"""
build_docs.py — ksept-lab 작업일지 생성기

`git log`를 읽어 docs/index.html(정적 작업일지)을 만든다.
- 데이터(커밋 메시지) = 단일 진실 공급원(source of truth)
- 표현(HTML/Mermaid) = 이 스크립트의 템플릿

사용:  python scripts/build_docs.py
의존성 없음(파이썬 표준 라이브러리만).
"""

import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "index.html"

# 레코드 구분자: 커밋 필드는 \x1f, 커밋 간은 \x1e 로 나눈다(공백/줄바꿈 충돌 방지).
GIT_FORMAT = "%H%x1f%h%x1f%an%x1f%ad%x1f%s%x1f%b%x1e"


def get_commits():
    """git log를 파싱해 커밋 dict 리스트(최신순)를 돌려준다."""
    raw = subprocess.run(
        ["git", "log", f"--pretty=format:{GIT_FORMAT}", "--date=format:%Y-%m-%d %H:%M"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    commits = []
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        full, short, author, date, subject, body = (record.split("\x1f") + [""] * 6)[:6]
        commits.append(
            {
                "full": full,
                "short": short,
                "author": author,
                "date": date,
                "subject": subject,
                "body": body.strip(),
            }
        )
    return commits


def render_commit(c):
    """커밋 하나를 타임라인 카드 HTML로 변환한다."""
    # 본문 줄 중 'Co-Authored-By' 같은 트레일러는 작업일지에서 가린다.
    body_lines = [
        ln for ln in c["body"].splitlines()
        if ln.strip() and not ln.startswith("Co-Authored-By")
    ]
    body_html = ""
    if body_lines:
        items = "".join(f"<li>{html.escape(ln.lstrip('- '))}</li>" for ln in body_lines)
        body_html = f"<ul class='body'>{items}</ul>"

    return f"""
    <li class="commit">
      <div class="sha"><code>{html.escape(c['short'])}</code></div>
      <div class="content">
        <div class="subject">{html.escape(c['subject'])}</div>
        <div class="meta">{html.escape(c['author'])} · {html.escape(c['date'])}</div>
        {body_html}
      </div>
    </li>"""


def build():
    commits = get_commits()
    timeline = "\n".join(render_commit(c) for c in commits)
    last_updated = commits[0]["date"] if commits else "(아직 커밋 없음)"
    count = len(commits)

    page = PAGE_TEMPLATE.format(
        timeline=timeline,
        last_updated=html.escape(last_updated),
        count=count,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({count} commits)")


# ─────────────────────────────────────────────────────────────────────────────
# 아래는 정적 템플릿. 개념 설명은 한글, Mermaid 다이어그램 라벨은 영어.
# {timeline} / {last_updated} / {count} 만 동적으로 치환된다.
# ─────────────────────────────────────────────────────────────────────────────
PAGE_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ksept-lab · 작업일지</title>
  <style>
    :root {{
      --bg: #0d1117; --panel: #161b22; --border: #30363d;
      --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --green: #3fb950;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; background: var(--bg); color: var(--fg);
      font-family: -apple-system, "Apple SD Gothic Neo", "Pretendard", system-ui, sans-serif;
      line-height: 1.7;
    }}
    .wrap {{ max-width: 860px; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }}
    h1 {{ font-size: 2rem; margin: 0 0 .25rem; }}
    h2 {{ font-size: 1.35rem; margin: 2.75rem 0 .75rem; border-bottom: 1px solid var(--border); padding-bottom: .4rem; }}
    h3 {{ font-size: 1.05rem; margin: 1.5rem 0 .4rem; color: var(--accent); }}
    p, li {{ color: var(--fg); }}
    .sub {{ color: var(--muted); margin-top: 0; }}
    code {{ background: #1f2530; padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.25rem; margin: 1rem 0; }}
    .mermaid {{ background: #fff; border-radius: 8px; padding: 1rem; margin: .75rem 0; overflow-x: auto; }}
    .note {{ color: var(--muted); font-size: .92rem; }}

    /* 타임라인 */
    ul.timeline {{ list-style: none; padding: 0; margin: 0; position: relative; }}
    ul.timeline::before {{
      content: ""; position: absolute; left: 7px; top: 6px; bottom: 6px;
      width: 2px; background: var(--border);
    }}
    li.commit {{ display: flex; gap: .9rem; padding: .6rem 0; position: relative; }}
    li.commit .sha {{ flex: 0 0 auto; z-index: 1; }}
    li.commit .sha::before {{
      content: ""; position: absolute; left: 2px; top: 1.05rem;
      width: 12px; height: 12px; border-radius: 50%;
      background: var(--green); border: 2px solid var(--bg);
    }}
    li.commit .sha code {{ margin-left: 1.4rem; }}
    li.commit .subject {{ font-weight: 600; }}
    li.commit .meta {{ color: var(--muted); font-size: .85rem; }}
    ul.body {{ margin: .4rem 0 0; padding-left: 1.1rem; }}
    ul.body li {{ color: var(--muted); font-size: .92rem; }}
    .badge {{ display: inline-block; background: #1f6feb22; color: var(--accent);
      border: 1px solid #1f6feb55; border-radius: 999px; padding: .1rem .6rem; font-size: .8rem; }}
    a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>ksept-lab <span class="badge">작업일지</span></h1>
    <p class="sub">Flask + React(Vite) hello-world를 만들며 배운 것들 · 마지막 업데이트 {last_updated} · 커밋 {count}개</p>

    <h2>1. 이 프로젝트가 작동하는 방식</h2>
    <div class="card">
      <p>두 개의 <strong>독립된 서버</strong>가 돈다. Flask(:5001)는 JSON 데이터를,
         Vite(:5173)는 React 화면을 책임진다. 브라우저는 5173하고만 대화하고,
         <code>/api/*</code> 요청은 Vite가 몰래 Flask로 넘긴다(프록시).</p>
      <div class="mermaid">
sequenceDiagram
    participant B as Browser (:5173)
    participant V as Vite dev server
    participant F as Flask (:5001)
    B->>V: GET /api/hello
    Note over V: path starts with /api -> proxy rule matches
    V->>F: GET /api/hello (forwarded)
    F-->>V: 200 {{"message":"Hello from Flask"}}
    V-->>B: 200 {{"message":"Hello from Flask"}}
    Note over B: React setState -> re-render message
      </div>
      <p class="note">브라우저 입장에선 전부 5173에서 온 응답이라, 다음에 볼 CORS 문제가 아예 생기지 않는다.</p>
    </div>

    <h2>2. CORS — 왜 프록시가 이걸 우회하나</h2>
    <div class="card">
      <p>브라우저는 보안상 <strong>다른 출처(origin)</strong>의 응답을 JS가 읽지 못하게 막는다
         (Same-Origin Policy). 출처 = (scheme, host, port) 셋이 모두 같아야 한다.
         <code>localhost:5173</code> ≠ <code>localhost:5001</code> 이므로 직접 부르면 막힌다.
         서버가 <code>Access-Control-Allow-Origin</code> 헤더를 붙여줘야(=flask-cors) 풀린다.
         하지만 dev에선 프록시 덕에 브라우저가 보기엔 동일 출처라 검사 자체가 안 일어난다.</p>
      <div class="mermaid">
flowchart TD
    A[Browser JS: fetch] --> B{{Same origin?}}
    B -- Yes, via Vite proxy --> C[No CORS check needed]
    B -- No, direct to :5001 --> D{{Response has<br/>Access-Control-Allow-Origin?}}
    D -- Yes, flask-cors added it --> E[Browser exposes body to JS]
    D -- No --> F[Browser blocks: CORS error]
      </div>
      <p class="note">그래서 우리는 안전망으로 <code>flask-cors</code>도 켜두고, 동시에 프록시도 쓴다. 두 겹.</p>
    </div>

    <h2>3. 가상환경(venv)은 무엇을 격리하나</h2>
    <div class="card">
      <p><code>python3 -m venv .venv</code>는 프로젝트 전용 파이썬 + 전용 <code>site-packages</code>를 만든다.
         <code>pip install</code>은 시스템이 아니라 이 폴더 안에 쓴다. 그래서 프로젝트마다
         버전이 충돌하지 않고, 시스템 파이썬은 깨끗하게 유지된다.</p>
      <div class="mermaid">
flowchart LR
    subgraph SYS["System Python 3.9"]
        sp["site-packages: clean"]
    end
    subgraph VENV[".venv (project-local)"]
        vp["site-packages: flask, flask-cors, werkzeug ..."]
    end
    run[".venv/bin/python app.py"] --> vp
    pip["pip install -r requirements.txt"] --> vp
    pip -. "does NOT touch" .-> sp
      </div>
      <p class="note"><code>source .venv/bin/activate</code>는 단지 <code>.venv/bin</code>을 PATH 앞에 끼워주는 단축일 뿐.</p>
    </div>

    <h2>4. 로컬 → GitHub → Pages 배포 흐름</h2>
    <div class="card">
      <p><code>git commit</code>은 로컬에 스냅샷을 찍고, <code>git push</code>는 그걸 GitHub로 보낸다.
         GitHub Pages를 <code>main</code>의 <code>/docs</code> 폴더로 설정해두면, 푸시될 때마다
         그 폴더의 정적 파일을 웹에 띄운다.</p>
      <div class="mermaid">
sequenceDiagram
    participant L as Local repo
    participant G as GitHub repo
    participant P as GitHub Pages
    participant U as Visitor
    L->>L: git commit (snapshot)
    L->>G: git push origin main
    G->>P: serve main:/docs as a website
    U->>P: GET index.html
    P-->>U: static HTML + Mermaid (rendered in browser)
      </div>
    </div>

    <h2>5. 이 작업일지는 어떻게 자동으로 갱신되나</h2>
    <div class="card">
      <p><code>scripts/build_docs.py</code>가 <code>git log</code>를 읽어 이 페이지의 타임라인을 다시 만든다.
         즉 <strong>커밋 메시지가 곧 작업일지</strong>다. 커밋 → 생성기 실행 → 푸시.</p>
      <div class="mermaid">
flowchart LR
    C[git commit] --> R[run build_docs.py]
    R --> RL[read git log]
    RL --> W[write docs/index.html]
    W --> C2[git commit docs] --> PUSH[git push]
    PUSH --> PAGES[GitHub Pages redeploys]
      </div>
      <p class="note">한계: 페이지는 자기 자신을 만든 커밋은 못 담는다(해시는 내용으로 정해지므로 자기 해시를 자기 안에 넣을 수 없다). 그래서 항상 한 박자 늦다 — GitHub Actions로 없앨 수 있는 lag.</p>
    </div>

    <h2>작업일지 (git log)</h2>
    <ul class="timeline">
{timeline}
    </ul>

    <p class="note" style="margin-top:2rem">
      소스: <a href="https://github.com/welovecherry/ksept-lab">github.com/welovecherry/ksept-lab</a>
    </p>
  </div>

  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "default", securityLevel: "loose" }});
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
