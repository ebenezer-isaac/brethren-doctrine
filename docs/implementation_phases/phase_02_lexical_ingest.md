# Phase 02: Lexical Ingest Runbook

## Scope

This phase reseeds the lexical Neo4j store from the 20 in-scope Layer 0 sources in `docs/data_inventory_catalog.json` plus the four procurement entries (peshitta, vulgate-clementine, coptic-scriptorium, open-cbgm-3-john). The phase is preceded by a full wipe driven by `tools/wipe_lexical.py`. Per-adapter contracts (record shape, fields, predicate types, edge cases) come from `docs/SCHEMA_DECISIONS.md` and its 17 decision blocks. The graph constraint and index set is in `graph/lexical.cypher`, where every constraint and index carries a trailing `// Decision N` reference so the Auditor in Phase H can mechanically check coverage. No embedding, no Pipeline 2 invocation, and no cultural-store work happens here.

## Dispatch order

The adapters run in five groups. Each group establishes structures the next group depends on. Within a group, adapters can run in any order. Edge counts and node counts per source are not inlined below; `tools/expected_counts.json` (written in Phase A.4) is the single source of truth.

### Group 1: Text floor

The text-floor group emits the canonical `Word`, `Morpheme`, and `Verse` nodes. Nothing else can run until these exist because every downstream layer joins on the OSIS reference and the canonical Strong identifier.

1. `ingest/lexical/oshb.py` (OSHB-morphology)
   - Decisions implemented: 1, 14, 15.
   - Inventory source: `OSHB-morphology` at `data/private/oshb/wlc`.
   - Upstream input: OSIS XML tree under `wlc/`.
   - Emitted labels and edges: `Word`, `Morpheme`, `Verse`, `Strong`, `Source`, `Reading` (for qere). Edges: `HAS_MORPHEME`, `IN_VERSE`, `INSTANCE_OF`, `IS_QERE_OF`, `FROM_EDITION`.
   - Acceptance Cypher:
     ```cypher
     MATCH (w:Word {source: 'OSHB-morphology'})
     OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
     WITH count(w) AS words, count(m) AS morphs
     RETURN words, morphs, morphs >= words
     ```
   - Dependency: none. First adapter in the run.

2. `ingest/lexical/macula_hebrew.py` (MACULA-Hebrew)
   - Decisions implemented: 1, 4, 14.
   - Inventory source: `MACULA-Hebrew` at `data/private/macula-hebrew/WLC/tsv/macula-hebrew.tsv`.
   - Upstream input: TSV plus the lowfat XML mirror.
   - Emitted labels and edges: `MaculaToken` enrichment, `Lemma`, `GreekLemma`, `LouwNidaDomain`. Edges: `HAS_MACULA_ENRICHMENT`, `INSTANCE_OF`, `BRIDGES_LXX`, `IN_DOMAIN`.
   - Acceptance Cypher:
     ```cypher
     MATCH (w:Word {source: 'OSHB-morphology'})-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
     WITH count(w) AS aligned
     RETURN aligned, aligned > 0
     ```
   - Dependency: OSHB Word nodes must exist; alignment join uses OSIS and lemma identity.

3. `ingest/lexical/macula_greek.py` (MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT)
   - Decisions implemented: 2, 4, 14, 15.
   - Inventory sources: `MACULA-Greek-Nestle1904`, `MACULA-Greek-SBLGNT`.
   - Upstream input: two TSV files; the adapter ingests both editions as distinct rows keyed by edition slug.
   - Emitted labels and edges: `Word`, `GreekLemma`, `LouwNidaDomain`, `Source`. Edges: `INSTANCE_OF`, `IN_DOMAIN`, `FROM_EDITION`.
   - Acceptance Cypher:
     ```cypher
     MATCH (w:Word)
     WHERE w.source IN ['MACULA-Greek-Nestle1904', 'MACULA-Greek-SBLGNT']
       AND w.ln IS NOT NULL
     WITH count(w) AS with_ln
     RETURN with_ln, with_ln > 0
     ```
   - Dependency: none on OSHB; runs alongside the Hebrew floor.

