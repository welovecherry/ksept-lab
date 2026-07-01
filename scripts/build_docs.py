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
import re
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
    ("changelog.html", "📜 변경 이력"),
]

# RAG 콘테스트: 사이드바에서 번호로 나뉘는 하위 페이지들 (학습 모듈처럼).
# (파일, 번호, 짧은 제목, [이 페이지에 담을 section id들])
RAG_PAGES = [
    ("rag-project.html", "", "🛩️ RAG 콘테스트", ["overview"]),
    ("rag-glossary.html", "01", "용어 사전", ["glossary"]),
    ("rag-embeddings.html", "02", "임베딩 모델", ["embeddings"]),
    ("rag-cache.html", "03", "캐시 원리", ["embed-tutorial"]),
    ("rag-setup.html", "04", "모델 세팅", ["embed-setup"]),
    ("rag-experiments.html", "05", "실험 계획", ["experiments"]),
    ("rag-ensemble.html", "06", "앙상블", ["ensemble"]),
    ("rag-progress.html", "07", "진행 단계", ["progress"]),
    ("rag-log.html", "08", "작업 일지", ["log", "ideas", "questions"]),
]
RAG_TITLES = {  # 각 페이지 h1 (사이드바 짧은 제목과 별개)
    "rag-project.html": "🛩️ RAG 콘테스트 프로젝트",
    "rag-glossary.html": "📖 용어 사전",
    "rag-embeddings.html": "🔢 임베딩 모델",
    "rag-cache.html": "🎓 캐시 원리 튜토리얼",
    "rag-setup.html": "⚙️ 임베딩 모델 세팅",
    "rag-experiments.html": "🧪 실험 계획",
    "rag-ensemble.html": "🧩 앙상블 — 모델 합치기",
    "rag-progress.html": "🛠️ 진행 단계 (Phase 0~1)",
    "rag-log.html": "📝 작업 일지 · 메모 · 질문",
}

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
def rag_subnav(active=""):
    """RAG 콘테스트 = 그룹 헤더 + 번호 매긴 하위 페이지(01·02·03…)."""
    head_file = RAG_PAGES[0][0]
    head_cls = ' class="active"' if active == head_file else ""
    subs = []
    for href, num, title, _ids in RAG_PAGES[1:]:
        cls = ' class="active"' if href == active else ""
        subs.append(f'<a href="{href}"{cls}><span class="n">{num}</span>{html.escape(title)}</a>')
    return (f'<a href="{head_file}"{head_cls}>🛩️ RAG 콘테스트</a>'
            f'<div class="subnav">{"".join(subs)}</div>')


