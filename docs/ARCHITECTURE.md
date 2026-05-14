# Architecture

Canonical reference for the brethren-doctrine engine. This document supersedes everything in `docs/archive-2026-05-12/`.

Last revised: 2026-05-12 (post-PoC validation round).

## Goal

A manuscript-anchored biblical doctrine engine that produces doctrinal verdicts from the original-language manuscript tradition alone, with cultural and denominational material strictly walled off on the other side of an air-gap. The engine surfaces every meaningful variant in the manuscript record with the scholarly debate around it, so the reader can make informed decisions about contested readings. It is built for one user, personal use, single developer, with the engine code intended for public release on GitHub. Derived corpora are not publicly redistributed because most upstream datasets are CC BY 4.0 with attribution requirements, CC BY-NC for some (ETCBC BHSA, MARBLE / SDBH / Louw-Nida word senses, TTESV), and a few are proprietary in their published apparatus (NA28, BHQ, BDAG, HALOT, DCH, full Gottingen LXX).

The end-user question the engine is built to answer takes a form like: *"Does Brethren teaching on the Lord's Supper match Scripture better than Reformed teaching, and what do the original-language texts say?"* The engine produces a lexical verdict from Scripture alone, then attaches a diagnostic cultural overlay showing how each tracked tradition reads the same lexical pattern.

## The three pipelines

The engine is organized as three pipelines that share two physical stores.

```
INGEST (Pipeline 1)               PRE-INFERENCE (Pipeline 2)         QUERY (Pipeline 3)
─────────────────                 ──────────────────────────         ──────────────────

Open datasets       Lexical store   Opus reads only the              User question
   MACULA           (Docker A:        lexical store.                  via MCP
   STEPBible         Neo4j           For each doctrinal                   │
   ETCBC BHSA        lex_db +        proposition in                       ▼
   OSHB              Qdrant          questions.json:                  Router classifies
   MorphGNT          lex_col)                                         intent
   TSK                  │              walks concordance,                  │
   OpenBible            │              cross-refs, semantic                ▼
   Theographic          │              domains, syntax,               Hybrid retrieve
   INTF NTVMR           │              apparatus where ECM.           dense + BM25
                        │                                             + graph expand
                        ▼              Output:                              │
                   AIR GAP             evidence/<id>.json                   ▼
                   (Docker             with lexical verdict,           BGE rerank
                    network            citations, hermeneutics              │
                    boundary)          block, license_audit.                ▼
                        ▲                                              Opus synthesis
                        │              Stored back to                  reads both stores
Cultural corpus     Cultural store     lexical store.                  at this stage
   CCEL patristics  (Docker B:                                              │
   Vatican.va       Neo4j cult_db    Triangle test: re-run                  ▼
   Book of Concord  + Qdrant         on identical inputs              Output envelope:
   Reformed         cult_col)         epsilon-stable.                 lexical verdict
   Anglican             │                                             + cultural overlay
   Methodist            │                                             (diagnostic, not
   Anabaptist           │           Opus tags each cultural            authoritative)
   Pentecostal          │           chunk with:                       + citations
   Orthodox             │            (doctrine, stance,               + variant
   Brethren                          confidence, anchor).             sensitivity flag
   Conciliar
                                     High-confidence ships;
                                     low-confidence flagged
                                     for review.
```

Pipeline 1 ingests open datasets into two stores. Pipeline 2 runs Opus over the lexical store to produce per-question lexical verdicts. Pipeline 3 serves runtime queries through an MCP server, synthesizing across both stores.

## Two air-gapped stores

The single most important architectural commitment in this project is that the lexical pipeline and the cultural pipeline live in physically separate stores with no possibility of cross-contamination.

**Mechanism.** Two Docker stacks. Lexical stack runs Neo4j 5-community and Qdrant on Docker network `lexical_net`. Cultural stack runs a second Neo4j 5-community and a second Qdrant on Docker network `cultural_net`. Containers on `lexical_net` cannot resolve names on `cultural_net`, and vice versa, because Docker user-defined bridge networks are isolated by default. Pipeline 2 (lexical pre-inference) connects only to the lexical stack. Pipeline 3 (runtime query synthesis) connects to both, but reads them as separate services with separate license stacks, never mixing data into a single fused index.