4. `ingest/lexical/morphgnt.py` (MorphGNT-SBLGNT)
   - Decisions implemented: 15.
   - Inventory source: `MorphGNT-SBLGNT` at `data/private/morphgnt`.
   - Upstream input: per-book `.txt` files (BCV, POS, parsing, text, word, normalized, lemma).
   - Emitted labels and edges: `Word {source: 'MorphGNT-SBLGNT'}`, `Verse`. Edges: `PARSE_OF` (to MACULA Greek SBLGNT Word), `IN_VERSE`. Adapter populates `Verse.text` for NT verses per Decision 15.
   - Acceptance Cypher:
     ```cypher
     MATCH (w:Word {source: 'MorphGNT-SBLGNT'})-[:PARSE_OF]->(g:Word {source: 'MACULA-Greek-SBLGNT'})
     WITH count(w) AS pairs
     RETURN pairs, pairs > 0
     ```
   - Dependency: MACULA-Greek-SBLGNT Word nodes must exist for the `PARSE_OF` join.

### Group 2: Witness layer

The witness layer joins surface tokens to per-verse witness manuscripts plus the versification rule set. It runs after the text floor because every witness row keys to an OSIS verse the floor has populated.

5. `ingest/lexical/stepbible_tahot.py` (STEPBible-TAHOT)
   - Decisions implemented: 16.
   - Inventory source: `STEPBible-TAHOT`.
   - Upstream input: TSV files under `data/private/stepbible/Translators Amalgamated OT+NT/`.
   - Emitted labels and edges: `TaggedToken {source: 'STEPBible-TAHOT'}`. Edges: `INSTANCE_OF` to `Lemma`, `IN_VERSE` to `Verse`.
   - Acceptance Cypher:
     ```cypher
     MATCH (t:TaggedToken {source: 'STEPBible-TAHOT'})
     WHERE t.strong IS NOT NULL AND t.morph IS NOT NULL
     WITH count(t) AS tokens
     RETURN tokens, tokens > 0
     ```
   - Dependency: `Verse` and `Lemma` nodes from Group 1.

6. `ingest/lexical/stepbible_tagnt.py` (STEPBible-TAGNT)
   - Decisions implemented: 16.
   - Inventory source: `STEPBible-TAGNT`.
   - Upstream input: TSV files under the same TAHOT/TAGNT root.
   - Emitted labels and edges: `TaggedToken {source: 'STEPBible-TAGNT'}`. Edges: `INSTANCE_OF` to `GreekLemma`, `IN_VERSE`.
   - Acceptance Cypher:
     ```cypher
     MATCH (t:TaggedToken {source: 'STEPBible-TAGNT'})
     WHERE size(t.meaning_variants) >= 0
     WITH count(t) AS tokens
     RETURN tokens, tokens > 0
     ```
   - Dependency: `Verse` and `GreekLemma` from Group 1.

7. `ingest/lexical/stepbible_tvtms.py` (STEPBible-TVTMS)
   - Decisions implemented: 5, 7, 8, 9.
   - Inventory source: `STEPBible-TVTMS` at `data/private/stepbible/tvtms.parsed.json`.
   - Upstream input: parsed versification rules.
   - Emitted labels and edges: `VersificationRule` plus serialized rule set on disk for the cross-version adapters in Group 5.
   - Acceptance Cypher:
     ```cypher
     MATCH (r:VersificationRule {source: 'STEPBible-TVTMS'})
     WHERE r.rule_type IS NOT NULL
     WITH count(r) AS rules
     RETURN rules, rules > 0
     ```
   - Dependency: none on text floor; required by Peshitta, Vulgate, Coptic, TSK, OpenBible adapters before they can project to OSIS.

### Group 3: Lexicons

Lexicon adapters write `BriefLexEntry`, `LsjEntry`, `MorphCode`, `ProperNoun` reference nodes that downstream verifier queries lean on.

8. `ingest/lexical/stepbible_tbesh.py` (STEPBible-TBESH)
   - Decisions implemented: 11.
   - Inventory source: `STEPBible-TBESH`.
   - Upstream input: `data/private/stepbible/Lexicons/TBESH ...`.
   - Emitted labels and edges: `BriefLexEntry {language: 'hebrew'}`. Edges: `LEX_FOR` to `Lemma`.
   - Acceptance Cypher:
     ```cypher
     MATCH (l:BriefLexEntry {source: 'STEPBible-TBESH', language: 'hebrew'})
     WHERE l.strong_disambig IS NOT NULL AND l.definition IS NOT NULL
     WITH count(l) AS entries
     RETURN entries, entries > 0
     ```
   - Dependency: `Lemma` nodes from Group 1 for the `LEX_FOR` join.

