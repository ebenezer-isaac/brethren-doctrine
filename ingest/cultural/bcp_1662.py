"""Book of Common Prayer 1662 adapter.

The full BCP is a large prayer book with extensive non-doctrinal liturgy
(calendars, psalter, marriage rites). For cultural-overlay use we extract
the doctrinally-dense sections: catechism, Athanasian Creed, Litany,
Morning and Evening Prayer (with creeds), and Holy Communion. Source:
eskimo.com mirror, which is the most reliable plain-HTML copy.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import bcp1662_qa_blocks, bcp1662_section
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "bcp-1662"
WORK_ID = "bcp-1662"
TRADITION: Literal["anglican"] = "anglican"
LICENSE = "public_domain"
REDISTRIBUTE = True
BASE = "https://www.eskimo.com/~lhowell/bcp1662"
CANONICAL_URL = f"{BASE}/intro/contents.html"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Book of Common Prayer (1662)"
DATE_WRITTEN = "1662"
EXPECTED = (10, 200)

SECTIONS: list[tuple[str, str, str]] = [
    ("catechism", "Catechism", f"{BASE}/baptism/catechism.html"),
    ("athanasian", "Athanasian Creed", f"{BASE}/daily/athanasian.html"),
    ("morning", "Order for Morning Prayer", f"{BASE}/daily/morning.html"),
    ("evening", "Order for Evening Prayer", f"{BASE}/daily/evening.html"),
    ("litany", "The Litany", f"{BASE}/daily/litany.html"),
    ("communion", "Order of Holy Communion", f"{BASE}/communion/index.html"),
]


def _chunk(
    anchor: str,
    text: str,
    section_title: str,
) -> CulturalChunk:
    return CulturalChunk(
        chunk_id=f"{SOURCE_SLUG}.{anchor}",
        tradition=TRADITION,
        source=CulturalChunkSource(
            work_id=WORK_ID,
            work_title=WORK_TITLE,
            author="Church of England",
            date_written=DATE_WRITTEN,
            is_confessional_text=True,
            anchor_id=anchor,
            language="en",
            translator=None,
        ),
        text=text,
        text_to_embed=f"{section_title}. {text}",
        license=LICENSE,
        redistribute=REDISTRIBUTE,
        license_note=None,
    )


def parse_catechism(raw: bytes) -> list[CulturalChunk]:
    qs = bcp1662_qa_blocks(raw)
    out: list[CulturalChunk] = []
    for q in qs:
        anchor = f"BCP.Catechism.Q{q['q_num']:02d}"
        text = f"Q. {q['question']} A. {q['answer']}"
        out.append(_chunk(anchor, text, "Catechism"))
    return out


def parse_section(raw: bytes, slug: str, title_default: str) -> list[CulturalChunk]:
    sec = bcp1662_section(raw, title_default=title_default)
    text = sec["text"]
    if not text:
        return []
    anchor = f"BCP.{slug}"
    return [_chunk(anchor, text, sec["title"] or title_default)]


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    for slug, title, url in SECTIONS:
        raw = scrape_source(f"{SOURCE_SLUG}.{slug}", url, [])
        if slug == "catechism":
            out.extend(parse_catechism(raw))
        else:
            out.extend(parse_section(raw, slug, title))
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