**Verified by H8 in the PoC round.** Cross-network DNS lookups return `NSS_NOTFOUND`; HTTP fails with network unreachable; positive controls within each network confirm DNS is healthy and the negative results are real isolation.

**Rationale.** Every prior attempt at biblical RAG that I have seen has lexical and confessional sources retrieved through the same index, ranked by the same scoring function, and synthesized by the same prompt context. That contaminates the verdict. Asking "what does Scripture say about real presence?" returns Trent before BDAG `deipnon`. The lexical pattern is downweighted because there is more confessional material to retrieve.

This engine refuses to mix them at the data-model level. Pipeline 2 cannot see confessional sources because they are not in the database it queries. The synthesis layer in Pipeline 3 can attach a cultural overlay only after the lexical verdict is locked.

**`internal: true` is not used.** It blocks image pull from the public internet, which would prevent first-time bring-up. The air-gap relies on Docker's default isolation between user-defined bridge networks, which is sufficient for inter-stack isolation.

## Layered architecture

Numbered from manuscript floor to client. Data flows downward in the diagram. Lower numbers feed higher numbers; never the reverse.

| Layer | Role | Tech / data sources |
|---|---|---|
| 0 | Manuscript floor | Hebrew: WLC, OSHB. Greek: SBLGNT, Nestle1904. Versions: LXX Rahlfs, Peshitta (ETCBC), Vulgate. Apparatus: NA28 footnotes via INTF NTVMR transcriptions where published. Deferred for v1: DSS, full ECM, Old Latin, Coptic. |
| 0.5 | Versification mapping | STEPBible TVTMS. Every cross-version operation routes through it. |
| 1 | Critical text and apparatus | open-cbgm (MIT) over INTF TEI XML where ECM is published. **Deferred in v1 per user decision; will resume once 3 John pilot proves value.** |
| 2 | Unified lexical foundation | MACULA Hebrew + Greek (Clear Bible, CC BY 4.0). Includes WLC + OSHB morphology + Westminster syntax + UBS MARBLE Louw-Nida and SDBH semantic domains + Berean glosses. STEPBible TAHOT / TAGNT / TTESV layered on top. Access via Text-Fabric (MIT) for BHSA, ETCBC peshitta, ETCBC syrnt; via lxml for OSHB; via direct .txt parse for MorphGNT. |
| 3 | Deterministic analytics | Concordance graph, cross-reference topology (TSK + OpenBible), syntactic structure (ETCBC for Hebrew, MACULA Greek trees), semantic domains (Louw-Nida, SDBH), pericope boundaries (OpenText annotations). Deferred for v1: chiasm detection, stylometry, conceptual metaphor mapping, speech-act classification beyond Speaker-Quotations dataset. |
| 4 | Lexical verdict engine | Pipeline 2. Opus reads layers 0-3 (no cultural data, ever), produces `evidence/<id>.json` per doctrinal proposition. LLM is constrained to writing structured evidence; a deterministic post-processor computes `lexical_score` from the structured fields. The LLM cannot override the score. |
| 5 | Translation view | STEPBible TTESV plus Clear Bible Alignments. Parallel rendering only. Never feeds Layer 4. |
| 6 | Cultural sibling corpus | CCEL patristic + Vatican.va magisterial + Book of Concord + Reformed confessions + 39 Articles + UMC + Schleitheim + AG + OCA + Plymouth Brethren archives + conciliar. Air-gapped store. |
| 6.5 | Light doctrinal tagging | Per-chunk `(tradition, doctrine_coarse, doctrine_fine, stance, confidence, anchor_id)`. No formal ontology. Opus auto-tags at ingest; high-confidence tags ship, low-confidence flagged for review. |
| 7 | Cultural overlay engine | Pipeline 3 synthesis stage. Reads Layer 4 verdict and Layer 6/6.5 tags. Attaches "how each lineage reads this lexical pattern" as diagnostic information. Never edits the Layer 4 verdict. |
| 8 | Variant debate surface | Per-verse: every variant in Layer 0, every CBGM-derived reading from Layer 1 where ECM exists, every translation choice from Layer 5, every Layer 4 verdict that is variant-sensitive. The "informed decision" reading surface. **Variant data deferred in v1 because Layer 1 is deferred.** |
| 9 | MCP server and client | Python MCP SDK (`pip install mcp`). 11 tools (specified in docs/MCP_TOOLS.md). Streamable HTTP transport with progress tokens for the long-running `doctrinal_verdict` tool. Flutter client deferred to v2; v1 is MCP-only, queryable from Claude Code or other MCP-native clients. |

