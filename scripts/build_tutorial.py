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


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


# font-size를 가진 "잎(leaf)" 블록(div/p, 내부에 또 다른 div/p 없음)만 잡는다.
# 원본 슬라이드는 글자 크기로만 위계를 표현하므로, 이를 의미적 태그로 번역한다.
LEAF_RE = re.compile(
    r"<(div|p)\b[^>]*?font-size:\s*(\d+)px[^>]*>((?:(?!</?(?:div|p)\b).)*?)</\1>",
    re.S,
)


def restructure(inner, module_title):
    """슬라이드 한 장의 HTML을 (제목, 본문HTML)로 재구조화.

    - 가장 큰 글자 = 슬라이드 제목 → 본문에서 빼고 h2로 승격
    - 26px 이상 = 소제목 → <h3>
    - 'MODULE n' / 모듈명 반복 눈썹(대문자) = 중복이라 제거
    - 그 외 = 문단 <p>
    내용 텍스트는 그대로 두고 '태그'만 바꾼다.
    """
    title = ""
    max_fs = -1
    for m in LEAF_RE.finditer(inner):
        fs, txt = int(m.group(2)), strip_tags(m.group(3)).strip()
        if txt and fs > max_fs:
            max_fs, title = fs, html_mod.unescape(txt)

    removed_title = [False]

    def _map(m):
        fs, block, children = int(m.group(2)), m.group(0), m.group(3)
        txt = html_mod.unescape(strip_tags(children)).strip()
        if not txt:
            return ""
        if not removed_title[0] and fs == max_fs and txt == title:
            removed_title[0] = True  # 제목은 h2로 빠지므로 본문에서 제거(1회)
            return ""
        upper = "text-transform: uppercase" in block
        if upper and (txt == module_title or re.match(r"^MODULE\s+\d+$", txt)):
            return ""  # 모듈명/‘MODULE n’ 반복 눈썹 제거
        if fs >= 26:
            return f"<h3>{children}</h3>"
        return f"<p>{children}</p>"

    return title, LEAF_RE.sub(_map, inner)


def build_module(slug, title, subtitle, index, total):
    page = fetch_text(f"{BASE}/{slug}")
    sections = split_sections(page)

    md_parts = []
    for i, sec in enumerate(sections, start=1):
        label = data_label(sec)
        # <section> 래퍼를 벗기고, 글자 크기 위계를 의미 태그로 번역
        inner = re.sub(r"^<section\b[^>]*>", "", sec).rsplit("</section>", 1)[0]
        heading, inner = restructure(inner, title)
        heading = heading or label  # 큰 글자 못 찾으면 data-label로 폴백
        # 남은 인라인 style 제거(다크 테마 충돌·leak 방지) 후 markdown 변환
        inner = re.sub(r'\sstyle="[^"]*"', "", inner)
        body = pandoc(inner, "html", "gfm").strip()
        md_parts.append(f"## {i}. {heading}\n\n{body}\n")

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

    <section class="roadmap">
      <h2>🗺 일주일 학습 로드맵</h2>
      <p class="lead">“LLM에게 말 거는 법”에서 출발해 “책임질 수 있는 AI 제품을 혼자 출시하기”로 끝나는 한 주.
        매 모듈이 새 앱이 아니라 <b>같은 채팅 앱에 능력을 하나씩</b> 얹어 갑니다.</p>

      <h3>앞 절반 — 능력을 쌓는다</h3>
      <ol class="steps">
        <li><span class="step-n">1</span><div><b>Setup · 작업실 차리기</b><br>
          VSCode·Git·Node·Python·Claude Code·API 키 설치. <i>→ AI에게 코드를 시킬 환경이 준비됨.</i></div></li>
        <li><span class="step-n">2</span><div><b>Foundations · LLM을 알고 첫 앱을 만든다</b><br>
          LLM이 뭔지, 챗앱 vs 모델 API의 차이, 첫 API 호출로 Flask+React 채팅 앱 + 스트리밍.
          <i>→ 앞으로 키워갈 ‘씨앗 앱’이 돌아감.</i></div></li>
        <li><span class="step-n">3</span><div><b>Tools &amp; Structure · 수다쟁이를 일꾼으로</b><br>
          신뢰성 4단계: 텍스트 파싱 → JSON 스키마 강제·검증 → 툴 사용(에이전트 루프) → MCP.
          <i>→ 정해진 형식으로 답하고 스스로 도구를 써서 일함.</i></div></li>
        <li><span class="step-n">4</span><div><b>Context Management · 내 자료를 기억시키기 (RAG)</b><br>
          임베딩 → 벡터 DB → 청킹 → 관련 조각을 검색해 근거(출처)와 함께 답변.
          <i>→ 내가 넣은 문서를 근거로 대답함.</i></div></li>
      </ol>

      <h3>뒤 절반 — 시스템으로 키우고, 책임지고 내보낸다</h3>
      <ol class="steps">
        <li><span class="step-n">5</span><div><b>Architecture &amp; Agents · 한 번 호출 → 에이전트 시스템</b><br>
          에이전트 루프, Claude Code의 정체, 서브에이전트, 메모리, 멀티모델 라우팅, 캐싱, 안전.
          <i>→ 여러 에이전트가 협력하는 시스템을 설계함.</i></div></li>
        <li><span class="step-n">6</span><div><b>Production · ‘내 컴퓨터에서 됨’과 ‘세상에 내놔도 됨’의 차이</b><br>
          평가(골든셋·LLM-as-judge·회귀 게이트), 보안(프롬프트 인젝션·PII), 관측·지연속도.
          <i>→ 측정되고·방어되고·들여다보이는 앱.</i></div></li>
        <li><span class="step-n">7</span><div><b>Workshop · 직접 만들어 본다</b><br>
          배운 걸 합치는 빌드 데이 — 앱을 확장하거나 새로 출시 + 마지막 퀴즈.
          <i>→ 혼자서 AI 앱을 처음부터 끝까지.</i></div></li>
      </ol>

      <p class="arc"><b>능력의 4단 진화:</b> 말한다(2) → 믿을 수 있게 답한다(3) → 행동한다(3) → 안다(4),
        그 위에 <b>5</b> 협력 에이전트 · <b>6</b> 실서비스화 · <b>7</b> 직접 빌드.</p>
    </section>

    <h2>모듈</h2>
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
