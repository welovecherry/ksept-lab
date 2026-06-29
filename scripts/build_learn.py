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
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TUT_DIR = ROOT / "docs" / "tutorial"
NOTES_DIR = ROOT / "notes"
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

    # 노트 스타일 주입 (한 번)
    html = html.replace("</head>", NOTE_CSS + "</head>", 1)

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
