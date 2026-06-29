#!/usr/bin/env python3
"""
build_learn.py — 원본 튜토리얼 + 내 노트 = 통합 학습본(docs/learn/)

구조:
  - 각 슬라이드(<h2 id="slide-N">)를 <details>로 감싸 접을 수 있게.
  - 그 슬라이드에 해당하는 내 노트를 원본 바로 아래에 인라인으로 삽입.
  - 사이드바는 계층형: 모듈 → (현재 모듈의) 슬라이드 목록(#slide-N 점프).
  - 원본 보관소(docs/tutorial/*)는 그대로 두고 사이드바 하단에서 링크.

입력(사람이 씀, git 추적):
  - docs/tutorial/*.html   원본 (수정 안 함)
  - notes/<module>.md      내 노트. `@slide-N` 줄로 슬라이드별 분리, 그 전은 개요.
  - quizzes/<module>.json  (선택) 슬라이드 본문을 인터랙티브 퀴즈로 교체

출력(자동 생성, .gitignore):
  - docs/learn/<module>.html
의존성 없음(표준 라이브러리만).
"""

import html as html_lib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TUT_DIR = ROOT / "docs" / "tutorial"
NOTES_DIR = ROOT / "notes"
QUIZ_DIR = ROOT / "quizzes"
OUT_DIR = ROOT / "docs" / "learn"

SLIDE_OPEN = True  # 슬라이드를 기본 펼침으로(위→아래로 읽기). False면 접힌 채 시작.

# 사이드바 모듈 순서 + 표시 이름 + 번호
MODULES = [
    ("index", "개요", ""),
    ("setup", "Setup", "01"),
    ("foundations", "Foundations", "02"),
    ("tools", "Tools & Structure", "03"),
    ("context", "Context", "04"),
    ("agents", "Agents", "05"),
    ("production", "Production", "06"),
    ("workshop", "Workshop", "07"),
]