9. `ingest/lexical/stepbible_tbesg.py` (STEPBible-TBESG)
   - Decisions implemented: 12.
   - Inventory source: `STEPBible-TBESG`.
   - Upstream input: `data/private/stepbible/Lexicons/TBESG ...`.
   - Emitted labels and edges: `BriefLexEntry {language: 'greek'}`. Edges: `LEX_FOR` to `GreekLemma`.
   - Acceptance Cypher:
     ```cypher
     MATCH (l:BriefLexEntry {source: 'STEPBible-TBESG', language: 'greek'})
     WHERE l.greek IS NOT NULL
     WITH count(l) AS entries
     RETURN entries, entries > 0
     ```
   - Dependency: `GreekLemma` nodes from Group 1.

10. `ingest/lexical/stepbible_tflsj.py` (STEPBible-TFLSJ)
    - Decisions implemented: 13.
    - Inventory source: `STEPBible-TFLSJ`.
    - Upstream input: `data/private/stepbible/Lexicons`.
    - Emitted labels and edges: `LsjEntry`. Edges: `LEX_FOR` to `GreekLemma`.
    - Acceptance Cypher:
      ```cypher
      MATCH (e:LsjEntry {source: 'STEPBible-TFLSJ'})
      WHERE e.strong IS NOT NULL AND e.lemma IS NOT NULL
      WITH count(e) AS entries
      RETURN entries, entries > 0
      ```
    - Dependency: `GreekLemma` from Group 1.

11. `ingest/lexical/stepbible_morph_codes.py` (STEPBible-morph-codes)
    - Decisions implemented: 17.
    - Inventory source: `STEPBible-morph-codes`.
    - Upstream input: `data/private/stepbible/Morphology codes ...`.
    - Emitted labels and edges: `MorphCode`. No outbound edges; lookup table.
    - Acceptance Cypher:
      ```cypher
      MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
      WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL
      WITH count(m) AS codes
      RETURN codes, codes > 0
      ```
    - Dependency: none.

12. `ingest/lexical/stepbible_proper_nouns.py` (STEPBible-proper-nouns)
    - Decisions implemented: 17.
    - Inventory source: `STEPBible-proper-nouns`.
    - Upstream input: `data/private/stepbible/Proper Nouns/TI...`.
    - Emitted labels and edges: `ProperNoun`. Edges: `NAMED_AT` to `Verse` when `first_occurrence` resolves.
    - Acceptance Cypher:
      ```cypher
      MATCH (p:ProperNoun {source: 'STEPBible-proper-nouns'})
      WHERE p.proper_name_entry IS NOT NULL
      WITH count(p) AS names
      RETURN names, names > 0
      ```
    - Dependency: `Verse` nodes from Group 1.

13. `ingest/lexical/stepbible_ttesv.py` (STEPBible-TTESV)
    - Decisions implemented: 14, 15.
    - Inventory source: `STEPBible-TTESV`.
    - Upstream input: `data/private/stepbible/Tagged-Bibles/T...`.
    - Emitted labels and edges: `TaggedToken {source: 'STEPBible-TTESV', license: 'CC-BY-NC-4.0', redistribute: false}`. Edges: `INSTANCE_OF` to `Lemma` or `GreekLemma`.
    - Acceptance Cypher:
      ```cypher
      MATCH (t:TaggedToken {source: 'STEPBible-TTESV'})
      WHERE t.license = 'CC-BY-NC-4.0' AND t.redistribute = false
      WITH count(t) AS tokens
      RETURN tokens, tokens > 0
      ```
    - Dependency: `Lemma`, `GreekLemma`, `Verse` from Group 1.

### Group 4: Syntactic context

Syntactic-context adapters build the multi-layer text-fabric projection (`BhsaWord`, `BhsaPhrase`, `BhsaClause`) plus parallels and phonological enrichment. They depend on `Verse` and Strong identifiers from Group 1.