## Authority hierarchy

The authority hierarchy is a discipline applied within the lexical pipeline. Cultural sources are not on it.

| Level | Layer | Source |
|---|---|---|
| 0 | Critical apparatus | BHS footnotes (where extractable), NA28 footnotes via INTF NTVMR transcriptions, ECM apparatus where published |
| 1 | Interlinear + concordance | MACULA Hebrew + Greek, STEPBible, OSHB, MorphGNT, TSK + OpenBible cross-references |
| 2 | Formal-equivalence translation | NKJV, ESV, NASB. Used in Layer 5 parallel rendering. Never as Layer 4 exegetical authority. |
| 3 | Dynamic-equivalence translation | NIV, NLT. Useful for narrative grasp only. Forbidden as Layer 4 exegetical authority. |
| 4 | Exegetical application | Personal teaching notes, archaeology, church history. Treated as commentary, not authority. |

**Confessions do not appear on the hierarchy.** They sit on the cultural sibling track at Layer 6. Counter-witness from any tradition is recorded as diagnostic information for the reader; it never settles a Layer 4 verdict.

When tiers disagree within the lexical pipeline, the engine surfaces the conflict rather than silently picking a side. A Level 4 sermon claim cannot override a Level 1 interlinear reading. A Level 1 interlinear reading cannot override a Level 0 apparatus footnote where one exists.

## Pipeline 2 walkthrough

For each doctrinal proposition in `questions.json`, the Pipeline 2 orchestrator does the following.

1. Pull the question entry (id, statement, scripture_anchors, confessional_anchors-as-references-only, historical_consensus metadata).
2. Build a lexical context bundle from the lexical store: anchor lemmas with occurrence counts, anchor verses with surface forms and key terms, cross-references via TSK + OpenBible, semantic-domain neighbors via Louw-Nida and SDBH, syntactic context where ETCBC has it, any variant units where Layer 1 is populated.
3. Hand the question + context bundle to Opus with the lean prompt (see `docs/EVIDENCE_SCHEMA.md` for the prompt contract). Opus is forbidden from citing confessions, magisterial documents, denominational commentary, or Reformed-aligned commentary sites (carm.org, equip.org, gotquestions.org, monergism.com, ligonier.org, thegospelcoalition.org, brethrenarchive.org). Allowed citations: apparatus, MACULA, STEPBible, ETCBC, BibleHub interlinear, INTF NTVMR.
4. Opus produces structured JSON conforming to evidence v3.0 schema. Fields cover: verdict (affirms / confidence / variant_robust / pan_canonical / rationale), lexical_evidence (anchor_lemmas, concordance_traversed, scripture with force / supports / genre / figures / macula_anchor, cross_refs_invoked, complicating_texts), variants block, hermeneutics block, stem_audit, lay_summary, citations with license per source, license_audit.
5. The deterministic post-processor reads the structured fields and computes `lexical_score` as a weighted aggregate of six factors: pan_canonical (0.25), anchor_lemma breadth (0.20), complicating_resolved rate (0.15), cross_ref density (0.15), variant_robust flag (0.15), concordance_breadth (0.10). Order-invariant by construction. The LLM never writes this number.
6. The triangle test: re-run on identical inputs must produce identical lexical_score (epsilon-stable to within 0.01). Permuted-order inputs must also produce identical score. Verified in H11.
7. Validate against the v3.0 Pydantic schema (`extra="forbid"` at every level). Write to `evidence/<question_id>.json`.

**Verdict authority.** `verdict.affirms` is one of `true`, `false`, `null`, `disputed`. `null` covers "lexical pattern is open" and "insufficient evidence." `disputed` covers "lexical pattern is genuinely contested across the canon," reserved for cases like paedobaptism where the lexical evidence supports multiple defensible readings.

