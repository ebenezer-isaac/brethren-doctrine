# USAGE: Querying the brethren-doctrine corpus

This guide is for any Claude session opening the project in VSCode (or any other tool with file access). It tells you what's where, what queries work today, and what's planned.

For the full project picture, read [docs/PROJECT.md](docs/PROJECT.md). For the inferred-baseline methodology, read [tools/derive_baseline_prompt.md](tools/derive_baseline_prompt.md).

---

## What's in the corpus

Two distinct stores share a Neo4j + Qdrant backbone:

**Tier 1, sermon + SOF corpus (live)**: structured JSON in `parsed/`, plus Tier 2 hybrid retrieval CLI for semantic queries. This is the "what does my teaching tradition say?" layer. Used by Pipeline B (per-respondent files); NOT used during inferred-baseline derivation.

**Concordance + Bible text (built)**: STEPBible TAHOT + TAGNT + OSHB + OpenBible + TSK ingested into Neo4j (17k lemmas, 448k tokens, 34k verses, 600k OpenBible refs, 591k TSK refs). This is the spider-map layer that backs the inferred-baseline pipeline. See `docs/CONCORDANCE.md`.

---

## Tier 1 (sermon + SOF)

The static corpus is queryable using only Read + Grep. No external services, no embeddings, no graph DB. This is the baseline working today.

### What's in `parsed/`

15 structured JSON files, one per source document. Each follows the schema in `.claude/skills/ingest-sermons/SKILL.md` Step 4.

Per-document fields you'll use most:
- `doc_slug`: anchor identifier
- `session_metadata.title`, `session_metadata.session_topic`, `session_metadata.topic_clusters`
- `theological_themes`: top-level themes for the document
- `scripture_refs`: every scripture reference, OSIS-normalized
- `chunks[]`: semantic chunks with `content`, `themes`, `claims`, `scripture_refs`, optional `perspectives_within_chunk`
- `confidence`: extraction confidence per dimension

Two aggregate files at the root of `parsed/`:
- `_index.json`: corpus-wide aggregate (themes, scripture coverage, per-doc summaries)
- `_perspectives.json`: cross-document perspective sets (where different docs address the same theme with distinct claims)

### Common Tier 1 query patterns

**"What documents touch a theme?"**
- Read `parsed/_index.json` → `by_theme["<theme>"]` returns document slugs.

**"What does the corpus say about [topic]?"**
- Find candidate docs via `_index.json` themes.
- Read those JSONs and pull the matching `chunks[]` by their `themes` array.

**"Show me everything referencing [scripture]"**
- Read `_index.json` → `scripture_coverage["<OSIS book>"]` gives doc slugs.
- For exact verse: Grep across `parsed/*.json` for the OSIS form.

**"Where do documents disagree or present multiple angles?"**
- Read `parsed/_perspectives.json` → `perspective_sets[]`.

### jq one-liners

```bash
# All themes from a doc
jq '.theological_themes' parsed/sof_holy_spirit.json

# Perspective sets touching a theme
jq '.perspective_sets[] | select(.shared_theme | contains("baptism"))' parsed/_perspectives.json
```

### Authority hierarchy in Tier 1

Every parsed chunk is `authority_level: 4` (exegetical application). When you cite a Tier 1 result, label it as a *teaching claim*, not as Bible-textual ground truth. The interlinear and original-language verification layer is at Level 1 (concordance + apparatus, see below).

---

## Tier 2 retrieval (live for sermon/SOF)

```bash
# Hybrid retrieval over the sermon + SOF corpus
uv run python -m retrieval.cli "what does the corpus say about substitutionary atonement?"

# Machine-readable
uv run python -m retrieval.cli "Romans 6:1-4 baptism" --k 8 --json-only
```

Returns the `answer_context[]` envelope with `chunk_id`, `score`, `source_doc`, `authority_level`, `chunk_type`, `themes`, `scripture_refs`, `text`, `citations`, `graph_context`.

This CLI is for Pipeline B (per-respondent overlays) and downstream church-evaluation queries. **It is not used during inferred-baseline derivation.**

---

## Inferred-baseline pipeline