14. `ingest/lexical/bhsa.py` (ETCBC-BHSA)
    - Decisions implemented: 3, 14.
    - Inventory source: `ETCBC-BHSA` at `C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021`.
    - Upstream input: text-fabric module release 2021.
    - Emitted labels and edges: `BhsaClause`, `BhsaPhrase`, `BhsaWord`, `TFNode`. Edges: `CONTAINS_PHRASE`, `CONTAINS_WORD`, `IN_VERSE`.
    - Acceptance Cypher:
      ```cypher
      MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
      WITH count(DISTINCT w) AS words
      RETURN words, words > 0
      ```
    - Dependency: `Verse` for OSIS join.

15. `ingest/lexical/etcbc_parallels.py` (ETCBC-parallels)
    - Decisions implemented: 3.
    - Inventory source: `ETCBC-parallels`.
    - Upstream input: text-fabric parallels module.
    - Emitted labels and edges: `PARALLEL_OF` edges between `BhsaWord` nodes with a `similarity` float property.
    - Acceptance Cypher:
      ```cypher
      MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord)
      WHERE r.similarity IS NOT NULL
      WITH count(r) AS pairs
      RETURN pairs, pairs > 0
      ```
    - Dependency: BHSA Group 4 step 14.

16. `ingest/lexical/etcbc_phono.py` (ETCBC-phono)
    - Decisions implemented: 3.
    - Inventory source: `ETCBC-phono`.
    - Upstream input: text-fabric phono module.
    - Emitted labels and edges: optional `phono` property on `BhsaWord`. No new node label.
    - Acceptance Cypher:
      ```cypher
      MATCH (w:BhsaWord)
      WHERE w.phono IS NOT NULL
      WITH count(w) AS with_phono
      RETURN with_phono, with_phono > 0
      ```
    - Dependency: BHSA Group 4 step 14.

### Group 5: Cross-references and metadata

This group attaches verse-to-verse cross-references and per-entity metadata. It depends on `Verse` from Group 1 and the TVTMS rule set from Group 2.

17. `ingest/lexical/openbible.py` (OpenBible-cross-refs)
    - Decisions implemented: 5.
    - Inventory source: `OpenBible-cross-refs`.
    - Upstream input: `data/private/openbible/cross_references...`.
    - Emitted labels and edges: `OPENBIBLE_CROSS_REF` between `Verse` nodes with a `votes` int property.
    - Acceptance Cypher:
      ```cypher
      MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse)
      WHERE r.votes IS NOT NULL
      WITH count(r) AS edges
      RETURN edges, edges > 0
      ```
    - Dependency: `Verse` nodes; TVTMS rule set for KJV-to-OSIS remap.

18. `ingest/lexical/tsk.py` (TSK)
    - Decisions implemented: 5.
    - Inventory source: `TSK` at `data/private/tskxref.txt`.
    - Upstream input: SWORD TSK module text.
    - Emitted labels and edges: `CrossRef` keyed by `(book_num, chapter, verse, word_num)` plus `CROSS_REF` edges to `Verse`.
    - Acceptance Cypher:
      ```cypher
      MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
      WHERE a.book_num IS NOT NULL
      WITH count(r) AS edges
      RETURN edges, edges > 0
      ```
    - Dependency: `Verse` and TVTMS.

19. `ingest/lexical/theographic.py` (Theographic-Bible-Metadata)
    - Decisions implemented: 10.
    - Inventory source: `Theographic-Bible-Metadata`.
    - Upstream input: `data/private/theographic/json/`.
    - Emitted labels and edges: `Person`, `Place`, `Period`, `Event`, `Group`, `Tribe`. Edges: `MENTIONS` from entity to `Verse`.
    - Acceptance Cypher:
      ```cypher
      MATCH (p:Person {source: 'Theographic-Bible-Metadata'})
      WHERE p.entity_id IS NOT NULL AND p.display_name IS NOT NULL
      WITH count(p) AS persons
      RETURN persons, persons > 0
      ```
    - Dependency: `Verse` nodes from Group 1.

### Group 6: Procurement sources

These four adapters run last because their upstreams are either fetched fresh (Peshitta, Vulgate, Coptic) or read from a local CBGM SQLite asset (open-cbgm-3-john). Each adapter respects the air-gap by reading from a pre-fetched local cache at ingest time; live network access is blocked under `--network=none` per Network isolation below.

