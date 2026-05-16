"""Run one cultural-source scrape, persist chunks as JSONL, ingest to Neo4j.

Usage:
    python -m tools.run_cultural_scrape <source_module>

Writes:
    data/cultural_chunks/<source_module>.jsonl   (one chunk per line)
    data/cultural_chunks/<source_module>.status  ({chunks, neo4j_counts, error?})
"""

from __future__ import annotations

import importlib
import json
import sys
import time
import traceback
from pathlib import Path

from ingest.cultural._common import Settings, get_cultural_driver, upsert_chunks

OUTPUT_DIR = Path("data/cultural_chunks")


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        print("usage: run_cultural_scrape <source_module>", file=sys.stderr)
        return 2
    name = args[0]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUTPUT_DIR / f"{name}.jsonl"
    status_path = OUTPUT_DIR / f"{name}.status"

    start = time.monotonic()
    try:
        mod = importlib.import_module(f"ingest.cultural.{name}")
        chunks = mod.scrape()
    except Exception as exc:
        status_path.write_text(
            json.dumps(
                {
                    "source": name,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "elapsed_seconds": round(time.monotonic() - start, 1),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"FAIL {name}: {exc}", file=sys.stderr)
        return 1

    elapsed = round(time.monotonic() - start, 1)

    with jsonl_path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(chunk.model_dump_json() + "\n")

    neo4j_counts: dict[str, int] = {}
    ingest_error: str | None = None
    if chunks:
        try:
            settings = Settings()  # type: ignore[call-arg]
            driver = get_cultural_driver(settings)
            try:
                neo4j_counts = upsert_chunks(driver, chunks)
            finally:
                driver.close()
        except Exception as exc:
            ingest_error = f"{type(exc).__name__}: {exc}"

    status = {
        "source": name,
        "chunks": len(chunks),
        "elapsed_seconds": elapsed,
        "jsonl_path": str(jsonl_path),
        "neo4j_counts": neo4j_counts,
        "ingest_error": ingest_error,
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
