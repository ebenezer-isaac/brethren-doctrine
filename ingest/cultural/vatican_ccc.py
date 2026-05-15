"""Catechism of the Catholic Church adapter (Pipeline 1 cultural, stub).

Stub adapter: deferred to live-scrape pass. scrape() returns an empty list when
BD_CULTURAL_LIVE_SCRAPE is unset. Live implementation pulls from CANONICAL_URL
(with FALLBACK_URLS) per docs/INGESTION_PATTERNS.md politeness rules.
"""

from __future__ import annotations

from ingest.cultural._adapter_stub import SKIP_LIVE_SCRAPE
from ingest.models import CulturalChunk

SOURCE_SLUG = "vatican-ccc"
WORK_ID = "vatican-ccc"
TRADITION = "catholic-magisterial"
LICENSE = "Libreria-Editrice-Vaticana"
REDISTRIBUTE = False
CANONICAL_URL = "https://www.vatican.va/archive/ccc_css/archive/catechism/p1.htm"
FALLBACK_URLS: list[str] = []
EXPECTED = (2850, 2870)


def scrape() -> list[CulturalChunk]:
    if SKIP_LIVE_SCRAPE:
        return []
    raise NotImplementedError(
        f"{SOURCE_SLUG} live scrape not implemented in this session; "
        "set BD_CULTURAL_LIVE_SCRAPE=1 only after the per-source live implementation lands"
    )


def expected_chunk_count() -> tuple[int, int]:
    return EXPECTED
