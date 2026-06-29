#!/usr/bin/env python3
"""
build_learn.py — 원본 튜토리얼 + 내 학습 노트 = 학습본(docs/learn/) 생성기

입력 (사람이 쓰는 것, git 추적):
  - docs/tutorial/*.html  : 원본 튜토리얼 (절대 수정하지 않음)
  - notes/<module>.md     : 내 학습 노트 (마크다운)

출력 (자동 생성, .gitignore):
  - docs/learn/<module>.html : 원본 맨 아래에 "📝 내 학습 노트"를 붙인 합본

의존성 없음(파이썬 표준 라이브러리만). 마크다운은 아래 간이 변환기로 처리.
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

# 학습 노트 영역 스타일 (각 학습본 <head>에 주입)
NOTE_CSS = """
<style>
  .mynote { margin-top: 2.5rem; border-top: 2px solid #3fb950; padding-top: 1rem; }
  .mynote > h2 { color: #3fb950; }
  .mynote pre { background: #0d1117; color: #e6edf3; padding: .8rem 1rem;
    border-radius: 6px; overflow-x: auto; }
  .mynote code { background: #1f2530; color: #e6edf3; padding: .1rem .35rem; border-radius: 4px; }
  .mynote-empty { color: #8b949e; font-style: italic; }
  .learn-badge { display:inline-block; background:#3fb95022; color:#3fb950;
    border:1px solid #3fb95066; border-radius:999px; padding:.05rem .5rem; font-size:.75rem; margin-left:.4rem; }
  .readonly-banner { background:#1f2530; border:1px solid #30363d; border-radius:8px;
    padding:.6rem .9rem; margin:0 0 1.2rem; font-size:.9rem; color:#8b949e; }
  .readonly-banner b { color:#58a6ff; }
</style>
"""


# 인터랙티브 퀴즈 스타일 + 동작 (학습본에만 주입)
QUIZ_CSS = """
<style>
  .quiz { background:#0f1620; border:1px solid #30363d; border-radius:10px; padding:1rem 1.2rem; margin:1rem 0 1.5rem; }
  .quiz-review { background:#11271a; border-left:3px solid #3fb950; border-radius:6px; padding:.7rem .9rem; margin-bottom:1rem; line-height:1.6; color:#e6edf3; }
  .quiz-q { margin:1.1rem 0; }
  .quiz-question { margin:0 0 .6rem; }
  .quiz-question .q-en { display:block; font-weight:700; color:#e6edf3; }
  .quiz-question .q-ko { display:block; color:#8b949e; font-size:.92rem; margin-top:.15rem; }
  .quiz-opts { display:flex; flex-direction:column; gap:.45rem; }
  .quiz-opt { text-align:left; background:#161b22; color:#e6edf3; border:1px solid #30363d;
    border-radius:8px; padding:.6rem .8rem; font:inherit; cursor:pointer; transition:background .12s,border-color .12s; }
  .quiz-opt:hover { border-color:#58a6ff; }
  .quiz-q.answered .quiz-opt { cursor:default; }
  .quiz-opt.correct { background:#1f6f2e33; border-color:#3fb950; color:#d6ffe0; }
  .quiz-opt.correct::after { content:"  \\2705"; }
  .quiz-opt.wrong { background:#6f1f1f33; border-color:#f85149; color:#ffdcdc; }
  .quiz-opt.wrong::after { content:"  \\274C"; }
  .quiz-exp { margin-top:.7rem; padding:.7rem .9rem; background:#161b22; border:1px dashed #30363d;
    border-radius:8px; color:#c9d1d9; line-height:1.6; }
  .quiz-retry { margin-left:.6rem; background:none; border:1px solid #30363d; color:#58a6ff;
    border-radius:6px; padding:.15rem .6rem; cursor:pointer; font:inherit; font-size:.85rem; }
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
      if (!correct){
        var right = q.querySelector('.quiz-opt[data-correct="true"]');
        if (right) right.classList.add('correct');
      }
      var exp = q.querySelector('.quiz-exp'); if (exp) exp.hidden = false;
      return;
    }
    var retry = e.target.closest('.quiz-retry');
    if (retry){
      var q2 = retry.closest('.quiz-q');
      q2.classList.remove('answered');
      var opts = q2.querySelectorAll('.quiz-opt');
      for (var i=0;i<opts.length;i++){ opts[i].classList.remove('correct','wrong'); }
      var exp2 = q2.querySelector('.quiz-exp'); if (exp2) exp2.hidden = true;
    }
  });
})();
</script>
"""

_LETTERS = "ABCDEFGH"


def render_quiz(quiz):
    """퀴즈 데이터(dict) -> 인터랙티브 HTML 블록."""
    parts = ['<div class="quiz">']
    if quiz.get("review"):
        parts.append('<div class="quiz-review">🧠 <b>잠깐 복습</b><br>%s</div>'
                     % html_lib.escape(quiz["review"]))
    for q in quiz["questions"]:
        parts.append('<div class="quiz-q">')
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
    """quizzes/<module>.json이 있으면 해당 슬라이드 본문을 인터랙티브 퀴즈로 교체.
    돌려주는 값: (바뀐 html, 퀴즈 1개라도 넣었는지 여부)."""
    qpath = QUIZ_DIR / f"{module}.json"
    if not qpath.exists():
        return html, False
    data = json.loads(qpath.read_text(encoding="utf-8"))
    injected = False
    for sid, quiz in data.items():
        quiz_html = render_quiz(quiz)
        # h2(슬라이드 제목)는 남기고, 그 슬라이드 본문(다음 h2/<hr> 전까지)을 교체
        pat = re.compile(
            r'(<h2 id="%s">.*?</h2>)(.*?)(?=<h2 id="slide-\d+">|<hr>)' % re.escape(sid),
            re.S,
        )
        html, n = pat.subn(lambda m: m.group(1) + "\n" + quiz_html + "\n", html, count=1)
        if n:
            injected = True
        else:
            print(f"    ! quiz target {sid} not found in {module}")
    return html, injected


# ── 아주 작은 마크다운 → HTML 변환기 (노트 작성에 필요한 부분집합) ──────────────
def _inline(text):
    """한 줄 안의 인라인 마크다운: 코드 -> 굵게 -> 링크. (먼저 이스케이프)"""
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

        # 코드 펜스 ```
        if line.strip().startswith("```"):
            close_lists()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            i += 1  # 닫는 펜스 건너뜀
            out.append("<pre><code>" + html_lib.escape("\n".join(code)) + "</code></pre>")
            continue

        s = line.strip()
        if not s:
            close_lists(); i += 1; continue

        # 제목 (#=h3, ##=h4, ###=h5 — 페이지의 h2는 '학습 노트' 타이틀 전용)
        m = re.match(r"(#{1,6})\s+(.*)", s)
        if m:
            close_lists()
            level = len(m.group(1))
            tag = "h3" if level <= 1 else ("h4" if level == 2 else "h5")
            out.append(f"<{tag}>{_inline(m.group(2))}</{tag}>")
            i += 1; continue

        # 순서 없는 목록
        m = re.match(r"[-*]\s+(.*)", s)
        if m:
            if not in_ol and not in_ul:
                out.append("<ul>"); in_ul = True
            elif in_ol:
                close_lists(); out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1; continue

        # 순서 있는 목록
        m = re.match(r"\d+\.\s+(.*)", s)
        if m:
            if not in_ul and not in_ol:
                out.append("<ol>"); in_ol = True
            elif in_ul:
                close_lists(); out.append("<ol>"); in_ol = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1; continue

        # 일반 문단
        close_lists()
        out.append(f"<p>{_inline(s)}</p>")
        i += 1

    close_lists()
    return "\n".join(out)


# ── 원본 + 노트 합치기 ────────────────────────────────────────────────────────
def build_page(tut_path):
    module = tut_path.stem  # e.g. "setup"
    html = tut_path.read_text(encoding="utf-8")

    # 원본의 퀴즈 슬라이드를 인터랙티브 퀴즈로 교체 (quizzes/<module>.json 있을 때)
    html, has_quiz = inject_quizzes(html, module)

    # 노트 읽기 (없으면 빈 안내)
    note_path = NOTES_DIR / f"{module}.md"
    if note_path.exists() and note_path.read_text(encoding="utf-8").strip():
        notes_html = md_to_html(note_path.read_text(encoding="utf-8"))
    else:
        notes_html = (
            f'<p class="mynote-empty">아직 노트가 없어요. '
            f'<code>notes/{module}.md</code>에 적으면 여기에 자동으로 나타나요.</p>'
        )

    note_block = (
        '\n    <section class="mynote">\n'
        '      <h2>📝 내 작업일지 <span class="learn-badge">내가 작성</span></h2>\n'
        f'      {notes_html}\n'
        '    </section>\n'
    )

    # 원본의 푸터(<hr> + 출처) 바로 앞에 노트 삽입. 없으면 </body> 앞에.
    anchor = html.rfind("<hr>")
    if anchor != -1 and "출처" in html[anchor:]:
        html = html[:anchor] + note_block + "    " + html[anchor:]
    else:
        html = html.replace("</body>", note_block + "</body>")

    # docs/learn/ 에서 ../tutorial 의 정적 자원을 참조하도록 경로 보정
    html = html.replace('href="style.css"', 'href="../tutorial/style.css"')
    html = html.replace('src="assets/', 'src="../tutorial/assets/')
    html = html.replace('href="assets/', 'href="../tutorial/assets/')

    # 노트 스타일 주입 (한 번) + 퀴즈가 있으면 퀴즈 스타일/동작도 주입
    head_inject = NOTE_CSS + (QUIZ_CSS if has_quiz else "")
    html = html.replace("</head>", head_inject + "</head>", 1)
    if has_quiz:
        html = html.replace("</body>", QUIZ_JS + "</body>", 1)

    # 본문 맨 위에 '학습본(읽기 전용)' 배너
    banner = ('<div class="readonly-banner">📖 <b>학습본</b> — 원본 튜토리얼(읽기 전용). '
              '내가 정리한 메모는 맨 아래 <b>📝 내 작업일지</b>에 있어요.</div>')
    html = html.replace('<div class="wrap">', '<div class="wrap">\n    ' + banner, 1)

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
