# brethren-doctrine: Project Overview

A personal-use theological GraphRAG engine. Combines parallel Bible translations, Hebrew/Greek interlinear with full concordance, archaeological data, church history, and curated doctrinal teaching notes into a single queryable knowledge system.

This document is the single source of truth for project structure, current architecture, and remaining work. Update it when structure or architecture changes.

---

## Purpose

The engine answers two classes of question:

**Diagnostic / discernment** (the stage-3 question Ebenezer is working through):
- "What does Scripture itself say about [doctrine] when read against the apparatus + interlinear + concordance, prior to any single tradition's confessional commitment?"
- "Where does each major Christian lineage read this passage differently, and why?"
- "Does this church's stated doctrine survive primary-source scrutiny?"

**Corpus exploration** (the trusted-source teaching notes):
- "What does the corpus say about [theme] across the documents I trust?"
- "Where do two source documents present different perspectives on the same theme?"
- "What does my baseline say about this proposition, and how does the church I'm visiting compare?"

It is a diagnostic and research tool, not a publishing platform. Single-user. Personal use.

---

## The two pipelines

The engine runs two distinct pipelines that share a graph backbone and an answer schema:

### Pipeline A — Inferred-baseline derivation

A tradition-neutral lexical-philological floor for the 221 questions in `questions.json`. Each question is settled by **apparatus + interlinear + concordance**, with counter-witness traditions consulted as research aids to verify the lexical reading isn't idiosyncratic. Confessions and Brethren teaching notes are NOT in this pipeline; they live in pipeline B.

Output: `baseline.json` (221 × 13-field answers) + `evidence/<id>.json` (per-question audit trail).

Driven by [tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md) and [tools/baseline_orchestrator.py](../tools/baseline_orchestrator.py); validated by [tools/verify_baseline.py](../tools/verify_baseline.py).

### Pipeline B — Respondent-specific overlays

Per-respondent files in `responses/<respondent_id>.json` capture how a specific church / elder / Ebenezer himself answers the same 221 questions, with their own confessional or teaching-tradition lens. This is where 1689 LBC, WCF, Brethren Archive, and `parsed/` sermon material live — they are inputs to *individual viewpoints*, not to the canonical baseline.

The retrieval CLI (`uv run python -m retrieval.cli`) is for pipeline B and for downstream church-evaluation queries. It is **not** invoked from the inferred-baseline run.

After all respondents file, `consolidated.json` is the final post-research baseline (collation + research) used to evaluate potential churches Ebenezer is considering visiting or joining.

---

## Tier model

The data infrastructure builds in three tiers. Each is independently usable.

### Tier 1: Static structured corpus (BUILT)
- Source documents become structured JSON via Opus subagent orchestration (`ingest-sermons` skill).
- Output lives in `parsed/`. Aggregate in `parsed/_index.json`. Cross-document perspectives in `parsed/_perspectives.json`.
- Any Claude session opening this project can query Tier 1 with Read + Grep + jq.
- Used by pipeline B (respondent overlays); not used by pipeline A.

### Tier 2: Semantic + Graph layer (BUILT for sermon/SOF; concordance + Bible-text loading PENDING)

What's built:
- Neo4j 5.x (Docker, see `docker/docker-compose.yml`) with Cypher schema in `graph/schema.cypher`: SermonChunk, SOFChunk, Concept nodes; MENTIONS / REFERENCES / PRESENTS_PERSPECTIVE_ON edges; vector + B-tree + full-text indexes.
- Qdrant (Docker, single-node) with the `chunks` collection (1024-dim dense vectors via voyage-context-3 + sparse BM25 vectors via FastEmbed Modifier.IDF).
- Ingestion adapters (`ingest/`, `embeddings/`) for sermon and SOF chunks from `parsed/*.json`. Idempotent MERGE-based upsert. authority_level stamped at the boundary.
- Hybrid retrieval CLI (`retrieval/`): router → Qdrant Query API with RRF fusion → BGE-reranker-v2-m3 → authority-boost → optional graph hop-1 → contradiction surface.
- Five sample queries pass the gold-set bar.

