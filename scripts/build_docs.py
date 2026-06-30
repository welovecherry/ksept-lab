#!/usr/bin/env python3
"""
build_docs.py — 학습 허브(홈) + 변경 이력 페이지 생성기

출력 (자동 생성, .gitignore):
  - docs/index.html     : 홈 허브 (주제 목록 + 기초 개념 노트)
  - docs/changelog.html : git log 변경 이력 (커밋 타임라인)

주제별 '학습본 + 내 작업일지'는 build_learn.py가 docs/learn/* 로 만든다.
의존성 없음(파이썬 표준 라이브러리만).
"""

import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_HOME = ROOT / "docs" / "index.html"
OUT_CHANGELOG = ROOT / "docs" / "changelog.html"
OUT_NOTES = ROOT / "docs" / "notes.html"
OUT_PRACTICE = ROOT / "docs" / "practice.html"
OUT_PROJECT = ROOT / "docs" / "rag-project.html"

# 사이트 수준 내비 (홈/노트/변경이력이 공유하는 사이드바) — '섹션 이동'만, 모듈/앵커 안 섞음
SITE = [
    ("index.html", "🏠 홈"),
    ("practice.html", "🧪 첫 호출 실습"),
    ("learn/index.html", "📚 학습 시작"),
    ("tutorial/index.html", "📖 원본 보관소"),
    ("notes.html", "🧩 프로젝트 노트"),
    ("rag-project.html", "🛩️ RAG 콘테스트"),
    ("changelog.html", "📜 변경 이력"),
]

GIT_FORMAT = "%H%x1f%h%x1f%an%x1f%ad%x1f%s%x1f%b%x1e"
RECENT_LIMIT = 20

# 사이드바/홈에서 쓰는 주제 목록 (learn/* 학습본으로 연결)
MODULES = [
    ("learn/index.html", "개요", "코스 전체 그림"),
    ("learn/setup.html", "Setup", "환경 구성 · Node · Python · venv"),
    ("learn/foundations.html", "Foundations", "기초 개념"),
    ("learn/tools.html", "Tools & Structure", "도구와 구조"),
    ("learn/context.html", "Context", "컨텍스트 관리"),
    ("learn/agents.html", "Agents", "아키텍처와 에이전트"),
    ("learn/production.html", "Production", "도커로 배포"),
    ("learn/workshop.html", "Workshop", "직접 만들기"),
]

# 홈에 있는 '기초 개념' 섹션 앵커 (사이드바에서 바로 점프)
CONCEPTS = [
    ("how", "작동 방식"),
    ("cors", "CORS"),
    ("venv", "가상환경(venv)"),
    ("deploy", "배포 흐름"),
    ("auto", "자동 갱신"),
]