# ── 스타일 ────────────────────────────────────────────────────────────────────
STYLE = """
<style>
  /* 내 노트 (개요 + 인라인 공통: .notesbody) */
  .notesbody h3 { font-size: 1.3rem; color: #58a6ff; margin: 1.3rem 0 .5rem;
    padding-bottom: .25rem; border-bottom: 1px solid #30363d; }
  .notesbody h4 { font-size: 1.12rem; color: #3fb950; margin: 1rem 0 .35rem; }
  .notesbody h5 { font-size: 1rem; color: #e3b341; margin: .85rem 0 .3rem; }
  .notesbody strong { color: #e3b341; }
  .notesbody ol, .notesbody ul { padding-left: 1.4rem; margin: .5rem 0; }
  .notesbody li { margin: .3rem 0; line-height: 1.7; }
  .notesbody p { line-height: 1.75; }
  .notesbody pre { background: #010409; color: #e6edf3; padding: .8rem 1rem;
    border-radius: 6px; overflow-x: auto; }
  .notesbody code { background: #1f2530; color: #e6edf3; padding: .1rem .35rem; border-radius: 4px; }

  .module-note { border-top: 2px solid #3fb950; margin: 1.5rem 0 1rem; padding-top: 1rem; }
  .module-note > h2 { color: #3fb950; }
  .learn-badge { display:inline-block; background:#3fb95022; color:#3fb950;
    border:1px solid #3fb95066; border-radius:999px; padding:.05rem .5rem; font-size:.75rem; margin-left:.4rem; }
  .readonly-banner { background:#1f2530; border:1px solid #30363d; border-radius:8px;
    padding:.6rem .9rem; margin:0 0 1.2rem; font-size:.9rem; color:#8b949e; }
  .readonly-banner b { color:#58a6ff; }

  /* 슬라이드 접기 */
  details.slide { border:1px solid #30363d; border-radius:8px; margin:.8rem 0; background:#0d1117; }
  details.slide > summary { cursor:pointer; padding:.7rem 1rem; font-weight:700;
    font-size:1.1rem; color:#e6edf3; list-style:none; }
  details.slide > summary::-webkit-details-marker { display:none; }
  details.slide > summary:hover { color:#58a6ff; }
  details.slide > summary::before { content:"\\25B6"; color:#8b949e; font-size:.8rem; margin-right:.5rem; }
  details.slide[open] > summary::before { content:"\\25BC"; }
  details.slide[open] > summary { border-bottom:1px solid #30363d; }
  .slide-num { display:inline-block; min-width:1.7em; color:#8b949e; font-variant-numeric:tabular-nums; }
  .slide-body { padding:.6rem 1.1rem 1.1rem; }
  .slide-body :target { scroll-margin-top: 1rem; }

  /* 슬라이드 바로 아래 내 노트 */
  .mynote-inline { margin-top:1.1rem; border-left:3px solid #3fb950;
    background:#0f1a12; border-radius:0 8px 8px 0; padding:.6rem 1rem; }
  .mynote-inline > h4 { margin:.2rem 0 .5rem; color:#3fb950; font-size:1rem; }

  /* 계층 사이드바 */
  .sidebar .modnav { display:flex; flex-direction:column; gap:.05rem; }
  .sidebar .modnav > a { color:#e6edf3; text-decoration:none; padding:.35rem .5rem;
    border-radius:6px; font-size:.92rem; }
  .sidebar .modnav > a:hover { background:#1f2530; }
  /* 현재 모듈 = 부모. 아래 슬라이드 목록과 한 덩어리로 읽히게 강조. */
  .sidebar .modnav > a.active { color:#58a6ff; font-weight:700;
    background:#1f6feb22; border:1px solid #1f6feb55; border-bottom-left-radius:0;
    border-bottom-right-radius:0; }
  /* 슬라이드 = 자식. 들여쓰기 + 파란 세로선 + 살짝 들어간 패널. */
  .sidebar .slidenav { display:flex; flex-direction:column; gap:.05rem;
    margin:0 0 .6rem .15rem; padding:.3rem 0 .35rem .55rem; background:#0d1117;
    border:1px solid #1f6feb33; border-top:none; border-left:2px solid #1f6feb88;
    border-bottom-left-radius:6px; border-bottom-right-radius:6px; }
  .sidebar .slidenav-cap { color:#6e7681; font-size:.68rem; font-weight:700;
    text-transform:uppercase; letter-spacing:.06em; padding:.25rem .5rem .3rem; }
  .sidebar .slidenav > a { display:flex; gap:.45rem; align-items:baseline;
    color:#8b949e; text-decoration:none; padding:.2rem .5rem;
    border-radius:5px; font-size:.8rem; line-height:1.35; }
  .sidebar .slidenav > a:hover { background:#1f2530; color:#58a6ff; }
  .sidebar .slidenav > a .sn { flex:0 0 auto; min-width:1.5em; text-align:right;
    color:#58a6ff; font-variant-numeric:tabular-nums; font-weight:700; }
  .sidebar .slidenav > a .st { flex:1 1 auto; }
  .sidebar .side-foot a { color:#58a6ff; text-decoration:none; }
</style>
"""

# 해시(#slide-N)로 점프하면 그 슬라이드(접힌 details)를 자동으로 펼친다.
HASH_JS = """
<script>
(function(){
  function openHash(){
    if(!location.hash) return;
    var el; try { el = document.querySelector(location.hash); } catch(e){ return; }
    var n = el;
    while(n){ if(n.tagName === 'DETAILS'){ n.open = true; } n = n.parentElement; }
    if(el) el.scrollIntoView();
  }
  window.addEventListener('hashchange', openHash);
  window.addEventListener('load', openHash);
})();
</script>
"""

