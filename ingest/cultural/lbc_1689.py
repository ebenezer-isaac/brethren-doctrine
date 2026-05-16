"""1689 London Baptist Confession adapter.

Source: bible-researcher.com (canonical clean HTML, one page per chapter). 32
chapters, ~146 numbered sections in total.
"""

from __future__ import annotations

import re
from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import parse_html, text_of
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "lbc-1689"
WORK_ID = "lbc-1689"
TRADITION: Literal["reformed"] = "reformed"
LICENSE = "public_domain"
REDISTRIBUTE = True
CHAPTER_URL_TMPL = "http://www.bible-researcher.com/1689/chapter{n}.html"
CANONICAL_URL = "http://www.bible-researcher.com/1689/confession.html"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "1689 London Baptist Confession of Faith"
DATE_WRITTEN = "1689"
EXPECTED = (140, 160)
N_CHAPTERS = 32

_CHAP_HEADER = re.compile(r"CHAP\.\s+([IVXLCDM]+)", re.IGNORECASE)
_ROMAN_TO_INT = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
    "XII": 12,
    "XIII": 13,
    "XIV": 14,
    "XV": 15,
    "XVI": 16,
    "XVII": 17,
    "XVIII": 18,
    "XIX": 19,
    "XX": 20,
    "XXI": 21,
    "XXII": 22,
    "XXIII": 23,
    "XXIV": 24,
    "XXV": 25,
    "XXVI": 26,
    "XXVII": 27,
    "XXVIII": 28,
    "XXIX": 29,
    "XXX": 30,
    "XXXI": 31,
    "XXXII": 32,
}


def parse_chapter(raw: bytes, chapter_num: int) -> list[CulturalChunk]:
    tree = parse_html(raw)
    title = ""
    h3s = tree.xpath("//h3")
    if h3s:
        full = text_of(h3s[0])
        m = re.search(r"\.\s*(.+)$", full)
        if m:
            title = m.group(1).strip().rstrip(".")
    out: list[CulturalChunk] = []
    for p in tree.xpath("//p[contains(@class,'close')]"):
        text = text_of(p)
        m = re.match(r"^(\d+)\.\s+(.+)$", text, re.DOTALL)
        if not m:
            continue
        section_num = int(m.group(1))
        body = m.group(2).strip()
        body = re.sub(r"\(\s*[a-z]\s*\)", "", body).strip()
        anchor = f"1689.{chapter_num}.{section_num}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="General Assembly of Particular Baptists",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator=None,
                ),
                text=body,
                text_to_embed=f"{title}. {body}" if title else body,
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=None,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    for n in range(1, N_CHAPTERS + 1):
        url = CHAPTER_URL_TMPL.format(n=n)
        raw = scrape_source(f"{SOURCE_SLUG}.ch{n}", url, [])
        out.extend(parse_chapter(raw, n))
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