20. `ingest/lexical/peshitta.py` (peshitta)
    - Decisions implemented: 7.
    - Procurement entry: `peshitta` at upstream `github.com/etcbc/peshitta`.
    - Upstream input: ETCBC text-fabric Syriac NT module, fetched once into `data/private/peshitta/`.
    - Emitted labels and edges: `SyriacWord` with `verse_ref` projected through TVTMS. Edges: `IN_VERSE`.
    - Acceptance Cypher:
      ```cypher
      MATCH (s:SyriacWord {source: 'peshitta'})
      WHERE s.lex IS NOT NULL AND s.verse_ref IS NOT NULL
      WITH count(s) AS covered
      RETURN covered, covered > 0
      ```
    - Dependency: `Verse`, TVTMS.

21. `ingest/lexical/vulgate_clementine.py` (vulgate-clementine)
    - Decisions implemented: 8.
    - Procurement entry: `vulgate-clementine` at upstream Wikisource.
    - Upstream input: Wikisource Special:Export bundle cached at `data/private/vulgate/`.
    - Emitted labels and edges: `VulgateVerse` keyed by OSIS reference.
    - Acceptance Cypher:
      ```cypher
      MATCH (v:VulgateVerse)
      WHERE v.text_latin IS NOT NULL AND v.osis IS NOT NULL
      WITH count(v) AS verses
      RETURN verses, verses > 0
      ```
    - Dependency: TVTMS for the Clementine-to-OSIS verse map.

22. `ingest/lexical/coptic_scriptorium.py` (coptic-scriptorium)
    - Decisions implemented: 9.
    - Procurement entry: `coptic-scriptorium` at upstream `github.com/CopticScriptorium`.
    - Upstream input: per-corpus TT files cached at `data/private/coptic/`.
    - Emitted labels and edges: `CopticWord` with a `dialect` discriminator.
    - Acceptance Cypher:
      ```cypher
      MATCH (c:CopticWord {source: 'coptic-scriptorium'})
      WHERE c.lemma IS NOT NULL AND c.dialect IN ['sahidic', 'bohairic']
      WITH count(c) AS coverage
      RETURN coverage, coverage > 0
      ```
    - Dependency: `Verse`, TVTMS.

23. `ingest/lexical/open_cbgm_3_john.py` (open-cbgm-3-john)
    - Decisions implemented: 6.
    - Procurement entry: `open-cbgm-3-john` at local asset `tmp/poc/cbgm/3_john.db`.
    - Upstream input: SQLite database plus `3_john_collation.xml` TEI source.
    - Emitted labels and edges: `Witness`, `VariantUnit`, `Reading`. Edges: `READS_AT` (Witness to Reading), `ATTESTED_BY` (Reading to VariantUnit), `CORRECTOR_OF` (corrector hand to base hand).
    - Acceptance Cypher:
      ```cypher
      MATCH (w:Witness)-[:READS_AT]->(rd:Reading)-[:ATTESTED_BY]->(v:VariantUnit)
      WHERE v.book = '3John' AND v.chapter = 1 AND v.verse >= 1 AND v.verse <= 15
      WITH count(DISTINCT v) AS units
      RETURN units, units > 0
      ```
    - Dependency: `Verse` nodes for 3 John must exist so the variant-unit-to-verse join is well-defined.

## Idempotency

Every adapter is idempotent through MERGE-by-stable-id. Stable identifiers are namespaced per source: OSHB uses `oshb:<osisRef>.w<pos>` and `oshb-morph:<osisRef>.w<wpos>.m<mpos>`, MACULA-Hebrew uses the `xml:id` value verbatim, MACULA-Greek uses `<edition>:<xml:id>`, MorphGNT uses `morphgnt-sblgnt:<osisRef>.w<pos>`, ETCBC uses `bhsa:tf:<node_id>`. The wipe contract in `tools/wipe_lexical.py` deletes every node and relationship in the lexical Neo4j before re-ingest so that the MERGE writes start from an empty store and uniqueness constraints in `graph/lexical.cypher` reject any second-write attempt for the same identifier. The triangle-test hash recompute in Phase D re-runs the adapter on the same source bytes; the per-row presence vector (see RESEED_PLAN D.3) produces a sorted list of per-row SHA-256 hashes that must match byte-for-byte across two runs.

