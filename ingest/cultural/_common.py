"""Shared helpers for Pipeline 1 cultural adapters.

Provides:
  - Settings (env-driven; uses NEO4J_CULTURAL_* and QDRANT_CULTURAL_*)
  - get_cultural_driver(settings) -> Driver
  - fetch_with_politeness(url, ua, ...) -> bytes (enforces 2s gap per host)
  - scrape_source(slug, canonical_url, fallbacks) -> bytes (tries each in order)
  - upsert_chunks(driver, chunks) -> dict[str, int] (Work + CulturalChunk + HAS_CHUNK)

TLS-fragile hosts surface SSLError instead of silently bypassing verification.
"""

from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any

from neo4j import Driver, GraphDatabase
from pydantic_settings import BaseSettings, SettingsConfigDict

from ingest.license_guard import check_redistribute
from ingest.models import CulturalChunk

POLITENESS_GAP_SECONDS = 2.0
DEFAULT_UA = "brethren-doctrine-bot/0.1 (+https://github.com/ebenezerisaac)"

TLS_FRAGILE_HOSTS = ("justus.anglican.org",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    neo4j_cultural_uri: str
    neo4j_cultural_user: str
    neo4j_cultural_password: str
    qdrant_cultural_url: str
    voyage_api_key: str = ""


_last_request_by_host: dict[str, float] = {}


def get_cultural_driver(settings: Settings) -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_cultural_uri,
        auth=(settings.neo4j_cultural_user, settings.neo4j_cultural_password),
    )


def _host_of(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).hostname or ""


def fetch_with_politeness(
    url: str,
    user_agent: str = DEFAULT_UA,
    timeout: float = 30.0,
    last_request_by_host: dict[str, float] | None = None,
) -> bytes:
    """GET with a 2s gap enforced per-host. Returns response bytes.

    Raises urllib.error.URLError on HTTP error, ssl.SSLError on TLS handshake failure.
    Never disables certificate verification (TLS_FRAGILE_HOSTS use fallbacks instead).
    """
    state = last_request_by_host if last_request_by_host is not None else _last_request_by_host
    host = _host_of(url)
    now = time.monotonic()
    if host in state:
        elapsed = now - state[host]
        wait = POLITENESS_GAP_SECONDS - elapsed
        if wait > 0:
            time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: bytes = resp.read()
    finally:
        state[host] = time.monotonic()
    return data


def scrape_source(
    source_slug: str,
    canonical_url: str,
    fallback_urls: list[str] | None = None,
    user_agent: str = DEFAULT_UA,
) -> bytes:
    """Fetch source bytes, falling back through alternative URLs on 4xx / SSLError."""
    candidates = [canonical_url] + (fallback_urls or [])
    errors: list[str] = []
    for url in candidates:
        try:
            return fetch_with_politeness(url, user_agent=user_agent)
        except urllib.error.HTTPError as e:
            errors.append(f"{url} -> HTTP {e.code}")
        except urllib.error.URLError as e:
            errors.append(f"{url} -> {e.reason}")
        except ssl.SSLError as e:
            errors.append(f"{url} -> SSL {e}")
    raise RuntimeError(f"scrape failed for {source_slug}: {'; '.join(errors)}")


_WORK_CYPHER = """
UNWIND $rows AS row
MERGE (w:Work {work_id: row.work_id})
SET w += row.properties
RETURN count(w) AS upserted
"""

_CHUNK_CYPHER = """
UNWIND $rows AS row
MERGE (c:CulturalChunk {chunk_id: row.chunk_id})
SET c += row.properties
WITH c, row
MATCH (w:Work {work_id: row.work_id})
MERGE (w)-[:HAS_CHUNK]->(c)
RETURN count(c) AS upserted
"""


def upsert_chunks(
    driver: Driver, chunks: Iterable[CulturalChunk], batch_size: int = 200
) -> dict[str, int]:
    counts: dict[str, int] = {}
    batch: list[CulturalChunk] = []

    def _flush(buf: list[CulturalChunk]) -> None:
        if not buf:
            return
        works: dict[str, dict[str, Any]] = {}
        chunk_rows: list[dict[str, Any]] = []
        for c in buf:
            redistribute_ok = check_redistribute(c.license, "bulk")
            text_value = c.text if redistribute_ok else c.text_to_embed
            works[c.source.work_id] = {
                "work_id": c.source.work_id,
                "properties": {
                    "title": c.source.work_title,
                    "author": c.source.author,
                    "date_written": c.source.date_written,
                    "tradition": c.tradition,
                    "language": c.source.language,
                    "is_confessional_text": c.source.is_confessional_text,
                },
            }
            chunk_rows.append(
                {
                    "chunk_id": c.chunk_id,
                    "work_id": c.source.work_id,
                    "properties": {
                        "tradition": c.tradition,
                        "anchor_id": c.source.anchor_id,
                        "text": text_value,
                        "text_to_embed": c.text_to_embed,
                        "license": c.license,
                        "redistribute": c.redistribute,
                        "license_note": c.license_note,
                        "source_work_id": c.source.work_id,
                        "translator": c.source.translator,
                        "doctrine_tags": [t.model_dump_json() for t in c.doctrine_tags],
                    },
                }
            )
        with driver.session() as session:
            session.run(_WORK_CYPHER, rows=list(works.values())).consume()
            result = session.run(_CHUNK_CYPHER, rows=chunk_rows).single()
            n = int(result["upserted"]) if result else 0
            counts["CulturalChunk"] = counts.get("CulturalChunk", 0) + n
            counts["Work"] = counts.get("Work", 0) + len(works)

    for c in chunks:
        batch.append(c)
        if len(batch) >= batch_size:
            _flush(batch)
            batch = []
    _flush(batch)
    return counts
