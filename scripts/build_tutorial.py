#!/usr/bin/env python3
"""
build_tutorial.py — ksetp.netlify.app 튜토리얼을 사이트에 통합한다.

ksetp.netlify.app의 모듈 7개(슬라이드 덱)를 스크랩해서 다크 테마의
정적 HTML로 변환하고 docs/tutorial/ 아래에 모듈당 1페이지로 저장한다.

- 각 슬라이드(<section>)는 data-label을 제목으로 하는 카드가 된다.
- HTML→markdown 변환은 pandoc에 위임(표/코드/리스트/이미지 무손실).
- 이미지는 docs/tutorial/assets/로 내려받아 로컬 상대경로로 치환.

CI가 아니라 "로컬에서 1회 실행 → 결과물(HTML/이미지) 커밋"이 전제다
(외부 사이트 스크랩 + pandoc 의존성 때문). 작업일지 갱신은 기존
build_docs.py가 계속 담당하며 이 스크립트가 만든 파일은 건드리지 않는다.

사용:  python3 scripts/build_tutorial.py    (pandoc 필요)
"""
import html as html_mod
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://ksetp.netlify.app"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "tutorial"
ASSETS = OUT / "assets"

# (슬러그, 표시 제목, 한 줄 설명) — 랜딩 카드와 사이드바에 쓰인다.
MODULES = [
    ("setup", "Setup", "환경 구성: VSCode·Git·Node·Python·Claude Code·API 키"),
    ("foundations", "Foundations", "API 기초, 시스템 프롬프트, 프롬프트/컨텍스트 엔지니어링, 스트리밍, 에러 처리"),
    ("tools", "Tools & Structure", "함수/툴 호출, 구조화 출력, 스키마 검증, 파싱, MCP"),
    ("context", "Context Management", "임베딩, 벡터 DB, RAG, 대화 메모리, 청킹"),
    ("agents", "Architecture & Agents", "에이전트 루프, Claude Code 내부, 서브에이전트, 멀티모델 라우팅, 컴퓨터 유즈, 안전"),
    ("production", "Production", "평가·테스트(골든셋, LLM-as-judge), 가드레일·보안(프롬프트 인젝션, PII)"),
    ("workshop", "Workshop", "빌드 데이 — 기존 프로젝트 확장 또는 새 결과물"),
]


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req).read()


def fetch_text(url):
    return fetch_bytes(url).decode("utf-8")


def split_sections(page_html):
    """슬라이드는 중첩 없는 평평한 <section> 요소들이다."""
    return re.findall(r"<section\b.*?</section>", page_html, re.S)


def data_label(section_html):
    m = re.search(r'data-label="([^"]*)"', section_html)
    return html_mod.unescape(m.group(1)) if m else "(제목 없음)"


def pandoc(text, from_fmt, to_fmt, *extra):
    proc = subprocess.run(
        ["pandoc", "-f", from_fmt, "-t", to_fmt, "--wrap=none", *extra],
        input=text, capture_output=True, text=True, check=True,
    )
    return proc.stdout


def localize_images(html_str, slug):
    """HTML 속 src="url" 이미지를 내려받아 로컬 상대경로로 치환.
    (pandoc은 width/height가 있는 <img>를 markdown이 아닌 raw 태그로 내므로
     markdown이 아니라 최종 HTML의 src 기준으로 처리한다.)"""
    ASSETS.mkdir(parents=True, exist_ok=True)

    def repl(m):
        url = m.group(1)
        if url.startswith("data:"):  # 인라인 SVG/base64는 그대로 둔다
            return m.group(0)
        # 상대경로 './assets/..' 같은 형태를 urljoin으로 정규화(BASE/./.. 404 방지)
        full = url if url.startswith("http") else urllib.parse.urljoin(BASE + "/", url)
        raw_name = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        fname = f"{slug}-{raw_name}".replace(" ", "-")
        dest = ASSETS / fname
        if not dest.exists():
            try:
                dest.write_bytes(fetch_bytes(full))
            except Exception as e:  # 이미지 하나 실패해도 페이지는 만든다
                print(f"    ! image failed {full}: {e}")
                return m.group(0)
        return f'src="assets/{fname}"'

    return re.sub(r'src="([^"]+)"', repl, html_str)


