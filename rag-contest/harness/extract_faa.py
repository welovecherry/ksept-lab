"""Extract FAA 14 CFR PDFs to clean plaintext markdown (step 3-1).

Concern here is extraction QUALITY only: pull clean plain text out of each PDF
and strip the per-page boilerplate (page number, edition/agency running header,
bare "§ NN.NN" running header). §-boundary tagging is step 3-2.

Input : rag-contest/corpus/documents/CFR-2025-title14-*.pdf   (6 files)
Output: rag-contest/rag-starter/documents/{vol1,part61,...}.md (plain, no § tags)

Primary extractor is PyMuPDF — fast, clean single-column text. The two-column
medical-standards table in part67 is the known risk; eyeball it after running,
and if it comes out scrambled, re-extract that one file with a column-aware tool.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "corpus" / "documents"
OUT_DIR = ROOT / "rag-starter" / "documents"

# Lines repeated at the top of every page — GPO running headers, not content.
# A bare "§ 91.123" (number only) is a running header; a real section heading
# carries its title on the same line ("§ 91.151 Fuel requirements ..."), so this
# pattern leaves real headings intact.
_BOILERPLATE = re.compile(
    r"""^\s*(?:
        \d+                                    # bare page number:  704
      | \d+\s+CFR\s+Ch\..*                     # 14 CFR Ch. I (1–1–25 Edition)
      | Federal\s+Aviation\s+Administration.*  # Federal Aviation Administration, DOT
      | §\s*\d+\.\d+\w?                         # bare running-header section: § 91.123
      | Pt\.\s*\d+                              # Pt. 91
    )\s*$""",
    re.VERBOSE,
)


# A section heading starts a line: "§ 91.151", "Sec. 91.151", or "Section 91.151".
# Anchored to line start (re.MULTILINE) so inline cross-references mid-sentence
# ("... as provided in § 91.167 ...") are NOT mistaken for section boundaries.
# Matching more than the bare § glyph guards against the § dropping in extraction
# (a single-point-of-failure that would silently null every tag).
#
# The trailing lookahead separates a heading from a cross-reference that happens
# to wrap to a line start: a real heading is the number followed by end-of-line
# or a Capitalized title, whereas a reference continues with a "(a)(3)" subsection
# or lowercase prose ("§ 91.107(a)(3) of this chapter"). Horizontal-space classes
# ([ \t], not \s) keep the match from jumping across a line break.
_SECTION_RE = re.compile(
    r"^(?:§|Sec\.|Section)[ \t]*(\d+\.\d+\w?)(?=[ \t]*$|[ \t]+[A-Z])",
    re.MULTILINE,
)

# part91 is the big file; if it tags far too few sections, extraction or the §
# pattern silently broke — fail the build rather than ship an untagged corpus.
MIN_PART91_SECTIONS = 50


def _part_of(section_number: str) -> str:
    """'91.151' -> 'part91'; '1.1' -> 'part1'. Derived from the number, not the
    filename, so vol1 (Parts 1–59 in one file) tags each section to its own part."""
    return "part" + section_number.split(".")[0]


def parse_sections(text: str) -> list[tuple[str, str]]:
    """Return [(section, part), ...] for every section heading in `text`.

    section is normalized with a leading § and no space ('§91.151'); part is
    derived from the section number. Returns [] when the text has no headings.
    """
    return [(f"§{m.group(1)}", _part_of(m.group(1))) for m in _SECTION_RE.finditer(text)]


def tag_sections(text: str) -> str:
    """Insert a '<!-- §91.151 | part91 -->' comment before each section heading."""
    def _mark(m: re.Match) -> str:
        num = m.group(1)
        return f"<!-- §{num} | {_part_of(num)} -->\n{m.group(0)}"

    return _SECTION_RE.sub(_mark, text)


def _out_name(pdf_name: str) -> str:
    """CFR-2025-title14-vol2-part91.pdf -> 'part91'; ...-vol1.pdf -> 'vol1'."""
    m = re.search(r"part\d+", pdf_name) or re.search(r"vol\d+", pdf_name)
    if not m:
        raise ValueError(f"cannot derive output name from {pdf_name!r}")
    return m.group(0)


def clean_page(text: str) -> str:
    """Drop the leading per-page header block; keep the body."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) and (not lines[i].strip() or _BOILERPLATE.match(lines[i])):
        i += 1
    return "\n".join(lines[i:])


def normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces, trim each line, cap blank-line runs at one."""
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip() + "\n"


def extract_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        pages = [clean_page(page.get_text("text")) for page in doc]
    finally:
        doc.close()
    return normalize_whitespace("\n".join(pages))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PDF_DIR.glob("CFR-*.pdf"))
    if not pdfs:
        raise SystemExit(f"No CFR PDFs found in {PDF_DIR}")
    counts: dict[str, int] = {}
    for pdf in pdfs:
        name = _out_name(pdf.name)  # fail fast before extracting
        text = tag_sections(extract_pdf(pdf))
        out = OUT_DIR / f"{name}.md"
        out.write_text(text, encoding="utf-8")
        counts[name] = text.count("<!-- §")
        print(f"  {pdf.name} → {out.name}  ({len(text):,} chars, {counts[name]} sections)")

    # Hard gate against a silent 0-tag build (dropped § glyph, broken pattern).
    canary = counts.get("part91", 0)
    if canary < MIN_PART91_SECTIONS:
        raise SystemExit(
            f"§-tagging gate FAILED: part91 tagged {canary} sections "
            f"(< {MIN_PART91_SECTIONS}). Extraction or the § pattern is broken."
        )
    print(f"\n✓ Tagged {len(pdfs)} PDFs → {OUT_DIR}/  "
          f"(part91 gate: {canary} ≥ {MIN_PART91_SECTIONS})")


if __name__ == "__main__":
    main()
