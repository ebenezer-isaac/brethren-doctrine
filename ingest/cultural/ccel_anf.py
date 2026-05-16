"""CCEL Ante-Nicene Fathers (Vol. 1-10) adapter.

The ANF set is the most theologically significant pre-Nicene corpus in English
public domain. Vol. 1 alone has 25+ works; the full set has ~150. We crawl
each volume's TOC, walk to chapter pages, and emit one chunk per chapter-prose
paragraph block. License is PD throughout.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urljoin

from ingest.cultural._common import fetch_with_politeness, scrape_source
from ingest.cultural._html import ccel_page_paragraphs, ccel_toc_chapter_links, chunk_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "ccel-anf"
WORK_ID = "ccel-anf"
TRADITION: Literal["patristic"] = "patristic"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.ccel.org/ccel/schaff/anf01.toc.html"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Ante-Nicene Fathers"
DATE_WRITTEN = "1885"
EXPECTED = (200, 50000)

VOLUME_TOCS: list[tuple[int, str]] = [
    (1, "https://www.ccel.org/ccel/schaff/anf01.toc.html"),
    (2, "https://www.ccel.org/ccel/schaff/anf02.toc.html"),
    (3, "https://www.ccel.org/ccel/schaff/anf03.toc.html"),
    (4, "https://www.ccel.org/ccel/schaff/anf04.toc.html"),
    (5, "https://www.ccel.org/ccel/schaff/anf05.toc.html"),
    (6, "https://www.ccel.org/ccel/schaff/anf06.toc.html"),
    (7, "https://www.ccel.org/ccel/schaff/anf07.toc.html"),
    (8, "https://www.ccel.org/ccel/schaff/anf08.toc.html"),
    (9, "https://www.ccel.org/ccel/schaff/anf09.toc.html"),
    (10, "https://www.ccel.org/ccel/schaff/anf10.toc.html"),
]

MAX_CHUNKS = 60000


def parse_chapter(raw: bytes, vol: int, chap_url: str) -> list[CulturalChunk]:
    paras = ccel_page_paragraphs(raw)
    if not paras:
        return []
    chunks = chunk_paragraphs(paras, target_tokens=400, min_tokens=100)
    out: list[CulturalChunk] = []
    chap_slug = chap_url.rsplit("/", 1)[-1].replace(".html", "")
    for idx, text in enumerate(chunks, start=1):
        anchor = f"ANF.vol{vol}.{chap_slug}.{idx:03d}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=f"{WORK_ID}.vol{vol}",
                    work_title=f"{WORK_TITLE}, Vol. {vol}",
                    author="Various (pre-Nicene Fathers)",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=False,
                    anchor_id=anchor,
                    language="en",
                    translator="ANF series (Schaff ed.)",
                ),
                text=text,
                text_to_embed=text,
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=None,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    out: list[CulturalChunk] = []
    last_request: dict[str, float] = {}
    for vol, toc_url in VOLUME_TOCS:
        try:
            toc_raw = fetch_with_politeness(toc_url, last_request_by_host=last_request)
        except Exception:
            continue
        chap_urls = ccel_toc_chapter_links(toc_raw, toc_url)
        for chap_url in chap_urls:
            if len(out) >= MAX_CHUNKS:
                break
            full = urljoin(toc_url, chap_url)
            try:
                chap_raw = fetch_with_politeness(full, last_request_by_host=last_request)
            except Exception:
                continue
            out.extend(parse_chapter(chap_raw, vol, full))
        if len(out) >= MAX_CHUNKS:
            break
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED


_ = scrape_source
