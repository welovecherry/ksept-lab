"""Unit tests for §/part parsing and tagging (step 3-2, 리뷰 T3).

Covers:
  1. §91.151 / Sec. 91.151 / Section 91.151 all parse to (§91.151, part91)
  2. vol1 multi-part: §1.1 and §61.5 in one text split to part1 / part61
  3. text with no section markers returns [] (no crash)
Plus: inline cross-references are not mistaken for headings, and tagging
inserts the expected comment.
"""
from __future__ import annotations

from harness.extract_faa import parse_sections, tag_sections


def test_three_patterns_same_result():
    for text in ("§ 91.151 Fuel", "Sec. 91.151 Fuel", "Section 91.151 Fuel"):
        assert parse_sections(text) == [("§91.151", "part91")], text


def test_vol1_multipart():
    text = "§ 1.1 Definitions\nsome prose\n§ 61.5 Certificates\nmore prose"
    assert parse_sections(text) == [("§1.1", "part1"), ("§61.5", "part61")]


def test_missing_section_returns_empty():
    assert parse_sections("Just prose, no section markers at all.") == []


def test_inline_crossref_not_a_heading():
    # A reference in the middle of a sentence is not a section boundary.
    text = "You must comply as provided in § 91.167 of this chapter."
    assert parse_sections(text) == []


def test_line_start_crossref_with_subsection_excluded():
    # A wrapped cross-reference that lands at a line start is still not a heading:
    # the "(a)(3)" subsection / lowercase prose after the number gives it away.
    assert parse_sections("§ 91.107(a)(3)(ii) of this chapter.") == []
    assert parse_sections("§ 91.107(a)(3) to occupy a seat") == []


def test_lettered_section_number_kept():
    assert parse_sections("§ 91.151a Special") == [("§91.151a", "part91")]


def test_heading_with_title_on_next_line():
    # GPO format: number alone on its line, title wraps to the next line.
    text = "§ 91.153\nVFR flight plan: Information\nrequired.\n(a) ..."
    assert parse_sections(text) == [("§91.153", "part91")]


def test_tag_sections_inserts_comment():
    out = tag_sections("§ 91.151\nFuel requirements")
    assert "<!-- §91.151 | part91 -->" in out
    assert out.count("<!-- §") == 1