**LLM cost path.** Pipeline 2 dispatches Claude Code subagents under the user's Max plan rather than calling the Anthropic API directly. This keeps per-question cost at zero relative to the existing Max subscription. A programmatic API client is wired as a fallback if Max-plan quota is exhausted.

## Pipeline 3 walkthrough

User question arrives at the MCP server. The router classifies intent (scripture / named_figure / comparative / general / doctrinal-verdict). For doctrinal queries:

1. Retrieve relevant `evidence/<id>.json` from the lexical store.
2. Retrieve cultural overlay chunks from the cultural store, filtered by the doctrine slugs in the relevant `questions.json` entry.
3. Pass both to Opus for synthesis with a strict instruction: the lexical evidence is authoritative; the cultural material is diagnostic. The output envelope segregates the two with separate citation blocks. The license stack is attached to the envelope so the calling agent never accidentally bulk-exports NC content.

Streaming: long-running tools (`doctrinal_verdict`) accept a `progressToken` and emit `notifications/progress` events keyed by it, with `{stage, pct}` granularity. Partial JSON is not streamed; the final structured response arrives in one piece.

## Orchestrator pattern

All agentic work in this architecture is dispatched in-house through a single orchestrator agent running as a Claude Code session under the user's Max plan. **There is no programmatic Anthropic API access.** No `anthropic` Python package is installed; no `ANTHROPIC_API_KEY` is needed in `.env`; no per-call billing occurs. Every LLM call is a Claude Code subagent dispatch, which consumes Max plan quota.

The orchestrator is the only entity that calls the Agent tool. Subagents do not dispatch further subagents (except for read-only Explore agents when warranted). The orchestrator reads `docs/ARCHITECTURE.md` and the phase prompts in `docs/phase_prompts/` on startup, then routes work according to the operational phase.

### Phase prompts

Each operational phase has an explicit, canonical prompt stored under `docs/phase_prompts/`. The orchestrator loads the relevant prompt verbatim and dispatches a subagent with it. Prompts are self-contained: the subagent does not need to read the conversation history.

| Phase | Prompt file | Dispatched by | Cardinality | Model |
|---|---|---|---|---|
| Orchestrator (master) | `docs/phase_prompts/orchestrator.md` | Bootstrapped by user | 1 per session | Opus 4.7 |
| Lexical ingest | `docs/phase_prompts/pipeline1_lexical_ingest.md` | Orchestrator | 1 per dataset (MACULA-H, MACULA-G, STEPBible, OSHB, MorphGNT, TSK, OpenBible, Theographic, BHSA) | Sonnet 4.6 |
| Cultural scrape | `docs/phase_prompts/pipeline1_cultural_scrape.md` | Orchestrator | 1 per cultural source (CCEL ANF/NPNF, Vatican.va, Book of Concord, WCF, 1689, Heidelberg, Belgic, Dort, 39 Articles, UMC, Schleitheim, AG, OCA, BrethrenArchive, conciliar) | Sonnet 4.6 |
| Cultural auto-tag | `docs/phase_prompts/cultural_autotag.md` | Orchestrator | 1 per batch of ~50 chunks | Sonnet 4.6 |
| Pipeline 2 verdict | `docs/phase_prompts/pipeline2_verdict.md` | Orchestrator | 1 per doctrinal proposition (231 total) | Opus 4.7 |
| Pipeline 3 synthesis | `docs/phase_prompts/pipeline3_synthesis.md` | MCP server (functions as a thin orchestrator delegate) | 1 per user query | Sonnet 4.6 default; Opus 4.7 for `doctrinal_verdict` |
| Validation | `docs/phase_prompts/validation.md` | Orchestrator | 1 per validation run | Sonnet 4.6 |

The orchestrator does not embed prompts in code. It reads the markdown files and passes the content as the subagent prompt parameter. Prompt updates are git operations on these files, not code changes.

### Dispatch contract

Every subagent receives, at minimum:
- the verbatim phase prompt
- a JSON `inputs` block scoped to its phase
- a target output path under `tmp/<phase>/<task_id>/` for any files it produces
- explicit `allowed_stores` and `forbidden_stores` lists (e.g. Pipeline 2 verdict has `allowed_stores: ["lexical"]`, `forbidden_stores: ["cultural"]`)

