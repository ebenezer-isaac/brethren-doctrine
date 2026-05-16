"""STEM Publishing (Plymouth Brethren) adapter.

Scrapes the author indexes for the major Brethren writers (Darby, Kelly,
Mackintosh, Bellett, Stoney) and emits one chunk per substantive paragraph.
Most authors died before 1928 (PD); the editorial layer is copyright but
not redistributed verbatim.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urljoin

from ingest.cultural._common import fetch_with_politeness
from ingest.cultural._html import ccel_page_paragraphs, chunk_paragraphs, parse_html
from ingest.models import CulturalChunk, CulturalChunkSource

SOURCE_SLUG = "stem-publishing"
WORK_ID = "stem-publishing"
TRADITION: Literal["plymouth-brethren"] = "plymouth-brethren"
LICENSE = "public_domain"
REDISTRIBUTE = True
CANONICAL_URL = "https://www.stempublishing.com/"
FALLBACK_URLS: list[str] = []
EXPECTED = (50, 10000)

AUTHOR_INDEXES: list[tuple[str, str, str]] = [
    ("J. N. Darby", "1882", "https://www.stempublishing.com/authors/darby/"),
    ("William Kelly", "1906", "https://www.stempublishing.com/authors/kelly/"),
    ("C. H. Mackintosh", "1896", "https://www.stempublishing.com/authors/mackintosh/"),
    ("J. G. Bellett", "1864", "https://www.stempublishing.com/authors/bellett/"),
    ("J. B. Stoney", "1897", "https://www.stempublishing.com/authors/stoney/"),
]
MAX_CHUNKS = 20000
MAX_WORKS_PER_AUTHOR = 80


def _author_work_links(raw: bytes, index_url: str) -> list[str]:
    tree = parse_html(raw)
    out: list[str] = []
    seen: set[str] = set()
    for a in tree.xpath("//a/@href"):
        if not isinstance(a, str):
            continue
        if not a.endswith(".html") or a.startswith("#"):
            continue
        if "index" in a.lower():
            continue
        if a in seen:
            continue
        seen.add(a)
        full = urljoin(index_url, a)
        if "stempublishing.com" not in full:
            continue
        out.append(full)
    return out


def parse_work(
    raw: bytes,
    author: str,
    work_id: str,
    anchor_prefix: str,
    date_written: str,
) -> list[CulturalChunk]:
    paras = ccel_page_paragraphs(raw)
    if not paras:
        return []
    chunks = chunk_paragraphs(paras, target_tokens=400, min_tokens=100)
    out: list[CulturalChunk] = []
    for idx, text in enumerate(chunks, start=1):
        anchor = f"{anchor_prefix}.{idx:03d}"
        out.append(
            CulturalChunk(
                chunk_id=f"{SOURCE_SLUG}.{anchor}",
                tradition=TRADITION,
                source=CulturalChunkSource(
                    work_id=work_id,
                    work_title=anchor_prefix.replace(".", " "),
                    author=author,
                    date_written=date_written,
                    is_confessional_text=False,
                    anchor_id=anchor,
                    language="en",
                    translator=None,
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
    for author, date_written, index_url in AUTHOR_INDEXES:
        try:
            raw_index = fetch_with_politeness(index_url, last_request_by_host=last_request)
        except Exception:
            continue
        works = _author_work_links(raw_index, index_url)[:MAX_WORKS_PER_AUTHOR]
        author_slug = author.split()[-1].lower()
        for url in works:
            if len(out) >= MAX_CHUNKS:
                break
            try:
                raw = fetch_with_politeness(url, last_request_by_host=last_request)
            except Exception:
                continue
            work_slug = url.rsplit("/", 1)[-1].replace(".html", "")
            anchor_prefix = f"STEM.{author_slug}.{work_slug}"
            work_id = f"{SOURCE_SLUG}.{author_slug}.{work_slug}"
            out.extend(parse_work(raw, author, work_id, anchor_prefix, date_written))
        if len(out) >= MAX_CHUNKS:
            break
    return out


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
