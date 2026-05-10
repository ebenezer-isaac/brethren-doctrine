# brethren-doctrine

A personal-use theological GraphRAG engine. Combines parallel Bible translations, Hebrew/Greek interlinear, archaeological data, church history, and curated doctrinal teaching notes into a single queryable knowledge system.

This repository is part of a deliberate, three-stage personal apologetic progression:

1. *Does God exist?*
2. *Is Jesus God?*
3. *If Jesus is truth, why are there so many different denominations, and which one is right?*

This engine is the diagnostic tool for stage 3. It is built to triangulate a London (or any) church's stated doctrine against:

- the original Hebrew/Greek (interlinear with Strong's + morphology),
- multiple English translations (formal and dynamic equivalence),
- archaeological context (Open Context, DAAHL, Dead Sea Scrolls),
- church-history nodes (Ecumenical councils, Reformation, modern denominational lineages),
- and a curated personal teaching baseline.

The aim is *calibrated discernment*, not church-scoring.

---

## Layout

```
brethren-doctrine/
├── parsed/                 Sanitized structured JSON corpus (per-document + aggregate index + cross-doc perspectives).
├── docs/                   Project-level docs: PROJECT.md, AUTHORITY_HIERARCHY.md, ANONYMIZATION.md, TIER_2_SPEC.md.
├── ingest/                 Pydantic models and Neo4j upsert adapters (sermon + SOF).
├── embeddings/             Voyage contextualized_embed + FastEmbed BM25 → Qdrant; Neo4j MERGE upsert.
├── retrieval/              Stage 0–4 hybrid retriever (router, hybrid RRF, BGE rerank, authority boost, envelope, Typer CLI).
├── graph/                  Neo4j schema (constraints + vector / fulltext / btree indexes).
├── docker/                 Neo4j + Qdrant compose (Qdrant on 6433/6434 to avoid host-port collisions).
├── research/               Tier 2 design research (embeddings, GraphRAG, hybrid+rerank, Bible data sources, MCP).
├── tools/                  PDF renderers for the personal-beliefs baseline + questionnaire.
├── personal-beliefs.json   241-entry doctrinal taxonomy with KPIs (tier, martyrdom, cult markers, relationship-ladder).
├── personal-beliefs.pdf    Hybrid index + detail PDF rendered from the JSON.
├── personal-beliefs-questionnaire.pdf  Tick-box self-evaluation form rendered from the JSON.
├── USAGE.md                Cross-session guide for querying the corpus from any Claude session.
└── .claude/skills/         `ingest-sermons` skill (Opus subagent orchestration for source → JSON parsing).
```

The `source-docs/` and `converted/` directories are **gitignored**. They contain the raw private inputs (originally personal teaching notes); only sanitized derivatives are public.

## Anonymization

The only personal name permitted anywhere in this repository is the project owner's own. Every other personal contributor (teachers whose teaching is in the corpus, friends, organization members, etc.) is redacted from `parsed/`, code, docs, server responses, and downstream artifacts. External published authors (John Piper, Justin Martyr, Augustine, Calvin, etc.) are retained as citations because they preserve the chain back to public sources. See [docs/ANONYMIZATION.md](docs/ANONYMIZATION.md) for the full policy.

## Authority hierarchy

Every record carries an `authority_level` (0–4):

| Level | Layer | Source |
|---|---|---|
| 0 | Critical Apparatus | Manuscript variants, textual criticism. |
| 1 | Interlinear | OSHB, WLC, SBLGNT, STEPBible alignment. **Source of truth.** |
| 2 | Formal Equivalence | NKJV, ESV. |
| 3 | Dynamic Equivalence | NIV, NLT. (Narrative grasp only — never used for doctrinal mapping.) |
| 4 | Exegetical Application | Personal teaching notes, archaeology, church history, commentaries. |

A Level 4 sermon claim cannot override a Level 1 interlinear reading. See [docs/AUTHORITY_HIERARCHY.md](docs/AUTHORITY_HIERARCHY.md).

## Tiers

- **Tier 1 — Static structured corpus** — *built*. Per-document JSON in `parsed/`, queryable from any Claude session via Read + Grep + jq.
- **Tier 2 — Semantic + Graph layer** — *built for sermon + SOF; Bible / graph traversal / MCP server pending*. See [docs/TIER_2_SPEC.md](docs/TIER_2_SPEC.md).
- **Tier 3 — Interactive surface** — *planned*. MCP server + Flutter client.

## Running locally

```bash
# Set up environment
cp .env.example .env
# Fill in: VOYAGE_API_KEY, NEO4J_PASSWORD

# Bring up Neo4j + Qdrant
docker compose -f docker/docker-compose.yml up -d

# Install Python deps
uv sync

# Apply Neo4j schema
cypher-shell -f graph/schema.cypher

# Bootstrap Qdrant collection
uv run python -m embeddings.bootstrap_qdrant

# Embed and load (requires source-docs/ + parsed/ locally)
uv run python -m embeddings.embed_and_load

# Query
uv run python -m retrieval.cli "what does the corpus say about substitutionary atonement?"
```

To regenerate the personal-beliefs PDFs from the JSON:

```bash
uv run python tools/render_beliefs_pdf.py
uv run python tools/render_beliefs_questionnaire.py
```

## Status

Personal-use, single-user. Design choices reflect that scope: no auth, no multi-tenant, no public API. See [docs/PROJECT.md](docs/PROJECT.md) for the full project picture.

## License

No license declared. Personal-use code shared as-is for educational reference; treat anything you reuse as inspiration rather than a library to depend on.