What's pending:
- **Concordance ingestion**: TAHOT + TAGNT (Strong's-tagged Hebrew/Greek tokens), OSHB cross-validation, OpenBible cross-references, TSK long-tail xrefs. Ingestion loaders are written ([ingest/adapters/concordance_loader.py](../ingest/adapters/concordance_loader.py)) but **not yet run**. See [CONCORDANCE.md](CONCORDANCE.md).
- **Bible-text ingestion**: ESV/NLT/NIV/NKJV translations via api.bible (free tier). Not yet started. Tied into the Verse nodes already in the schema.
- **MCP server**: FastMCP 3.x exposing 5 tools (`search_bible_interlinear`, `query_sermon_graph`, `get_doctrine_perspectives`, `lookup_archaeology`, `evaluate_statement_of_faith`) — schema is designed, server not yet built.

### Tier 3: Interactive surface (PLANNED)
- MCP server consumed by Claude Desktop, VSCode Claude Code, and a custom Flutter client.
- Conversational diagnostic queries, parallel translation viewer, interlinear interaction.

---

## Architectural decisions (canonical)

**Pattern.** Agentic GraphRAG (not naive chunk+embed RAG). Theological data is heavily relational; vector similarity alone misses cross-references and lemma-occurrence mappings. The concordance layer makes `analogia scripturae` mechanical instead of editorial.

**Authority hierarchy.** Critical Apparatus (Level 0) → Interlinear (Level 1, source of truth) → Formal translations (Level 2) → Dynamic translations (Level 3) → Application / sermons / archaeology / history (Level 4). Confessions are NOT a tier; they are an information layer recorded as `counter_witness[]` in evidence files. See [AUTHORITY_HIERARCHY.md](AUTHORITY_HIERARCHY.md).

**Tradition-neutral baseline.** The inferred baseline is a lexical-philological floor all 8 major lineages (Eastern Orthodox, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal) can audit. The phrasing "Scripture-only" is deliberately avoided — `sola scriptura` is itself a Reformed distinctive; the baseline frames itself as "lexical force of the original languages, prior to confessional commitment." See [HERMENEUTICS.md](HERMENEUTICS.md) §primary methods.

**Cult-marker bar.** Three conditions, all canonical: (i) `would_die_for=true` entailment; (ii) apparatus + interlinear + concordance demonstrate the doctrine canonically; (iii) ≥6 distinct counter-witness lineages corroborate with `stance="affirms"`. **Even Trinity is not exempt.** Cross-tradition consensus is corroborating evidence the lexical reading isn't idiosyncratic; it is not the bar. See [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md) §Cult-marker bar.

**Anonymization.** Strangers must be able to use the corpus without knowing the original teachers. Only "Ebenezer" appears anywhere; every other personal name is `[REDACTED]`. See [ANONYMIZATION.md](ANONYMIZATION.md).

**Concrete stack.**

| Layer | Choice |
|---|---|
| Embeddings | `voyage-context-3` @ 1024-dim float32, 32k ctx |
| Vector DB | Qdrant (self-hosted Docker), dense + sparse BM25 with Modifier.IDF |
| Knowledge graph | Neo4j 5.x Community (Docker) with APOC |
| Reranker | BGE-reranker-v2-m3 in-process (sentence-transformers, CPU) |
| Concordance | STEPBible TAHOT + TAGNT + OSHB cross-validation, OpenBible.info + TSK cross-references, all CC BY 4.0 / public domain |
| Orchestration | `neo4j-graphrag-python` for `VectorCypherRetriever` and `QdrantNeo4jRetriever` |
| MCP server (planned) | FastMCP 3.x, stdio transport |

---

## Directory layout (current)

```
brethren-doctrine/
├── source-docs/              [BUILT, gitignored] Original sermon source files (15 docs).
├── converted/                [BUILT, gitignored] Pandoc/python-pptx markdown for non-native formats.
├── parsed/                   [BUILT] Per-document structured JSON outputs.
│   ├── _index.json           [BUILT] Corpus aggregate index.
│   └── _perspectives.json    [BUILT] Cross-document perspective comparison.
├── research/                 [BUILT] Tier 2 design research (5 markdown files).
├── docs/                     [BUILT]
│   ├── PROJECT.md            (this file)
│   ├── ANSWER_SCHEMA.md      Locked answer + evidence shape.
│   ├── QUESTION_SCHEMA.md    Locked question shape + envelope.
│   ├── AUTHORITY_HIERARCHY.md  0-4 tier scale; confessions are not a tier.
│   ├── HERMENEUTICS.md       Primary methods, frameworks, figures, genre rules.
│   ├── CONCORDANCE.md        Spider-map data sources + Neo4j schema.
│   ├── ANONYMIZATION.md      Privacy policy.
│   └── RELATED_WORK.md       Survey of public Bible-RAG / theology-MCP / confession-text projects; novelty discriminators.
├── ingest/                   [BUILT for sermons/SOF; concordance loaders WRITTEN, not yet run]
│   ├── models.py             Pydantic GraphRecord types with authority_level.
│   ├── upsert.py             Single-writer Cypher MERGE.
│   └── adapters/
│       ├── sermon_loader.py
│       ├── sof_loader.py
│       └── concordance_loader.py   [WRITTEN] TAHOT + TAGNT + OSHB + OpenBible + TSK.
├── embeddings/               [BUILT] Voyage contextualized_embed + FastEmbed BM25 → Qdrant; Neo4j upsert.
├── retrieval/                [BUILT] Hybrid retriever (router, hybrid RRF, BGE rerank, authority boost, envelope, Typer CLI).
├── graph/                    [BUILT] Neo4j schema (constraints + vector / fulltext / btree indexes).
├── docker/                   [BUILT] Neo4j + Qdrant compose (Qdrant on 6433/6434).
├── tools/                    [BUILT]
│   ├── derive_baseline_prompt.md     Methodology doc for the inferred-baseline run.
│   ├── baseline_orchestrator.py      Runtime template + validator.
│   ├── verify_baseline.py            KPI verifier (run before any orchestrator run).
│   ├── verify_catalogs.json          Pre-seeded catalogs (H5 anthropomorphism, H6 dispensational, K2 cult-marker eligibility).
│   └── evidence_to_pdf.py            A4 PDF report renderer.
├── evidence/                 [POPULATED BY ORCHESTRATOR RUN] Per-question audit trail.
├── responses/                [PRIVATE, gitignored] Filled questionnaires from trusted-elder collaborators + Ebenezer.
├── questions.json            Universal question bank (221 entries; phase-3 reframe pending).
├── README.md                 Public framing.
├── USAGE.md                  Cross-session query guide.
└── .claude/skills/
    └── ingest-sermons/       [BUILT] Source doc → structured JSON parser.
```

---

## Phase plan

| Phase | Scope | Status |
|---|---|---|
| **1. Architecture rewrite** | All docs/, tools/, schemas, README, memory aligned to the tradition-neutral lexical-philological architecture with concordance + hermeneutics + counter-witness pillars. | **Complete** |
| **1.5 Concordance ingestion** | Run `ingest/adapters/concordance_loader.py` to populate Neo4j with TAHOT + TAGNT + OSHB validation + OpenBible cross-references. | In progress / next |
| **1.6 Question-text reframe** | Audit `questions.json` for verdict-pre-loading, confessional-vocabulary smuggling, named-carrier inlining, and overlap; rewrite `statement` fields to neutral propositions. Gated by `tools/verify_questions.py`. **Must complete BEFORE phase 2** — running the orchestrator on biased stems wastes a multi-day Max-subscription run. Audit produced `questions-reframe-proposal.md` (1075 lines, 78 sections); 71 reframes applied via `tools/apply_question_reframe.py`. Two destructive merge candidates (prc-believers-baptism-only ⇄ doc-paedobaptism-denial; prc-weekly-breaking-of-bread ⇄ prc-communion-frequency) flagged for explicit user approval. | **Complete** (0 of 221 questions flagged by hygiene verifier) |
| **2. Inferred-baseline orchestrator run** | Run `tools/baseline_orchestrator.py` to produce `baseline.json` + `evidence/*.json` for all 221 questions. Recommended model: Opus on tier=essential/convictional, Sonnet on rest (or all-Opus if rate-limit windows tolerable). Gated on phases 1, 1.5, and 1.6 all green. | Awaiting gates |
| **2.5 Verdict-graph ingestion** | `ingest/adapters/verdict_loader.py load-all` bridges `baseline.json` + `evidence/*.json` into the existing concordance graph as `:Question`, `:Verdict`, `:ScriptureCitation`, `:CounterWitness`, `:Framework`, `:CompetingLens`, `:Flag` nodes — with edges INTO `:Verse` and `:Lemma`. **This is the bridge from flat JSON to the queryable Tier 3 surface.** Once ingested, the MCP chatbot can answer "what verdicts cite Romans 6:3?" or "find verdicts where my baseline disagrees with Catholic counter-witness" via Cypher. Idempotent MERGE; supports `viewpoint='inferred-from-sources'` initially, `'individual:<id>'` for respondents, `'consolidated'` later. | Loader written; runs after orchestrator |
| **3. Trusted-elder questionnaire round** | Distribute the 221-question form to trusted churches/elders; collect `responses/*.json`. Each respondent's answers ingest via `verdict_loader load-baseline --viewpoint individual:<id>` so their lens joins the graph alongside the inferred baseline. | Pending |
| **4. Consolidation** | Collate baseline + responses + research into `consolidated.json`; ingest as `viewpoint='consolidated'`. The same 221 question nodes now have multiple verdict edges (inferred + per-respondent + consolidated), each queryable. | Pending |
| **5. Tier 3 surface** | MCP server with tools that traverse the unified graph: `query_verdict(question_id, viewpoint?)`, `evaluate_church_statement(text)` (semantic match → verdict node), `find_verdicts_citing(verse_osis)`, `compare_traditions_on(question_id)`. + Flutter client. | Pending |

---

## Override protocol

When the user gives an instruction conflicting with anything established in this project, the new instruction is canonical. The old method is investigated, mapped, and removed everywhere; not preserved as a fallback. Every override is logged in `~/.claude/projects/.../memory/override_log.md`.

---

## Memory locations

Two memory tiers:

1. **Project-public docs** (this `docs/` directory). Architectural and operational rules.
2. **Claude private memory** (`~/.claude/projects/e--projects-working-dir-brethren-doctrine/memory/`). Ebenezer's profile, project goals with personal context, doctrinal context, override log.

When updating an architectural rule, update both the docs/ file and the corresponding memory file.

---

## Current status (2026-05-10)

- Tier 1 extraction: **complete** (15 documents, ~230 chunks).
- Tier 2 sermon + SOF ingestion: **complete** (Neo4j + Qdrant loaded; retrieval CLI live).
- Tier 2 concordance + Bible-text ingestion: **loaders written, not yet run**.
- Tier 2 MCP server: **not started**.
- Tier 3 (Flutter client): **not started**.
- Inferred-baseline architecture (phase 1): **complete in this rewrite**.
- Inferred-baseline orchestrator run (phase 2): **gated on phase 1.5 + KPI green-light**.