Every subagent returns, at minimum:
- a structured result JSON conforming to the phase's output schema
- a `license_audit` block enumerating every source touched
- a `confidence` self-assessment

The orchestrator aggregates results and writes them to the appropriate store via the Pipeline 1 adapter modules (no subagent writes to Neo4j or Qdrant directly).



- **Python**: 3.12 via uv. The `.venv` at repo root is the canonical venv.
- **Neo4j**: 5-community (Docker, two instances). Lexical at host port 7475/7688, cultural at 7476/7689 in PoC; production picks final ports.
- **Qdrant**: latest (Docker, two instances). Lexical at 7100/7102, cultural at 7101/7103.
- **Voyage**: `voyage-4-large` for v1. Pricing: $0.12 / M tokens after 200 M free tier; our v1 ingest is roughly 22 M tokens so cost is $0. Locked over voyage-context-3 and voyage-3-large.
- **Reranker**: BGE-reranker-v2-m3 (Apache-2.0, open weights, multilingual). Loaded locally; no API.
- **LLM**: Claude Opus 4.7 for Pipeline 2 lexical verdicts (highest reasoning quality). Sonnet 4.6 for cultural-corpus auto-tagging and Pipeline 3 query synthesis (good cost-quality balance). **Haiku is not used.** **All LLM dispatch is via in-house Claude Code subagents under the user's Max plan.** Programmatic Anthropic API access is forbidden in this architecture.
- **MCP**: official Python SDK (`pip install mcp`). FastMCP server pattern. Streamable HTTP transport per the 2025-06-18 spec revision.
- **Text-Fabric**: 13.x for BHSA / ETCBC peshitta / ETCBC syrnt access.
- **Anthropic SDK**: **not installed, not used.** No programmatic API path. All agentic work routes through Claude Code subagents.

## License posture

Every chunk and node carries an explicit `license` field. Synthesis enforces redistribution rules through the `license_guard.check_redistribute()` function (see `docs/LICENSE_TAGGING.md`).

| Tier | Posture | Sources |
|---|---|---|
| Permissive open | Allowed in bulk, attribution required | MACULA (Clear Bible CC BY 4.0), STEPBible TAHOT / TAGNT / TVTMS (CC BY 4.0), OSHB (CC BY 4.0), OpenBible (CC BY), public-domain confessions (WCF, 1689 LBC, Heidelberg, Belgic, Dort, 39 Articles, BCP 1662, Schleitheim, UMC Articles, Book of Concord older translations), CCEL ANF / NPNF (PD), conciliar texts via Wikisource (PD), pre-1923 Plymouth Brethren writings (PD) |
| Open share-alike | Allowed; derivatives must propagate SA | MorphGNT morphology (CC BY-SA 4.0), Theographic Bible Metadata (CC BY-SA 4.0), First1KGreek (CC BY-SA 4.0) |
| Open non-commercial | Personal use only; bulk export forbidden | ETCBC BHSA (CC BY-NC 4.0), MARBLE / SDBH / Louw-Nida word senses (CC BY-NC), STEPBible TTESV (CC BY-NC 4.0) |
| EULA-restricted | Snippet quotation OK; bulk forbidden; per-vendor reporting | SBLGNT text (SBLGNT EULA; ≤ 500 verses per year without separate license) |
| Proprietary / fair-use only | Snippet only, never bulk | Vatican.va content (Libreria Editrice Vaticana copyright; widespread fair-use practice); AG Fundamental Truths; OCA topical articles; modern Book of Concord translations (Tappert / Kolb-Wengert) |

**v1 posture: 100% open.** No proprietary purchases. No paid lexicons. No paid ECM apparatus. The £200 reference budget goes to print NA28 + UBS6 + ECM Catholic Letters Part 1 for human cross-check, not for ingestion.

**Public release of derivatives.** The engine code is intended for GitHub release under MIT or Apache-2.0 (pending decision). Derived corpora are NOT redistributed; the engine works against the user's locally-ingested data. Sample evidence outputs may be published as long as they cite only permissively-licensed source layers (license_audit field `evidence_safe_to_publish` must be `true`).

## Hosting model

Hybrid. Biblical data and both stores run locally in Docker. LLM (Opus, Sonnet, Haiku via Max plan) and embedding (Voyage via free tier) calls go to cloud APIs. BGE reranker model runs locally.

