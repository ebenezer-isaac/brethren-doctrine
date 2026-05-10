# Authority Hierarchy

Every retrievable record in this project carries an `authority_level` (0–4). Retrieval ranking, conflict resolution, and LLM citation MUST honor this hierarchy.

## Levels

### Level 0 — Critical Apparatus (highest authority)
Footnotes of the *Biblia Hebraica Stuttgartensia* (BHS) and *Nestle-Aland* (NA28/UBS5) showing manuscript variants and editorial decisions. Explains *why* the critical text reads as it does.

### Level 1 — Interlinear (Critical Text) — SOURCE OF TRUTH
- **OT:** Masoretic Text via BHS, anchored on the Leningrad Codex (1008 AD), validated against the Dead Sea Scrolls (~95% identical across a 1,200-year gap).
- **NT:** Eclectic Greek text (Nestle-Aland), reconciling Alexandrian and Byzantine manuscript families.
- Tagged Hebrew with Strong's + morphology via Open Scriptures Hebrew Bible (OSHB).
- Word-level English alignment via STEPBible (Tyndale House) — TAHOT for OT, TAGNT for NT.

The interlinear defines what a verse *says*. Every higher-level claim must trace back to this layer.

### Level 2 — Formal Equivalence Translations (high-fidelity auxiliary)
ESV, NASB, NKJV. Word-for-word priority. Use as secondary reference when interpreting interlinear results.

### Level 3 — Dynamic Equivalence Translations (narrative grasp only)
NIV, NLT. Thought-for-thought. Useful for high-level flow, **never** for doctrinal mapping into the graph.

### Level 4 — Exegetical Application & Context
Sermon notes (in `parsed/`), Open Context archaeology, ESV Archaeological Study Bible enrichment, church history nodes, commentaries, external published authors cited within the corpus.

## Retrieval rules

- **Conflict resolution:** When a Level 4 claim contradicts a Level 1 reading, the Level 1 reading wins. The conflict must be surfaced in the LLM response — never silently overridden.
- **Citation order:** When citing in user-facing responses, surface the highest-authority source first, then expand to lower levels for context.
- **Boost in ranking:** Higher authority gets a monotone bonus in the final ranking score (per the Tier 2 hybrid pipeline). Authority is a re-rank weight, not a hard filter.
- **Tier 1 search (current):** When using only the static corpus (no embeddings yet), every claim retrieved is Level 4. This is fine for "what does the corpus say" queries; flag clearly if asked to verify against original-language data, since that requires Tier 2.

## Schema requirement

Every record in `parsed/`, `chunks/`, `embeddings/`, and `graph/` carries an `authority_level: <int>` field. Records lacking this field are invalid for retrieval and must be flagged.