# ── git log → 커밋 타임라인 ───────────────────────────────────────────────────
def get_commits():
    raw = subprocess.run(
        ["git", "log", f"--pretty=format:{GIT_FORMAT}", "--date=format:%Y-%m-%d %H:%M"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    commits = []
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        full, short, author, date, subject, body = (record.split("\x1f") + [""] * 6)[:6]
        commits.append({"short": short, "author": author, "date": date,
                        "subject": subject, "body": body.strip()})
    return commits


def render_commit(c):
    body_lines = [ln for ln in c["body"].splitlines()
                  if ln.strip() and not ln.startswith("Co-Authored-By")]
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


def group_by_date(commits):
    groups = []
    for c in commits:
        day = c["date"].split(" ")[0] or "(unknown)"
        if not groups or groups[-1][0] != day:
            groups.append((day, []))
        groups[-1][1].append(c)
    return groups


def render_timeline(commits):
    recent, older = [], []
    shown = older_count = 0
    for day, cs in group_by_date(commits):
        block = f"""
    <section class="date-group">
      <h3 class="date">{html.escape(day)}</h3>
      <ul class="timeline">{''.join(render_commit(c) for c in cs)}</ul>
    </section>"""
        if shown < RECENT_LIMIT:
            recent.append(block); shown += len(cs)
        else:
            older.append(block); older_count += len(cs)
    out = "\n".join(recent)
    if older:
        out += (f'\n    <details class="older"><summary>이전 이력 {older_count}개 펼치기 ▸</summary>'
                f'{"".join(older)}</details>')
    return out


# ── 공유 사이드바 (사이트 수준 내비만) ────────────────────────────────────────
def sidebar_html(active=""):
    items = []
    for href, name in SITE:
        cls = ' class="active"' if href == active else ""
        items.append(f'<a href="{href}"{cls}>{html.escape(name)}</a>')
    links = "".join(items)
    return f"""  <aside class="sidebar">
    <div class="side-title"><a href="index.html">📒 ksept-lab</a></div>
    <nav>{links}</nav>
    <div class="side-foot">welovecherry/ksept-lab</div>
  </aside>"""


# ── 홈 본문 ───────────────────────────────────────────────────────────────────
def home_body(last_updated, count):
    entry = [
        ("practice.html", "🧪 첫 API 호출 실습", "따라만 하면 10분 안에 내 컴퓨터에서 Claude 호출"),
        ("learn/index.html", "📚 학습 시작", "원본 + 내 노트 + 인터랙티브 퀴즈로 공부하는 곳"),
        ("tutorial/index.html", "📖 원본 보관소", "스크랩한 튜토리얼 슬라이드 원본 (참고용)"),
        ("notes.html", "🧩 프로젝트 노트", "작동방식·CORS·venv·배포를 쉬운 말로 정리"),
        ("rag-project.html", "🛩️ RAG 콘테스트", "FAA 항공법 RAG 챗봇 — 개요·임베딩·실험·작업일지"),
        ("changelog.html", "📜 변경 이력", "커밋 메시지로 자동 생성되는 작업일지"),
    ]
    entry_cards = "".join(
        f'<a class="entrycard" href="{h}"><b>{html.escape(n)}</b><span>{html.escape(d)}</span></a>'
        for h, n, d in entry
    )
    cards = "".join(
        f'<a class="topiccard" href="{href}"><b>{html.escape(name)}</b><span>{html.escape(desc)}</span></a>'
        for href, name, desc in MODULES[1:]
    )
    return f"""    <h1>ksept-lab <span class="badge">학습 홈</span></h1>
    <p class="sub">Claude Code로 풀스택을 배우는 개인 학습 사이트예요. 아래에서 갈 곳을 고르세요.</p>

    <div class="entry-grid">{entry_cards}</div>

    <h2>📚 모듈 바로가기</h2>
    <p class="note">특정 주제로 바로 가고 싶다면. 각 페이지엔 <b>학습본 + 내 노트 + 퀴즈</b>가 있어요.</p>
    <div class="topic-grid">{cards}</div>

    <p class="note" style="margin-top:2rem">마지막 업데이트 {html.escape(last_updated)} · 커밋 {count}개 ·
      <a href="https://github.com/welovecherry/ksept-lab">소스</a> · <a href="changelog.html">📜 변경 이력</a></p>"""


def notes_body():
    jump = " · ".join(f'<a href="#{cid}">{html.escape(label)}</a>' for cid, label in CONCEPTS)
    return f"""    <h1>🧩 프로젝트 노트 <span class="badge">직접 정리</span></h1>
    <p class="sub"><a href="index.html">← 홈으로</a> · 이 사이트(Flask + React + GitHub Pages)를 만들며 이해한 핵심을 쉬운 말로 정리했어요.</p>
    <p class="note">바로가기: {jump}</p>

    <h2 id="how">이 앱은 어떻게 움직일까?</h2>
    <div class="card">
      <div class="analogy">📚 <b>비유:</b> 식당을 떠올려요. 손님(브라우저)은 <b>홀 직원</b>(화면 담당)하고만 이야기해요.
        주방(데이터 담당)은 직접 안 만나요. 주문이 들어오면 홀 직원이 대신 주방에 전하고, 음식을 받아다 손님에게 줘요.</div>
      <p>우리 앱은 프로그램이 <strong>두 개</strong>예요. 하나는 <b>화면</b>을 보여주고(React, 5173번 문),
         하나는 <b>데이터</b>를 만들어요(Flask, 5001번 문). 브라우저는 화면 담당하고만 이야기하고,
         데이터가 필요하면 화면 담당이 <b>대신</b> 데이터 담당에게 물어봐요. 이렇게 대신 전해 주는 걸 <code>프록시</code>라고 해요.</p>
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
      <p class="note">🗺️ <b>그림 읽는 법:</b> 화살표를 <b>위 → 아래 순서</b>로 따라가요. 주문이 손님→홀→주방으로 갔다가, 음식이 거꾸로 손님에게 돌아오는 길이에요.</p>
    </div>

    <h2 id="cors">CORS — 브라우저의 "낯선 사람 조심"</h2>
    <div class="card">
      <div class="analogy">📚 <b>비유:</b> 브라우저는 깐깐한 <b>경비원</b>이에요. 우리 집(5173)에서 보낸 편지의 답장은 받아주지만,
        <b>모르는 집</b>(5001)에서 온 답장은 "누구세요?" 하며 막아요.</div>
      <p>브라우저는 안전을 위해, <b>주소가 다른 곳</b>에서 온 데이터를 함부로 못 읽게 막아요.
         이 규칙 이름이 <code>CORS</code>예요. 5173과 5001은 끝번호(포트)가 달라서 '다른 곳'으로 쳐요.
         푸는 방법은 둘이에요: ① 서버가 "얘는 믿어도 돼요" <b>도장</b>을 찍어주거나(<code>flask-cors</code>),
         ② 애초에 <b>같은 집처럼 보이게</b> 프록시로 전해 주기. 개발 중엔 ②(프록시) 덕분에 막힐 일이 없어요.</p>
      <div class="mermaid">
flowchart TD
    A[Browser JS: fetch] --> B{{Same origin?}}
    B -- Yes, via Vite proxy --> C[No CORS check needed]
    B -- No, direct to :5001 --> D{{Response has<br/>Access-Control-Allow-Origin?}}
    D -- Yes, flask-cors added it --> E[Browser exposes body to JS]
    D -- No --> F[Browser blocks: CORS error]
      </div>
      <p class="note">🗺️ <b>그림 읽는 법:</b> 갈림길에서 "같은 집인가?"를 먼저 물어요. <b>예</b>면 그냥 통과, <b>아니오</b>면 "믿어도 된다는 도장 있나?"를 또 확인해요. 도장이 없으면 막혀요(CORS 에러).</p>
    </div>

    <h2 id="venv">가상환경(venv) — 프로젝트 전용 서랍</h2>
    <div class="card">
      <div class="analogy">📚 <b>비유:</b> 프로젝트마다 <b>전용 서랍</b>을 따로 두는 거예요. 이 서랍에 도구(라이브러리)를 넣어도,
        다른 서랍이나 공용 책상(컴퓨터 전체)은 전혀 안 건드려요.</div>
      <p>파이썬 도구를 컴퓨터 <b>전체</b>에 깔면 프로젝트끼리 버전이 서로 꼬여요.
         <code>venv</code>는 <b>이 프로젝트만의 공간</b>이에요. 여기 깔면 다른 곳은 깨끗하게 유지돼요.
         <code>activate</code>는 "지금 이 서랍을 열어둔다"는 뜻일 뿐이에요.</p>
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
      <p class="note">🗺️ <b>그림 읽는 법:</b> <code>pip install</code> 화살표가 <b>전용 서랍(.venv)</b>으로만 들어가요. 공용 책상(System)으로 가는 길은 점선 = "건드리지 않음"이에요.</p>
    </div>

    <h2 id="deploy">인터넷에 올리기 (GitHub Pages)</h2>
    <div class="card">
      <div class="analogy">📚 <b>비유:</b> <code>git commit</code>은 지금 상태를 <b>사진 찍어 저장</b>, <code>git push</code>는 그 사진을 <b>GitHub에 올리기</b>예요.
        GitHub Pages는 올린 폴더를 <b>무료 웹사이트</b>로 띄워주는 서비스고요.</div>
      <p>코드를 저장하고(<code>commit</code>) GitHub로 보내면(<code>push</code>),
         Pages가 <code>docs</code> 폴더를 웹페이지로 보여줘요. 그래서 누구나 인터넷에서 볼 수 있어요.</p>
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
      <p class="note">🗺️ <b>그림 읽는 법:</b> 왼쪽부터 <b>내 컴퓨터 → GitHub → Pages → 방문자</b> 순서로 흘러가요.</p>
    </div>

    <h2 id="auto">이 사이트가 저절로 갱신되는 이유</h2>
    <div class="card">
      <div class="analogy">📚 <b>비유:</b> 일기를 손으로 안 쓰고, <b>"오늘 한 일 목록"을 그대로 옮겨 적어주는 자동 비서</b>가 있는 셈이에요.</div>
      <p><code>scripts/</code>의 작은 프로그램들이 <code>git log</code>와 내 노트를 읽어 이 사이트를 다시 만들어요.
         지금은 GitHub Actions가 <code>push</code>할 때마다 <b>자동</b>으로 해줘요.
         자세한 작업 기록은 <a href="changelog.html">📜 변경 이력</a>에서 볼 수 있어요.</p>
      <div class="mermaid">
flowchart LR
    C[git commit] --> PUSH[git push]
    PUSH --> A[GitHub Actions]
    A --> B[build_docs.py + build_learn.py]
    B --> PAGES[GitHub Pages redeploys]
      </div>
      <p class="note">🗺️ <b>그림 읽는 법:</b> 저장 → 올리기 → 자동 빌드 → 배포. 손댈 곳은 <b>커밋 메시지</b>와 <b>notes/*.md</b>뿐이에요.</p>
    </div>

    <p class="note" style="margin-top:2.5rem"><a href="index.html">← 홈으로</a> · <a href="changelog.html">📜 변경 이력</a></p>"""


# ── 변경 이력 본문 ────────────────────────────────────────────────────────────
def changelog_body(timeline, last_updated, count):
    return f"""    <h1>📜 변경 이력 <span class="badge">git log</span></h1>
    <p class="sub"><a href="index.html">← 홈으로</a> · 커밋 메시지에서 자동 생성 · 마지막 업데이트 {html.escape(last_updated)} · {count}개</p>
    <div class="timeline-wrap">
{timeline}
    </div>"""


# ── 공통 셸(레이아웃 + 스타일) ────────────────────────────────────────────────
# ── 첫 API 호출 실습 (따라 하기) ──────────────────────────────────────────────
# 공개 페이지이므로 진짜 키는 절대 넣지 않는다. 코드 블록의 중괄호는 .format 값이라 안전.
def practice_body():
    return r"""    <style>
      .lead { font-size: 1.06rem; color: #c9d1d9; }
      .steps { margin: 1.6rem 0; }
      .step { position: relative; border: 1px solid var(--border); border-radius: 10px;
        background: var(--panel); padding: 1rem 1.2rem 1.1rem 3.3rem; margin: .9rem 0; }
      .step > .n { position: absolute; left: 1rem; top: 1rem; width: 1.7rem; height: 1.7rem;
        border-radius: 50%; background: var(--accent); color: #0d1117; font-weight: 700;
        display: flex; align-items: center; justify-content: center; font-size: .92rem; }
      .step h3 { margin: .15rem 0 .55rem; color: var(--fg); }
      .step p { margin: .4rem 0; }
      pre { background: #010409; border: 1px solid var(--border); border-radius: 8px;
        padding: .8rem 1rem; overflow-x: auto; font-size: .88rem; line-height: 1.6; }
      pre code { background: none; padding: 0; font-size: inherit; }
      .cmt { color: #6e7681; }
      .ok { background: #11271a; border-left: 3px solid var(--green); border-radius: 6px;
        padding: .55rem .85rem; margin: .75rem 0 0; font-size: .93rem; }
      .ok b { color: var(--green); }
      .warn { background: #2a1d11; border-left: 3px solid #e3b341; border-radius: 6px;
        padding: .55rem .85rem; margin: .75rem 0 0; font-size: .93rem; }
      .warn b { color: #e3b341; }
      table.err { border-collapse: collapse; width: 100%; margin: .6rem 0; font-size: .9rem; }
      table.err td { border: 1px solid var(--border); padding: .45rem .65rem; vertical-align: top; }
      table.err td:first-child { color: #f85149; white-space: nowrap; font-weight: 600; }
      .tag { display: inline-block; background: #1f6feb22; color: var(--accent);
        border: 1px solid #1f6feb55; border-radius: 999px; padding: .05rem .55rem; font-size: .78rem; }
    </style>

    <h1>🧪 첫 Claude API 호출 <span class="badge">실습</span></h1>
    <p class="sub"><a href="index.html">← 홈으로</a> · 위에서부터 그대로 따라 하세요. 복붙만 하면 <b>10분 안에</b> 내 컴퓨터에서 Claude한테 말 걸고 답을 받습니다.</p>

    <p class="analogy">🍳 <b>비유:</b> API 호출 = <b>식당 주방에 주문서 넣기</b>. 정해진 양식의 주문서(요청)를 창구에 넣으면 주방(Claude 서버)이 요리(답)를 돌려줘요. 주방이 어떻게 요리하는지는 몰라도 됩니다.</p>

    <div class="steps">

      <div class="step"><span class="n">0</span>
        <h3>준비물 확인</h3>
        <p>터미널(맥: <code>터미널</code>, 윈도우: <code>PowerShell</code>)을 열고 파이썬이 있는지 확인:</p>
        <pre><code>python3 --version</code></pre>
        <div class="ok"><b>이렇게 나오면 OK:</b> <code>Python 3.x.x</code> (3.9 이상이면 충분). 없다면 <a href="learn/setup.html">Setup 모듈</a>에서 설치.</div>
      </div>

      <div class="step"><span class="n">1</span>
        <h3>실습 폴더 만들기</h3>
        <pre><code>mkdir claude-practice
cd claude-practice</code></pre>
        <p class="note">아무 위치나 괜찮아요. 바탕화면이든 문서든.</p>
      </div>

      <div class="step"><span class="n">2</span>
        <h3>가상환경 + 패키지 설치</h3>
        <p>이 폴더 전용 파이썬 공간(<code>.venv</code>)을 만들고, 그 안에 <code>anthropic</code> 패키지를 깝니다.</p>
        <pre><code><span class="cmt"># 맥 / 리눅스</span>
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv</code></pre>
        <pre><code><span class="cmt"># 윈도우(PowerShell)면 활성화 줄만 이렇게</span>
.venv\Scripts\Activate.ps1</code></pre>
        <div class="ok"><b>성공 신호:</b> 줄 맨 앞에 <code>(.venv)</code>가 붙어요. 그게 "이 폴더 환경에 들어왔다"는 뜻.</div>
      </div>

      <div class="step"><span class="n">3</span>
        <h3>API 키를 <code>.env</code> 파일에 넣기</h3>
        <p>같은 폴더에 <code>.env</code> 라는 파일을 만들고 <b>딱 한 줄</b> 적습니다. (강사가 준 수업 키 또는 본인 키)</p>
        <pre><code>ANTHROPIC_API_KEY=sk-ant-여기에_내_키_붙여넣기</code></pre>
        <div class="warn"><b>보안 ⚠️</b> 이 키는 신분증 + 결제수단이에요. <b>깃허브·채팅·공개 파일에 절대 올리지 마세요.</b> <code>.env</code>에만 두면 코드에 키가 안 박혀서 안전해요.</div>
      </div>

      <div class="step"><span class="n">4</span>
        <h3>코드 파일 만들기 — <code>hello_claude.py</code></h3>
        <p>같은 폴더에 <code>hello_claude.py</code> 파일을 만들고 아래를 <b>그대로 복붙</b>:</p>
        <pre><code>from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()                 <span class="cmt"># .env 의 키를 환경변수로 올림</span>
client = Anthropic()          <span class="cmt"># ANTHROPIC_API_KEY 자동 로드</span>

resp = client.messages.create(
    model="claude-haiku-4-5",                 <span class="cmt"># 수업용: 빠르고 저렴</span>
    max_tokens=256,                           <span class="cmt"># 답 길이 상한</span>
    messages=[{"role": "user", "content": "한 문장으로 자기소개 해줘"}],
)

print(resp.content[0].text)   <span class="cmt"># 돌아온 답 출력</span></code></pre>
        <div class="note">더 똑똑한 답이 필요하면 <code>model</code> 한 줄만 <code>"claude-opus-4-8"</code>로 바꾸면 돼요(단, 비용 ↑).</div>
      </div>

      <div class="step"><span class="n">5</span>
        <h3>실행!</h3>
        <pre><code>python hello_claude.py</code></pre>
        <div class="ok"><b>🎉 성공:</b> 화면에 Claude의 답 한 줄이 찍히면 끝. <b>이게 "API 호출"의 전부예요.</b></div>
      </div>

      <div class="step"><span class="n">6</span>
        <h3>바꿔보며 감 잡기</h3>
        <p>코드의 <code>content</code> 문장을 바꿔서 다시 실행해 보세요. 그 다음 한 줄씩 실험:</p>
        <pre><code>    <span class="cmt"># 역할(규칙)을 줘 보기 — create(...) 안에 추가</span>
    system="너는 항상 반말로, 한 문장으로만 답한다.",

    <span class="cmt"># 답이 잘리면 max_tokens 를 키우기</span>
    max_tokens=512,</code></pre>
      </div>

    </div>

    <h2>🧩 방금 무슨 일이 일어났나 (한 줄씩)</h2>
    <ol>
      <li><code>load_dotenv()</code> — <code>.env</code>의 키를 <b>메모리(환경변수)</b>로 올림.</li>
      <li><code>Anthropic()</code> — 키를 들고 서버와 통신할 준비가 된 <b>클라이언트</b>.</li>
      <li><code>client.messages.create(...)</code> — <b>이 줄에서 실제로 인터넷 요청이 나가요.</b> 답이 올 때까지 잠깐 멈춤.</li>
      <li><code>resp.content[0].text</code> — 돌아온 답을 꺼냄. (응답은 블록들의 <b>리스트</b>라 <code>[0]</code>.)</li>
    </ol>

    <h2>🚑 자주 나는 에러</h2>
    <table class="err">
      <tr><td>ModuleNotFoundError: anthropic</td><td>2단계 <code>pip install</code>을 안 했거나 <code>(.venv)</code>가 안 켜짐. 다시 <code>source .venv/bin/activate</code> 후 설치.</td></tr>
      <tr><td>401 authentication_error</td><td>키가 틀렸거나 안 읽힘. <code>.env</code> 위치(같은 폴더)·오타·<code>load_dotenv()</code> 호출 확인.</td></tr>
      <tr><td>답이 중간에 잘림</td><td><code>max_tokens</code>를 키우기. (<code>resp.stop_reason</code>이 <code>"max_tokens"</code>면 길이 때문.)</td></tr>
    </table>

    <h2>➡️ 다음</h2>
    <p>이 <code>messages.create(...)</code> 호출이 <b>그대로</b> 챗 앱의 <code>/api/chat</code> 안으로 들어갑니다. 딱 하나만 바뀌어요 — "고정 질문" 대신 사용자가 입력한 질문을 넣는 것. 즉 <b>이 실습을 끝낸 순간, 챗 앱의 제일 어려운 조각은 이미 끝났어요.</b></p>
    <p class="note" style="margin-top:2rem"><a href="index.html">← 홈으로</a> · <a href="learn/foundations.html#slide-13">📚 Foundations 13번에서 더 깊이 보기</a></p>"""


def project_body():
    return r"""    <style>
      .proj-toc { display:flex; flex-wrap:wrap; gap:.4rem; margin:1rem 0 1.6rem; }
      .proj-toc a { background:#1f2530; color:#58a6ff; border:1px solid #30363d;
        border-radius:999px; padding:.2rem .7rem; font-size:.85rem; text-decoration:none; }
      .proj-toc a:hover { border-color:#58a6ff; }
      .sec { border-top:1px solid #30363d; margin:2rem 0 0; padding-top:1.2rem; scroll-margin-top:1rem; }
      .sec > h2 { color:#58a6ff; }
      .term { background:#0f1a12; border-left:3px solid var(--green,#3fb950); border-radius:0 8px 8px 0;
        padding:.5rem .9rem; margin:.7rem 0; font-size:.93rem; }
      table.cmp { border-collapse:collapse; width:100%; margin:.8rem 0; font-size:.9rem; }
      table.cmp th, table.cmp td { border:1px solid #30363d; padding:.45rem .65rem; text-align:left; vertical-align:top; }
      table.cmp th { background:#1f2530; color:#e6edf3; }
      table.cmp code { background:#1f2530; }
      .warn { background:#2a1d11; border-left:3px solid #e3b341; border-radius:6px;
        padding:.6rem .9rem; margin:.8rem 0; font-size:.93rem; }
      .warn b { color:#e3b341; }
      .ok { background:#11271a; border-left:3px solid #3fb950; border-radius:6px;
        padding:.6rem .9rem; margin:.8rem 0; font-size:.93rem; }
      .ok b { color:#3fb950; }
      .ph { background:#161b22; border:1px dashed #30363d; border-radius:8px;
        padding:.9rem 1.1rem; margin:.8rem 0; color:#8b949e; }
      .ph b { color:#c9d1d9; }
    </style>

    <h1>🛩️ RAG 콘테스트 프로젝트 <span class="badge">FAA 항공법 챗봇</span></h1>
    <p class="sub"><a href="index.html">← 홈으로</a> · 미국 연방항공규정(14 CFR) 위에 RAG 챗봇을 만들어 토너먼트로 겨루는 프로젝트. 여기에 개요·배경지식·실험·작업일지를 기록한다.</p>

    <div class="proj-toc">
      <a href="#overview">📌 개요</a>
      <a href="#embeddings">🔢 임베딩 모델</a>
      <a href="#experiments">🧪 실험 계획</a>
      <a href="#log">📝 작업 일지</a>
      <a href="#ideas">💡 메모·아이디어</a>
      <a href="#questions">❓ 질문 모음</a>
    </div>

    <section class="sec" id="overview">
      <h2>📌 개요</h2>
      <p class="analogy">📖 <b>비유:</b> RAG = <b>오픈북 시험 보는 학생</b>. 머릿속 지식만으로 답하면 틀린 말을 지어내니(환각), <b>관련 조항을 펼쳐 읽고 그 근거로</b> 답하게 만든다.</p>
      <p>대회는 같은 FAA 코퍼스(6개 PDF, 약 1,297쪽)로 모두가 챗봇을 만들고, 당일 <b>처음 보는 질문 3개</b>로 1:1 토너먼트. <b>더 잘 근거대고 인용한</b> 쪽이 승급. 승부처는 <b>답변 품질(30) + 인용·근거(25) = 55점.</b></p>
      <p class="note">전략 원본: <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/STRATEGY.md">STRATEGY.md</a> · 실험 런북: <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/EXPERIMENTS.md">EXPERIMENTS.md</a></p>
    </section>

    <section class="sec" id="embeddings">
      <h2>🔢 임베딩 모델 배경지식</h2>
      <p class="analogy">🧭 <b>비유:</b> 임베딩 = 문장을 <b>'뜻 좌표'</b>로 바꾸는 것. 뜻이 비슷한 문장은 좌표도 가까이 찍힌다 → 그래서 "뜻으로 검색"이 된다.</p>

      <div class="term"><b>차원(dimension)</b> = 벡터 숫자의 개수. MiniLM=384, bge·e5·gte=1024. 클수록 뜻을 세밀히 표현(대신 무겁고 느림).</div>
      <div class="term"><b>MTEB</b> = 임베딩 모델 공식 성적표. 검색 등 과제로 순위를 매긴 벤치마크.</div>
      <div class="term"><b>쿼리 프리픽스</b> = bge·e5를 <i>검색</i>에 쓸 때 질문 앞에 붙이는 주문. 안 붙이면 성능 급락.</div>

      <h3>우리 계획 — 기준 1 + 후보 3</h3>
      <p>스타터 기본 <code>MiniLM</code>(384차원·다국어용)은 작고 범용이라 영어 법조문엔 약하다. 영어 특화·고차원 모델 3개를 후보로 두고, <b>자동 실험(Recall@K)으로 어느 게 최고인지 데이터로</b> 고른다.</p>
      <table class="cmp">
        <tr><th>모델</th><th>sentence-transformers 이름</th><th>차원</th><th>프리픽스</th><th>특징</th></tr>
        <tr><td>기준 MiniLM</td><td><code>paraphrase-multilingual-MiniLM-L12-v2</code></td><td>384</td><td>불필요</td><td>스타터 기본·빠름·약함(비교 기준선)</td></tr>
        <tr><td><b>bge-large-en</b></td><td><code>BAAI/bge-large-en-v1.5</code></td><td>1024</td><td>필요</td><td>영어 검색 강자, 안정적</td></tr>
        <tr><td><b>e5-large</b></td><td><code>intfloat/e5-large-v2</code></td><td>1024</td><td><code>query:</code>/<code>passage:</code></td><td>bge와 쌍벽</td></tr>
        <tr><td><b>gte-large</b></td><td><code>thenlper/gte-large</code></td><td>1024</td><td>불필요</td><td>교체 가장 쉬움</td></tr>
      </table>

      <div class="warn"><b>함정 — 쿼리 프리픽스 ⚠️</b> bge·e5는 검색용으로 쓸 때 정해진 문구를 앞에 붙여야 제 성능이 난다. e5는 질문에 <code>query: </code>·문서에 <code>passage: </code>, bge는 검색용 지시문. <b>gte는 불필요</b>라 교체가 제일 쉽다. 안 붙이면 "좋은 모델로 바꿨는데 더 나빠짐"이 생긴다.</div>

      <div class="ok"><b>대회 규칙</b> 임베딩 모델은 <b>로컬 모델만 허용</b>(클라우드 임베딩 API ❌). bge·e5·gte는 전부 로컬·무료라 OK.</div>

      <p class="note">왜 하나로 안 정하고 다 시험하나 — "추측 말고 측정". 홀드아웃 질문으로 <b>Recall@K</b>(정답 조항이 검색 상위 K에 든 비율)를 재서 1등을 가린다. Claude를 안 부르니 채점이 공짜.</p>
    </section>

    <section class="sec" id="experiments">
      <h2>🧪 실험 계획 (요약)</h2>
      <p>전부 조합(폭발) 대신 <b>싼 검색 축은 작은 그리드, 비싼 생성 축은 순차</b>. 검색 실험(청킹·임베딩·검색방식·top-K)은 Claude 없이 <b>Recall@K로 공짜 채점</b>, 생성 실험만 과금(Batches 50%↓).</p>
      <p class="note">자세한 절차: <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/EXPERIMENTS.md">EXPERIMENTS.md</a></p>
    </section>

    <section class="sec" id="log">
      <h2>📝 작업 일지</h2>
      <div class="ph"><b>여기에 날짜별로 기록:</b> 오늘 한 일 / 막힌 점 / 해결. (예: "Phase 0 완료 — 스타터 Apollo 1,133청크 인덱싱 성공")</div>
    </section>

    <section class="sec" id="ideas">
      <h2>💡 메모·아이디어</h2>
      <div class="ph"><b>떠오른 개선 아이디어를 자유롭게:</b> §경계 청킹, 리랭킹, 인용 UI 등.</div>
    </section>

    <section class="sec" id="questions">
      <h2>❓ 질문 모음</h2>
      <div class="ph"><b>헷갈리는 것 / 나중에 물어볼 것:</b> 답을 찾으면 옆에 정리.</div>
    </section>

    <p class="note" style="margin-top:2rem"><a href="index.html">← 홈으로</a></p>"""


def shell(title, body, active=""):
    return SHELL.format(title=html.escape(title), sidebar=sidebar_html(active), body=body)


def build():
    commits = get_commits()
    last_updated = commits[0]["date"] if commits else "(아직 커밋 없음)"
    count = len(commits)

    OUT_HOME.parent.mkdir(parents=True, exist_ok=True)
    OUT_HOME.write_text(
        shell("ksept-lab · 학습 홈", home_body(last_updated, count), active="index.html"),
        encoding="utf-8",
    )
    OUT_NOTES.write_text(
        shell("프로젝트 노트 · ksept-lab", notes_body(), active="notes.html"),
        encoding="utf-8",
    )
    OUT_PRACTICE.write_text(
        shell("첫 API 호출 실습 · ksept-lab", practice_body(), active="practice.html"),
        encoding="utf-8",
    )
    OUT_PROJECT.write_text(
        shell("RAG 콘테스트 · ksept-lab", project_body(), active="rag-project.html"),
        encoding="utf-8",
    )
    OUT_CHANGELOG.write_text(
        shell("변경 이력 · ksept-lab", changelog_body(render_timeline(commits), last_updated, count),
              active="changelog.html"),
        encoding="utf-8",
    )
    print(f"wrote index.html, practice.html, notes.html, rag-project.html, changelog.html  ({count} commits)")


# ─────────────────────────────────────────────────────────────────────────────
# 셸 템플릿. CSS의 중괄호는 {{ }}로 이스케이프. {title}/{sidebar}/{body}만 치환된다.
# body 값 안의 중괄호(mermaid 등)는 '치환되는 값'이라 다시 해석되지 않는다.
# ─────────────────────────────────────────────────────────────────────────────
SHELL = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0d1117; --panel: #161b22; --border: #30363d;
      --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --green: #3fb950;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; scroll-padding-top: 1rem; }}
    body {{ margin: 0; background: var(--bg); color: var(--fg);
      font-family: -apple-system, "Apple SD Gothic Neo", "Pretendard", system-ui, sans-serif; line-height: 1.7; }}
    .wrap {{ max-width: 860px; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }}
    .layout {{ display: flex; align-items: flex-start; }}
    .sidebar {{ position: sticky; top: 0; align-self: flex-start; width: 220px; height: 100vh;
      overflow-y: auto; flex: 0 0 auto; background: var(--panel); border-right: 1px solid var(--border); padding: 1.5rem 1rem; }}
    .side-title {{ font-weight: 700; margin-bottom: 1rem; font-size: 1.05rem; }}
    .side-title a {{ color: var(--fg); text-decoration: none; }}
    .side-group {{ color: var(--muted); font-size: .75rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: .08em; margin: 1.2rem 0 .4rem; }}
    .sidebar nav {{ display: flex; flex-direction: column; gap: .1rem; }}
    .sidebar nav a {{ color: var(--fg); text-decoration: none; padding: .4rem .6rem; border-radius: 6px; font-size: .92rem; }}
    .sidebar nav a:hover {{ background: #1f2530; color: var(--accent); }}
    .sidebar nav a.active {{ background: #1f6feb22; color: var(--accent); font-weight: 600; }}
    .side-foot {{ color: var(--muted); font-size: .8rem; margin-top: 1.5rem; line-height: 1.7; }}
    .side-foot a {{ color: var(--accent); text-decoration: none; }}
    @media (max-width: 720px) {{
      .layout {{ flex-direction: column; }}
      .sidebar {{ position: static; width: auto; height: auto; border-right: none; border-bottom: 1px solid var(--border); }}
      .sidebar nav {{ flex-direction: row; flex-wrap: wrap; }}
    }}
    h1 {{ font-size: 2rem; margin: 0 0 .25rem; }}
    h2 {{ font-size: 1.35rem; margin: 2.75rem 0 .75rem; border-bottom: 1px solid var(--border); padding-bottom: .4rem; }}
    h3 {{ font-size: 1.05rem; margin: 1.5rem 0 .4rem; color: var(--accent); }}
    p, li {{ color: var(--fg); }}
    .sub {{ color: var(--muted); margin-top: 0; }}
    .sub a {{ color: var(--accent); }}
    code {{ background: #1f2530; padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.25rem; margin: 1rem 0; }}
    .analogy {{ background: #11271a; border-left: 3px solid var(--green); border-radius: 6px; padding: .65rem .9rem; margin: 0 0 .85rem; font-size: .98rem; }}
    .analogy b {{ color: var(--green); }}
    .mermaid {{ background: #fff; border-radius: 8px; padding: 1rem; margin: .75rem 0; overflow-x: auto; }}
    .mermaid, .mermaid span, .mermaid div, .mermaid p, .mermaid foreignObject,
    .mermaid .nodeLabel, .mermaid .edgeLabel, .mermaid .label, .mermaid text {{ color: #1a1a1a !important; fill: #1a1a1a !important; }}
    .mermaid .edgeLabel {{ background-color: #fff !important; }}
    .note {{ color: var(--muted); font-size: .92rem; }}
    .note a {{ color: var(--accent); }}
    .entry-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: .8rem; margin: 1.5rem 0; }}
    .entrycard {{ display: block; background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
      padding: 1.1rem 1.25rem; text-decoration: none; transition: border-color .12s, background .12s; }}
    .entrycard:hover {{ border-color: var(--accent); background: #1b2330; }}
    .entrycard b {{ display: block; font-size: 1.12rem; color: var(--fg); margin-bottom: .3rem; }}
    .entrycard span {{ font-size: .88rem; color: var(--muted); line-height: 1.5; }}
    .topic-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: .6rem; margin: 1rem 0 1.5rem; }}
    .topiccard {{ display: block; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: .7rem .9rem; text-decoration: none; }}
    .topiccard:hover {{ border-color: var(--accent); }}
    .topiccard b {{ display: block; color: var(--accent); margin-bottom: .15rem; }}
    .topiccard span {{ font-size: .85rem; color: var(--muted); }}
    ul.timeline {{ list-style: none; padding: 0; margin: 0; position: relative; }}
    ul.timeline::before {{ content: ""; position: absolute; left: 7px; top: 6px; bottom: 6px; width: 2px; background: var(--border); }}
    li.commit {{ display: flex; gap: .9rem; padding: .6rem 0; position: relative; }}
    li.commit .sha {{ flex: 0 0 auto; z-index: 1; }}
    li.commit .sha::before {{ content: ""; position: absolute; left: 2px; top: 1.05rem; width: 12px; height: 12px;
      border-radius: 50%; background: var(--green); border: 2px solid var(--bg); }}
    li.commit .sha code {{ margin-left: 1.4rem; }}
    li.commit .subject {{ font-weight: 600; }}
    li.commit .meta {{ color: var(--muted); font-size: .85rem; }}
    ul.body {{ margin: .4rem 0 0; padding-left: 1.1rem; }}
    ul.body li {{ color: var(--muted); font-size: .92rem; }}
    .badge {{ display: inline-block; background: #1f6feb22; color: var(--accent); border: 1px solid #1f6feb55;
      border-radius: 999px; padding: .1rem .6rem; font-size: .8rem; }}
    .date-group {{ margin: .25rem 0; }}
    h3.date {{ color: var(--muted); font-size: .85rem; font-weight: 700; margin: 1.5rem 0 .25rem; }}
    details.older {{ margin-top: 1.5rem; border-top: 1px dashed var(--border); padding-top: .5rem; }}
    details.older > summary {{ cursor: pointer; color: var(--accent); padding: .5rem 0; list-style: none; }}
    details.older > summary::-webkit-details-marker {{ display: none; }}
  </style>
</head>
<body>
  <div class="layout">
{sidebar}
  <div class="wrap">
{body}
  </div>
  </div><!-- /layout -->

  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, theme: "default", securityLevel: "loose" }});
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
