# brethren-doctrine

A theological GraphRAG engine for personal reflection and doctrinal evaluation.

It indexes the Hebrew/Greek interlinear, multiple English translations, archaeological data, church history, and a curated set of doctrinal teaching notes into a single queryable system. Then it lets me triangulate any church's stated doctrine against primary sources (the original languages, the manuscript tradition, ecumenical history) instead of trusting secondary chains.

The aim is *calibrated discernment*, not church-scoring. There's a difference.

---

## How I got here

I was born into a [Christian Brethren](https://en.wikipedia.org/wiki/Plymouth_Brethren) family, but my personality has always been to be a skeptic. For a long time I wasn't sure if God even existed. I used to pray something like: *I'm willing to forgo the blessing of believing without seeing because reaching heaven with one less blessing seems better than going altogether to hell for unbelief.* It was Pascal's Wager dressed up as humility, but I meant it. The is in reference to the line in [John 20:29](https://www.biblegateway.com/passage/?search=John+20%3A29) "Blessed are those who have not seen and yet have believed".

The conviction came during my early 20s during daily meditations. I used to sit under a tree and think about how the world was actually working. And I realized something obvious that I hadn't actually faced: if even one year all the trees never came back to life, the whole universe collapses. No oxygen, no food chain, no anything. Every life on the planet dies. For a system that delicate to operate flawlessly for thousands of years, *someone* has to be pulling the strings from the background. That's not naive. That's the [teleological argument](https://en.wikipedia.org/wiki/Teleological_argument) restated in the only terms I had at the time. From there I was convinced there was a God.

Then the next question landed. *If* God exists, *who* is God? Why are there so many gods? Was I leaning toward Jesus only because I'd been raised Christian? Would I have leaned toward Krishna or Allah if I'd been born somewhere else? The honest version of the question demanded I do real comparative work. So I started talking to friends, religious leaders from other traditions, reading their texts.

What I found was that only Christianity had bulletproof theology, philosophy, science, and history. It withstood every question I threw at it, to the point that it started to feel too perfect to be true. Almost like a conspiracy that was infallible, defensible from every angle. But the more I looked at the world itself, the more I saw the same signature: the same character, the same internal logic. The God of the Bible and the operations of the world ran on the same source code. Which brought me back, hard, to [John 1:1](https://www.biblegateway.com/passage/?search=John+1%3A1): *In the beginning was the Word.* Watching [Lee Strobel's *Case for Christ*](https://en.wikipedia.org/wiki/The_Case_for_Christ) put the last nail in my old self and forced me to publicly declare that there is no God other than Jesus.

That should have been the end of it. But I'm now in the next phase, and it's harder than the first two.

Back home in India, the answer to *which church?* was obvious: Brethren. It was what I was born into, what I knew, and the doctrine matched what I was taught. But the same skeptic question that pushed me through stages 1 and 2 keeps coming back: am I leaning toward Brethren only because I was raised in a Brethren family? Is my conviction inheritance, or is it verified? That question got significantly louder when I landed in London. There are very few distinct Brethren denominational churches here. The Brethren movement that initially originated in the UK has either been almost killed off or has reshaped so drastically from how it's practiced in India that I can hardly recognize it. So I'm forced to go in search of the truth again.

I came to Christianity *because of* its infallible truth and singular logic, grounded in Scripture. So why are there so many denominations within Christianity itself? If truth is singular, shouldn't there be a singular church?

The answer I've landed on, at least as a working frame: our access to truth was muddled when [Adam ate of the forbidden fruit](https://www.biblegateway.com/passage/?search=Genesis+3). Our ability to distinguish right from wrong has been compromised ever since. And it's further muddied by the devil, who [disguises himself as an angel of light](https://www.biblegateway.com/passage/?search=2+Corinthians+11%3A14) to spread misinformation. Whatever effort we put into defining truth is still just a best effort, because we lost the ability to share directly in God's truth. What we have left is one gift: the Bible, the ultimate source of truth God gave us. Interpretation is human best-effort aided by the Holy Spirit. The practice of doctrines is debatable. There's no escaping that, and pretending otherwise produces either fundamentalism or cynicism.

**This endeavour aims to identify, for myself, the truths I'm willing to lay my life down for, and the truths I'm willing to live and let live.**

That sentence is not rhetorical. It maps directly onto the `tier` field of every question in the doctrinal taxonomy: tier=`essential` is "die for"; tier=`preference` is "live and let live"; everything in between is graduated. The whole point of the engine is to calibrate that line *against primary sources* rather than inherit it from any single teacher.

---

## The three-stage progression

This project sits at the third step of a deliberate sequence:

1. *Does God exist?* Settled, under that tree.
2. *Is Jesus God?* Settled, after the comparative-religions work and Strobel.
3. *If Jesus is truth, why are there so many denominations, and which one is right?* **Open.** brethren-doctrine is the diagnostic tool I'm building to investigate this.

Each stage closes one trust gap so the next can be examined cleanly. I'm not delegating these conclusions to a single church or teacher. I'm verifying primary sources myself.

---

## What the engine actually does

The engine runs in two directions, with the doctrinal baseline as the hinge between them:

**Upstream (building the baseline).** I'm collaborating with a small set of churches and elders I personally know and trust. They fill out the same 222-question doctrinal questionnaire I do. The seed answers are autofilled by an inferred-baseline run (sources only: critical apparatus, interlinear, my teaching notes). The trusted-elder responses correct and refine that seed.

**Downstream (using the baseline).** Given a potential church I'm considering visiting or joining, the engine triangulates that church's statement of faith or sermon claim against:

- the **original Hebrew/Greek**, with Strong's tagging and morphology (via [OSHB](https://en.wikipedia.org/wiki/Open_Scriptures_Hebrew_Bible) for OT and the eclectic Greek text for NT),
- **multiple English translations** in parallel (formal equivalence: ESV/NASB/NKJV; dynamic: NIV/NLT, the latter only for narrative grasp),
- **archaeological context** (Open Context, DAAHL, Dead Sea Scrolls anchoring),
- **church history nodes** (ecumenical councils, the [Reformation](https://en.wikipedia.org/wiki/Reformation), modern denominational lineages),
- and the **consolidated baseline** built upstream.

Output of any query: where claims agree, where they diverge, and where one tier of authority overrides another.

---

## Authority (whose word counts when)

Every record in the corpus carries an `authority_level` from 0 to 4. The **critical apparatus is the source of truth**; everything else is downstream. Web sources and orthodox commentary are tertiary at best, never primary doctrinal authority.

| Level | Layer | Source |
|---|---|---|
| **0** | **Critical Apparatus** ← **source of truth** | [BHS](https://en.wikipedia.org/wiki/Biblia_Hebraica_Stuttgartensia) and [Nestle-Aland (NA28/UBS5)](https://en.wikipedia.org/wiki/Novum_Testamentum_Graece) footnotes: manuscript variants, editorial decisions, the bedrock that explains *why* the critical text reads what it does. |
| 1 | Interlinear (Critical Text) | OSHB, WLC, [SBLGNT](https://en.wikipedia.org/wiki/SBL_Greek_New_Testament), [STEPBible](https://www.stepbible.org/) alignment. The closest accessible representation when the apparatus itself is paywalled. |
| 2 | Formal Equivalence | NKJV, ESV. Word-for-word priority. Secondary reference when interpreting interlinear results. |
| 3 | Dynamic Equivalence | NIV, NLT. Thought-for-thought. Useful for narrative grasp; never for doctrinal mapping into the graph. |
| 4 | Exegetical Application | Personal teaching notes, archaeology, church history, commentaries. |

A Level 4 sermon claim cannot override a Level 1 interlinear reading; a Level 1 interlinear reading cannot override a Level 0 apparatus footnote. When tiers disagree, the engine surfaces the conflict; it does not silently pick a side. See [docs/AUTHORITY_HIERARCHY.md](docs/AUTHORITY_HIERARCHY.md) for the full policy.

---

## The doctrinal baseline (multi-stage, collaborative)

I'm not building the baseline alone in a room. The collaborators are churches and elders I already know and trust personally, the people whose discernment I'd want behind this work. The output is then the tool I use to evaluate potential churches I'm considering visiting or joining. The data model is staged accordingly.

```
questions.json (universal, locked, 222 entries)
        │
        │  tools/derive_baseline_prompt.md  (one Sonnet subagent per question)
        ▼
baseline.json (source-inferred seed)  ───┬─►  evidence/<id>.json (per-question audit trail)
        │                                │
        │  distributed to trusted elders │
        ▼                                │
responses/<respondent_id>.json (filled)  │
        │                                │
        │  collation + research          │
        ▼                                │
consolidated.json (final, canonical)  ───┘
```

| File | What it is | Status |
|---|---|---|
| [questions.json](questions.json) | Universal question bank with 222 entries, each carrying 10 fields (statement, scripture anchors, confessional anchors, tier, etc.). | Locked schema |
| `baseline.json` | **Source-inferred seed answers** (222 × 13 fields + viewpoint envelope). Generated autonomously from critical apparatus → interlinear → my teaching notes via the retrieval pipeline. **Provisional**: autofill drudgework so trusted-elder collaborators engage with substantive disagreements, not blank forms. | To be generated |
| `responses/<id>.json` | Filled questionnaires from churches and elders I personally know and trust (and from me). Same 13-field shape. **Private** (gitignored). | Pending input |
| `consolidated.json` | Final canonical baseline after collating all responses with the inferred seed and final research. The reference set my downstream church-evaluation queries are checked against. | Future |
| `evidence/<id>.json` | Per-question audit trail produced during baseline generation: scripture citations with interlinear notes, source-doc hits, web sources, confidence flag. Survives every later phase. | To be generated |

All three answer files (`baseline.json` / `responses/*.json` / `consolidated.json`) share the same 13-field boolean-pattern shape; the envelope's `viewpoint` field disambiguates whose stance is recorded (`inferred-from-sources` | `individual:<id>` | `consolidated`). Schemas are locked in [docs/QUESTION_SCHEMA.md](docs/QUESTION_SCHEMA.md) (the 10-field question bank) and [docs/ANSWER_SCHEMA.md](docs/ANSWER_SCHEMA.md) (the 13-field answer record + evidence shape).

The `tier` field is where the testimony lands in code: `essential` is "I'd lay my life down for this," `preference` is "live and let live."

---

## Confessions I cross-check against

When `questions.json` carries a `confessional_anchors` field, the inferred-baseline subagents verify it against this set:

- The [Westminster Confession of Faith (1646)](https://en.wikipedia.org/wiki/Westminster_Confession_of_Faith), the gold standard for Reformed confessional content.
- The [1689 London Baptist Confession of Faith](https://en.wikipedia.org/wiki/1689_Baptist_Confession_of_Faith), the Reformed credobaptist standard. It matches Brethren convictions on baptism, communion, and membership where WCF would create artificial paedobaptist friction.
- The three ecumenical creeds ([Apostles'](https://en.wikipedia.org/wiki/Apostles%27_Creed), [Nicene](https://en.wikipedia.org/wiki/Nicene_Creed), [Athanasian](https://en.wikipedia.org/wiki/Athanasian_Creed)). Pre-denominational and accepted across Roman Catholic, Eastern Orthodox, Reformed, Lutheran, and most evangelical lines. Athanasian especially nails Trinitarian/Christological precision for cult-marker questions (Watchtower, Mormon, Oneness Pentecostal).

**Caveat for fellow Brethren readers**: Plymouth Brethren historically reject formal confessions ("[no creed but Christ](https://en.wikipedia.org/wiki/Sola_scriptura)", sola scriptura strictly applied). Including WCF and 1689 LBC in this engine is a *verification tool*, not a subscription. The engine treats them as cross-checks, not authority. When confessions conflict (e.g., WCF and 1689 LBC on baptism), the engine references my private teaching notes via the retrieval pipeline, surfaces the conflict in `evidence/<id>.json`, and writes it into a manual-review report. I resolve those by hand. This is why the [Brethren Archive](https://www.brethrenarchive.org/) ([Darby](https://en.wikipedia.org/wiki/John_Nelson_Darby), [Mackintosh](https://en.wikipedia.org/wiki/Charles_Henry_Mackintosh), Kelly, Bellett) is also in the trusted-source set.

---

## Anonymization

The only personal name permitted anywhere in this repository is my own. Every other personal contributor (teachers whose teaching is in the corpus, friends, organization members) is redacted from `parsed/`, code, docs, server responses, and downstream artifacts. External published authors (John Piper, [Justin Martyr](https://en.wikipedia.org/wiki/Justin_Martyr), Augustine, Calvin) are retained as citations because they preserve the chain back to public sources. See [docs/ANONYMIZATION.md](docs/ANONYMIZATION.md) for the full policy.

The `source-docs/` and `converted/` directories are gitignored. They contain raw private teaching notes; only sanitized derivatives go public.

---

## What's built and what's not

- **Tier 1 (static structured corpus)**: *built*. Per-document JSON in [parsed/](parsed/), queryable from any Claude session via Read + Grep + jq.
- **Tier 2 (semantic + graph layer)**: *built for sermon and Statement-of-Faith corpora; Bible/critical-apparatus loading, graph traversal, and the MCP server are pending.* Hybrid retrieval CLI is live: `uv run python -m retrieval.cli "<query>"`. See [docs/TIER_2_SPEC.md](docs/TIER_2_SPEC.md).
- **Tier 3 (interactive surface)**: *planned.* MCP server + Flutter client.

---

## Layout

```
brethren-doctrine/
├── parsed/                 Sanitized structured JSON corpus (per-document + aggregate index + cross-doc perspectives).
├── docs/                   PROJECT.md, AUTHORITY_HIERARCHY.md, ANONYMIZATION.md, TIER_2_SPEC.md, QUESTION_SCHEMA.md, ANSWER_SCHEMA.md.
├── ingest/                 Pydantic models and Neo4j upsert adapters (sermon + SOF).
├── embeddings/             Voyage contextualized_embed + FastEmbed BM25 → Qdrant; Neo4j MERGE upsert.
├── retrieval/              Stage 0–4 hybrid retriever (router, hybrid RRF, BGE rerank, authority boost, envelope, Typer CLI).
├── graph/                  Neo4j schema (constraints + vector / fulltext / btree indexes).
├── docker/                 Neo4j + Qdrant compose (Qdrant on 6433/6434 to avoid host-port collisions).
├── research/               Tier 2 design research (embeddings, GraphRAG, hybrid+rerank, Bible data sources, MCP).
├── tools/                  derive_baseline_prompt.md handover for the inferred-seed run. (PDF renderers deleted under greenfield; will be rewritten against the new 13-field shape when needed.)
├── evidence/               Per-question audit trail (populated by the baseline derivation run).
├── responses/              Filled questionnaires from trusted-elder collaborators + me. Private (gitignored).
├── questions.json          Universal question bank (222 entries, locked 10-field schema; see docs/QUESTION_SCHEMA.md).
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

# Embed and load (requires source-docs/ + parsed/ locally)
uv run python -m embeddings.embed_and_load

# Query (pretty)
uv run python -m retrieval.cli "what does the corpus say about substitutionary atonement?"

# Query (machine-parseable)
uv run python -m retrieval.cli "Romans 6:1-4 baptism" --k 8 --json-only
```

PDF rendering is currently deferred. The legacy renderers were deleted under the greenfield policy; they targeted a deprecated answer-file shape. Fresh renderers will be written against the locked 13-field shape (see [docs/ANSWER_SCHEMA.md](docs/ANSWER_SCHEMA.md)) once the inferred-baseline run completes and the questionnaire round is ready.

---

## Status

Personal-use, single-user. No auth, no multi-tenant, no public API. The collaborative-questionnaire workflow runs in two directions: the baseline is built **with** churches and elders I personally know and trust; the baseline is then used to **evaluate** potential churches I'm considering visiting or joining. Personal due-diligence tooling. See [docs/PROJECT.md](docs/PROJECT.md) for the full picture.

If you're another believer running the same diagnostic for yourself, the rubric (`questions.json`, the eventual `consolidated.json`, the engine itself) is potentially useful. The personal questionnaire responses (`responses/*.json`) are private. The structure is reusable; the answers are mine.

## License

No license declared. Personal-use code shared as-is for educational reference; treat anything you reuse as inspiration rather than a library to depend on.
