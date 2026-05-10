# Concordance, the spider-map layer

> Methodology pillar #1. Makes `analogia scripturae` (Scripture interprets Scripture) mechanical instead of editorial: every Hebrew/Greek lemma maps deterministically to every occurrence in the canon, and every verse carries hand-curated cross-references to thematically linked verses.

The other two pillars are [HERMENEUTICS.md](HERMENEUTICS.md) (interpretive lens recorded per verdict) and the counter-witness panel ([../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md)). Concordance is the data layer that holds them honest: subagents cannot quietly skip inconvenient passages because the spider-map lists them.

---

## Why this exists

Two failure modes the lemma index catches that nothing else does:

**Selection bias at the citation level.** A subagent answering a question on omnipotence/immutability can produce a `scripture[]` array with all `supports: "for"` by quietly omitting Gen 6:6, Ex 32:14, 1 Sam 15:11, Jonah 3:10. With the concordance, the lemma `nacham` (H5162, "to be sorry / repent / be moved to pity") returns every occurrence in the canon, those passages are listed mechanically. Skipping them now requires an explicit choice the validator can flag.

**Single-passage doctrines.** A doctrine that rests on one passage is structurally fragile. The cult-marker bar in [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md) requires *canonical demonstration*: the doctrine must be visible across the canon, not from a single passage. The concordance is what makes "across the canon" measurable, every lemma's occurrence list either supports a pan-canonical reading or doesn't.

---

## Database stack

All sources verified active and well-maintained as of 2026.

| Source | What it gives | License | Format | Repo / URL |
|---|---|---|---|---|
| **STEPBible TAHOT** | Translators' Amalgamated Hebrew OT, every Hebrew word in the Tanakh with disambiguated Strong's lemma, ETCBC/OpenScriptures morphology, gloss. ~423k tokens. Variant-aware (Leningrad/WLC, Ketiv/Qere). | CC BY 4.0 | TSV (UTF-8, `$`-delimited records) | https://github.com/STEPBible/STEPBible-Data |
| **STEPBible TAGNT** | Translators' Amalgamated Greek NT, same shape; NA27/28, TR, SBLGNT, TH-GNT, Byz, WH. Disambiguated Strong's → LSJ + Robinson morphology. ~138k tokens. | CC BY 4.0 | TSV | Same repo |
| **OSHB / MorphHB** | Open Scriptures Hebrew Bible, full Hebrew Bible, Westminster Leningrad Codex with augmented Strong's + morphology, OSIS XML. Cross-validates TAHOT (shares the OpenScriptures morph dialect). | CC BY 4.0 | OSIS XML | https://github.com/openscriptures/morphhb |
| **OpenBible.info cross-references** | ~340k vote-weighted cross-references. Vote weights map cleanly to Neo4j edge `confidence` property. Primary thematic layer. | CC BY | TSV/zip | https://www.openbible.info/labs/cross-references/ |
| **Treasury of Scripture Knowledge (TSK)** | ~500k hand-curated cross-references (1834, public domain). Long-tail thematic backstop. | Public domain | CSV/SQLite/JSON | https://github.com/scrollmapper/bible_databases |