The 231-question doctrinal baseline is derived by `tools/baseline_orchestrator.py`, one subagent per question, each writing to `evidence/<id>.json`. The pipeline does NOT consult `parsed/`, `source-docs/`, confessions, or Brethren teaching notes. It only consults:

- Critical apparatus (BHS, NA28/UBS5)
- Interlinear (STEPBible, BibleHub, OSHB)
- Concordance (TAHOT + TAGNT lemma index, OpenBible + TSK cross-references) via Cypher
- Counter-witness traditions (patristic, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal, Eastern Orthodox primary sources), **research aids only, not authority**

Read `tools/derive_baseline_prompt.md` for the full methodology and `tools/verify_baseline.py` for the KPI matrix that gates the orchestrator run.

```bash
# Show worklist (questions without complete evidence)
python tools/baseline_orchestrator.py worklist

# Validate a single evidence file
python tools/baseline_orchestrator.py validate doc-trinity

# Validate all
python tools/baseline_orchestrator.py validate-all

# Run the KPI verifier (gates green-light for the orchestrator)
python -m tools.verify_baseline --check all --report

# Run the regression test suite (parsers + golden evidence schema round-trip)
.venv/Scripts/python -m pytest tests/ -v
```

The `tests/` directory contains pytest fixtures that lock:
- STEPBible TAHOT/TAGNT parser column extraction (`tests/test_concordance_parsers.py`)
- Evidence-schema validator + PDF renderer round-trip (`tests/test_evidence_schema.py`)
- Legacy-key rejection (any v1 schema field is hard-rejected by validator)
- Cult-marker canonical-demonstration enforcement (pan-canonical lexical breadth, not lineage count)
- Empty `concordance_lemmas_traversed` rejection (universal, all tiers)

If pytest exits zero AND `tools/verify_baseline.py --check all` exits zero, phase 2 (orchestrator run) is unblocked.

---

## Concordance ingestion (complete)

```bash
# Drop the STEPBible-Data and OSHB clones under data/private/
git clone https://github.com/STEPBible/STEPBible-Data data/private/stepbible
git clone https://github.com/openscriptures/morphhb data/private/oshb

# Run loaders (one-time, idempotent)
python -m ingest.adapters.concordance_loader load-all --src data/private
```

See `docs/CONCORDANCE.md` for the full plan, expected counts, and KPI verification.

---

## What you should NOT do

- **Never write personal contributor names into outputs.** See `docs/ANONYMIZATION.md`. External published authors are fine; teachers whose lessons populate this corpus are not.
- **Never override authority levels.** A teaching claim doesn't trump an interlinear reading. See `docs/AUTHORITY_HIERARCHY.md`.
- **Never modify `source-docs/`.** Those files are read-only inputs.
- **Never invoke the retrieval CLI from a baseline subagent.** Baseline derivation does not consult sermon material.
- **Never cite Reformed-aligned commentary sites as authority** (carm.org, equip.org, gotquestions.org, monergism.com, ligonier.org, thegospelcoalition.org). They share the formation-under-examination's substrate. Primary-source repositories only.
- **Don't reinvent ingestion.** Re-run the `ingest-sermons` skill if new docs land in `source-docs/`. Re-run `concordance_loader` if STEPBible data updates. Both are idempotent.

---

## Re-running the sermon ingestion

If new files land in `source-docs/`, invoke the `ingest-sermons` skill (or just say "ingest the sermons"). It will inventory new/changed files, dispatch parallel Opus subagents, and rebuild `parsed/_index.json` and `parsed/_perspectives.json`. Existing parsed files are not re-processed unless their source `mtime` has changed.

---

## When in doubt

- Project shape and architecture: `docs/PROJECT.md`
- Inferred-baseline methodology: `tools/derive_baseline_prompt.md`
- Authority rules: `docs/AUTHORITY_HIERARCHY.md`
- Hermeneutics methodology: `docs/HERMENEUTICS.md`
- Concordance / spider-map: `docs/CONCORDANCE.md`
- KPI verifier: `tools/verify_baseline.py`
- Privacy/anonymization: `docs/ANONYMIZATION.md`
- Sermon ingestion mechanics: `.claude/skills/ingest-sermons/SKILL.md`