# ── 퀴즈 (선택) ───────────────────────────────────────────────────────────────
QUIZ_CSS = """
<style>
  .quiz { background:#0f1620; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin:1rem 0 1.5rem; }
  .quiz-review { background:#11271a; border-left:3px solid #3fb950; border-radius:6px; padding:.7rem .9rem; margin-bottom:1rem; line-height:1.6; color:#e6edf3; }
  .quiz-q { margin:0; padding:1.4rem 0; }
  .quiz-q:first-of-type { padding-top:.4rem; }
  .quiz-q + .quiz-q { border-top:1px solid #30363d; }
  .quiz-qnum { display:inline-block; font-weight:700; color:#58a6ff; font-size:.8rem; letter-spacing:.06em; margin-bottom:.45rem; }
  .quiz-question { margin:0 0 .6rem; }
  .quiz-question .q-en { display:block; font-weight:700; color:#e6edf3; }
  .quiz-question .q-ko { display:block; color:#8b949e; font-size:.92rem; margin-top:.15rem; }
  .quiz-opts { display:flex; flex-direction:column; gap:.45rem; }
  .quiz-opt { text-align:left; background:#161b22; color:#e6edf3; border:1px solid #30363d; border-radius:8px; padding:.6rem .8rem; font:inherit; cursor:pointer; transition:background .12s,border-color .12s; }
  .quiz-opt:hover { border-color:#58a6ff; }
  .quiz-q.answered .quiz-opt { cursor:default; }
  .quiz-opt.correct { background:#1f6f2e33; border-color:#3fb950; color:#d6ffe0; }
  .quiz-opt.correct::after { content:"  \\2705"; }
  .quiz-opt.wrong { background:#6f1f1f33; border-color:#f85149; color:#ffdcdc; }
  .quiz-opt.wrong::after { content:"  \\274C"; }
  .quiz-exp { margin-top:.7rem; padding:.7rem .9rem; background:#161b22; border:1px dashed #30363d; border-radius:8px; color:#c9d1d9; line-height:1.6; }
  .quiz-retry { margin-left:.6rem; background:none; border:1px solid #30363d; color:#58a6ff; border-radius:6px; padding:.15rem .6rem; cursor:pointer; font:inherit; font-size:.85rem; }
  .quiz-retry:hover { border-color:#58a6ff; }
</style>
"""

QUIZ_JS = """
<script>
(function(){
  document.addEventListener('click', function(e){
    var opt = e.target.closest('.quiz-opt');
    if (opt){
      var q = opt.closest('.quiz-q');
      if (q.classList.contains('answered')) return;
      q.classList.add('answered');
      var correct = opt.getAttribute('data-correct') === 'true';
      opt.classList.add(correct ? 'correct' : 'wrong');
      if (!correct){ var r = q.querySelector('.quiz-opt[data-correct="true"]'); if (r) r.classList.add('correct'); }
      var exp = q.querySelector('.quiz-exp'); if (exp) exp.hidden = false;
      return;
    }
    var retry = e.target.closest('.quiz-retry');
    if (retry){
      var q2 = retry.closest('.quiz-q'); q2.classList.remove('answered');
      var opts = q2.querySelectorAll('.quiz-opt');
      for (var i=0;i<opts.length;i++){ opts[i].classList.remove('correct','wrong'); }
      var e2 = q2.querySelector('.quiz-exp'); if (e2) e2.hidden = true;
    }
  });
})();
</script>
"""

_LETTERS = "ABCDEFGH"


def render_quiz(quiz):
    parts = ['<div class="quiz">']
    if quiz.get("review"):
        parts.append('<div class="quiz-review">🧠 <b>잠깐 복습</b><br>%s</div>'
                     % html_lib.escape(quiz["review"]))
    for n, q in enumerate(quiz["questions"], start=1):
        parts.append('<div class="quiz-q">')
        parts.append('<div class="quiz-qnum">Q%d</div>' % n)
        parts.append('<p class="quiz-question"><span class="q-en">%s</span>'
                     '<span class="q-ko">%s</span></p>'
                     % (html_lib.escape(q["en"]), html_lib.escape(q["ko"])))
        parts.append('<div class="quiz-opts">')
        for idx, opt in enumerate(q["options"]):
            parts.append('<button class="quiz-opt" data-correct="%s">%s. %s</button>'
                         % ("true" if opt.get("correct") else "false",
                            _LETTERS[idx], html_lib.escape(opt["t"])))
        parts.append('</div>')
        parts.append('<div class="quiz-exp" hidden>💡 %s '
                     '<button class="quiz-retry">다시 풀기</button></div>'
                     % html_lib.escape(q["explanation"]))
        parts.append('</div>')
    parts.append('</div>')
    return "\n".join(parts)


