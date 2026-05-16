"""Westminster Confession of Faith (1646) adapter.

Source: opc.org (canonical OPC HTML). Parsed by chapter + numbered section.
33 chapters; 1-12 sections each; ~170 total chunks.
"""

from __future__ import annotations

from typing import Literal

from ingest.cultural._common import scrape_source
from ingest.cultural._html import opc_style_chapter_sections
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "wcf"
WORK_ID = "wcf"
TRADITION: Literal["reformed"] = "reformed"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.opc.org/wcf.html"
FALLBACK_URLS: list[str] = [
    "https://www.reformed.org/documents/wcf_with_proofs/",
]
WORK_TITLE = "Westminster Confession of Faith"
DATE_WRITTEN = "1646"
EXPECTED = (160, 200)


def parse(raw: bytes) -> list[CulturalChunk]:
    chapters = opc_style_chapter_sections(raw)
    out: list[CulturalChunk] = []
    for chap in chapters:
        for sec in chap["sections"]:
            anchor = f"WCF.{chap['chapter']}.{sec['section']}"
            text = sec["text"]
            if not text:
                continue
            out.append(
                CulturalChunk(
                    chunk_id=f"{SOURCE_SLUG}.{anchor}",
                    tradition=TRADITION,
                    source=CulturalChunkSource(
                        work_id=WORK_ID,
                        work_title=WORK_TITLE,
                        author="Westminster Assembly",
                        date_written=DATE_WRITTEN,
                        is_confessional_text=True,
                        anchor_id=anchor,
                        language="en",
                        translator=None,
                    ),
                    text=text,
                    text_to_embed=f"{chap['chapter_title']}. {text}",
                    license=LICENSE,
                    redistribute=REDISTRIBUTE,
                    license_note=None,
                )
            )
    return out


def scrape() -> list[CulturalChunk]:
    raw = scrape_source(SOURCE_SLUG, CANONICAL_URL, FALLBACK_URLS)
    return parse(raw)


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