**Why hybrid.** Local data means the engine works on a plane for lookups and is independent of upstream service uptime. Cloud LLM means we do not run a model locally (out of personal scope). Voyage free tier means we pay zero for embedding at v1 scale (~22M tokens estimated vs 200M token free allowance).

**Refresh.** Datasets are pinned at commit SHAs in a `pipeline1/lockfile.json`. Refresh is manual: bump the SHA, re-ingest, re-embed. No automatic git pulls.

## PoC validation summary

The architecture has been validated by 15 hypotheses across 6 parallel PoC agents on 2026-05-12. Detailed findings live in `docs/POC_FINDINGS.md`. Headline confidence:

- 100% structural: every architectural commitment validates (air-gap, MCP, all 7 lexical ingestion paths, license guard, retrieval pipeline, open-cbgm on 3 John).
- 90% live: three Opus-driven steps (H10 lean prompt, H11 triangle test, H13 auto-tagging) ran in stub mode because `ANTHROPIC_API_KEY` was not in `.env`. Live wiring is complete; the live validation pass uses Max-plan Claude Code subagents at zero marginal cost.

## Architecture deltas baked in (from PoC findings)

The following are non-negotiable for implementation:

1. **Canonical Strong's normalization at Pipeline 1 entry.** Five sources, five encodings (MACULA-H zero-pads `0430`, OSHB slash-prefixed `b/7225`, STEPBible curly-brace `{H0430G}`, MACULA-G plain `2316`, TAGNT prefixed `G`). A `canonical_strongs()` utility runs at ingest; cross-validation against all five reps is a unit test.
2. **Hebrew dual-granularity model.** OSHB collapses prefix + stem (Gen 1:1 = 7 words). MACULA and BHSA split (11 morphemes). Both layers ingested: `(:Word)-[:HAS_MORPHEME]->(:Morpheme)` with bidirectional edges.
3. **TVTMS is a 3-stage mapping service.** Block-scoped rules, rule types (OneToOne, SubdividedVerse, etc.), tradition columns. Build a `VersificationMapper` service, not a lookup table.
4. **MACULA Hebrew Hebrew↔Greek cross-reference bridge.** Each `<w>` carries `greek` and `greekstrong` attributes. Ingest as edges between Hebrew Word nodes and Greek Lemma nodes. Free LXX bridge.
5. **pysblgnt is dead on PyPI.** Direct `.txt` parse of `morphgnt/sblgnt` (space-delimited, 7 columns).
6. **text-fabric path quirk.** `use()` resolves `~/github/...`, not `~/text-fabric-data/github/...`. Bootstrap script must symlink or pass `locations=`.
7. **OpenBible "To Verse" ranges explode at ingest.** `Rom.1.19-Rom.1.20` becomes two edges. Range queries handled at retrieval time, not stored as a range property.
8. **Voyage model: `voyage-3-large` (not `voyage-context-3`).** Current `voyageai==0.3.7` client does not accept the contextual model. Revisit after a documented client upgrade.
9. **TTESV is CC BY-NC**, unlike the rest of STEPBible. Tag explicitly at ingest.
10. **Sparse-checkout strategy.** MACULA Hebrew full clone is 1.5 GB; Greek is 655 MB. TSV-only sparse checkout drops the total under 500 MB.
11. **Cultural scrape link-rot mitigation.** Wikisource slug drift (Schleitheim was 404 on PoC run) and TLS-fragile mirrors (justus.anglican.org SSLv3 handshake failure). Catalog records canonical URL plus fallback URLs per source. Re-probe on failure.
12. **OpenBible cross-references drift monthly.** Pin to a release date in `pipeline1/lockfile.json`.
13. **Docker air-gap relies on Docker default bridge isolation**, not `internal: true` (which blocks image pull). Document in compose comments.
14. **Cultural tag count cap.** Pydantic validator rejects more than 5 doctrine_tags per chunk.
15. **Disk hygiene policy.** PoCs prune downloads at completion. Production CI sparse-checks from the start.

## Phase plan