def inject_quizzes(html, module):
    qpath = QUIZ_DIR / f"{module}.json"
    if not qpath.exists():
        return html, False
    data = json.loads(qpath.read_text(encoding="utf-8"))
    injected = False
    for sid, quiz in data.items():
        quiz_html = render_quiz(quiz)
        pat = re.compile(
            r'(<h2 id="%s">.*?</h2>)(.*?)(?=<h2 id="slide-\d+">|<hr>)' % re.escape(sid),
            re.S)
        html, n = pat.subn(lambda m: m.group(1) + "\n" + quiz_html + "\n", html, count=1)
        injected = injected or bool(n)
    return html, injected


# ── 마크다운 → HTML (필요한 부분집합) ─────────────────────────────────────────
def _inline(text):
    text = html_lib.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>"); in_ul = False
        if in_ol:
            out.append("</ol>"); in_ol = False

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            close_lists(); i += 1; code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + html_lib.escape("\n".join(code)) + "</code></pre>")
            continue
        s = line.strip()
        if not s:
            close_lists(); i += 1; continue
        m = re.match(r"(#{1,6})\s+(.*)", s)
        if m:
            close_lists()
            lvl = len(m.group(1))
            tag = "h3" if lvl <= 1 else ("h4" if lvl == 2 else "h5")
            out.append(f"<{tag}>{_inline(m.group(2))}</{tag}>")
            i += 1; continue
        m = re.match(r"[-*]\s+(.*)", s)
        if m:
            if not in_ol and not in_ul:
                out.append("<ul>"); in_ul = True
            elif in_ol:
                close_lists(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1; continue
        m = re.match(r"\d+\.\s+(.*)", s)
        if m:
            if not in_ul and not in_ol:
                out.append("<ol>"); in_ol = True
            elif in_ul:
                close_lists(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1; continue
        close_lists()
        out.append(f"<p>{_inline(s)}</p>")
        i += 1
    close_lists()
    return "\n".join(out)


# ── 노트 파싱: @slide-N 마커로 슬라이드별 분리 ────────────────────────────────
def parse_notes(md):
    """('개요 md', {슬라이드번호: 'md'}) 반환. `@slide-N` 또는 `@N` 줄이 구분자."""
    intro, by_slide, buf = [], {}, None
    cur = intro
    for line in md.split("\n"):
        m = re.match(r"^@(?:slide-)?(\d+)\s*$", line.strip())
        if m:
            cur = by_slide.setdefault(m.group(1), [])
            continue
        cur.append(line)
    intro_md = "\n".join(intro).strip()
    slide_md = {k: "\n".join(v).strip() for k, v in by_slide.items()}
    return intro_md, slide_md


def extract_slides(html):
    """[(번호, 제목)] — 사이드바용."""
    out = []
    for m in re.finditer(r'<h2 id="slide-(\d+)">(.*?)</h2>', html, re.S):
        title = re.sub(r"<[^>]+>", "", m.group(2))      # 태그 제거
        title = re.sub(r"\s*#\s*$", "", title).strip()  # 앵커 '#' 제거
        title = re.sub(r"^\s*\d+\.\s*", "", title)       # 원본 앞번호 제거(번호 중복 방지)
        out.append((m.group(1), title))
    return out


def build_sidebar(current, slides):
    p = ['<aside class="sidebar">']
    p.append('<div class="side-title"><a href="../index.html">📒 ksept-lab</a></div>')
    p.append('<div class="side-group">📚 주제별 학습</div>')
    p.append('<nav class="modnav">')
    for fn, name, num in MODULES:
        label = (num + " " if num else "") + name
        active = ' class="active"' if fn == current else ""
        p.append(f'<a href="{fn}.html"{active}>{html_lib.escape(label)}</a>')
        if fn == current and slides:
            p.append('<div class="slidenav">')
            p.append('<div class="slidenav-cap">이 모듈의 슬라이드</div>')
            for sn, st in slides:
                p.append(f'<a href="#slide-{sn}">'
                         f'<span class="sn">{sn}</span>'
                         f'<span class="st">{html_lib.escape(st)}</span></a>')
            p.append('</div>')
    p.append('</nav>')
    p.append(f'<div class="side-foot"><a href="../tutorial/{current}.html">📖 원본 보관소</a>'
             f'<br><a href="../changelog.html">📜 변경 이력</a></div>')
    p.append('</aside>')
    return "\n".join(p)


def build_page(tut_path):
    module = tut_path.stem
    html = tut_path.read_text(encoding="utf-8")
    html, has_quiz = inject_quizzes(html, module)

    # 학습 개요(랜딩)는 원본 보관소 인덱스에서 파생되므로 제목만 학습용으로 교체
    if module == "index":
        html = re.sub(r"<h1>.*?</h1>", "<h1>📚 학습 개요</h1>", html, count=1, flags=re.S)
        html = html.replace("<title>튜토리얼 · ksept-lab</title>",
                            "<title>학습 개요 · ksept-lab</title>")

    slides = extract_slides(html)

    # 노트 읽기/파싱
    note_path = NOTES_DIR / f"{module}.md"
    raw = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    intro_md, slide_md = parse_notes(raw)
    slide_html = {n: md_to_html(md) for n, md in slide_md.items() if md}

    # 각 슬라이드를 <details>로 감싸고, 해당 노트를 본문 아래에 인라인 삽입
    open_attr = " open" if SLIDE_OPEN else ""

    def wrap(m):
        n = m.group(1)
        title = re.sub(r'<a class="anchor"[^>]*>#</a>', "", m.group(2)).strip()
        body = m.group(3)
        note = slide_html.get(n)
        note_block = (
            f'<div class="mynote-inline"><h4>📝 내 노트</h4>'
            f'<div class="notesbody">{note}</div></div>' if note else ""
        )
        return (f'<details class="slide" id="slide-{n}"{open_attr}>'
                f'<summary><span class="slide-num">{n}</span> {title}</summary>'
                f'<div class="slide-body">{body}{note_block}</div></details>')

    html = re.sub(
        r'<h2 id="slide-(\d+)">(.*?)</h2>(.*?)(?=<h2 id="slide-\d+">|<hr>)',
        wrap, html, flags=re.S)

    # 사이드바 교체 (계층형)
    html = re.sub(r'<aside class="sidebar">.*?</aside>',
                  lambda _: build_sidebar(module, slides), html, count=1, flags=re.S)

    # 본문 맨 위: 배너 + (있으면) 개요 노트
    if module == "index":
        banner = ('<div class="readonly-banner">📚 <b>학습 개요</b> — 아래 로드맵에서 모듈을 고르세요. '
                  '각 모듈 페이지엔 <b>원본 + 내 노트 + 퀴즈</b>가 있어요.</div>')
    else:
        banner = ('<div class="readonly-banner">📚 <b>통합 학습본</b> — 각 슬라이드(원본) 아래에 '
                  '<b>📝 내 노트</b>가 붙어요. 슬라이드 제목을 누르면 접고/펼칠 수 있어요. '
                  '순수 원본은 사이드바 하단 <b>📖 원본 보관소</b>.</div>')
    intro_block = ""
    if intro_md:
        intro_block = ('<section class="module-note"><h2>📝 내 작업일지 '
                       '<span class="learn-badge">개요</span></h2>'
                       f'<div class="notesbody">{md_to_html(intro_md)}</div></section>')
    html = html.replace('<div class="wrap">',
                        '<div class="wrap">\n    ' + banner + intro_block, 1)

    # 정적 자원 경로 보정 (docs/learn → ../tutorial)
    html = html.replace('href="style.css"', 'href="../tutorial/style.css"')
    html = html.replace('src="assets/', 'src="../tutorial/assets/')
    html = html.replace('href="assets/', 'href="../tutorial/assets/')

    # 스타일/스크립트 주입
    head = STYLE + (QUIZ_CSS if has_quiz else "")
    html = html.replace("</head>", head + "</head>", 1)
    body = HASH_JS + (QUIZ_JS if has_quiz else "")
    html = html.replace("</body>", body + "</body>", 1)

    return module, html


def build():
    if not TUT_DIR.exists():
        print(f"no tutorial dir: {TUT_DIR}"); return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for tut_path in sorted(TUT_DIR.glob("*.html")):
        module, html = build_page(tut_path)
        (OUT_DIR / f"{module}.html").write_text(html, encoding="utf-8")
        count += 1
    print(f"wrote {count} learn pages -> {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