**Skip MorphGNT/SBLGNT**, TAGNT supersedes it for our purpose (TAGNT carries Strong's; MorphGNT does not, and its last release is 2017).

---

## Neo4j schema

Concordance edges live alongside the existing Tier 2 graph schema. Verse and Token nodes are already defined in the inherited Tier 2 model; concordance adds the lemma index and cross-reference edges.

```cypher
// Lemma node, one per disambiguated Strong's number
(:Lemma {
  strongs,             // 'G3056', 'H7706', UNIQUE
  language,            // 'gr' | 'he'
  lemma_form,          // λόγος / שַׁדַּי
  transliteration,     // 'logos' / 'shaddai'
  gloss_short,         // brief gloss
  gloss_long,          // extended gloss
  semantic_domain      // optional Louw-Nida or SDBH tag
})

// Token node, one per word occurrence in the source text
(:Token {
  token_id,            // composite: '<verse_osis>:<word_position>', UNIQUE
  verse_osis,          // 'Rom.6.3'
  position,            // 1-indexed within verse
  surface_form,        // the inflected form as it appears
  morph,               // morphology code
  authority_level      // 1 (interlinear)
})

// Verse node, already exists in Tier 2; add cross-ref incoming/outgoing
(:Verse {
  verse_osis,          // 'Rom.6.3', UNIQUE
  book_osis, chapter, verse, testament,
  translations,
  authority_level      // 1
})

// Concordance edges
(:Token)-[:HAS_LEMMA]->(:Lemma)
(:Token)-[:OCCURS_IN]->(:Verse)
(:Verse)-[:CONTAINS_TOKEN {position}]->(:Token)

// Cross-reference edges
(:Verse)-[:OPENBIBLE_REF {weight, polarity}]->(:Verse)
// 'weight' from OpenBible vote count; 'polarity' = 'supports' | 'contrasts' | 'parallel'
(:Verse)-[:TSK_REF {category}]->(:Verse)
// 'category' from TSK classification (allusion, parallel, comparison, contrast)

// Convenience reverse-lookup edge for spider-map traversal
(:Lemma)-[:OCCURS_IN_VERSE {count}]->(:Verse)
// 'count' = how many tokens of this lemma appear in this verse
```

### Indexes & constraints

```cypher
CREATE CONSTRAINT lemma_strongs_uq IF NOT EXISTS
  FOR (l:Lemma) REQUIRE l.strongs IS UNIQUE;
CREATE CONSTRAINT token_id_uq IF NOT EXISTS
  FOR (t:Token) REQUIRE t.token_id IS UNIQUE;

CREATE INDEX lemma_language IF NOT EXISTS
  FOR (l:Lemma) ON (l.language);
CREATE INDEX token_verse IF NOT EXISTS
  FOR (t:Token) ON (t.verse_osis);

// Reverse-lookup edge needs to be findable
// (Neo4j 5.x doesn't index relationship properties without the relationship type;
//  edge weight queries traverse OPENBIBLE_REF and TSK_REF directly via the type)
```

---

## Spider-map traversal

Three traversal patterns subagents run during the analogia-scripturae step.

### Pattern A, lemma occurrences

Given a Strong's lemma, return every verse it appears in, with surface forms and morphology. This is the core spider-map query.

```cypher
MATCH (l:Lemma {strongs: $strongs})<-[:HAS_LEMMA]-(t:Token)-[:OCCURS_IN]->(v:Verse)
RETURN v.verse_osis AS osis,
       collect({surface: t.surface_form, position: t.position, morph: t.morph}) AS tokens,
       count(t) AS occurrence_count
ORDER BY v.book_osis, v.chapter, v.verse
```

Sample expected counts (validation spot-check via `tools/verify_baseline.py --check lemma-counts`):

| Strong's | Lemma | Expected count |
|---|---|---|
| H7706 | shaddai | 48 |
| H2617 | chesed | ~246 |
| H5162 | nacham | ~108 |
| G3056 | logos | 330 |
| G3551 | nomos | 195 |
| G26 | agape | 116 |

±2% tolerance accounts for canonical edition variations.

### Pattern B, verse cross-references

Given a verse, return all OpenBible-weighted and TSK cross-references.

```cypher
MATCH (src:Verse {verse_osis: $osis})
OPTIONAL MATCH (src)-[r:OPENBIBLE_REF]->(dst:Verse)
WITH src, collect({osis: dst.verse_osis, weight: r.weight, polarity: r.polarity}) AS openbible_refs
OPTIONAL MATCH (src)-[r2:TSK_REF]->(dst2:Verse)
WITH src, openbible_refs, collect({osis: dst2.verse_osis, category: r2.category}) AS tsk_refs
RETURN src.verse_osis AS osis,
       openbible_refs[0..30] AS openbible,
       tsk_refs[0..30] AS tsk
```

### Pattern C, full spider-map (lemma overlap + cross-references)

Given a verse, return every other verse that either shares ≥1 lemma or is cross-referenced from it. This is the operational `analogia scripturae` query: "what other passages bear on this one?"

```cypher
MATCH (src:Verse {verse_osis: $osis})-[:CONTAINS_TOKEN]->(:Token)-[:HAS_LEMMA]->(l:Lemma)
WHERE size((:Token)-[:HAS_LEMMA]->(l)) < $max_occurrences   // skip ultra-common particles
WITH src, collect(DISTINCT l.strongs) AS lemmas
MATCH (l2:Lemma)<-[:HAS_LEMMA]-(:Token)-[:OCCURS_IN]->(v:Verse)
WHERE l2.strongs IN lemmas AND v.verse_osis <> $osis
WITH src, v, count(DISTINCT l2.strongs) AS lemma_overlap
OPTIONAL MATCH (src)-[xref:OPENBIBLE_REF|TSK_REF]->(v)
RETURN v.verse_osis AS osis,
       lemma_overlap,
       count(xref) AS xref_edges
ORDER BY lemma_overlap DESC, xref_edges DESC
LIMIT $k
```

`$max_occurrences` filters out particles (e.g., καί has ~9000 occurrences and isn't doctrinally informative). Reasonable default: 800.

---

## Subagent traversal protocol

During the inferred-baseline run, each subagent runs the following concordance steps and records the result in `evidence.concordance_lemmas_traversed[]`:

1. **For each `scripture_anchors` entry**: run Pattern A on every Strong's-tagged lemma in the verse where the lemma is doctrinally salient (load-bearing for the verdict). Inspect the occurrence list; flag complicating uses (e.g., `nacham` in Gen 6:6 / Ex 32:14 when answering an immutability question).
2. **For each ambiguous lexical decision**: run Pattern A on the alternative reading's lemma if a different Strong's number could be in play.
3. **For at least one canonical-context check**: run Pattern C on the primary anchor verse to surface verses the editorial selection might have missed.

The final `concordance_lemmas_traversed[]` is the deduplicated list of Strong's numbers fed into Pattern A across all those steps. **An empty list is a hard validation failure on every tier.** A list shorter than the count of doctrinally salient lemmas in the anchor verses carries flag `concordance-traversal-undersized`.

---

## Ingestion plan

Loaders live in `ingest/adapters/`. Each is idempotent (re-runnable; uses Neo4j `MERGE`).

| Loader | Source | Output |
|---|---|---|
| `tahot_loader.py` | TAHOT TSV | `:Lemma{strongs,language='he'}`, `:Token`, `:Verse`, `[:HAS_LEMMA]`, `[:OCCURS_IN]`, `[:CONTAINS_TOKEN]` |
| `tagnt_loader.py` | TAGNT TSV | Same as above with `language='gr'` |
| `oshb_loader.py` | OSHB OSIS XML | Cross-validation pass for TAHOT; logs diffs to `logs/oshb_vs_tahot.diff`, writes nothing to graph (TAHOT is canonical) |
| `openbible_xref_loader.py` | OpenBible TSV | `[:OPENBIBLE_REF{weight,polarity}]` |
| `tsk_loader.py` | scrollmapper TSK CSV | `[:TSK_REF{category}]` |

Run order: `tahot` → `tagnt` → `oshb` (validation) → `openbible` → `tsk`. Each prints expected vs actual counts; a >5% deviation from expected halts the run with explanation.

The loaders are idempotent and have been run. As of 2026-05-10, Neo4j carries 17,003 lemmas, 447,700 tokens, 34,128 verses, 600,364 OpenBible cross-references, 591,039 TSK cross-references. Re-running is safe (MERGE-based upsert).

---

## Cost & data volume

Single-user, personal-use load.

| Item | Volume |
|---|---|
| TAHOT tokens | ~423k |
| TAGNT tokens | ~138k |
| Distinct lemmas (Hebrew + Greek) | ~14k |
| OpenBible cross-references | ~340k |
| TSK cross-references | ~500k |
| Total Neo4j edge count added | ~1.4M |
| Disk footprint (Neo4j + Qdrant) | ~500 MB |
| Embedding cost added | $0 (concordance edges don't need embeddings) |

No new monthly cost. Concordance is a one-time ingestion.

---

## Verification (KPIs from the verifier)

`tools/verify_baseline.py --check concordance` runs:

- **C1**: TAHOT row count vs Neo4j Hebrew token count (within ±0.5%)
- **C2**: TAGNT row count vs Neo4j Greek token count (within ±0.5%)
- **C3**: Lemma occurrence spot-checks (table above) within ±2%
- **C4**: TSK edge count ≥ 500k
- **C5**: OpenBible edge count ≥ 340k, all weights in `[-100, +100]`
- **C6**: Pattern C latency p95 < 2s on dev hardware (10 sample verses)
- **C7**: Pattern C from John 1:1 returns ≥ 100 linked verses

All KPIs must pass before the orchestrator run is approved.