| Stage | Scope | Target |
|---|---|---|
| Stage 0 | Two-Docker stacks up, lexical-store smoke test on MACULA Hebrew Gen 1:1 end-to-end | This week |
| Stage 1 | Full Pipeline 1 over all 7 lexical sources at pinned SHAs. Pipeline 1 over 7 cultural sources (Schleitheim, Augsburg, Heidelberg, WCF, 1689 LBC, 39 Articles, conciliar canons). MCP server with `lexical_lookup`, `cross_ref`, `versification_resolve` | Within a month |
| Stage 2 | Cultural corpus completion (CCEL, Vatican.va, remaining traditions). MCP tools `cultural_overlay`, `debate_for_verse`. Pipeline 2 on first 20-50 doctrinal propositions via Max-plan subagents | Within two months |
| Stage 3 | `doctrinal_verdict` MCP tool with streaming progress. Print reference purchase (NA28 + UBS6 + ECM Catholic Letters Part 1, ~£190-230) | Within three months |
| Future | Flutter client (v2). Variant data via INTF outreach for full Catholic Letters TEI. DSS / Peshitta / Vulgate ingestion. Deterministic layer extension (chiasm, stylometry, etc.) | v2+ |

## Anti-patterns avoided

Documented failure modes from prior biblical RAG attempts that this architecture explicitly resists:

| Anti-pattern | Where seen | Mitigation here |
|---|---|---|
| Lexical / confessional contamination | Magisterium AI by design; Logos AI by integration depth | Two-Docker air-gap at the data-model level |
| LLM-generated verdict | Most devotional Bible chatbots | Pipeline 2 score is deterministic post-processor; LLM cannot override |
| Hallucinated cross-references | Documented across consumer Bible LLMs | Citation validator: every LLM citation must verify against TSK / OpenBible / MACULA graph membership |
| Translation conflation | Naive RAG over English-only translations | Authority hierarchy; dynamic translations forbidden as Layer 4 exegetical authority |
| Strong's-only Greek/Hebrew claims | Every Strong's-driven concordance app | Disambiguated Strong's mandatory; Louw-Nida and SDBH semantic context required before any verdict |
| Confessional eisegesis disguised as exegesis | Most denominational study apps | Confessions on sibling diagnostic track only; UI segregates visually |
| Apparatus blindness | All consumer Bible apps | INTF NTVMR transcriptions ingested where ECM exists; variant_inspect tool surfaces variants per verse |
| Versification chaos | Many translation apps | STEPBible TVTMS as canonical versification service; every cross-version operation routes through it |
| Naive RAG chunking on biblical text | Common 2024 demos | Pericope-aware chunking using OpenText.org context annotations + MACULA syntactic trees; not token-window |
| Quotation / speaker attribution errors | Most apps | Clear Bible Speaker-Quotations dataset treated as gold |
| Stylometry on English translations | Popular-press articles | Stylometric features (when added in v2) operate on lemma sequences from MorphGNT / MACULA |
| TR / Byzantine / Majority Text / NA28 conflation | Popular Bible apps | STEPBible TAGNT per-word edition flags respected per chunk |

## Repo layout (target)