def build_module(slug, title, subtitle, index, total):
    page = fetch_text(f"{BASE}/{slug}")
    sections = split_sections(page)
    eyebrow = title  # 본문 첫 줄이 모듈명 반복이면 제거하기 위한 비교값

    md_parts = []
    for i, sec in enumerate(sections, start=1):
        label = data_label(sec)
        # <section> 래퍼를 벗기고 인라인 style을 제거(다크 테마와 충돌·leak 방지)
        inner = re.sub(r"^<section\b[^>]*>", "", sec).rsplit("</section>", 1)[0]
        inner = re.sub(r'\sstyle="[^"]*"', "", inner)
        body = pandoc(inner, "html", "gfm").strip()
        # 슬라이드 본문 첫 줄이 모듈명(eyebrow) 그대로면 중복이라 제거
        lines = body.split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and lines[0].strip() == eyebrow:
            lines.pop(0)
        body = "\n".join(lines).strip()
        md_parts.append(f"## {i}. {label}\n\n{body}\n")

    body_html = pandoc("\n\n".join(md_parts), "gfm", "html5")

    # h2 id를 슬라이드 순서대로 slide-N으로 재지정 + 클릭 앵커 부착 + TOC 수집
    toc = []

    def _fix_h2(m):
        n = len(toc) + 1
        inner = m.group(1)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        toc.append((f"slide-{n}", text))
        return f'<h2 id="slide-{n}">{inner} <a class="anchor" href="#slide-{n}">#</a></h2>'

    body_html = re.sub(r"<h2[^>]*>(.*?)</h2>", _fix_h2, body_html, flags=re.S)
    body_html = localize_images(body_html, slug)

    toc_html = "".join(
        f'<li><a href="#{sid}">{html_mod.escape(text)}</a></li>' for sid, text in toc
    )
    nav_links = []
    for s, t, _ in MODULES:
        cls = ' class="active"' if s == slug else ""
        nav_links.append(f'<a href="{s}.html"{cls}>{html_mod.escape(t)}</a>')
    nav_html = "".join(nav_links)

    page_html = PAGE_TMPL.format(
        title=html_mod.escape(title),
        slug=slug,
        index=index,
        total=total,
        count=len(sections),
        src=f"{BASE}/{slug}",
        subtitle=html_mod.escape(subtitle),
        nav=nav_html,
        toc=toc_html,
        body=body_html,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.html").write_text(page_html, encoding="utf-8")
    return len(sections)


def build_landing(counts):
    cards = ""
    for (slug, title, subtitle), n in zip(MODULES, counts):
        cards += (
            f'<a href="{slug}.html">'
            f'<div class="m-num">MODULE {MODULES.index((slug, title, subtitle)) + 1}</div>'
            f'<div class="m-title">{html_mod.escape(title)}</div>'
            f'<div class="m-desc">{html_mod.escape(subtitle)}</div>'
            f'<div class="m-meta">슬라이드 {n}개</div></a>'
        )
    nav_html = "".join(
        f'<a href="{s}.html">{html_mod.escape(t)}</a>' for s, t, _ in MODULES
    )
    page_html = LANDING_TMPL.format(
        nav=nav_html, cards=cards, total=sum(counts), src=BASE
    )
    (OUT / "index.html").write_text(page_html, encoding="utf-8")


PAGE_TMPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} · ksept-lab 튜토리얼</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="side-title"><a href="../index.html">📒 ksept-lab</a></div>
    <div class="side-group">📚 튜토리얼</div>
    <nav><a href="index.html">개요</a>{nav}</nav>
    <div class="side-foot">출처: ksetp.netlify.app<br>로컬 생성 후 커밋</div>
  </aside>
  <div class="wrap">
    <h1>{title}</h1>
    <p class="sub">Module {index}/{total} · 슬라이드 {count}개 · <a href="{src}" target="_blank" rel="noopener">원본 슬라이드 ↗</a></p>
    <p class="sub">{subtitle}</p>
    <details class="toc"><summary>이 모듈의 슬라이드 {count}개</summary><ol>{toc}</ol></details>
{body}
    <hr>
    <p class="sub">출처: <a href="{src}" target="_blank" rel="noopener">{src}</a> · ksept-lab 학습 아카이브</p>
  </div>
</div>
</body>
</html>
"""

LANDING_TMPL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>튜토리얼 · ksept-lab</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="side-title"><a href="../index.html">📒 ksept-lab</a></div>
    <div class="side-group">📚 튜토리얼</div>
    <nav><a href="index.html" class="active">개요</a>{nav}</nav>
    <div class="side-foot">출처: ksetp.netlify.app</div>
  </aside>
  <div class="wrap">
    <h1>튜토리얼 아카이브</h1>
    <p class="sub">Full Stack Application Development with Coding Agents — 모듈 7개 · 슬라이드 {total}개</p>
    <p class="sub">원본: <a href="{src}" target="_blank" rel="noopener">{src}</a></p>
    <div class="cards">{cards}</div>
  </div>
</div>
</body>
</html>
"""


def main():
    counts = []
    total = len(MODULES)
    for idx, (slug, title, subtitle) in enumerate(MODULES, start=1):
        n = build_module(slug, title, subtitle, idx, total)
        print(f"  {slug}: {n} slides -> docs/tutorial/{slug}.html")
        counts.append(n)
    build_landing(counts)
    print(f"  landing -> docs/tutorial/index.html ({sum(counts)} slides total)")


if __name__ == "__main__":
    main()
