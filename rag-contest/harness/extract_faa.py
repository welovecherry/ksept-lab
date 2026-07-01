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
    for pdf in pdfs:
        out = OUT_DIR / f"{_out_name(pdf.name)}.md"  # fail fast before extracting
        text = extract_pdf(pdf)
        out.write_text(text, encoding="utf-8")
        print(f"  {pdf.name} → {out.name}  ({len(text):,} chars)")
    print(f"\n✓ Extracted {len(pdfs)} PDFs → {OUT_DIR}/")


if __name__ == "__main__":
    main()
