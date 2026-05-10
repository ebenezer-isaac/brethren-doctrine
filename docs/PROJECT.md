# brethren-doctrine: Project Overview

A personal-use theological GraphRAG engine. Combines parallel Bible translations, Hebrew/Greek interlinear, archaeological data, church history, and curated doctrinal teaching notes into a single queryable knowledge system.

This document is the **single source of truth** for any Claude session, future contributor, or researcher operating on the project. Update it when structure or architecture changes.

---

## Purpose

The engine answers questions like:
- "What does the corpus say about [theme] across all teaching documents?"
- "Trace this church's stated doctrine back to its historical roots and show where it diverges from the underlying Hebrew/Greek."
- "Show me where two source documents present different perspectives on the same theme."
- "What is the substitutionary atonement claim grounded in, scripture-by-scripture?"

It is a diagnostic and research tool, not a publishing platform. Single-user. Personal use.

---

## Tier model

The project builds in three tiers. Each tier is independently usable.

### Tier 1: Static structured corpus (BUILT)
- Source documents become structured JSON via Opus subagent orchestration.
- Output lives in `parsed/`. Aggregate in `parsed/_index.json`. Cross-document perspectives in `parsed/_perspectives.json`.
- Any Claude session opening this project can query Tier 1 with Read + Grep + (optional) jq.
- Limitations: exact-match and theme-filter only; no semantic search.

### Tier 2: Semantic + Graph layer (PLANNED, spec at `docs/TIER_2_SPEC.md`)
- Chunks from `parsed/` plus full Bible (multiple translations) plus Hebrew/Greek interlinear plus archaeology plus church history.
- Embeddings + vector DB + knowledge graph.
- Hybrid retrieval (BM25 + dense vector) + cross-encoder rerank.
- Exposed via MCP server.

### Tier 3: Interactive surface (PLANNED)
- MCP server consumed by Claude Desktop, VSCode Claude Code, and a custom Flutter client.
- WebSocket token streaming to the Flutter client.
- Conversational diagnostic queries, parallel translation viewer, interlinear interaction, archaeology overlay.

---

## Directory layout (current)

```
brethren-doctrine/
├── source-docs/              [BUILT] Original sermon source files (15 docs). READ-ONLY.
├── converted/                [BUILT] Pandoc/python-pptx markdown for non-native formats.
├── parsed/                   [BUILT] Per-document structured JSON outputs.
│   ├── _index.json           [BUILT] Corpus aggregate index.
│   └── _perspectives.json    [BUILT] Cross-document perspective comparison.
├── research/                 [BUILT] Tier 2 design research (5 markdown files).
├── docs/                     [BUILT, this directory]
│   ├── PROJECT.md            (this file)
│   ├── AUTHORITY_HIERARCHY.md
│   ├── ANONYMIZATION.md
│   └── TIER_2_SPEC.md        (Tier 2 implementation spec)
├── chunks/                   [PLANNED] Pre-embedding chunked records.
├── embeddings/               [PLANNED] Local cache of vectors before vector DB upload.
├── graph/                    [PLANNED] Neo4j seed scripts and schema migrations.
├── server/                   [PLANNED] MCP server source.
├── client/                   [PLANNED] Flutter app.
├── USAGE.md                  [PLANNED] Cross-session query guide.
└── .claude/
    └── skills/
        └── ingest-sermons/   [BUILT] Source doc → structured JSON parser.
```

Future directories (`chunks/`, `embeddings/`, `graph/`, `server/`, `client/`) are added when their respective Tier 2/3 milestones land. See `TIER_2_SPEC.md`.

---

## Architectural decisions (canonical)

- **Pattern:** Agentic GraphRAG (not naive chunk+embed RAG). Theological data is heavily relational; vector similarity alone misses cross-references.
- **Authority hierarchy enforced everywhere**. See `AUTHORITY_HIERARCHY.md`. Interlinear is source of truth; English translations are derived; sermons/archaeology/history are application-level.
- **Anonymization enforced everywhere**. See `ANONYMIZATION.md`. Strangers must be able to use the corpus without knowing the original teachers.
- **Concrete stack:** see `TIER_2_SPEC.md` for the assembled choices (embedding model, vector DB, graph DB, reranker, MCP SDK).

---

## Override protocol

When the user gives an instruction conflicting with anything established in this project (plans, code, skills, prior conversation, this document), the new instruction is **canonical**. The old method is investigated, mapped, and removed everywhere. Not preserved as a fallback. See `~/.claude/projects/e--projects-working-dir-brethren-doctrine/memory/feedback_override_protocol.md` for the full rule.

Every override is logged in `~/.claude/projects/.../memory/override_log.md` with date, reason, and affected files.

---

## Memory locations

This project uses two memory tiers:

1. **Project-public docs** (this `docs/` directory). Accessible to any agent or future Claude session opening the project. Architectural and operational rules.
2. **Claude private memory** (`~/.claude/projects/e--projects-working-dir-brethren-doctrine/memory/`). Ebenezer's profile, project goals with personal context, doctrinal context, and override log. Loaded into the orchestrator's session automatically.

When updating an architectural rule, update **both** the docs/ file and the corresponding memory file.

---

## Current status (2026-05-10)

- Tier 1 extraction: **complete** (15 documents, ~230 chunks).
- Tier 2 research: **complete** (5 research outputs in `research/`); spec assembly in `docs/TIER_2_SPEC.md`.
- Tier 2 implementation: **not started**.
- Tier 3: **not started**.