## Per-adapter acceptance pattern

Each `tools/verify_adapter_<X>.py` follows the same ratio-of-non-empty-fields template, referencing `tools/predicates_by_type.cypher` via include so no predicate is inlined.

```cypher
:include tools/predicates_by_type.cypher

MATCH (n:`<Label>` {source: $source})
WITH count(n) AS total,
     count(CASE WHEN $pred_string(n.<field_a>) THEN 1 END) AS with_a,
     count(CASE WHEN $pred_int(n.<field_b>) THEN 1 END) AS with_b
RETURN total,
       with_a * 1.0 / total AS ratio_a,
       with_b * 1.0 / total AS ratio_b
```

The Phase D verifier asserts each ratio meets its source-tier floor in `tools/expected_counts.json` (Tier A exact, Tier B plus or minus two percent, Tier C plus or minus five percent).

## Network isolation

Adapter dry-runs execute inside Docker with `--network=none` per RESEED_PLAN C.4, which forbids any HTTP, DNS, or socket access during ingest. The AST scan `tools/check_adapter_purity.py` rejects any adapter that imports `subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`, `mmap`, `os.system`, `os.spawn*`, `posix_spawn`, `multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`, or dynamic `__import__`. Procurement adapters fetch their upstreams once into `data/private/` outside the air-gapped run; the in-air-gap ingest reads only the local cache.

## Edge floor

Explicit minimum edge counts per edge type are recorded in `tools/expected_counts.json` (written in Phase A.4). This runbook does not inline edge counts; the counts file is the single source of truth and `tools/check_thresholds_immutable.py` asserts its SHA-256 stays constant from A.4 through Phase H except via a commit whose subject begins with `[SCHEMA-REVISION]`.

## Variant ingest (3 John CBGM Layer 1)

The 3 John CBGM ingest populates `Variant`, `Witness`, and `Reading` nodes from `tmp/poc/cbgm/3_john.db` and `tmp/poc/cbgm/3_john_collation.xml` per Decision 6 in `docs/SCHEMA_DECISIONS.md`. The open-cbgm pipeline produces variant units keyed by OSIS reference within the range `3John.1.1` to `3John.1.15`. Each `VariantUnit` carries `book`, `chapter`, `verse`, and `variant_unit_id`. Each `Reading` carries `reading_id`, `text`, and an `is_lacuna` boolean for witnesses that are physically illegible at that unit. `READS_AT` edges link `Witness` to `Reading`; `ATTESTED_BY` edges link `Reading` to `VariantUnit`. Corrector hands such as `<witness>*` and `<witness>C` are emitted as distinct `Witness` nodes connected by `CORRECTOR_OF`. ECM Catholic Letters beyond 3 John are recorded in `docs/data_inventory_catalog.json` at `explicit_deadends[0]` and are not ingested in this phase.

## Acceptance gate

The Auditor (Phase H) re-runs these checks against the committed Phase 02 artifacts:

- per-adapter pytest passes
- per-source Cypher count matches `tools/expected_counts.json` to its tier tolerance
- triangle-test hash recomputes to the same value on two runs over identical inputs
- `tools/check_adapter_purity.py` AST scan passes on every adapter file under `ingest/lexical/`
- `tools/check_thresholds_immutable.py` passes (expected-counts SHA matches the A.4 commit)
- `tools/verify_no_deferral.py` passes against this file plus `docs/ARCHITECTURE.md` and `docs/SCHEMA_DECISIONS.md`
- `tools/check_caste.py --range b4d1a1a..HEAD` passes (every commit carries a `Caste:` trailer matching the changed-file set)

## What this phase does not do

- no embedding (Phase E owns Voyage vector generation and Qdrant population)
- no Pipeline 2 invocation (Phase F dispatches the verdict subagent over the lexical store)
- no cultural-store touches (Phase G runs the parallel reseed against the cultural Neo4j and Qdrant)
- no human edits to `evidence/*` files (per the evidence-write protocol; only Pipeline 2 subagents write those JSON outputs)
- no LLM writes to Neo4j (LLMs are forbidden from writing to the graph at any phase)
