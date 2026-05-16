"""CCEL Nicene and Post-Nicene Fathers, Series 2 (Vol. 1-14) adapter.

14 volumes covering Eusebius, Socrates, Sozomen, Theodoret, and ecumenical
conciliar documents (NPNF2 vol. XIV is Percival's *Seven Ecumenical Councils*).
PD pre-1923 translations.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urljoin

from ingest.cultural._common import fetch_with_politeness
from ingest.cultural._html import ccel_page_paragraphs, ccel_toc_chapter_links, chunk_paragraphs
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "ccel-npnf2"
WORK_ID = "ccel-npnf2"
TRADITION: Literal["patristic"] = "patristic"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.ccel.org/ccel/schaff/npnf201.toc.html"
FALLBACK_URLS: list[str] = []
WORK_TITLE = "Nicene and Post-Nicene Fathers, Series 2"
DATE_WRITTEN = "1890"
EXPECTED = (200, 30000)

VOLUME_TOCS: list[tuple[int, str]] = [
    (vol, f"https://www.ccel.org/ccel/schaff/npnf2{vol:02d}.toc.html") for vol in range(1, 15)
]
MAX_CHUNKS = 40000


def parse_chapter(raw: bytes, vol: int, chap_url: str) -> list[CulturalChunk]:
    paras = ccel_page_paragraphs(raw)
    if not paras:
        return []
    chunks = chunk_paragraphs(paras, target_tokens=400, min_tokens=100)
    out: list[CulturalChunk] = []
    chap_slug = chap_url.rsplit("/", 1)[-1].replace(".html", "")
    for idx, text in enumerate(chunks, start=1):
        anchor = f"NPNF2.vol{vol}.{chap_slug}.{idx:03d}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=f"{WORK_ID}.vol{vol}",
                    work_title=f"{WORK_TITLE}, Vol. {vol}",
                    author="Various (Eusebius, Athanasius, Cappadocians, et al.)",
                    date_written=DATE_WRITTEN,
                    is_confessional_text=False,
                    anchor_id=anchor,
                    language="en",
                    translator="NPNF series 2 (Schaff/Wace ed.)",
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
