# Authority Hierarchy

Every retrievable record in this project carries an `authority_level` (0 to 4). Retrieval ranking, conflict resolution, and LLM citation MUST honor this hierarchy.

The authority tier scale is **independent** of the inferred-baseline `judging_panel`. Tier defines what kind of source a record is; the panel defines whose voice settles a verdict during baseline derivation. Both rules apply simultaneously.

## Levels

### Level 0: Critical Apparatus (highest authority)
Footnotes of the *Biblia Hebraica Stuttgartensia* (BHS) and *Nestle-Aland* (NA28/UBS5) showing manuscript variants and editorial decisions. Explains *why* the critical text reads as it does.

### Level 1: Interlinear (Critical Text). SOURCE OF TRUTH.
- **OT:** Masoretic Text via BHS, anchored on the Leningrad Codex (1008 AD), validated against the Dead Sea Scrolls.
- **NT:** Eclectic Greek text (Nestle-Aland), reconciling Alexandrian and Byzantine manuscript families.
- Tagged Hebrew with Strong's plus morphology via STEPBible TAHOT and Open Scriptures Hebrew Bible (OSHB).
- Word-level English alignment via STEPBible (Tyndale House). TAHOT for OT, TAGNT for NT.
- **Concordance edges**: every word-token in the canon carries a Strong's lemma reference; lemma → all-occurrences traversal lives at this tier. See [CONCORDANCE.md](CONCORDANCE.md).

The interlinear defines what a verse *says*. Every higher-level claim must trace back to this layer.

### Level 2: Formal Equivalence Translations (high-fidelity auxiliary)
ESV, NASB, NKJV. Word-for-word priority. Use as secondary reference when interpreting interlinear results.

### Level 3: Dynamic Equivalence Translations (narrative grasp only)
NIV, NLT. Thought-for-thought. Useful for high-level flow, **never** for doctrinal mapping into the graph.

### Level 4: Exegetical Application & Context
Sermon notes (in `parsed/`), Open Context archaeology, ESV Archaeological Study Bible enrichment, church history nodes, commentaries, external published authors cited within the corpus.

## Confessions are NOT a tier

Reformed-Protestant confessions (Westminster, 1689 London Baptist, Belgic, Heidelberg, Savoy), the three ecumenical creeds (Apostles', Nicene, Athanasian), the Catholic Catechism (CCC), the Lutheran Book of Concord, the Anglican 39 Articles, the Anabaptist Schleitheim Confession, and primary statements from Eastern Orthodox / Methodist / Pentecostal lineages do **not** appear in the 0–4 tier scale.

They are an **information layer** consulted by the inferred-baseline subagents as `counter_witness[]` entries — research aids that record how a tradition reads the lexical text. They never settle a verdict and never override apparatus + interlinear.

The distinction matters: if a confession-based source claimed authority on the 0–4 scale, it would compete with the apparatus for the same role (settling what a verse means). Confessions don't claim that role; they record how their tradition reads what the apparatus shows. They live in `evidence.counter_witness[]` with a `tradition` tag.

See [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md) for how `counter_witness[]` is consulted, and [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md) for the schema.

## Concordance — the spider-map layer

The lemma index (Strong's-tagged TAHOT + TAGNT + OSHB) lives at Level 1. Cross-references (TSK + OpenBible.info) ride alongside as canonical-context edges.

Why this matters: the inferred-baseline run treats `analogia scripturae` (Scripture interprets Scripture) as a mechanical traversal, not an editorial choice. Every Hebrew/Greek lemma maps deterministically to every occurrence in the canon. Subagents cannot quietly skip inconvenient passages — the concordance lists them. Selection bias is removed at the data layer.

See [CONCORDANCE.md](CONCORDANCE.md) for the database stack (TAHOT, TAGNT, OSHB, OpenBible cross-refs, TSK), the Neo4j schema for spider-map edges, and the traversal patterns each subagent runs.

## Retrieval rules

- **Conflict resolution:** When a Level 4 claim contradicts a Level 1 reading, the Level 1 reading wins. The conflict must be surfaced in the LLM response, never silently overridden. When a confession (any tradition) contradicts a Level 1 reading, the Level 1 reading wins — confessions never override Scripture. Cross-tradition counter-witness disagreement among confessions, with a clear apparatus reading, is recorded as an intramural debate visible in `evidence.counter_witness[]`, not as a verdict-shifter.
- **Citation order:** When citing in user-facing responses, surface the highest-authority source first (Level 0/1), then expand to lower levels for context. Counter-witness citations cite primary confession URLs; never cite Reformed-aligned commentary sites (carm, equip, gotquestions, monergism, ligonier, gospelcoalition) as authority.
- **Boost in ranking:** Higher authority gets a monotone bonus in the final ranking score (per the Tier 2 hybrid pipeline). Authority is a re-rank weight, not a hard filter.
- **Concordance traversal is mandatory** in the inferred-baseline run regardless of tier. `evidence.concordance_lemmas_traversed: []` is a validation failure on every question. See [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md).

## Schema requirement

Every record in `parsed/`, `chunks/`, `embeddings/`, and `graph/` carries an `authority_level: <int>` field. Records lacking this field are invalid for retrieval and must be flagged.

The Neo4j node schema for the lemma index, cross-reference edges, and inferred-baseline data is documented in [CONCORDANCE.md](CONCORDANCE.md) (concordance) and [PROJECT.md](PROJECT.md) (full graph).