def sidebar_html(active=""):
    items = []
    for href, name in SITE:
        cls = ' class="active"' if href == active else ""
        items.append(f'<a href="{href}"{cls}>{html.escape(name)}</a>')
        if href == "notes.html":
            items.append(rag_subnav(active))
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
      .step { border:1px solid #30363d; border-radius:10px; padding:.9rem 1.1rem;
        margin:1rem 0; background:#0d1117; }
      .step h4 { margin:0 0 .55rem; font-size:1rem; display:flex; align-items:center;
        justify-content:space-between; gap:.6rem; }
      .step .st { font-size:.76rem; font-weight:700; border-radius:999px;
        padding:.12rem .62rem; white-space:nowrap; }
      .step .st.done { background:#11271a; color:#3fb950; border:1px solid #238636; }
      .step .st.now  { background:#2a1d11; color:#e3b341; border:1px solid #9e6a03; }
      .step .st.todo { background:#161b22; color:#8b949e; border:1px solid #30363d; }
      .step dl { margin:.3rem 0 0; display:grid; grid-template-columns:auto 1fr;
        gap:.28rem .8rem; font-size:.9rem; }
      .step dt { color:#8b949e; white-space:nowrap; }
      .step dd { margin:0; }
    </style>

    <h1>🛩️ RAG 콘테스트 프로젝트 <span class="badge">FAA 항공법 챗봇</span></h1>
    <p class="sub"><a href="index.html">← 홈으로</a> · 미국 연방항공규정(14 CFR) 위에 RAG 챗봇을 만들어 토너먼트로 겨루는 프로젝트. 여기에 개요·배경지식·실험·작업일지를 기록한다.</p>

    <div class="proj-toc">
      <a href="#overview">📌 개요</a>
      <a href="#glossary">📖 용어 사전</a>
      <a href="#embeddings">🔢 임베딩 모델</a>
      <a href="#embed-tutorial">🎓 캐시 원리</a>
      <a href="#embed-setup">⚙️ 모델 세팅</a>
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

    <section class="sec" id="glossary">
      <style>
        .glgroup { margin:1.1rem 0 1.4rem; }
        .glgroup > h3 { color:#3fb950; border-bottom:1px solid #30363d; padding-bottom:.25rem; }
        .gl { display:flex; gap:.6rem; padding:.5rem 0; border-bottom:1px dashed #21262d; flex-wrap:wrap; }
        .gl .t { flex:0 0 13rem; color:#e3b341; font-weight:700; }
        .gl .d { flex:1 1 18rem; line-height:1.7; color:#c9d1d9; }
        .gl .d code { background:#1f2530; }
        @media (max-width:640px){ .gl .t { flex-basis:100%; } }
      </style>
      <h2>📖 용어 사전 — 계획에 나온 말, 전부 쉽게</h2>
      <p class="sub">처음 보는 단어가 많아도 괜찮다. 비유와 예시로 하나씩. 위에서 아래로 읽으면 RAG 한 바퀴가 돈다.</p>

      <div class="glgroup">
        <h3>🌐 1. 큰 그림</h3>
        <div class="gl"><span class="t">RAG (검색 증강 생성)</span><span class="d">Retrieval-Augmented Generation. <b>오픈북 시험 보는 학생</b>. 머릿속 지식만으로 답하지 않고, 관련 문서를 <b>찾아 읽고(검색)</b> 그 근거로 <b>답을 쓴다(생성)</b>.</span></div>
        <div class="gl"><span class="t">코퍼스 (corpus)</span><span class="d">말뭉치 = <b>문서 한 더미</b>. 챗봇이 근거로 삼는 자료 전체. 우리 경우 FAA 항공법 PDF 6개.</span></div>
        <div class="gl"><span class="t">FAA</span><span class="d">미국 연방항공청. 미국 하늘의 규칙을 정하는 정부기관.</span></div>
        <div class="gl"><span class="t">CFR · Title 14</span><span class="d">미국 연방규정집(법전). 그중 14편이 항공·우주. = 우리 코퍼스의 정체.</span></div>
        <div class="gl"><span class="t">도메인 한정 챗봇</span><span class="d">한 분야(항공법)만 답하는 챗봇. 범위 밖 질문("점심 뭐 먹지?")엔 "출처 밖"이라 <b>거부</b>해야 점수.</span></div>
        <div class="gl"><span class="t">루브릭 (rubric)</span><span class="d">채점 기준표. 6개 항목 100점(품질30·인용25·비용15·명확10·UX10·견고10).</span></div>
        <div class="gl"><span class="t">토너먼트 / 상대평가</span><span class="d">두 챗봇이 같은 새 질문에 답하고 <b>더 나은 쪽</b>이 승급. 절대 점수가 아니라 "옆보다 나은가".</span></div>
      </div>

      <div class="glgroup">
        <h3>🧱 2. 데이터 만들기 (문서 → 검색 준비)</h3>
        <div class="gl"><span class="t">텍스트 추출</span><span class="d">PDF에서 글자만 뽑아내기. PDF는 글자가 좌표로 흩어져 있어 표·머리말이 섞여 지저분 → 정리가 필요.</span></div>
        <div class="gl"><span class="t">청크 (chunk)</span><span class="d">긴 문서에서 잘라낸 <b>한 토막</b>(책의 한 페이지 조각). 검색·인용의 최소 단위.</span></div>
        <div class="gl"><span class="t">청킹 (chunking)</span><span class="d">문서를 청크로 <b>자르는 일</b>. 너무 크면 검색이 흐려지고, 너무 작으면 맥락이 끊긴다.</span></div>
        <div class="gl"><span class="t">오버랩 (overlap)</span><span class="d">조각끼리 <b>겹치는 부분</b>. 자른 경계에서 맥락이 끊기지 않게 앞 조각 끝 일부를 다음 조각에 겹쳐 넣음.</span></div>
        <div class="gl"><span class="t">§조항 / 조항번호</span><span class="d">법조문의 항목 번호(예: <code>§91.151</code> = 연료 예비 규정). "한 조각 = 한 조항"이 가장 깔끔한 의미 단위.</span></div>
        <div class="gl"><span class="t">메타데이터 (metadata)</span><span class="d">조각에 붙이는 <b>꼬리표</b>(예: "이건 §91.151, Part 91"). 검색·인용을 한꺼번에 좋게 만든다.</span></div>
        <div class="gl"><span class="t">임베딩 (embedding)</span><span class="d">문장을 <b>'뜻 좌표'</b>(숫자 묶음)로 바꾸기. 뜻이 비슷하면 좌표도 가까이.</span></div>
        <div class="gl"><span class="t">벡터 (vector)</span><span class="d">그 숫자 묶음 자체. "공간 속 한 점".</span></div>
        <div class="gl"><span class="t">차원 (dimension)</span><span class="d">벡터 숫자의 개수. MiniLM=384, bge·e5·gte=1024. 클수록 세밀(대신 무겁다).</span></div>
        <div class="gl"><span class="t">인덱스 · <code>index.pkl</code></span><span class="d">모든 청크 + 그 벡터를 담은 <b>검색용 카드 상자</b> 파일.</span></div>
        <div class="gl"><span class="t">인덱싱 (indexing)</span><span class="d">문서를 잘라 벡터로 바꿔 인덱스에 저장하는 <b>전 과정</b>(사서가 색인 만들기).</span></div>
        <div class="gl"><span class="t">sentence-transformers</span><span class="d">문장을 임베딩으로 바꿔주는 <b>로컬·무료</b> 파이썬 도구. 인터넷·API 불필요.</span></div>
        <div class="gl"><span class="t">쿼리 프리픽스</span><span class="d">bge·e5를 검색에 쓸 때 질문 앞에 붙이는 <b>주문</b>(e5는 <code>query:</code>). 안 붙이면 성능 급락. gte는 불필요.</span></div>
        <div class="gl"><span class="t">MTEB</span><span class="d">임베딩 모델 공식 성적표(벤치마크). "어느 모델이 검색을 더 잘하나"의 근거.</span></div>
      </div>

      <div class="glgroup">
        <h3>🔎 3. 검색 (관련 조항 찾기)</h3>
        <div class="gl"><span class="t">검색 (retrieval)</span><span class="d">질문에 맞는 청크를 인덱스에서 골라오기. RAG의 심장.</span></div>
        <div class="gl"><span class="t">의미검색 (dense)</span><span class="d">뜻이 비슷한 걸 찾기(임베딩 사용). 똑똑하지만 <b>흐릿</b>해서 정확한 번호엔 약할 수 있음.</span></div>
        <div class="gl"><span class="t">코사인 유사도</span><span class="d">두 벡터(뜻 좌표)가 <b>얼마나 같은 방향인가</b>를 0~1로 잰 값. 클수록 비슷.</span></div>
        <div class="gl"><span class="t">키워드검색 · BM25 (sparse)</span><span class="d">정확히 그 <b>단어/번호</b>가 든 조각 찾기(예: "§91.151"). 정확하지만 융통성 없음.</span></div>
        <div class="gl"><span class="t">하이브리드 (hybrid)</span><span class="d">의미검색 + 키워드검색 <b>점수를 합쳐</b> 재정렬. 법조문처럼 정확 단어가 생명인 자료에 강함.</span></div>
        <div class="gl"><span class="t">top-K</span><span class="d">검색에서 <b>상위 K개</b> 조각만 골라 챗봇에 줌(예: K=5면 5조각). 많으면 정확↑·토큰↑.</span></div>
        <div class="gl"><span class="t">리랭킹 (reranking)</span><span class="d">1차로 넉넉히 뽑은 뒤 <b>정밀 재채점</b>해 진짜 좋은 순으로 다시 정렬(cross-encoder 사용).</span></div>
        <div class="gl"><span class="t">top-K 다양성</span><span class="d">5조각이 <b>전부 한 문서</b>에서 안 나오게 분산 → 여러 Part를 합쳐야 하는 질문에 대비.</span></div>
      </div>

      <div class="glgroup">
        <h3>✍️ 4. 생성 (답 만들기)</h3>
        <div class="gl"><span class="t">프롬프트 (prompt)</span><span class="d">모델에게 주는 <b>지시문+자료</b>. 시스템 프롬프트 = "넌 이렇게 답해" 규칙.</span></div>
        <div class="gl"><span class="t">CONTEXT 블록</span><span class="d">검색한 조각들을 번호 붙여(<code>[1] §91.151: ...</code>) 질문과 함께 모델에 넣는 부분.</span></div>
        <div class="gl"><span class="t">토큰 (token)</span><span class="d">모델이 글을 세는 <b>단위</b>(대략 단어 조각). 입력+출력 토큰만큼 과금.</span></div>
        <div class="gl"><span class="t">환각 (hallucination)</span><span class="d">근거 없이 <b>그럴듯하게 지어낸</b> 답. 항공법에선 치명적(틀린 연료 시간 = 위험).</span></div>
        <div class="gl"><span class="t">종합 (synthesis)</span><span class="d">여러 조각을 나열만 하지 말고 <b>비교·통합</b>해 한 답으로. 루브릭이 요구.</span></div>
        <div class="gl"><span class="t">거부 (abstention)</span><span class="d">근거가 없으면 우기지 말고 <b>"출처에 없습니다"</b>라고 말하기. 환각 방지·신뢰 점수.</span></div>
        <div class="gl"><span class="t">인용 · <code>[n]</code> · provenance</span><span class="d">주장마다 출처를 <b>[1]</b>처럼 표시하고, 그게 진짜 그 조항을 가리키게. 가짜 출처 금지(25점).</span></div>
        <div class="gl"><span class="t">프롬프트 인젝션</span><span class="d">검색된 문서 안에 숨은 악성 지시("이전 지시 무시하고…")에 모델이 휘둘리는 공격. 방어 필요.</span></div>
        <div class="gl"><span class="t">약어 정의</span><span class="d">처음 나오는 약어를 풀어주기(VFR=시계비행규칙). 명확성 점수.</span></div>
      </div>

      <div class="glgroup">
        <h3>📊 5. 평가 &amp; 실험</h3>
        <div class="gl"><span class="t">베이스라인 (baseline)</span><span class="d">아무것도 안 고친 <b>출발점 점수</b>. "얼마나 좋아졌나"의 기준.</span></div>
        <div class="gl"><span class="t">홀드아웃 (hold-out)</span><span class="d">튜닝에 안 쓰고 <b>검증에만</b> 쓰는 비밀 시험지. 처음 보는 질문을 흉내 → 과적합 점검.</span></div>
        <div class="gl"><span class="t">정답 라벨 (label)</span><span class="d">채점용 모범답안. 우리 경우 "이 질문의 근거는 §91.151" 같은 <b>정답 조항번호</b>.</span></div>
        <div class="gl"><span class="t">과적합 (overfitting)</span><span class="d">연습문제 <b>몇 개에만</b> 잘 맞춰져, 새 질문엔 무너지는 상태. 대회의 가장 큰 함정.</span></div>
        <div class="gl"><span class="t">Recall@K (회수율)</span><span class="d">정답 §조항이 <b>검색 상위 K개</b>에 들어온 비율. Claude 없이 코드로 채점 → 공짜.</span></div>
        <div class="gl"><span class="t">커버리지 (coverage)</span><span class="d">정답이 여러 개일 때 <b>몇 개를 맞췄나</b> 비율(2개 중 1개 = 0.5). 교차질문 채점에 필요.</span></div>
        <div class="gl"><span class="t">MRR</span><span class="d">정답이 <b>몇 번째로</b> 떴나의 역수 평균(1위=1.0, 5위=0.2). "얼마나 위로 올렸나".</span></div>
        <div class="gl"><span class="t">그리드 서치 (grid search)</span><span class="d">손잡이(설정) 값들을 <b>여러 조합</b>으로 다 시험해 최고를 찾기.</span></div>
        <div class="gl"><span class="t">OFAT / 탐욕적 순차</span><span class="d">손잡이를 <b>하나만</b> 돌리고 이긴 값을 고정한 채 다음으로. 해석 쉽고 호출 적음.</span></div>
        <div class="gl"><span class="t">LLM-as-judge (LLM 심판)</span><span class="d">답을 <b>Claude가 채점</b>. 생성 모델과 심판 모델을 분리해 편향을 줄임.</span></div>
        <div class="gl"><span class="t">프로그램 검증</span><span class="d">"인용한 §가 실제 그 청크에 있나"를 <b>코드로 대조</b> → 공짜·객관, 가짜 인용 색출.</span></div>
        <div class="gl"><span class="t">JSONL</span><span class="d">한 줄 = 한 JSON. 실험 결과를 한 줄씩 덧붙여 저장(밤새 돌다 죽어도 이미 쓴 줄은 안전).</span></div>
        <div class="gl"><span class="t">Batches API</span><span class="d">요청을 모아 한꺼번에 처리하는 <b>50% 할인</b> 방식. 밤샘 대량 실험에 최적.</span></div>
        <div class="gl"><span class="t">비용 가드</span><span class="d">누적 비용이 한도를 넘으면 <b>자동 중단</b>. 공유 키($100) 보호.</span></div>
      </div>

      <div class="glgroup">
        <h3>🛠️ 6. 도구 &amp; 환경</h3>
        <div class="gl"><span class="t">모델 (Claude)</span><span class="d">답을 쓰는 LLM. <code>opus-4-8</code>(똑똑·비쌈) / <code>sonnet-4-6</code>(균형·스타터 기본) / <code>haiku-4-5</code>(빠름·쌈).</span></div>
        <div class="gl"><span class="t">API · API 키 · <code>.env</code></span><span class="d">API=프로그램이 Claude 서버에 주문 넣는 창구. 키=신분증+결제수단. <code>.env</code>=키를 숨겨 두는 파일(커밋 금지).</span></div>
        <div class="gl"><span class="t">venv (가상환경)</span><span class="d">프로젝트 <b>전용 도구 서랍</b>. 여기 라이브러리를 깔면 다른 프로젝트와 안 꼬임.</span></div>
        <div class="gl"><span class="t">GitHub Pages · CI · 워크플로</span><span class="d">main에 push하면 자동(워크플로 <code>pages.yml</code>)으로 사이트를 빌드·배포하는 구조. 지금 이 페이지가 그렇게 올라온다.</span></div>
      </div>

      <p class="note">더 풀어야 할 용어가 있으면 알려줘 — 이 사전에 계속 추가한다.</p>
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

    <section class="sec" id="embed-tutorial">
      <h2>🎓 튜토리얼 — 모델은 어떻게 "받아지나" (캐시의 원리)</h2>
      <p class="sub">"4개 모델을 한 번씩 로드해 캐시"가 <b>왜 가능한지</b>를, 실제 캐시를 열어보며 6강으로 배운다.</p>

      <div class="term"><b>HuggingFace Hub</b> = 모델들의 GitHub(공개 저장소).</div>
      <div class="term"><b>가중치(weights)</b> = 모델의 '뇌' = 학습으로 정해진 숫자 덩어리(<code>.safetensors</code>).</div>
      <div class="term"><b>토크나이저(tokenizer)</b> = 글자를 모델이 먹는 토큰으로 쪼개는 사전.</div>
      <div class="term"><b>캐시(cache)</b> = 한 번 받은 걸 디스크에 보관해 재사용.</div>

      <h3>1강. 모델은 사실 '파일 묶음'이다</h3>
      <p class="analogy">📦 <b>비유:</b> 모델 = <b>조립가구 한 상자</b> = 부품(가중치) + 설명서(config) + 나사규격(tokenizer).</p>
      <p>우리가 Phase 0에서 받은 MiniLM의 실제 캐시 내용:</p>
      <pre><code>model.safetensors        # 470MB — '뇌'(학습된 숫자)
config.json              # 모델 구조 설명서
tokenizer.json           # 글자를 토큰으로 쪼개는 사전
modules.json             # 조립 순서
README.md, ...           # 기타</code></pre>

      <h3>2강. 모델 이름은 '주소'다</h3>
      <p><code>BAAI/bge-large-en-v1.5</code> = Hub의 <b>조직/저장소</b> 주소 (GitHub의 <code>user/repo</code>와 같은 꼴). <code>SentenceTransformer("주소")</code>에 주면 거기서 받아온다.</p>

      <h3>3강. 로드 한 줄이 하는 일 = 3단계</h3>
      <pre><code>SentenceTransformer("intfloat/e5-large-v2")
  # ① 로컬 캐시에 있나 확인
  # ② 없으면 Hub에서 파일 다운로드 (느림 · 첫 1회만)
  # ③ 디스크 → RAM 으로 올려 사용 준비</code></pre>
      <p><b>첫 호출만 ②</b>가 일어나고, 그다음부턴 ①에서 바로 찾아 <b>오프라인</b>으로 쓴다.</p>

      <h3>4강. 캐시는 어디에, 어떻게 생겼나</h3>
      <pre><code>~/.cache/huggingface/hub/
  models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/
    snapshots/e8f8c211.../        # 커밋 해시 = 버전 고정(재현성)
      model.safetensors  config.json  tokenizer.json  modules.json ...</code></pre>
      <p><code>snapshots/&lt;해시&gt;</code>는 <b>그 시점 버전을 그대로 고정</b>한다 → 나중에 받아도 같은 결과(재현성).</p>

      <h3>5강. 그래서 "한 번씩 로드 = 미리 받기"가 성립</h3>
      <div class="ok"><b>핵심:</b> 다운로드는 <b>멱등(idempotent)</b> — 두 번째 로드는 받지 않고 <b>캐시를 읽는다</b>. 그래서 4개를 한 번씩만 로드하면 전부 캐시 완료, 당일은 인터넷 없이 쓸 수 있다.</div>
      <pre><code>du -sh ~/.cache/huggingface     # 받은 총 용량 확인
export HF_HUB_OFFLINE=1         # 당일: 캐시만 사용(네트워크 차단)</code></pre>

      <h3>6강. 실전 주의</h3>
      <ul>
        <li><b>디스크</b> ~4~5GB 필요(4개 합).</li>
        <li><b>네트워크가 끊겨도</b> 다시 실행하면 <b>이어받기</b> 된다(이미 받은 파일은 건너뜀).</li>
        <li><code>set HF_TOKEN</code> 경고는 <b>익명 다운로드 속도제한 안내</b>일 뿐 — 공개 모델은 토큰 없이도 받아진다.</li>
      </ul>
      <p class="note">이 원리를 알면 다음 <b>⚙️ 모델 세팅</b>의 "미리 받기" 스크립트가 *왜 한 번 돌리면 끝인지* 이해된다.</p>
    </section>

    <section class="sec" id="embed-setup">
      <h2>⚙️ 임베딩 모델 세팅 (미리 받아두기)</h2>
      <p class="analogy">📦 <b>비유:</b> 모델 세팅 = <b>장 미리 봐두기</b>. 요리(검색) 당일에 재료(모델)를 그때 사러 가면 늦으니, <b>전날 사다 냉장고(로컬 캐시)에 넣어둔다.</b></p>
      <p>sentence-transformers는 모델을 처음 부를 때 가중치(0.5~1.3GB)를 인터넷에서 받아 <code>~/.cache</code>에 저장한다. 한 번 받으면 그다음은 오프라인. <b>대회 전날 4개를 미리 받아 캐시</b>해 두면 당일 인터넷 사고·지연을 피한다. (총 약 4~5GB.)</p>

      <div class="ok"><b>✅ 실측 상태 (2026-06-30 완료):</b> 후보 4종 <b>모두 로컬 캐시 + 스모크 통과</b>. 세 후보 다 차원 1024d, "연료 조항 문장 &gt; 아폴로 문장" 유사도 순서 정상. 당일 다운로드 리스크 제거됨.</div>
      <table class="cmp">
        <tr><th>모델</th><th>차원</th><th>연료 vs 아폴로 (코사인)</th><th>용량</th><th>상태</th></tr>
        <tr><td>MiniLM (기준)</td><td>384</td><td>Phase 0 아폴로 스모크로 확인</td><td>458MB</td><td>✅</td></tr>
        <tr><td>bge-large-en-v1.5</td><td>1024</td><td><b>0.711</b> &gt; 0.311 <span class="note">(간격 0.40 — 분별력 큼)</span></td><td>1.2GB</td><td>✅</td></tr>
        <tr><td>e5-large-v2</td><td>1024</td><td><b>0.850</b> &gt; 0.708</td><td>1.2GB</td><td>✅</td></tr>
        <tr><td>gte-large</td><td>1024</td><td><b>0.897</b> &gt; 0.705</td><td>640MB</td><td>✅</td></tr>
      </table>
      <p class="note">주의: 이 스모크는 <b>문장 1쌍</b>으로 "작동 확인"만 한 것 — 모델 우열은 홀드아웃 전체 <b>Recall@K(실험 2)</b>에서 갈린다. 코사인 절댓값보다 <b>관련/무관 간격</b>이 검색 순위에 중요.</p>

      <h3>1) 준비 — venv + 패키지</h3>
      <p>프로젝트 전용 가상환경에 <code>sentence-transformers</code>가 있으면 끝(스타터 설치에 포함). 없으면:</p>
      <pre><code>pip install sentence-transformers</code></pre>

      <h3>2) 4개 모델 미리 받기 (코드 세션에서 1회)</h3>
      <p>각 이름을 한 번 로드하면 <b>자동 다운로드 + 캐시</b>된다.</p>
      <pre><code>from sentence_transformers import SentenceTransformer

MODELS = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 기준선
    "BAAI/bge-large-en-v1.5",
    "intfloat/e5-large-v2",
    "thenlper/gte-large",
]
for name in MODELS:
    print("downloading:", name)
    SentenceTransformer(name)     # 첫 호출 = 다운로드 + 캐시
print("all cached.")</code></pre>

      <h3>3) 캐시 확인 (위치·용량)</h3>
      <pre><code># 보통 여기에 저장됨
du -sh ~/.cache/huggingface 2>/dev/null
ls ~/.cache/huggingface/hub</code></pre>
      <div class="ok"><b>성공 신호:</b> <code>models--BAAI--bge-large-en-v1.5</code> 같은 폴더들이 보이고 총 용량이 수 GB.</div>

      <h3>4) 프리픽스 헬퍼 (모델별 주문)</h3>
      <p>bge·e5는 <b>검색용 질문 앞에 정해진 문구</b>를 붙여야 제 성능이 난다. gte·MiniLM은 그대로. 이 헬퍼를 인덱싱·검색 양쪽에서 같이 쓴다.</p>
      <pre><code>def embed(model, texts, model_name, kind):   # kind = "query" 또는 "passage"
    if "e5" in model_name:
        texts = [f"{kind}: {t}" for t in texts]                 # e5: query:/passage:
    elif "bge" in model_name and kind == "query":
        texts = ["Represent this sentence for searching relevant passages: " + t
                 for t in texts]                                # bge: 질문에만 지시문
    # gte, MiniLM: 프리픽스 없음
    return model.encode(texts, normalize_embeddings=True)</code></pre>
      <div class="warn"><b>주의 ⚠️</b> 문서(passage)는 인덱싱 때 <code>kind="passage"</code>, 질문은 검색 때 <code>kind="query"</code>로 — <b>둘을 일관되게</b> 해야 한다. 프리픽스를 빠뜨리면 "좋은 모델이 오히려 더 나쁨"이 생긴다.</div>

      <h3>5) 스모크 테스트 (잘 받아졌나)</h3>
      <p>질문 1개 vs 문단 2개의 코사인을 재서, <b>관련 문단이 더 높게</b> 나오면 정상.</p>
      <pre><code>m = SentenceTransformer("intfloat/e5-large-v2")
q  = embed(m, ["fuel reserve for day VFR flight"], "intfloat/e5-large-v2", "query")
ps = embed(m, ["No person may begin a flight unless there is enough fuel ...",
               "An applicant for a first-class medical certificate ..."],
           "intfloat/e5-large-v2", "passage")
print(q @ ps.T)     # 정규화돼 있어 내적 = 코사인. 1번이 더 커야 정상</code></pre>

      <h3>6) 대회날 오프라인 고정</h3>
      <p>캐시만 쓰도록 잠가 네트워크 사고를 차단:</p>
      <pre><code>export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1</code></pre>

      <p class="note">요약: <b>전날 ②로 4개 캐시 → ③로 확인 → ④ 헬퍼를 코드에 고정 → ⑤로 검증 → 당일 ⑥로 오프라인.</b> 이러면 모델 교체가 "이름만 바꾸면" 되는 상태가 된다.</p>
    </section>

    <section class="sec" id="experiments">
      <h2>🧪 실험 계획</h2>
      <p class="analogy">🔬 <b>비유:</b> 요리 대회 전날 <b>레시피 변수를 하나씩 바꿔 맛을 보는 것</b>. 단, 맛보기(채점)를 사람이 아니라 <b>자/저울(코드)</b>로 해서 수십 번을 밤새 자동으로.</p>
      <p>핵심: 설정을 <b>추측으로 정하지 않고 데이터로 고른다.</b> 처음 보는 질문(홀드아웃)에서 가장 잘 되는 설정을 자동 실험으로 찾는다. 대부분 참가자는 손으로 5문제 돌려보고 끝내는데, 이 하네스가 1등을 가르는 차별점.</p>

      <h3>① 큰 그림 — 3막</h3>
      <table class="cmp">
        <tr><th>막</th><th>시점</th><th>하는 일</th><th>공유 키</th></tr>
        <tr><td>🌞 1막 제작</td><td>낮(6h)</td><td>RAG 파이프라인 고도화 + 실험 하네스 제작</td><td>❌</td></tr>
        <tr><td>🌙 2막 자동실험</td><td>밤(무인)</td><td>설정 그리드 순회 → 답 생성 → <code>runs.jsonl</code> 적재 + 프로그램 검증</td><td>✅ 생성만</td></tr>
        <tr><td>🌅 3막 심판</td><td>아침</td><td>프로그램 점수로 1차 랭킹 → 상위만 LLM 심판 → 최적 설정 반영 → 출전</td><td>❌(Claude Code)</td></tr>
      </table>

      <h3>② 무엇을 실험하나 — 그리드 축(knobs)</h3>
      <table class="cmp">
        <tr><th>축</th><th>후보 값</th></tr>
        <tr><td>청크 크기</td><td>800 / 1200 / 1600자</td></tr>
        <tr><td>청킹 방식</td><td>문자 기준 / <b>§조항 경계</b> / 문서별 라우팅</td></tr>
        <tr><td>임베딩 모델</td><td>기준 MiniLM + 후보 bge·e5·gte</td></tr>
        <tr><td>검색 방식</td><td>의미 / BM25 / <b>하이브리드</b></td></tr>
        <tr><td>top-K</td><td>3 / 5 / 8</td></tr>
        <tr><td>리랭킹</td><td>off / on</td></tr>
        <tr><td>생성 모델</td><td>sonnet-4-6 / opus-4-8</td></tr>
        <tr><td>프롬프트</td><td>종합·거부 강조 A/B</td></tr>
      </table>

      <h3>③ 어떻게 — 탐욕적 순차 + "검색 먼저(무료)"</h3>
      <p>모든 조합을 다 돌리면 폭발(약 5천 가지). 그래서 <b>손잡이를 하나씩</b> 최적화하고 이긴 값을 고정한 채 다음으로 간다(탐욕적 순차). 순서는 <b>싸고 효과 큰 검색부터, 비싼 생성은 마지막</b>:</p>
      <table class="cmp">
        <tr><th>#</th><th>실험(축)</th><th>채점</th><th>Claude 호출</th></tr>
        <tr><td>0</td><td>베이스라인(현재 설정)</td><td>Recall@K</td><td>최소</td></tr>
        <tr><td>1</td><td>청킹</td><td>Recall@K</td><td>❌</td></tr>
        <tr><td>2</td><td>임베딩 모델</td><td>Recall@K</td><td>❌</td></tr>
        <tr><td>3</td><td>검색 방식</td><td>Recall@K</td><td>❌</td></tr>
        <tr><td>4</td><td>top-K</td><td>Recall@K + 토큰</td><td>❌</td></tr>
        <tr><td>5</td><td>생성 모델</td><td>LLM 심판 + 인용검증</td><td>✅</td></tr>
        <tr><td>6</td><td>프롬프트</td><td>LLM 심판</td><td>✅</td></tr>
      </table>
      <div class="ok"><b>핵심 절약:</b> 실험 1~4는 <b>검색 단계만</b> 보므로 Claude를 안 부르고 <b>Recall@K로 공짜 채점</b>. 비싼 생성 호출은 검색이 확정된 5~6에만 → 예산 1/10. 무료라서 검색 축은 작은 <b>전조합</b>으로 돌리고, 재인덱싱은 <b>청킹×임베딩(12개)</b>만 만들고 검색·K는 그 인덱스에서 재사용.</div>

      <h3>④ for문 한 바퀴에 하는 일 (실험 횟수 ≠ API 호출)</h3>
      <p>오케스트레이터 for문이 <b>한 바퀴</b> 돌 때 뭘 하는지가 헷갈리기 쉽다. <b>검색 바퀴</b>와 <b>생성 바퀴</b>는 하는 일이 다르다.</p>
      <p><b>검색 실험 한 바퀴</b> (예: §청킹 + bge + 하이브리드 + K5) — <b>Claude 안 부름 · 공짜</b>:</p>
      <pre><code>그 설정으로 홀드아웃 질문 12개를 하나씩:
  질문을 벡터로            (로컬 임베딩, 공짜)
  → 상위 K개 문단 검색
  → 정답 §가 그 안에 있나?   (Recall@K, 코드 채점)
  → runs.jsonl 에 한 줄 기록
※ API 호출 0번 — 전부 내 컴퓨터에서.</code></pre>
      <p><b>생성 실험 한 바퀴</b> (검색이 확정된 뒤에만) — <b>여기서만 API · 유료</b>:</p>
      <pre><code>검색으로 찾은 문단 + 질문 → Claude API 전송 → 답 받음
  → 인용 검증(코드) → 기록
※ 이 단계에서만 Claude API 호출.</code></pre>
      <p>그래서 <b>실험(평가) 횟수와 API 호출 수는 전혀 다르다</b>:</p>
      <table class="cmp">
        <tr><th>단계</th><th>실험(평가) 횟수</th><th>API 호출</th><th>비용</th></tr>
        <tr><td>검색 (1~4)</td><td>108설정 × 12질문 ≈ <b>1,296</b></td><td><b>0</b></td><td>$0</td></tr>
        <tr><td>생성 (5~6)</td><td>finalist 2 × 모델·프롬프트 × 12질문</td><td>≈ <b>70~120</b></td><td>유료(소량)</td></tr>
      </table>
      <div class="ok"><b>요점:</b> for문은 대부분 <b>공짜 검색 채점을 수천 번</b> 돌고, Claude API는 <b>마지막 생성에서만 수십 번</b> 부른다. 순진하게 전체 그리드(생성 포함)를 다 돌리면 <b>5,000번 넘는 API 호출</b>로 폭발 — 그걸 피하려 검색(무료)과 생성(유료)을 갈라놓은 것. <span class="note">(숫자는 예시 — 홀드아웃·finalist 수에 따라 변함)</span></div>

      <h3>⑤ 채점 3종 + 기록 원칙</h3>
      <div class="term"><b>Recall@K</b> = 정답 §이 상위 K에 든 비율(무료). 정답이 여러 개면 <b>커버리지</b>(몇 개 맞췄나), 순위는 <b>MRR</b>로 보강.</div>
      <div class="term"><b>LLM 심판</b> = Claude가 사실성·인용·완전성 1~5점(생성≠심판 모델로 분리).</div>
      <div class="term"><b>프로그램 인용검증</b> = 인용한 §가 실제 그 청크에 있나 코드 대조(무료·객관, 가짜 인용 색출).</div>
      <div class="warn"><b>원칙 — 기록은 버리지 않는다.</b> recall=0·추출 실패·깨진 표도 <code>status:"failed"</code>로 <code>runs.jsonl</code>에 한 줄 남긴다. <b>왜 안 됐는지가 대시보드의 핵심 신호</b>다.</div>
      <pre><code>{"run_id":"r042","config":{"chunk":1200,"chunking":"section","embed":"bge-large",
 "retrieval":"hybrid","topk":5,"gen_model":"sonnet-4-6","prompt":"A"},
 "question_id":"H07","citations":["§91.151"],"program_check":{"citation_grounded":true},
 "status":"ok"}</code></pre>
      <div class="warn"><b>차단 작업(blocker):</b> 무료 채점은 전부 <b>정답 § 라벨의 정확성</b>에 의존한다. 라벨이 틀리면 Recall이 거짓말을 한다 → Phase 1 직후 <code>grep</code>으로 전수 검증하기 전엔 점수를 신뢰하지 않는다.</div>

      <h3>⑥ 비용 — 두 지갑 분리</h3>
      <ul>
        <li><b>검색 실험(1~4):</b> 로컬 임베딩 → <b>$0</b>.</li>
        <li><b>생성 실험(5~6):</b> 공유 키 사용 → <b>Batches API 50%↓</b> + 누적 상한 가드(초과 시 자동 중단). 추산 ~$9~12.</li>
        <li><b>LLM 심판:</b> <b>Claude Code(별도 지갑) → 0원.</b></li>
      </ul>

      <h3>⑦ 진행 단계 (Phase 0~1)</h3>
      <p>단계 1~5의 <b>상태·결과·막힌 점</b>은 단계 카드로 분리했다 →
        <a href="rag-progress.html"><b>06 진행 단계</b></a>.</p>

      <p class="note">원본 상세: <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/STRATEGY.md">STRATEGY.md</a>(전략·3막) · <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/EXPERIMENTS.md">EXPERIMENTS.md</a>(채점·체크리스트) · <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/todo/06_30_phase0_1.md">todo/06_30_phase0_1.md</a>(Phase 0~1 실행계획)</p>
    </section>

    <section class="sec" id="ensemble">
      <h2>🧩 앙상블 — 여러 모델(방법) 합치기</h2>
      <p class="analogy">🏥 <b>비유:</b> 한 명의 의사보다 <b>여러 과 의사의 협진</b>이 더 정확하듯, 검색도 <b>여러 방법의 결과를 합치면</b> 더 잘 찾는다. 이게 <b>앙상블</b>.</p>

      <h3>① 앙상블이 뭐야 (한 문장)</h3>
      <p><b>여러 개의 의견을 모아 하나의 더 나은 결론</b>을 내는 것. 딥러닝에서 여러 모델 예측을 합쳐 정확도를 올리던 그거 맞다.</p>

      <h3>② 우리 프로젝트에선 = "검색 방법 두 개를 합친다"</h3>
      <p>챗봇이 답의 근거를 찾는 방법은 크게 둘이 있다:</p>
      <table class="cmp">
        <tr><th>방법</th><th>잘하는 것</th><th>비유</th></tr>
        <tr><td><b>의미 검색</b><br>(dense)</td><td>말을 바꿔 물어도 <b>뜻</b>으로 찾음<br>("연료 얼마나?" → fuel reserve 조항)</td><td>뜻을 이해하는 사서</td></tr>
        <tr><td><b>키워드 검색</b><br>(BM25)</td><td><b>정확한 단어·번호</b>를 안 놓침<br>("§91.151", "30 minutes", "Class B")</td><td>색인 카드로 찾는 사서</td></tr>
      </table>
      <p>이 <b>둘을 합친 게 "하이브리드 검색"</b>이고, 그게 바로 앙상블이다.</p>

      <div class="mermaid">
flowchart LR
    Q["Question<br/>질문"] --> D["Dense search<br/>의미 검색"]
    Q --> B["BM25 search<br/>키워드 검색"]
    D --> F["Rank fusion<br/>등수 합치기"]
    B --> F
    F --> A["Best passages<br/>→ 답 생성"]
      </div>

      <h3>③ 왜 항공법에 딱 맞나</h3>
      <div class="ok"><b>서로 다른 실수를 하니까 서로를 메운다.</b> 의미 검색은 뜻은 알아도 정확한 조항 번호를 흘릴 수 있고, 키워드 검색은 번호는 정확히 짚어도 말 바꾼 질문을 놓친다. 항공법 답은 <b>뜻도, 정확한 §번호·수치도</b> 둘 다 필요(인용 25점!) → 합치면 강해진다.</div>

      <h3>④ 딥러닝 앙상블과 딱 한 가지 차이</h3>
      <p>예전엔 여러 모델의 <b>예측값(숫자)을 평균</b>냈지? 검색 앙상블은 평균이 아니라 <b>"등수표를 합친다".</b> 각 방법이 "1등은 이 문단, 2등은 저 문단…" 순위를 내면, 그 순위들을 합산해 종합 순위를 만든다. (모델마다 숫자 좌표계가 달라서 <b>벡터를 평균내면 오히려 망가진다.</b>)</p>

      <h3>⑤ 어떤 앙상블을 쓸까 (결정)</h3>
      <table class="cmp">
        <tr><th>종류</th><th>쓸까?</th><th>이유 (한 줄)</th></tr>
        <tr><td>하이브리드 (의미+키워드)</td><td>✅ <b>쓴다</b></td><td>무료·효과 큼. 이미 <a href="rag-experiments.html">실험 3</a>에 있음</td></tr>
        <tr><td>리랭킹 (재정렬)</td><td>🟡 여유 시</td><td>후보를 많이 건진 뒤 정밀 재정렬. 무료지만 느려짐</td></tr>
        <tr><td>임베딩 여러 개 (bge+e5)</td><td>🟡 후순위</td><td>비슷한 둘이라 이득 적고 인덱스 2벌 필요</td></tr>
        <tr><td>답 여러 번 생성 투표</td><td>❌ 안 씀</td><td>Claude를 N번 불러 <b>비용 N배</b> → 비용 점수 손해</td></tr>
      </table>

      <h3>⑥ 이번 상황 정리 (내 고민 → 결정)</h3>
      <div class="term"><b>고민:</b> 딥러닝처럼 임베딩 모델 여러 개를 앙상블하면 더 좋아질까?<br>
      <b>알게 된 것:</b> RAG 앙상블은 벡터가 아니라 <b>검색 결과(등수)를 합치는 것</b>. 비슷한 임베딩 둘보다 <b>성격이 다른 의미+키워드 조합</b>이 이 법조문 데이터엔 더 이득.<br>
      <b>결정:</b> <b>하이브리드(의미+키워드)에 집중.</b> 리랭킹·다중임베딩은 시간 남으면. 생성 앙상블은 비용 때문에 제외.</div>

      <h3>용어 미니사전</h3>
      <div class="term"><b>앙상블</b> — 여러 방법의 결과를 합쳐 더 나은 결론.</div>
      <div class="term"><b>하이브리드 검색</b> — 의미 검색 + 키워드 검색을 함께 쓰기.</div>
      <div class="term"><b>순위 융합(RRF)</b> — 여러 검색의 <b>등수표를 합산</b>하는 표준 방법.</div>
      <div class="term"><b>리랭킹</b> — 후보를 많이 건진 뒤 더 똑똑한 모델로 <b>다시 줄 세우기</b>.</div>
    </section>

    <section class="sec" id="progress">
      <h2>🛠️ 진행 단계 (Phase 0~1)</h2>
      <p>스타터(아폴로 예제)를 <b>FAA 항공법 챗봇</b>으로 갈아끼우는 5단계. 각 카드 =
        <b>목적 · 결과 · 막힌 점</b>. 통과기준·커밋 같은 실행 디테일은
        <a href="https://github.com/welovecherry/ksept-lab/blob/main/rag-contest/todo/06_30_phase0_1.md">todo/06_30_phase0_1.md</a>에.</p>
      <div class="ok"><b>지금 여기:</b> <b>단계 5(§ 인용 표시)만 남음</b> — 1·2·3-1·3-2·4 완료(4는 커밋 대기), 임베딩 프리페치 완료.</div>

      <div class="step">
        <h4>준비 — 임베딩 후보 프리페치 <span class="st done">✅ 완료 (실험 2 선행)</span></h4>
        <dl>
          <dt>목적</dt><dd>실험 2(임베딩 축) 전에 후보 3종을 미리 받아 캐시 + 작동 검증. 느리고 실패 가능한 다운로드를 <b>밤샘 루프 밖에서</b> 끝냄.</dd>
          <dt>결과</dt><dd><b>bge·e5·gte 모두 로컬 캐시</b>(1.2G·1.2G·640M) + 스모크 통과. 전부 1024d, "연료 &gt; 아폴로" 유사도 순서 정상. 프리픽스 규칙(e5·bge)도 로딩과 안 엉킴. → <a href="rag-setup.html">04 모델 세팅</a>에 실측표.</dd>
          <dt>의미</dt><dd>당일 다운로드 리스크 제거. 임베딩 교체가 "이름만 바꾸면" 되는 상태.</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 1 — 스모크 테스트 <span class="st done">✅ 완료 · 4761d04</span></h4>
        <dl>
          <dt>목적</dt><dd>스타터를 아폴로 예제 그대로 켜서 "RAG가 돈다"를 눈으로 확인.</dd>
          <dt>결과</dt><dd>아폴로 <b>1,133청크</b> 인덱싱 → 질문에 답 + 출처 2개 정상 반환.</dd>
          <dt>막힌 점</dt><dd>venv가 Python 3.9라 <code>SentenceTransformer | None</code>(PEP 604, 3.10+)가 import에서 <code>TypeError</code>. → <code>from __future__ import annotations</code> 한 줄로 해결(주석 lazy 평가, venv 교체보다 영향 범위 최소).</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 2 — 기록 스키마 + 로거 <span class="st done">✅ 완료 · a158bc5</span></h4>
        <dl>
          <dt>목적</dt><dd>모든 실험을 성공·실패 가리지 않고 한 줄씩 쌓는 <code>runs.jsonl</code>·<code>index_manifest.jsonl</code> 형식과 로거 확정.</dd>
          <dt>결과</dt><dd><code>harness/</code> 패키지화 + <code>recorder.py</code>(append-only, 한 줄 원자적 write &lt;4096B) + <b>pytest 8건</b> 통과(왕복·failed 보존·malformed·오버사이즈 거부·유니코드).</dd>
          <dt>원칙</dt><dd>한 줄=한 실행(크래시 내성) · 성공도 실패도 기록 · config를 줄 안에 인라인(자기완결) · 원천(jsonl)과 파생(leaderboard) 분리.</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 3-1 — PDF → 깨끗한 평문 추출 <span class="st done">✅ 완료 · 9fe97ef</span></h4>
        <dl>
          <dt>목적</dt><dd>FAA 6 PDF를 머리말·쪽번호·러닝헤더를 걷어낸 평문 마크다운으로(§태깅은 3-2).</dd>
          <dt>결과</dt><dd>PyMuPDF로 <b>~480만 자</b> 추출. part91 연료조항(§91.151·§91.167) 온전, 리딩 블록만 제거해 boilerplate 0건 잔존 확인.</dd>
          <dt>막힌 점</dt><dd>part67 청력 <b>audiometric 표</b>가 셀당 한 줄로 세로 선형화됨. 값은 검색 가능해 pdfplumber 보정 <b>생략</b>(방어코드 최소화) — 표 정확도 질문 나오면 재검토.</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 3-2 — §·part 태깅 + 파서 테스트 <span class="st done">✅ 완료 · 51eba47</span></h4>
        <dl>
          <dt>목적</dt><dd>평문에 <code>&lt;!-- §91.151 | part91 --&gt;</code> 꼬리표를 삽입하고 <code>parse_sections()</code>를 테스트로 검증.</dd>
          <dt>핵심</dt><dd>§ 글리프 하나에 의존 금지 → <code>§|Sec.|Section</code> 다중 패턴. part는 파일명이 아니라 <b>§번호 앞자리에서 유도</b>(vol1은 여러 part가 한 파일). § 블록 <b>&gt;50 하드게이트</b>로 조용한 0건 차단.</dd>
          <dt>결과</dt><dd>1차엔 part91 태그가 <b>361개(과다)</b> — <code>§ 91.107(a)(3) of this chapter</code> 같은 <b>본문 참조</b>까지 제목으로 오인. 정규식에 <b>전방탐색(lookahead)</b> 추가(번호 뒤가 줄끝/대문자 제목일 때만 인정, 줄 시작에 고정) → <b>256개·중복 0</b>. §91.151 제목 정확 태깅, 파서 테스트 8건 통과.</dd>
          <dt>막힌 점→해결</dt><dd>"조항 제목"과 "다른 조항을 가리키는 참조"가 글자로는 같음. <b>중복 태그 수</b>가 오탐의 신호(제목은 한 번뿐, 참조는 반복) → 중복 0이 곧 품질 증거.</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 4 — FAA 인덱싱 + §·part 메타 <span class="st now">✅ 검증 통과 · 커밋 대기</span></h4>
        <dl>
          <dt>목적</dt><dd>아폴로를 빼고 FAA만 §경계로 청킹, 각 레코드에 <code>section</code>·<code>part</code> 저장.</dd>
          <dt>결과</dt><dd>아폴로 21개 → <code>_apollo_backup/</code> 이동. FAA <b>2,184 chunks</b>(part91 256·vol1 1,719 등), 전 레코드 section·part, <b>part 불일치 0</b>. 청킹 라우팅은 파일명 하드코딩 대신 <b>내용에 <code>&lt;!-- §</code> 있으면 §단위</b>로(T4/P2 해결).</dd>
          <dt>증명</dt><dd>T5 스모크: "day VFR fuel-reserve" → top <b>§91.151</b>(정확!)·§91.167. <code>index_manifest</code> 1줄·<code>runs.jsonl</code> 1줄 실제 적재 → 스키마를 <b>실행으로</b> 증명.</dd>
        </dl>
      </div>

      <div class="step">
        <h4>단계 5 — 답변 Sources에 § 인용 노출 <span class="st todo">⏳ 예정</span></h4>
        <dl>
          <dt>목적</dt><dd><code>citations</code>에 <code>section</code>·<code>part</code>를 실어 Sources 라벨을 조항 번호로.</dd>
          <dt>UI</dt><dd>Sources가 <code>part91.md</code> → <b><code>§91.151 (Part 91)</code></b>로 바뀜 ← <b>시나리오 결과 장면</b>.</dd>
          <dt>검증</dt><dd>범위밖 질문("공항 근처 맛집")은 "출처에 없음"으로 거부 — 환각 없음 확인.</dd>
        </dl>
      </div>
    </section>

    <section class="sec" id="log">
      <h2>📝 작업 일지</h2>

      <h3>2026-06-30 — 준비 + Phase 0 완료</h3>
      <ul>
        <li><b>코퍼스 배치:</b> <code>faa-rag-corpus.zip</code> → <code>rag-contest/corpus/</code> (6개 PDF, 약 1,297쪽).</li>
        <li><b>베이스 확보:</b> <code>rag-starter</code>(동작형 RAG: indexer + 인용 백엔드 + React) 분석·배치.</li>
        <li><b>전략 문서:</b> STRATEGY.md(6시간 로드맵·3막 구조) + EXPERIMENTS.md(탐욕적 순차 실험) + holdout.jsonl(검증 14문제).</li>
        <li><b>Phase 0 완료:</b> Python 3.12 격리 venv → 의존성(torch·sentence-transformers·anthropic) 설치 → Apollo 예제 인덱싱 <b>1,133청크</b> → 채팅 경로(검색+생성+인용) 실제 동작 확인.</li>
        <li><b>관찰:</b> 인용이 "파일명+청크번호"로 떨어짐 → §조항 번호로 고도화할 빈틈 확인(25점 레버).</li>
      </ul>

      <h3>2026-06-30 — 결정: 실험 모니터링은 "20줄 CLI 리더보드"</h3>
      <ul>
        <li><b>문제:</b> 실험마다 <code>runs.jsonl</code> 원본을 눈으로 보는 게 힘듦 → 진행 확인용 뷰가 필요.</li>
        <li><b>결정:</b> Streamlit 대시보드 대신 <b>작은 CLI 리더보드</b> 채택. 이유 — ① 오늘 병목은 시각화가 아니라 라벨 정확성, ② CLI 표는 <code>tail -f</code>로 야간 무인 실행과 궁합, ③ 대회 전날 새 의존성은 리스크.</li>
        <li><b>스펙:</b> <code>runs.jsonl</code> → 점수순 표(콘솔 + <code>leaderboard.md</code>). 정렬 = coverage↓ → mrr↓ → cost↑(동점이면 <b>싼 설정</b>이 위). <code>status:failed</code>도 숨기지 않고 표시.</li>
        <li><b>실시간:</b> 야간엔 <code>tail -f runs.jsonl</code>, 리더보드는 아무 때나 재실행해 스냅샷.</li>
        <li><b>보류:</b> Streamlit UI는 대회 후 여유 있으면.</li>
      </ul>

      <h3>2026-06-30 — 임베딩 후보 3종 프리페치 완료</h3>
      <ul>
        <li><b>한 일:</b> bge·e5·gte를 로컬 캐시(1.2G·1.2G·640M) + 스모크 통과. 전부 1024d, "연료 조항 &gt; 아폴로" 유사도 순서 정상.</li>
        <li><b>의미:</b> 후보 4종(+MiniLM) 모두 실전 준비 → 당일 다운로드 리스크 제거, 임베딩 교체가 "이름만 바꾸면" 되는 상태.</li>
        <li><b>상세:</b> 실측표는 <a href="rag-setup.html">04 모델 세팅</a>, 준비 카드는 <a href="rag-progress.html">07 진행 단계</a>.</li>
      </ul>

      <h3>2026-06-30 — Phase 1 진척: FAA 추출 → §태깅 → 인덱싱 (단계 3-1·3-2·4)</h3>
      <ul>
        <li><b>3-1 추출 (9fe97ef):</b> PyMuPDF로 6 PDF → 평문 md(~480만 자). 페이지 boilerplate 제거, 연료조항(§91.151·§91.167) 온전.</li>
        <li><b>3-2 §태깅 (51eba47):</b> 조항마다 <code>&lt;!-- §… --&gt;</code> 꼬리표. 1차엔 <b>361개(과다)</b> — 본문 참조(<code>§ 91.107(a)(3)</code>)까지 오인 → 정규식 <b>lookahead</b>(줄시작+뒤가 제목)로 <b>256개·중복 0</b>. 파서 테스트 8건.</li>
        <li><b>4 인덱싱 (커밋 대기):</b> 아폴로 백업, FAA <b>2,184 chunks</b>, part 불일치 0. T5 스모크 "day VFR fuel-reserve" → top <b>§91.151</b> 정확. runs/manifest 실제 1줄씩 적재.</li>
        <li><b>남은 것:</b> 단계 5(답변 Sources에 <code>§91.151 (Part 91)</code> 노출)만 남음. 상세 카드 → <a href="rag-progress.html">07 진행 단계</a>.</li>
      </ul>

      <div class="ph"><b>다음 칸 — 날짜별로 계속 기록:</b> 오늘 한 일 / 막힌 점 / 해결.</div>
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


def _rag_overview_partslist():
    lis = "".join(
        f'<li><a href="{f}"><b>{n} {html.escape(t)}</b></a></li>'
        for f, n, t, _ in RAG_PAGES[1:]
    )
    return f'    <section class="sec"><h2>📑 이 프로젝트의 페이지</h2><ul>{lis}</ul></section>'


def _rag_prevnext(i):
    nav = []
    if i > 0:
        f, n, t, _ = RAG_PAGES[i - 1]
        nav.append(f'<a href="{f}">← {(n + " " + t).strip()}</a>')
    if i < len(RAG_PAGES) - 1:
        f, n, t, _ = RAG_PAGES[i + 1]
        nav.append(f'<a href="{f}">{(n + " " + t).strip()} →</a>')
    return '    <p class="note" style="margin-top:2.5rem">' + " · ".join(nav) + "</p>"


def render_rag_pages():
    """project_body()를 섹션 단위로 잘라 RAG_PAGES의 짧은 페이지들로 조립·기록."""
    proj = project_body()
    style = re.search(r"<style>.*?</style>", proj, re.S).group(0)
    sections = {
        m.group(1): m.group(0)
        for m in re.finditer(r'<section class="sec" id="([\w-]+)">.*?</section>', proj, re.S)
    }
    for i, (file, num, short, ids) in enumerate(RAG_PAGES):
        parts = [
            "    " + style,
            f'    <h1>{RAG_TITLES[file]} <span class="badge">FAA 항공법 챗봇</span></h1>',
            '    <p class="sub"><a href="rag-project.html">← RAG 콘테스트</a> · <a href="index.html">🏠 홈</a></p>',
        ]
        if file == "rag-project.html":
            parts.append(_rag_overview_partslist())
        parts += [sections[sid] for sid in ids if sid in sections]
        parts.append(_rag_prevnext(i))
        body = "\n".join(parts)
        title = f'{(short or "RAG").replace("🛩️ ", "")} · RAG · ksept-lab'
        (ROOT / "docs" / file).write_text(shell(title, body, active=file), encoding="utf-8")


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
    render_rag_pages()  # 🛩️ RAG 콘테스트 = 사이드바에서 번호로 나뉜 여러 짧은 페이지
    OUT_CHANGELOG.write_text(
        shell("변경 이력 · ksept-lab", changelog_body(render_timeline(commits), last_updated, count),
              active="changelog.html"),
        encoding="utf-8",
    )
    print(f"wrote index/practice/notes/changelog + {len(RAG_PAGES)} RAG pages  ({count} commits)")


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
    .sidebar .subnav {{ display: flex; flex-direction: column; gap: .05rem;
      margin: .1rem 0 .35rem .35rem; padding-left: .45rem; border-left: 1px solid var(--border); }}
    .sidebar .subnav a {{ color: var(--muted); font-size: .85rem; padding: .28rem .5rem; border-radius: 6px;
      text-decoration: none; }}
    .sidebar .subnav a:hover {{ background: #1f2530; color: var(--accent); }}
    .sidebar .subnav a.active {{ background: #1f6feb22; color: var(--accent); font-weight: 600; }}
    .sidebar .subnav a .n {{ display: inline-block; min-width: 1.5em; color: #6e7681;
      font-variant-numeric: tabular-nums; margin-right: .35rem; }}
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
