"""Pipeline 1 cultural ingest CLI.

Dispatches per-source scrape adapters, optionally autotag, then upsert into
cultural Neo4j (and later, cult_col in Qdrant). The Brethren parsed adapter
is offline; all other adapters are stubs unless BD_CULTURAL_LIVE_SCRAPE=1.
"""

from __future__ import annotations

import argparse
import importlib
import json

from ingest.cultural._common import Settings, get_cultural_driver, upsert_chunks
from ingest.models import CulturalChunk

ADAPTERS = [
    "schleitheim",
    "augsburg",
    "heidelberg",
    "belgic",
    "dort",
    "wcf",
    "wlc_catechism",
    "wsc",
    "lbc_1689",
    "articles_39",
    "umc",
    "ag",
    "oca_hopko",
    "vatican_ccc",
    "vatican_dv",
    "ccel_anf",
    "ccel_npnf1",
    "ccel_npnf2",
    "conciliar",
    "stem_publishing",
    "bcp_1662",
    "brethren_parsed",
]


def _run_source(name: str, settings: Settings, write: bool) -> dict[str, int]:
    mod = importlib.import_module(f"ingest.cultural.{name}")
    scrape_fn = mod.scrape
    chunks: list[CulturalChunk] = scrape_fn()
    counts = {"chunks": len(chunks)}
    if write and chunks:
        driver = get_cultural_driver(settings)
        try:
            counts.update(upsert_chunks(driver, chunks))
        finally:
            driver.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="all")
    parser.add_argument("--skip-autotag", action="store_true")
    parser.add_argument("--autotag-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.source == "all":
        chosen = ADAPTERS
    else:
        chosen = [s.strip() for s in args.source.split(",") if s.strip()]

    settings = Settings()  # type: ignore[call-arg]
    write = not args.dry_run
    results: dict[str, dict[str, int]] = {}
    for name in chosen:
        try:
            results[name] = _run_source(name, settings, write)
        except NotImplementedError as e:
            results[name] = {"_skipped": 1, "_reason": str(e)[:80]}  # type: ignore[dict-item]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