```
brethren-doctrine/
├── docs/                                Canonical documentation
│   ├── ARCHITECTURE.md                  (this file)
│   ├── INGESTION_PATTERNS.md            Per-dataset ingestion notes
│   ├── LICENSE_TAGGING.md               License posture + guard contract
│   ├── MCP_TOOLS.md                     11 MCP tool specifications
│   ├── EVIDENCE_SCHEMA.md               v3.0 evidence schema + Pipeline 2 prompt contract
│   ├── CULTURAL_SCHEMA.md               Per-chunk doctrine-tagging schema
│   ├── POC_FINDINGS.md                  Aggregated PoC findings 2026-05-12
│   └── archive-2026-05-12/              Pre-greenfield-rewrite docs
├── docker/
│   ├── lexical/docker-compose.yml       Lexical Neo4j + Qdrant stack
│   └── cultural/docker-compose.yml      Cultural Neo4j + Qdrant stack
├── graph/
│   ├── lexical.cypher                   Lexical Neo4j schema
│   └── cultural.cypher                  Cultural Neo4j schema
├── ingest/
│   ├── lexical/                         Pipeline 1 lexical adapters
│   │   ├── macula_hebrew.py
│   │   ├── macula_greek.py
│   │   ├── stepbible.py
│   │   ├── oshb.py
│   │   ├── morphgnt.py
│   │   ├── tsk.py
│   │   ├── openbible.py
│   │   ├── theographic.py
│   │   └── bhsa.py
│   ├── cultural/                        Pipeline 1 cultural adapters
│   │   ├── ccel.py
│   │   ├── vatican.py
│   │   ├── bookofconcord.py
│   │   ├── reformed_confessions.py
│   │   ├── 39_articles.py
│   │   ├── conciliar.py
│   │   └── brethren_archive.py
│   ├── canonical_strongs.py             Strong's normalization utility
│   ├── versification_mapper.py          TVTMS-driven service
│   ├── models.py                        Pydantic chunk and node models
│   └── license_guard.py                 Redistribution enforcement
├── embeddings/
│   ├── bootstrap.py                     Creates lex_col + cult_col Qdrant collections
│   └── embed_and_load.py                Voyage embed + load with --store flag
├── retrieval/
│   ├── router.py                        Intent classifier with store routing
│   ├── hybrid.py                        Dense + BM25 + graph expand
│   ├── rerank.py                        BGE reranker
│   └── envelope.py                      Per-store response envelopes
├── mcp/
│   ├── server.py                        FastMCP server with 11 tools
│   ├── tools/                           One file per tool
│   └── streaming.py                     progressToken handling
├── pipeline2/
│   ├── orchestrator.py                  Per-question Opus subagent dispatcher
│   ├── lean_prompt.md                   Lean prompt template
│   ├── evidence_schema.py               Pydantic v3.0 model
│   └── score_calc.py                    Deterministic post-processor
├── tools/
│   ├── verify_baseline.py               KPI verifier (rewrite for lean schema)
│   ├── verify_questions.py              Question hygiene
│   └── evidence_to_pdf.py               PDF renderer
├── tests/                               Real test suite
├── questions.json                       231-question bank (locked)
├── evidence/                            Pipeline 2 output (regenerated under v3.0)
├── responses/                           Gitignored per-respondent answers
├── parsed/                              Brethren Tier 1 corpus (cultural-store input)
├── source-docs/, converted/             Gitignored raw inputs
├── README.md, USAGE.md                  User-facing
├── pyproject.toml, uv.lock              Python project
└── .env, .env.example                   VOYAGE_API_KEY, ANTHROPIC_API_KEY (when needed), NEO4J_*, QDRANT_URL
```

## Glossary

- **Air-gap**: physical separation between lexical and cultural data stores. Pipeline 2 cannot reach the cultural store; Pipeline 3 reads both as separate services with separate license stacks.
- **Apparatus**: footnotes in a critical edition listing manuscript variants and editorial decisions.
- **CBGM**: Coherence-Based Genealogical Method. INTF's algorithm for reconstructing manuscript relationships from variant readings.
- **Cultural overlay**: diagnostic information attached after a lexical verdict is locked. Shows how each tracked tradition reads the same lexical pattern. Never authoritative.
- **Doctrinal proposition**: a single testable belief statement from `questions.json` (e.g. "Scripture is the sole and final authority for the rule of faith").
- **ECM**: Editio Critica Maior. INTF's full critical edition of the NT. Published so far: Catholic Letters, Acts, Mark, Revelation. Matthew expected 2026.
- **Lexical store**: the air-gapped Neo4j + Qdrant pair that holds biblical text, morphology, syntax, cross-references, semantic domains, apparatus (where Layer 1 is populated).
- **Lexical verdict**: the engine's Layer 4 output for a doctrinal proposition. Derived from Scripture alone. Includes `affirms`, `lexical_score`, `confidence`, citations, hermeneutics, license_audit.
- **Pipeline 1**: ingestion of open datasets into the two stores.
- **Pipeline 2**: per-question Opus pre-inference producing `evidence/<id>.json`.
- **Pipeline 3**: runtime RAG via MCP server.
- **Triangle test**: re-running Pipeline 2 on identical inputs must produce identical `lexical_score`. Order-permutation of inputs must produce identical score. Verified by H11.
- **TVTMS**: STEPBible's Translators Versification Mapping Specification. Reconciles Hebrew, English, Greek-Brenton, Latin, KJV verse numbering schemes.
