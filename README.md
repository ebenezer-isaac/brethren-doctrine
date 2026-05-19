# christian-doctrine

A manuscript-anchored personal Bible-doctrine engine. It produces a doctrinal verdict from the original-language manuscript tradition alone, then attaches a separate diagnostic overlay showing how each tracked Christian tradition reads the same lexical pattern. The system runs two physically separate, air-gapped data stores: a lexical store (Scripture, lexicon, morphology, syntax, cross-references, apparatus where published) and a cultural store (church teaching: confessions, patristic, magisterial, denominational). An in-house orchestrator dispatches the work and voyage-4-large supplies embeddings at native 2048 dimensions for both stores. Pipeline 2 derives the Scripture-only doctrinal baseline and is air-gapped from the cultural store at the data-model level; the cultural side is a separate diagnostic overlay that records, never adjudicates. It is single-user, personal-use tooling.

## Canonical documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) system spec, governance model, the standing trustworthiness gate, and the intentional scope boundaries.
- [docs/SCHEMA_DECISIONS.md](docs/SCHEMA_DECISIONS.md) and [docs/CULTURAL_SCHEMA_DECISIONS.md](docs/CULTURAL_SCHEMA_DECISIONS.md) the graph contracts for the lexical and cultural stores.
- [docs/EVIDENCE_SCHEMA.md](docs/EVIDENCE_SCHEMA.md) and [docs/CULTURAL_SCHEMA.md](docs/CULTURAL_SCHEMA.md) the output schemas (per-question lexical audit trail, per-chunk doctrine tagging).
- [docs/data_inventory_catalog.json](docs/data_inventory_catalog.json) and [docs/cultural_data_inventory_catalog.json](docs/cultural_data_inventory_catalog.json) the authoritative source-count contract.

## Bring-up

```bash
# 1. Start the two air-gapped Docker stacks (separate projects, separate networks)
docker compose -p brethren-lexical  -f docker/lexical/docker-compose.yml  up -d
docker compose -p brethren-cultural -f docker/cultural/docker-compose.yml up -d

# 2. Apply the graph schema to each Neo4j (lexical bolt :7688, cultural bolt :7689)
cypher-shell -a bolt://localhost:7688 -f graph/lexical.cypher
cypher-shell -a bolt://localhost:7689 -f graph/cultural.cypher

# 3. Bootstrap the two Qdrant collections
python embeddings/bootstrap.py --store lexical
python embeddings/bootstrap.py --store cultural

# 4. Ingest the lexical sources into the lexical store
python ingest/lexical/run.py --dataset all

# 5. Reseed the cultural store (deterministic from captured jsonl by default)
python tools/cultural_reseed.py --mode from-jsonl --source all

# 6. Embed both stores with voyage-4-large
python embeddings/embed_lexical.py
python embeddings/embed_cultural.py --sources all
```

`ingest/lexical/run.py --list` prints every wired lexical dataset.
`tools/cultural_reseed.py --mode scrape` re-acquires the cultural sources live (resumable, bounded concurrency) instead of replaying captured jsonl.

## Trust and verification

The standing proof of trustworthiness is the manifest at `docs/RESEED_MANIFEST_<ts>.json`, re-executed independently against the live stores:

```bash
python tools/verify_manifest.py --manifest docs/RESEED_MANIFEST_20260519T192150Z.json
python tools/generate_trust_report.py        # writes reports/TRUST_REPORT_latest.pdf
```

`verify_manifest.py` recomputes every claim and only then compares it to the manifest. `generate_trust_report.py` turns that verdict into a plain-language PDF. A GREEN report means the live data reproduces the certified contract. Re-run both after any restore.

## Backup and restore

`backups/` (gitignored) holds consistent physical backups of both stores, taken with the containers stopped for filesystem consistency. The backup procedure is its own inverse, so a restore is reliable. The runbook is [backups/RESTORE.md](backups/RESTORE.md). After restoring, re-run the trust verification above.
