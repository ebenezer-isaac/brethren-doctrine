# The Case for Brethren Doctrine

This project is a manuscript-anchored biblical doctrine engine for personal reflection and doctrinal evaluation, grounded in the conviction that Scripture is divine revelation and that doctrinal claims should be tested against the original-language manuscript tradition rather than against any one church's summary.

It indexes the Hebrew and Greek interlinear with full Strong's-tagged concordance, multiple English translations, cross-reference graph, semantic-domain data, and a curated set of historical confessional and patristic sources. It runs the lexical sources and the cultural sources in **two physically separate, air-gapped stores**. The engine produces a doctrinal verdict from Scripture alone, then attaches a diagnostic overlay showing how each tracked Christian tradition reads the same lexical pattern.

The aim is *calibrated discernment*, not church-scoring. A church that checks green on all markers can still fall flat in practical execution. There is a difference between believing the doctrine and practicing the doctrine.

---

## How I got here

I was born into a [Christian Brethren](https://en.wikipedia.org/wiki/Plymouth_Brethren) family, but my personality has always been to be a skeptic. For a long time I wasn't sure if God even existed. I used to pray something like: *I'm willing to forgo the blessing of believing without seeing because reaching heaven with one less blessing seems better than going altogether to hell for unbelief.* It was Pascal's Wager dressed up as humility, but I meant it. The is in reference to the line in [John 20:29](https://www.biblegateway.com/passage/?search=John+20%3A29) "Blessed are those who have not seen and yet have believed".

The conviction came during my early 20s during daily meditations. I used to sit under a tree and think about how the world was actually working. And I realized something obvious that I hadn't actually faced: if even one year all the trees never came back to life, the whole universe collapses. No oxygen, no food chain, no anything. Every life on the planet dies. For a system that delicate to operate flawlessly for thousands of years, *someone* has to be pulling the strings from the background. That's not naive. That's the [teleological argument](https://en.wikipedia.org/wiki/Teleological_argument) restated in the only terms I had at the time. From there I was convinced there was a God.

Then the next question landed. *If* God exists, *who* is God? Why are there so many gods? Was I leaning toward Jesus only because I'd been raised Christian? Would I have leaned toward Krishna or Allah if I'd been born somewhere else? The honest version of the question demanded I do real comparative work. So I started talking to friends, religious leaders from other traditions, reading their texts.

What I found was that only Christianity had bulletproof theology, philosophy, science, and history. It withstood every question I threw at it, to the point that it started to feel too perfect to be true. Almost like a conspiracy that was infallible, defensible from every angle. But the more I looked at the world itself, the more I saw the same signature: the same character, the same internal logic. The God of the Bible and the operations of the world ran on the same source code. Which brought me back, hard, to [John 1:1](https://www.biblegateway.com/passage/?search=John+1%3A1): *In the beginning was the Word.* Watching [Lee Strobel's *Case for Christ*](https://en.wikipedia.org/wiki/The_Case_for_Christ) put the last nail in my old self and forced me to publicly declare that there is no God other than Jesus.

That should have been the end of it. But I'm now in the next phase, and it's harder than the first two.

Back home in India, the answer to *which church?* was obvious: Brethren. It was what I was born into, what I knew, and the doctrine matched what I was taught. But the same skeptic question that pushed me through stages 1 and 2 keeps coming back: am I leaning toward Brethren only because I was raised in a Brethren family? Is my conviction inheritance, or is it verified? That question got significantly louder when I landed in London. There are very few distinct Brethren denominational churches here and the others have substantially changed over time. So I'm forced to go in search of the truth again.

I came to Christianity *because of* its infallible truth and singular logic, grounded in Scripture. So why are there so many denominations within Christianity itself? If truth is singular, shouldn't there be a singular church?

The answer I've landed on, at least as a working frame: our access to truth was muddled when [Adam ate of the forbidden fruit](https://www.biblegateway.com/passage/?search=Genesis+3). Our ability to distinguish right from wrong has been compromised ever since. And it's further muddied by the devil, who [disguises himself as an angel of light](https://www.biblegateway.com/passage/?search=2+Corinthians+11%3A14) to spread misinformation. Whatever effort we put into defining truth is still just a best effort, because we lost the ability to share directly in God's truth. What we have left is one gift: the Bible, the ultimate source of truth God gave us. Interpretation is human best-effort aided by the Holy Spirit. The practice of doctrines is debatable. There's no escaping that, and pretending otherwise produces either fundamentalism or cynicism.

**This endeavour aims to identify, for myself, the truths I'm willing to lay my life down for, and the truths I'm willing to live and let live.**

That sentence is not rhetorical. It maps directly onto the boolean pattern of every respondent answer. `would_die_for=true` is "die for"; `would_be_member=true` is "live and let live"; everything in between is graduated. The standings (gospel-essential, convictional, preference, adiaphora) emerge from the booleans rather than being pre-assigned to the question. The whole point of the engine is to calibrate that line *against primary sources* rather than inherit it from any single teacher, including the Brethren tradition I was formed in.

---

## The three-stage progression

This project sits at the third step of a deliberate sequence:

1. *Does God exist?* Settled, under that tree.
2. *Is Jesus God?* Settled, after the comparative-religions work and Strobel.
3. *If Jesus is truth, why are there so many denominations, and which one is right?* **Open.** brethren-doctrine is the diagnostic tool I'm building to investigate this.

Each stage closes one trust gap so the next can be examined cleanly. I'm not delegating these conclusions to a single church or teacher. I'm verifying primary sources myself.

---

## What the engine actually does

The engine runs in three pipelines and uses two physically separate, air-gapped stores. This is the load-bearing architectural commitment: the lexical pipeline cannot see the cultural pipeline, and vice versa, at the data-model level. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture.

**Pipeline 1: Ingestion.** Open biblical datasets flow into the lexical store. Confessional, patristic, magisterial, and denominational sources flow into the cultural store. Both stores are Neo4j + Qdrant, but they run in separate Docker stacks on separate Docker networks. Containers on one network cannot reach the other.

**Pipeline 2: Lexical pre-inference.** For each of 231 doctrinal propositions in `questions.json`, an Opus subagent reads ONLY the lexical store (apparatus where available, MACULA Hebrew + Greek, STEPBible, ETCBC, OSHB, MorphGNT, TSK + OpenBible cross-references, Theographic metadata, INTF NTVMR transcriptions where ECM is published). It cannot see confessions, magisterial documents, or denominational commentary. It produces a per-question audit trail at `evidence/<id>.json` under a lean v3.0 schema. The verdict is settled by Scripture's lexical pattern alone. A deterministic post-processor then computes `lexical_score` from the structured fields; the LLM cannot override it.

**Pipeline 3: Query-time RAG via MCP.** An MCP server exposes 11 tools (`lexical_lookup`, `cross_ref`, `cultural_overlay`, `doctrinal_verdict`, etc.). At query time, the engine retrieves lexical evidence from Pipeline 2 and a cultural overlay from the cultural store, then synthesizes a response with the two clearly segregated. The lexical verdict is authoritative; the cultural overlay is diagnostic (it records how each tradition reads the same lexical pattern, never adjudicating).

**Per-respondent overlays** are a separate concept. Trusted churches and elders (and I myself) can fill out the same 231-question form. These responses live in `responses/<respondent_id>.json` and capture each respondent's commitment threshold via the boolean pattern (would_die_for, would_be_member, etc.). They are private and do not enter the lexical store.

---

## Authority

Every record in the lexical store carries an `authority_level` from 0 to 4. **The critical apparatus is the source of truth; everything else is downstream.** Confessions sit OUTSIDE the hierarchy on a sibling diagnostic track.

| Level | Layer | Source |
|---|---|---|
| **0** | **Critical Apparatus** ← **source of truth** | BHS footnotes (where extractable), Nestle-Aland (NA28/UBS5) apparatus via INTF NTVMR transcriptions, ECM apparatus where published |
| 1 | Interlinear + Concordance | MACULA Hebrew + Greek, STEPBible TAHOT/TAGNT/TVTMS, OSHB, MorphGNT, TSK + OpenBible cross-references, Theographic metadata |
| 2 | Formal Equivalence | NKJV, ESV, NASB. Word-for-word priority. Layer 5 parallel rendering, never Pipeline 2 exegetical authority. |
| 3 | Dynamic Equivalence | NIV, NLT. Thought-for-thought. Useful for narrative grasp; **forbidden as exegetical authority** in Pipeline 2. |
| 4 | Exegetical Application | Personal teaching notes (in `parsed/`), archaeology, church history. Commentary, not authority. |

A Level 4 sermon claim cannot override a Level 1 interlinear reading; a Level 1 interlinear reading cannot override a Level 0 apparatus footnote. **Confessions do not appear on this scale.** They are recorded in the cultural store with `(tradition, doctrine, stance, confidence)` tags. When tiers disagree within the lexical pipeline, the engine surfaces the conflict; it does not silently pick a side. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full hierarchy.

---

## The doctrinal baseline

I am not building the baseline alone. The collaborators are churches and elders I personally know and trust. The output is then the tool I use to evaluate potential churches I am considering visiting or joining.

```
questions.json (universal question bank, 231 entries)
        │
        │  Pipeline 2: orchestrator dispatches Opus subagents
        │  (one per question, reading only the lexical store)
        ▼
evidence/<id>.json (Pipeline 2 output, lexical-only audit trail)
        │
        │  distributed to trusted elders for testimony
        ▼
responses/<respondent_id>.json (filled questionnaires from trusted elders + me)
        │
        │  collation
        ▼
consolidated.json (final canonical baseline)
```

| File | What it is | Status |
|---|---|---|
| [questions.json](questions.json) | Universal question bank, 231 entries, 9 fields each | **Locked schema.** |
| `evidence/<id>.json` | Per-question lexical audit trail (v3.0 schema). Citations, anchor lemmas, cross-references, hermeneutics, license_audit. | Schema locked; Pipeline 2 regeneration pending implementation. The archived v2 evidence files from the prior session live under `evidence/archive-v2-2026-05-12/`. |
| `responses/<respondent_id>.json` | Filled questionnaires with respondent's commitment booleans. **Private** (gitignored). | Pending input |
| `consolidated.json` | Final canonical baseline collating Pipeline 2 verdicts with respondent testimonies | Future |

Schemas are locked in [docs/EVIDENCE_SCHEMA.md](docs/EVIDENCE_SCHEMA.md) (per-question lexical audit trail) and [docs/CULTURAL_SCHEMA.md](docs/CULTURAL_SCHEMA.md) (per-chunk doctrine tagging for the cultural store).

---

## How each question gets tested

Pipeline 2 runs each doctrinal proposition through deterministic lexical analytics, in order, before any verdict is recorded. Cultural sources are NOT in this pipeline.

| Pillar | Source | Purpose |
|---|---|---|
| **1. Concordance** (mechanical) | STEPBible TAHOT + TAGNT (Strong's-tagged Hebrew / Greek tokens), MACULA Hebrew + Greek, OSHB cross-validation, OpenBible + TSK cross-references via Neo4j Cypher | Makes `analogia scripturae` (Scripture interprets Scripture) deterministic. Every Strong's lemma in the anchor verses is spider-mapped to every occurrence in the canon. Selection bias dies at the data layer. |
| **2. Hermeneutics** (visible) | Recorded per verdict in `evidence.hermeneutics` | Primary method (grammatico-historical / redemptive-historical / quadriga / patristic-typological / accommodation), frameworks in play, figures of speech per scripture citation, genre rules, competing-lens verdicts. Forces the subagent to surface *how* the verdict was reached. |
| **3. Variant analysis** (manuscript) | INTF NTVMR transcriptions where ECM is published; NA28 apparatus shadow elsewhere | Surfaces variant-sensitive verdicts. Critical Apparatus drives Layer 0. **Deferred from v1 per scope decision** pending a 3 John pilot. |

A clear interlinear reading contradicted by every cultural-overlay tradition is still a clear interlinear reading. Cultural overlay records what each tradition says; it does not adjudicate.

**Forbidden in Pipeline 2 derivation**: Reformed-aligned commentary sites (carm.org, equip.org, gotquestions.org, monergism, ligonier, gospelcoalition, brethrenarchive.org). Only primary lexical repositories are permitted: MACULA, STEPBible, ETCBC, OSHB, MorphGNT, BibleHub interlinear (cross-validation only), INTF NTVMR.

**Caveat for fellow Brethren readers**: Plymouth Brethren historically reject formal confessions ("[no creed but Christ](https://en.wikipedia.org/wiki/Sola_scriptura)", sola scriptura strictly applied, though that phrase is itself a Reformed distinctive, which is part of what this engine is designed to surface). Including WCF, 1689 LBC, the Catechism, Book of Concord, and the rest in the **cultural store** is informational diagnostic only, not subscription. They are how each tradition reads the lexical text, useful to record, never authoritative for the verdict.

---

## Orchestrator pattern

All agentic work runs in-house via Claude Code subagents under the user's Max plan. **No programmatic Anthropic API access.** The single orchestrator agent reads `docs/ARCHITECTURE.md` and the phase prompts in `docs/phase_prompts/` on startup, then dispatches subagents per operational phase: lexical ingest, cultural scrape, cultural auto-tag, Pipeline 2 verdict derivation, Pipeline 3 query synthesis, validation. Every dispatch carries a `task_id`, explicit `allowed_stores` and `forbidden_stores` lists, and an output path under `tmp/<phase>/<task_id>/`. See [docs/phase_prompts/orchestrator.md](docs/phase_prompts/orchestrator.md).

---

## Anonymization

The only personal name permitted anywhere in this repository is my own. Every other personal contributor (teachers whose teaching is in the corpus, friends, organization members) is redacted from `parsed/`, code, docs, server responses, and downstream artifacts. External published authors (John Piper, [Justin Martyr](https://en.wikipedia.org/wiki/Justin_Martyr), Augustine, Calvin) are retained as citations because they preserve the chain back to public sources.

The `source-docs/` and `converted/` directories are gitignored. They contain raw private teaching notes; only sanitized derivatives go public. The `parsed/` Brethren corpus is ingested into the cultural store under `tradition=plymouth-brethren` with `redistribute: false`.

---

## What is built and what is not

- **Architecture: locked** (2026-05-12 PoC validation round). See [docs/POC_FINDINGS.md](docs/POC_FINDINGS.md). 15 hypotheses validated structurally; 90% live (3 Opus-driven steps run in stub mode pending Max-plan validation).
- **Tier 1 static corpus**: built. Per-document JSON in [parsed/](parsed/). Ingested into the cultural store under `tradition=plymouth-brethren`.
- **Two-Docker air-gap (lexical and cultural stacks)**: PoC validated; production compose files pending implementation.
- **Pipeline 1 lexical adapters**: PoC validated for 9 datasets; production adapters pending implementation.
- **Pipeline 1 cultural scrapers**: PoC validated for 4 sources; remaining sources pending implementation.
- **Pipeline 2 (Opus pre-inference)**: prompt + schema + score_calc PoC validated; production orchestrator pending. Earlier archived v2 evidence files moved to `evidence/archive-v2-2026-05-12/`; re-derivation under v3.0 schema pending.
- **Pipeline 3 (MCP server with 11 tools)**: tool surface specified in [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md); server implementation pending.
- **CBGM / variant data**: **deferred from v1** per scope decision. 3 John pilot validated on open-cbgm; full Catholic Letters TEI requires INTF outreach later.
- **Flutter client**: planned for v2.

---

## Layout

```
brethren-doctrine/
├── parsed/                      Sanitized Brethren teaching corpus (cultural-store input)
├── docs/
│   ├── ARCHITECTURE.md          Canonical architecture reference
│   ├── INGESTION_PATTERNS.md    Per-dataset ingestion recipes
│   ├── LICENSE_TAGGING.md       License posture + guard contract
│   ├── MCP_TOOLS.md             11 MCP tool specifications
│   ├── EVIDENCE_SCHEMA.md       v3.0 evidence schema + Pipeline 2 prompt contract
│   ├── CULTURAL_SCHEMA.md       Per-chunk doctrine-tagging schema
│   ├── POC_FINDINGS.md          Aggregated PoC findings (2026-05-12)
│   ├── phase_prompts/           Orchestrator + 6 phase prompts
│   └── archive-2026-05-12/      Pre-greenfield-rewrite docs
├── docker/
│   ├── lexical/                 Lexical Neo4j + Qdrant stack (pending)
│   └── cultural/                Cultural Neo4j + Qdrant stack (pending)
├── graph/
│   ├── lexical.cypher           Lexical Neo4j schema (pending)
│   └── cultural.cypher          Cultural Neo4j schema (pending)
├── ingest/
│   ├── lexical/                 Pipeline 1 lexical adapters (pending)
│   ├── cultural/                Pipeline 1 cultural adapters (pending)
│   ├── canonical_strongs.py     Strong's normalization utility (pending)
│   ├── versification_mapper.py  TVTMS-driven versification service (pending)
│   ├── models.py                Pydantic chunk and node models (pending)
│   └── license_guard.py         Redistribution enforcement (pending)
├── embeddings/                  Voyage embed + load to lex_col / cult_col (pending)
├── retrieval/                   Hybrid retrieve + BGE rerank + envelope (pending)
├── bd_mcp/                      FastMCP server with 11 tools (pending; named bd_mcp to avoid PyPI mcp SDK collision)
├── pipeline2/                   Lean prompt + Pydantic schema + score_calc (pending)
├── tools/                       verify_baseline, verify_questions, evidence_to_pdf
├── tests/                       Real test suite (pending rewrite)
├── questions.json               231-question bank (locked)
├── evidence/                    Pipeline 2 output (regeneration under v3.0 pending)
├── responses/                   Gitignored per-respondent answers
├── source-docs/, converted/     Gitignored raw inputs
├── tmp/                         Gitignored scratch (PoC outputs lived here)
├── README.md, USAGE.md          User-facing
├── pyproject.toml, uv.lock      Python project (uv, Python 3.12+)
└── .env, .env.example           VOYAGE_API_KEY, NEO4J_*, QDRANT_URL (no ANTHROPIC_API_KEY)
```

---

## Running it locally

The implementation is pending; this section describes the target. The architecture and PoC verification are complete; production code begins after the memory update pass and live validation.

```bash
# Set up environment
cp .env.example .env
# Fill in: VOYAGE_API_KEY, NEO4J_LEXICAL_PASSWORD, NEO4J_CULTURAL_PASSWORD
# Do NOT add ANTHROPIC_API_KEY; the engine uses Claude Code subagents under Max plan

# Install Python deps
uv sync

# Bring up two Docker stacks
docker compose -p lexical -f docker/lexical/docker-compose.yml up -d
docker compose -p cultural -f docker/cultural/docker-compose.yml up -d

# Apply Neo4j schemas
cypher-shell -a bolt://localhost:7475 -f graph/lexical.cypher
cypher-shell -a bolt://localhost:7476 -f graph/cultural.cypher

# Bootstrap two Qdrant collections
uv run python -m embeddings.bootstrap --store lexical
uv run python -m embeddings.bootstrap --store cultural

# Pipeline 1: lexical ingest (orchestrator dispatches subagents)
# (run as a Claude Code session at repo root, invoking the orchestrator phase prompt)

# Pipeline 1: cultural scrape + auto-tag (same orchestrator)

# Pipeline 2: lexical verdict derivation across 231 questions (same orchestrator)

# Validate
uv run python -m tools.verify_questions
uv run python -m tools.verify_evidence --mode full

# Start the MCP server
uv run python -m bd_mcp.server
```

---

## Status

Personal-use, single-user. No auth, no multi-tenant, no public API. The collaborative-questionnaire workflow runs in two directions: the lexical baseline is derived from Scripture alone via Pipeline 2; trusted churches and elders fill responses with their commitment booleans; the consolidated baseline is then used to evaluate potential churches I am considering visiting or joining. Personal due-diligence tooling.

If you are another believer running the same diagnostic for yourself, the rubric (`questions.json`, the engine itself, the lexical evidence files where the license stack allows public release) is potentially useful. The personal questionnaire responses (`responses/*.json`) are private. The Brethren teaching corpus in `parsed/` is private. The structure is reusable; the answers and corpus are mine.

---

## License

No license declared on the engine code yet. The plan is MIT or Apache-2.0 once the v1 implementation is far enough along to warrant a public README that says so honestly. Until then, treat anything you reuse as inspiration rather than a library to depend on.

Derived corpora are NOT redistributed in bulk. The engine works against the user's locally-ingested data. See [docs/LICENSE_TAGGING.md](docs/LICENSE_TAGGING.md) for per-source license posture and the redistribution-enforcement contract.
