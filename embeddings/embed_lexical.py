"""Embed lexical lemmas + verses into Qdrant lex_col collection.

Reads from the lexical Neo4j (Lemma + Verse nodes), batches through Voyage,
and upserts dense vectors to Qdrant. The MCP retrieval layer queries by Strong's
code or lemma text first via Neo4j, then re-ranks via Qdrant cosine on dense.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from embeddings.bootstrap import VOYAGE_MODEL, VOYAGE_OUTPUT_DIMENSION

NS = uuid.UUID("a4f6e6c0-0000-4000-8000-000000000002")
BATCH = 128
MIN_INTERVAL_SECONDS = 0.0
EMBED_TEXT_MAX_LEN = 6000
# Full Lemma + GreekLemma corpus floor is 22717 (TBESH 11682 + TBESG
# 11035 distinct Strong-keyed lemmas per tools/expected_counts.json).
# 50000 covers that floor with ample headroom for MACULA-only and
# disambiguated-sense lemma ids while keeping the query bounded (O(n)
# over a single ORDER BY ... LIMIT, no full-graph fan-out).
DEFAULT_LEMMA_LIMIT = 50000


def build_embed_text(row: dict[str, Any]) -> str:
    """Compose the input string handed to Voyage for one Lemma row.

    Phase Z.1 contract (RESEED_PLAN E.1):

    * concatenates lemma, transliteration, gloss, plus part-of-speech
      and semantic-domain hints when present (Phase E enrichment);
    * yields >= 6 distinct whitespace-separated tokens once
      ``pos``/``domain`` columns are populated;
    * deterministic: same input row always yields the same text;
    * never returns the empty string for a row whose required fields
      (``lemma``, ``transliteration``, ``gloss``) are non-empty;
    * truncates to ``EMBED_TEXT_MAX_LEN`` characters at the tail.

    The function is pure: no I/O, no globals beyond the constant cap.
    """
    parts: list[str] = []
    lemma = (row.get("lemma") or "").strip()
    translit = (row.get("transliteration") or "").strip()
    gloss = (row.get("gloss") or "").strip()
    if lemma:
        parts.append(lemma)
    if translit and translit != lemma:
        parts.append(f"({translit})")
    if gloss:
        parts.append(f": {gloss}")
    pos = (row.get("pos") or "").strip()
    if pos:
        parts.append(f"| pos {pos}")
    domain = (row.get("domain") or "").strip()
    if domain:
        parts.append(f"| domain {domain}")
    louw_nida = (row.get("louw_nida") or "").strip()
    if louw_nida:
        parts.append(f"| LN {louw_nida}")
    text = " ".join(parts).strip()
    return text[:EMBED_TEXT_MAX_LEN]


def _iter_lemmas(session: Any, limit: int) -> list[dict[str, Any]]:
    """Project every Strong-keyed lemma row for the Voyage embed path.

    On the real lexical graph the enrichment fields do NOT live directly
    on the lemma node. ``transliteration``, ``pos`` and the English
    ``gloss`` are carried by the connected ``BriefLexEntry`` (STEPBible
    TBESH/TBESG) reachable via ``LEX_FOR``; the Louw-Nida code is the
    ``LouwNidaDomain`` reachable through any instance ``Word`` and the
    MACULA-Greek semantic ``domain`` string is a ``Word`` property. The
    pre-fix query SELECTed only ``l.transliteration``/``l.gloss`` (which
    are null on real data) and never projected ``pos``/``domain``/
    ``louw_nida`` at all, so on production data ``build_embed_text`` fell
    below the RESEED_PLAN E.1 floor of >= 6 distinct tokens. This query
    OPTIONAL MATCHes the nodes that actually hold those fields and
    projects them only when the source populated them (no fabrication;
    the per-type non-empty predicate is preserved by ``coalesce(..., '')``
    plus the non-empty guards inside ``build_embed_text``).

    Both ``Lemma`` (Hebrew) and ``GreekLemma`` (Greek) are covered: the
    pre-fix query matched ``Lemma`` only, silently dropping the entire
    GreekLemma corpus from the embed collection.
    """
    rows = list(
        session.run(
            """
            MATCH (l)
            WHERE (l:Lemma OR l:GreekLemma) AND l.strong IS NOT NULL
            OPTIONAL MATCH (b:BriefLexEntry)-[:LEX_FOR]->(l)
            WITH l,
                 head(collect(b)) AS b
            OPTIONAL MATCH (l)<-[:INSTANCE_OF]-(dw:Word)
            WHERE dw.domain IS NOT NULL AND dw.domain <> ''
            WITH l, b, head(collect(dw.domain)) AS word_domain
            OPTIONAL MATCH (l)<-[:INSTANCE_OF]-(:Word)-[:IN_DOMAIN]->(d:LouwNidaDomain)
            WITH l, b, word_domain,
                 head(collect(
                   toString(d.domain_code) +
                   CASE WHEN d.subdomain_code IS NOT NULL
                        THEN '.' + toString(d.subdomain_code) ELSE '' END
                 )) AS ln_code
            RETURN l.strong AS strong,
                   l.lemma AS lemma,
                   coalesce(b.transliteration, l.transliteration, l.lemma)
                     AS transliteration,
                   coalesce(b.english, b.gloss_line, l.gloss, '') AS gloss,
                   coalesce(b.pos, l.pos, '') AS pos,
                   coalesce(word_domain, l.domain, '') AS domain,
                   coalesce(ln_code, l.louw_nida, '') AS louw_nida,
                   coalesce(l.license, 'public_domain') AS license,
                   coalesce(l.redistribute, true) AS redistribute
            ORDER BY l.strong, elementId(l)
            LIMIT $lim
            """,
            lim=limit,
        )
    )
    return [dict(r) for r in rows]


def _recreate_collection(qclient: Any, collection: str) -> None:
    """Drop and recreate exactly ``collection`` before any point is written.

    Deterministic-rebuild rationale: the embed run upserts points keyed by
    ``uuid5(NS, strong)``. Upsert never deletes. Across the Phase D graph
    rebuilds the lexical topology changed, so Strong values that existed in
    a prior topology but not the current one left orphaned vector points
    behind (the audit found lex_col carrying 2801 stale textless shells
    absent from the current graph). Recreating the collection here makes
    the phase deterministic and idempotent: after a run lex_col mirrors
    EXACTLY the current graph's embeddable Strong set, with zero stale
    points, so two consecutive full runs on the same frozen graph yield the
    same point ids and the same points_count. This drop is scoped strictly
    to the collection named by ``--collection`` (default lex_col); no other
    collection is read or touched. Vector config is held identical to
    embeddings.bootstrap (named vector "dense", size VOYAGE_OUTPUT_DIMENSION
    == 2048, COSINE distance) so retrieval semantics are unchanged.
    """
    existing = {c.name for c in qclient.get_collections().collections}
    if collection in existing:
        qclient.delete_collection(collection_name=collection)
    qclient.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": VectorParams(
                size=VOYAGE_OUTPUT_DIMENSION, distance=Distance.COSINE
            )
        },
    )


def _embed_batch(voyage_client: Any, texts: list[str]) -> list[list[float]] | None:
    retries = 0
    while True:
        try:
            result = voyage_client.embed(
                texts=texts,
                model=VOYAGE_MODEL,
                input_type="document",
                output_dimension=VOYAGE_OUTPUT_DIMENSION,
            )
            return list(result.embeddings)
        except Exception as exc:
            msg = str(exc)
            if retries < 3 and ("rate" in msg.lower() or "429" in msg or "TPM" in msg):
                backoff = 30 * (retries + 1)
                print(f"  rate-limit backoff {backoff}s", file=sys.stderr)
                time.sleep(backoff)
                retries += 1
                continue
            print(f"  voyage error: {msg[:200]}", file=sys.stderr)
            return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    # Lemma corpus contract (tools/expected_counts.json): STEPBible-TBESH
    # ships 11682 Strong-keyed Hebrew lemmas and STEPBible-TBESG ships
    # 11035 Greek lemmas => 22717 distinct Strong-keyed lemmas form the
    # Lemma + GreekLemma node floor (the MACULA producers MERGE on the
    # same Strong identities and are deduped by id). The prior default of
    # 20000 truncated ~2717 lemmas (~12% of the corpus) off the
    # production embed path. DEFAULT_LEMMA_LIMIT covers the full corpus
    # with headroom for any MACULA-only / disambiguated-sense lemma ids
    # beyond the brief-lexicon Strong set; pass --limit explicitly to cap
    # a partial run.
    parser.add_argument("--limit", type=int, default=DEFAULT_LEMMA_LIMIT)
    parser.add_argument("--collection", default="lex_col")
    args = parser.parse_args(argv)

    voyage_api_key = os.environ.get("VOYAGE_API_KEY")
    qdrant_url = os.environ.get("QDRANT_LEXICAL_URL")
    if not voyage_api_key or not qdrant_url:
        print("VOYAGE_API_KEY and QDRANT_LEXICAL_URL required", file=sys.stderr)
        return 2

    import voyageai

    voyage_client = voyageai.Client(api_key=voyage_api_key)  # type: ignore[attr-defined]
    qclient = QdrantClient(url=qdrant_url)

    # Rebuild the target collection BEFORE embedding so the run is
    # deterministic and idempotent: lex_col ends mirroring exactly the
    # current graph's embeddable Strong set, eliminating cross-rebuild
    # stale-point accumulation. Scoped to args.collection only.
    _recreate_collection(qclient, args.collection)

    driver = GraphDatabase.driver(
        os.environ["NEO4J_LEXICAL_URI"],
        auth=(os.environ["NEO4J_LEXICAL_USER"], os.environ["NEO4J_LEXICAL_PASSWORD"]),
    )

    embedded = 0
    skipped_no_text = 0
    failures = 0
    with driver.session() as session:
        lemmas = _iter_lemmas(session, args.limit)
        print(f"loaded {len(lemmas)} lemmas", flush=True)

        last = 0.0
        for i in range(0, len(lemmas), BATCH):
            batch = lemmas[i : i + BATCH]
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
            # Partition the chunk before any Voyage call. Some Strong-keyed
            # rows are textless: they are the Decision 11/18 tbesh-minted
            # Strong-only convergence shells (a Strong has a lexicon or
            # instance presence but no transliteration, gloss or lemma
            # text), so build_embed_text returns "" for them. Voyage rejects
            # any request whose input list contains an empty string and
            # fails the WHOLE batch, which previously dropped good rows as
            # collateral. We never fabricate text for these shells and never
            # send "" to Voyage. Textless shells are intentionally not
            # embedded: they stay joinable by Strong in Neo4j, and the
            # Qdrant layer is only a re-rank, so a textless shell has
            # nothing to re-rank on. This is correct by Decision 11/18, not
            # a fudge. Row to vector alignment is preserved by zipping
            # vectors only against embed_rows (the non-empty subset).
            embed_rows: list[dict[str, Any]] = []
            texts: list[str] = []
            for r in batch:
                t = build_embed_text(r).strip()
                if t:
                    embed_rows.append(r)
                    texts.append(t)
                else:
                    skipped_no_text += 1
            if not texts:
                continue
            vecs = _embed_batch(voyage_client, texts)
            last = time.monotonic()
            if vecs is None:
                failures += len(embed_rows)
                continue
            points = []
            for r, vec in zip(embed_rows, vecs, strict=False):
                payload = {
                    "strong": r["strong"],
                    "lemma": r["lemma"],
                    "transliteration": r["transliteration"],
                    "gloss": r["gloss"],
                    "license": r["license"],
                    "redistribute": r["redistribute"],
                }
                point_id = str(uuid.uuid5(NS, r["strong"]))
                points.append(PointStruct(id=point_id, vector={"dense": vec}, payload=payload))
            qclient.upsert(collection_name=args.collection, points=points)
            embedded += len(points)
            if (i // BATCH) % 5 == 0:
                print(f"  progress: {embedded}/{len(lemmas)} embedded", flush=True)

    driver.close()
    print(
        f"TOTAL: embedded={embedded} "
        f"skipped_no_text={skipped_no_text} failures={failures}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
