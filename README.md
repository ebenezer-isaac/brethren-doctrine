# The Case for Brethren Doctrine

A theological GraphRAG engine for personal reflection and doctrinal evaluation.

It indexes the Hebrew/Greek interlinear with full Strong's-tagged concordance, multiple English translations, archaeological data, church history, and a curated set of doctrinal teaching notes into a single queryable system. Then it lets me triangulate any church's stated doctrine against primary sources (the original languages, the manuscript tradition, ecumenical history) instead of trusting secondary chains.

The aim is *calibrated discernment*, not church-scoring. A church which checks green on all markers can still fall flat in practical execution. There's a difference between beliveing the doctrine and practicing the doctrine. 

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

That sentence is not rhetorical. It maps directly onto the `tier` field of every question in the doctrinal taxonomy: tier=`essential` is "die for"; tier=`preference` is "live and let live"; everything in between is graduated. The whole point of the engine is to calibrate that line *against primary sources* rather than inherit it from any single teacher — including the Brethren tradition I was formed in.

---

## The three-stage progression

This project sits at the third step of a deliberate sequence:

1. *Does God exist?* Settled, under that tree.
2. *Is Jesus God?* Settled, after the comparative-religions work and Strobel.
3. *If Jesus is truth, why are there so many denominations, and which one is right?* **Open.** brethren-doctrine is the diagnostic tool I'm building to investigate this.

Each stage closes one trust gap so the next can be examined cleanly. I'm not delegating these conclusions to a single church or teacher. I'm verifying primary sources myself.

---

## What the engine actually does

The engine runs in two pipelines, sharing a Neo4j + Qdrant graph backbone:

**Pipeline A — Inferred-baseline derivation (tradition-neutral lexical-philological floor).** For each of 221 doctrinal propositions, the engine derives an answer that any of the eight major Christian lineages (Eastern Orthodox, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal) could audit. The verdict is settled by **apparatus + interlinear + concordance**. Counter-witness traditions are consulted as research aids to verify the lexical reading isn't idiosyncratic — they corroborate, they don't vote. **My Brethren-adjacent teaching notes are NOT in this pipeline.** Confessions (1689 LBC, WCF, Westminster Standards, Brethren Archive — all of them) are NOT in this pipeline. The whole point is that the formation I came from has to be tested against the lexical floor, not granted authority over it. See [tools/derive_baseline_prompt.md](tools/derive_baseline_prompt.md).

**Pipeline B — Per-respondent overlays.** A small set of churches and elders I personally know and trust fill out the same 221-question form, with their own confessional lens. So do I, when I fill out my own. This is where the 1689 LBC, the WCF, my Brethren teaching notes, and the sermon corpus in `parsed/` actually live — they are inputs to specific respondents' viewpoints, not to the canonical baseline. After all responses come in, `consolidated.json` is the final post-research baseline used downstream.

**Downstream.** Given a potential church I'm considering visiting or joining, the engine triangulates that church's statement of faith or sermon claim against:

- the **original Hebrew/Greek**, with Strong's tagging and morphology (via [STEPBible TAHOT/TAGNT](https://github.com/STEPBible/STEPBible-Data) and [OSHB](https://github.com/openscriptures/morphhb)),
- the **canon-wide concordance** (every Strong's lemma → every occurrence; OpenBible + TSK cross-references),
- **multiple English translations** in parallel (formal: ESV/NASB/NKJV; dynamic: NIV/NLT, only for narrative grasp),
- **archaeological context** (Open Context, DAAHL, Dead Sea Scrolls anchoring),
- **church history nodes** (ecumenical councils, the [Reformation](https://en.wikipedia.org/wiki/Reformation), modern denominational lineages),
- and the **consolidated baseline** built upstream.

Output of any query: where claims agree, where they diverge, and where one tier of authority overrides another.

---

## Authority (whose word counts when)

Every record in the corpus carries an `authority_level` from 0 to 4. The **critical apparatus is the source of truth**; everything else is downstream.

| Level | Layer | Source |
|---|---|---|
| **0** | **Critical Apparatus** ← **source of truth** | [BHS](https://en.wikipedia.org/wiki/Biblia_Hebraica_Stuttgartensia) and [Nestle-Aland (NA28/UBS5)](https://en.wikipedia.org/wiki/Novum_Testamentum_Graece) footnotes: manuscript variants, editorial decisions. |
| 1 | Interlinear (Critical Text) + Concordance | OSHB, WLC, [SBLGNT](https://en.wikipedia.org/wiki/SBL_Greek_New_Testament), [STEPBible](https://www.stepbible.org/) alignment. Strong's-tagged lemma index for canon-wide spider-mapping. |
| 2 | Formal Equivalence | NKJV, ESV. Word-for-word priority. |
| 3 | Dynamic Equivalence | NIV, NLT. Thought-for-thought. Useful for narrative grasp; never for doctrinal mapping. |
| 4 | Exegetical Application | Personal teaching notes, archaeology, church history, commentaries. |

A Level 4 sermon claim cannot override a Level 1 interlinear reading; a Level 1 interlinear reading cannot override a Level 0 apparatus footnote. **Confessions (Reformed or otherwise) do not appear in this tier scale** — they are an information layer recorded as `counter_witness[]` in evidence files, not authority. When tiers disagree, the engine surfaces the conflict; it does not silently pick a side. See [docs/AUTHORITY_HIERARCHY.md](docs/AUTHORITY_HIERARCHY.md).

---

## The doctrinal baseline (multi-stage, collaborative)

I'm not building the baseline alone in a room. The collaborators are churches and elders I already know and trust personally. The output is then the tool I use to evaluate potential churches I'm considering visiting or joining.

```
questions.json (universal, locked envelope, 221 entries)
        │
        │  tools/derive_baseline_prompt.md  (one subagent per question)
        │  Pillars: concordance + hermeneutics + counter-witness
        ▼
baseline.json (lexical-philological seed)  ───┬─►  evidence/<id>.json (per-question audit trail)
        │                                     │
        │  distributed to trusted elders      │
        ▼                                     │
responses/<respondent_id>.json (filled, with respondent's confessional lens)
        │                                     │
        │  collation + research                │
        ▼                                     │
consolidated.json (final, canonical)  ───────┘
```

| File | What it is | Status |
|---|---|---|
| [questions.json](questions.json) | Universal question bank with 221 entries, each carrying 10 fields. Envelope updated to `formation_under_examination` + `judging_panel`. | Locked schema; question text scheduled for phase-3 reframe. |
| `baseline.json` | **Tradition-neutral lexical-philological seed answers** (221 × 13 fields + viewpoint envelope). Generated autonomously from apparatus + interlinear + concordance, with counter-witness corroboration. **Provisional**: autofill drudgework so trusted-elder collaborators engage with substantive disagreements, not blank forms. | To be generated |
| `responses/<id>.json` | Filled questionnaires from churches and elders I personally know and trust (and from me, with my own Brethren-adjacent confessional lens recorded). Same 13-field shape. **Private** (gitignored). | Pending input |
| `consolidated.json` | Final canonical baseline after collating all responses with the inferred seed and final research. | Future |
| `evidence/<id>.json` | Per-question audit trail: scripture citations with genre + figures, concordance lemma traversal, hermeneutic block, counter-witness citations, web sources, confidence flag. Survives every later phase. | To be generated |

All three answer files share the same 13-field boolean-pattern shape; the envelope's `viewpoint` field disambiguates whose stance is recorded (`inferred-from-sources` | `individual:<id>` | `consolidated`). Schemas are locked in [docs/QUESTION_SCHEMA.md](docs/QUESTION_SCHEMA.md) and [docs/ANSWER_SCHEMA.md](docs/ANSWER_SCHEMA.md).

The `tier` field is where the testimony lands in code: `essential` is "I'd lay my life down for this," `preference` is "live and let live."

---

## How each question gets tested

Every question runs through three pillars, in order, before any verdict is recorded:

| Pillar | Source | Purpose |
|---|---|---|
| **1. Concordance** (mechanical) | STEPBible TAHOT + TAGNT (Strong's-tagged Hebrew/Greek tokens), OSHB cross-validation, OpenBible + TSK cross-references via Neo4j Cypher | Makes `analogia scripturae` (Scripture interprets Scripture) deterministic. Every Strong's lemma in the anchor verses is spider-mapped to every occurrence in the canon. Selection bias dies at the data layer — a subagent cannot quietly skip Gen 6:6 / Ex 32:14 / Jonah 3:10 when the lemma index lists them mechanically. See [docs/CONCORDANCE.md](docs/CONCORDANCE.md). |
| **2. Hermeneutics** (visible) | Recorded per verdict in `evidence.hermeneutics` | Primary method (grammatico-historical / redemptive-historical / quadriga / patristic-typological / accommodation), frameworks in play (covenant / dispensational / NCT / progressive covenantalism / historic premillennial), figures of speech per scripture citation, genre rules, competing-lens verdicts. Forces the subagent to surface *how* the verdict was reached. See [docs/HERMENEUTICS.md](docs/HERMENEUTICS.md). |
| **3. Counter-witness** (research aid) | Patristic ([ccel.org](https://ccel.org/fathers)), Catholic magisterial ([CCC at vatican.va](https://www.vatican.va/archive/ENG0015/_INDEX.HTM)), Lutheran ([Book of Concord](https://bookofconcord.org)), Anglican ([39 Articles](https://www.churchofengland.org/prayer-and-worship/worship-texts-and-resources/book-common-prayer/articles-religion)), Reformed (Westminster, Heidelberg, Belgic), Methodist ([UMC Articles](https://www.umc.org/en/content/articles-of-religion)), Anabaptist (Schleitheim 1527), Pentecostal ([AG Fundamental Truths](https://ag.org/Beliefs/Statement-of-Fundamental-Truths)), Eastern Orthodox ([OCA](https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture)) primary sources | Tests whether the apparatus reading survives reading by a non-Reformed-Baptist tradition. **Mandatory ≥1** for any tier=essential or tier=convictional verdict. **Does NOT settle the verdict** — apparatus + interlinear + concordance settle. Counter-witness corroborates that the lexical reading isn't idiosyncratic. |

A clear interlinear reading contradicted by every counter-witness source is still a clear interlinear reading. Confessions never override Scripture. Reformed-Baptist confessions specifically (1689 LBC, the substrate the Brethren tradition shares with) cannot serve as independent corroboration for a Brethren reading because they share the same substrate.

For the same substrate-pluralism reason, the inferred-baseline subagents are **forbidden** from citing Reformed-aligned commentary sites (carm.org, equip.org, gotquestions.org, monergism, ligonier, gospelcoalition) as authority. Only primary repositories: BibleHub, STEPBible, OSHB, ccel.org (Schaff), vatican.va (CCC), bookofconcord.org, oca.org, ag.org, umc.org, openbible.info.

**Cult-marker bar — three conditions, all canonical.** A position counts as cult-grade only when:

1. `would_die_for=true` (moral entailment).
2. Apparatus + interlinear + concordance demonstrate the doctrine across the canon (not from a single passage).
3. Counter-witness from ≥6 distinct lineages corroborates with `stance="affirms"`.

**Even Trinity is not exempt.** Each question — including the Nicene-Chalcedonian foundations — clears or fails the bar on its own per-question evidence. Cross-tradition consensus is corroborating evidence the lexical reading isn't idiosyncratic; it does not, by itself, grant cult-marker status. A position rejected only by Reformed-Baptist confessions (the formation's substrate) carries `flags: ["cult-marker-substrate-only"]` and is downgraded to `would_die_for=true, cult_marker=false`. A position rejected by some major lineages but not others (e.g. Reformed-distinctive forensic justification, Catholic/Orthodox baptismal regeneration) is gospel-essential at most, not cult-grade.

**Caveat for fellow Brethren readers**: Plymouth Brethren historically reject formal confessions ("[no creed but Christ](https://en.wikipedia.org/wiki/Sola_scriptura)", sola scriptura strictly applied — though that phrase is itself a Reformed distinctive, which is part of what this engine is designed to surface). Including WCF, 1689 LBC, the Catechism, Book of Concord, and the rest in this engine is *informational research only*, not subscription. They are how each tradition reads the lexical text — useful to record, never authoritative for the verdict.

---

## Anonymization

The only personal name permitted anywhere in this repository is my own. Every other personal contributor (teachers whose teaching is in the corpus, friends, organization members) is redacted from `parsed/`, code, docs, server responses, and downstream artifacts. External published authors (John Piper, [Justin Martyr](https://en.wikipedia.org/wiki/Justin_Martyr), Augustine, Calvin) are retained as citations because they preserve the chain back to public sources. See [docs/ANONYMIZATION.md](docs/ANONYMIZATION.md) for the full policy.

The `source-docs/` and `converted/` directories are gitignored. They contain raw private teaching notes; only sanitized derivatives go public.

---

## What's built and what's not

- **Tier 1 (static structured corpus)**: *built*. Per-document JSON in [parsed/](parsed/), queryable from any Claude session via Read + Grep + jq.
- **Tier 2 retrieval (semantic + graph layer for sermon/SOF)**: *built*. Hybrid retrieval CLI is live: `uv run python -m retrieval.cli "<query>"`. Used by Pipeline B (per-respondent overlays).
- **Tier 2 concordance + Bible-text ingestion**: *loaders written, not yet run*. See [docs/CONCORDANCE.md](docs/CONCORDANCE.md) and [ingest/adapters/concordance_loader.py](ingest/adapters/concordance_loader.py).
- **Inferred-baseline pipeline**: *architecture complete*; orchestrator gated on concordance ingestion + KPI verifier green-light. See [tools/derive_baseline_prompt.md](tools/derive_baseline_prompt.md), [tools/baseline_orchestrator.py](tools/baseline_orchestrator.py), [tools/verify_baseline.py](tools/verify_baseline.py).
- **MCP server (Tier 3)**: *planned.* Schema designed; server not yet built.
- **Flutter client (Tier 3)**: *planned.*

---

## Layout

```
brethren-doctrine/
├── parsed/                 Sanitized structured JSON corpus (per-document + aggregate index + cross-doc perspectives).
├── docs/                   PROJECT.md, ANSWER_SCHEMA.md, QUESTION_SCHEMA.md, AUTHORITY_HIERARCHY.md, HERMENEUTICS.md, CONCORDANCE.md, ANONYMIZATION.md.
├── ingest/                 Pydantic models + Neo4j MERGE upsert adapters (sermon, SOF, concordance).
├── embeddings/             Voyage contextualized_embed + FastEmbed BM25 → Qdrant; Neo4j MERGE upsert.
├── retrieval/              Stage 0–4 hybrid retriever (router, hybrid RRF, BGE rerank, authority boost, envelope, Typer CLI).
├── graph/                  Neo4j schema (constraints + vector / fulltext / btree indexes).
├── docker/                 Neo4j + Qdrant compose.
├── research/               Tier 2 design research (embeddings, GraphRAG, hybrid+rerank, Bible data sources, MCP).
├── tools/                  derive_baseline_prompt.md (methodology), baseline_orchestrator.py (runtime + validator), verify_baseline.py (KPI verifier), verify_catalogs.json (catalogs), evidence_to_pdf.py (A4 PDF renderer).
├── evidence/               Per-question audit trail (populated by the baseline derivation run).
├── responses/              Filled questionnaires from trusted-elder collaborators + me. Private (gitignored).
├── questions.json          Universal question bank (221 entries; phase-3 reframe pending).
├── USAGE.md                Cross-session guide for querying the corpus from any Claude session.
└── .claude/skills/         `ingest-sermons` skill (Opus subagent orchestration for source → JSON parsing).
```

---

## Running it locally

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

# Ingest sermon + SOF corpus into Neo4j + Qdrant (Pipeline B)
uv run python -m embeddings.embed_and_load

# Ingest the concordance layer (one-time, idempotent; see docs/CONCORDANCE.md)
git clone https://github.com/STEPBible/STEPBible-Data data/private/stepbible
git clone https://github.com/openscriptures/morphhb data/private/oshb
uv run python -m ingest.adapters.concordance_loader load-all --src data/private

# Run regression tests (parsers + golden evidence schema)
uv run python -m pytest tests/ -v

# Run KPI verifier (gates the baseline orchestrator run)
uv run python -m tools.verify_baseline --check all --report

# Audit questions.json for verdict pre-loading / confessional-vocab smuggling
# (must pass before phase 2; the orchestrator's stem_audit step is a safety net,
#  not a substitute for clean question stems)
uv run python -m tools.verify_questions --report

# Run the inferred-baseline orchestrator (only after pytest + KPI verifier + question hygiene are green)
# (orchestrator is invoked by handing tools/derive_baseline_prompt.md to a fresh
# Claude Code session at the project root)

# Render an evidence/<id>.json as an A4 PDF
uv run python -m tools.evidence_to_pdf evidence/doc-trinity.json

# Query the live retrieval CLI (Pipeline B / downstream church-evaluation)
uv run python -m retrieval.cli "what does the corpus say about substitutionary atonement?"
uv run python -m retrieval.cli "Romans 6:1-4 baptism" --k 8 --json-only
```

---

## Status

Personal-use, single-user. No auth, no multi-tenant, no public API. The collaborative-questionnaire workflow runs in two directions: the baseline is built **with** churches and elders I personally know and trust; the baseline is then used to **evaluate** potential churches I'm considering visiting or joining. Personal due-diligence tooling. See [docs/PROJECT.md](docs/PROJECT.md) for the full picture and phase plan.

If you're another believer running the same diagnostic for yourself, the rubric (`questions.json`, the eventual `consolidated.json`, the engine itself) is potentially useful. The personal questionnaire responses (`responses/*.json`) are private. The structure is reusable; the answers are mine.

## License

No license declared. Personal-use code shared as-is for educational reference; treat anything you reuse as inspiration rather than a library to depend on.
