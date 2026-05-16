"""Catechism of the Catholic Church (1992 / 1997) adapter.

Source: vatican.va archive (IntraText edition). The index lists ~374 paragraph
pages (`__PNN.HTM`), each containing a small handful of numbered paragraphs.
2865 paragraphs total. The full crawl is ~13 minutes at the 2-second politeness
gap; live ingest is gated behind orchestrator decision.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urljoin

from ingest.cultural._common import fetch_with_politeness, scrape_source
from ingest.cultural._html import vatican_ccc_paragraph_pages, vatican_ccc_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "vatican-ccc"
WORK_ID = "vatican-ccc"
TRADITION: Literal["catholic-magisterial"] = "catholic-magisterial"
LICENSE = "©Libreria-Editrice-Vaticana"
REDISTRIBUTE = False
LICENSE_NOTE = "CCC text © Libreria Editrice Vaticana; personal ingest only"
INDEX_URL = "https://www.vatican.va/archive/ENG0015/_INDEX.HTM"
CANONICAL_URL = INDEX_URL
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Catechism of the Catholic Church"
DATE_WRITTEN = "1992"
EXPECTED = (2400, 2870)


def parse_page(raw: bytes) -> list[CulturalChunk]:
    paras = vatican_ccc_paragraphs(raw)
    out: list[CulturalChunk] = []
    for p in paras:
        anchor = f"CCC.{p['paragraph']}"
        text = p["text"]
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=WORK_ID,
                    work_title=WORK_TITLE,
                    author="Magisterium of the Catholic Church",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=True,
                    anchor_id=anchor,
                    language="en",
                    translator="Libreria Editrice Vaticana",
                ),
                text=text,
                text_to_embed=text,
                license=LICENSE,
                redistribute=REDISTRIBUTE,
                license_note=LICENSE_NOTE,
            )
        )
    return out


def scrape() -> list[CulturalChunk]:
    raw_index = scrape_source(f"{SOURCE_SLUG}.index", INDEX_URL, FALLBACK_URLS)
    pages = vatican_ccc_paragraph_pages(raw_index)
    out: list[CulturalChunk] = []
    last_request: dict[str, float] = {}
    for page in pages:
        url = urljoin(INDEX_URL, page)
        try:
            raw = fetch_with_politeness(url, last_request_by_host=last_request)
        except Exception:
            continue
        out.extend(parse_page(raw))
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
