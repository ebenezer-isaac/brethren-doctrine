# Phase D Verification Harness

Caste: auditor. READ-ONLY spec-build. Branch main, HEAD 02ebae8.

Doctrinal frame: brethren-on-trial. This document is an execution-ready
verification harness so that the MOMENT the live lexical ingest finishes the
orchestrator can run the Phase D.4 count gate and the per-edge correctness
pass with zero further design work. Every Cypher below is concrete and
runnable. No em or en dashes anywhere.

Inputs reconciled: `tools/expected_counts.json` (the FINAL reconciled catalog
after [SCHEMA-REVISION] ceb3898 + 01e09c6), `docs/implementation_phases/phase_02_lexical_ingest.md`
sections 1 to 23, `tools/predicates_by_type.cypher`,
`docs/PHASE_D_CATALOG_RECONCILIATION.md`, `docs/AUDIT_phase_d_preflight_verification.md`,
and the per-adapter `SOURCE_SLUG` constants read directly from each adapter in
`ingest/lexical/`.

## CRITICAL PROVENANCE NOTE: the exact `source` property string

The exact `source` property string each adapter stamps was derived by reading
the `SOURCE_SLUG` module constant in each adapter file (and the adapter
emitted-record contract docstring), NOT guessed. Every adapter uses the
inventory-name style verbatim (for example `Word {source:'OSHB-morphology'}`,
`TaggedToken {source:'STEPBible-TAHOT'}`, `Word {source:'MACULA-Greek-SBLGNT'}`).

INCONSISTENCY FLAGGED (see Section 5, item 1): the stale `--verify-only`
block inside `ingest/lexical/run.py` lines 183 to 203 queries slug-style
strings (`{source:'macula-hebrew'}`, `{source:'macula-greek-sblgnt'}`,
`{source:'morphgnt-sblgnt'}`, `[:CROSS_REF {source:'openbible'}]`,
`[:CROSS_REF {source:'tsk'}]`). NONE of those match what the adapters emit
(`MACULA-Hebrew`, `MACULA-Greek-SBLGNT`, `MorphGNT-SBLGNT`,
`OPENBIBLE_CROSS_REF`, `CROSS_REF {source:'TSK'}`). The count gate in Section
1 uses the adapter-authoritative `SOURCE_SLUG` strings. The run.py
`--verify-only` block must NOT be used as the gate; flagged not resolved.

---

## SECTION 1: Count gate table

One row per source. The `source` property value column is the verbatim
`SOURCE_SLUG` constant of the adapter (authoritative over phase_02 prose and
over the stale run.py verify block). Tolerance is stated in absolute terms.

Tier policy from `tools/expected_counts.json`:

- Tier A: `tolerance = 0`. `pass = (live == expected)` exactly.
- Tier B: `tolerance_relative = 0.02`, `tolerance_absolute_cap_records = 1000`.
  `pass = abs(live - expected) <= min(ceil(0.02*expected), 1000)`. Where the
  file states an explicit `min`/`max` envelope, the envelope is authoritative
  and `pass = (min <= live <= max)`.
- Tier C: `tolerance_relative = 0.05`. For the three procurement placeholders
  `expected_count` is `null`: there is NO numeric gate; assert only the
  Section 2 acceptance-Cypher `> 0` shape (contract-sanctioned placeholder
  slice, legitimate).

| # | Source name | Adapter file | Primary node label + exact `source` property | Tier | Expected (or min/max) | Tolerance rule (absolute) | Concrete count Cypher | Compare-to literal |
|---|---|---|---|---|---|---|---|---|
| 1 | OSHB-morphology | `ingest/lexical/oshb.py` | `Word {source:'OSHB-morphology'}` | A | 305507 (min 305507, max 305507) | exact: live == 305507 | `MATCH (n:Word {source:'OSHB-morphology'}) RETURN count(n) AS n` | 305507 |
| 2 | MACULA-Hebrew | `ingest/lexical/macula_hebrew.py` | `MaculaToken` enrichment; node count gate on `Word {source:'OSHB-morphology'}` carrying enrichment is an edge check (see note A). Catalog record_unit is morpheme; the morpheme floor is OSHB. expected_count 475911 is the MACULA-Hebrew morpheme element count. Count `MaculaToken` nodes: `MaculaToken` carries no per-source slug distinct from MACULA; assert against the MACULA-Hebrew morpheme count. | A | 475911 (min 475911, max 475911) | exact: live == 475911 | `MATCH (n:MaculaToken) RETURN count(n) AS n` | 475911 |
| 3 | MACULA-Greek-Nestle1904 | `ingest/lexical/macula_greek.py` | `Word {source:'MACULA-Greek-Nestle1904'}` | A | 137779 (min 137779, max 137779) | exact: live == 137779 | `MATCH (n:Word {source:'MACULA-Greek-Nestle1904'}) RETURN count(n) AS n` | 137779 |
| 4 | MACULA-Greek-SBLGNT | `ingest/lexical/macula_greek.py` | `Word {source:'MACULA-Greek-SBLGNT'}` | A | 137741 (min 137741, max 137741) | exact: live == 137741 | `MATCH (n:Word {source:'MACULA-Greek-SBLGNT'}) RETURN count(n) AS n` | 137741 |
| 5 | MorphGNT-SBLGNT | `ingest/lexical/morphgnt.py` | `Word {source:'MorphGNT-SBLGNT'}` | A | 137554 (min 137554, max 137554) | exact: live == 137554 | `MATCH (n:Word {source:'MorphGNT-SBLGNT'}) RETURN count(n) AS n` | 137554 |
| 6 | STEPBible-TAHOT | `ingest/lexical/stepbible_tahot.py` | `TaggedToken {source:'STEPBible-TAHOT'}` | A | 283721 (min 283721, max 283721) | exact: live == 283721 | `MATCH (n:TaggedToken {source:'STEPBible-TAHOT'}) RETURN count(n) AS n` | 283721 |
| 7 | STEPBible-TAGNT | `ingest/lexical/stepbible_tagnt.py` | `TaggedToken {source:'STEPBible-TAGNT'}` | A | 142096 (min 142096, max 142096) | exact: live == 142096 | `MATCH (n:TaggedToken {source:'STEPBible-TAGNT'}) RETURN count(n) AS n` | 142096 |
| 8 | STEPBible-TVTMS | `ingest/lexical/stepbible_tvtms.py` | `VersificationRule {source:'STEPBible-TVTMS'}` | A | 1308 (min 1308, max 1308) | exact: live == 1308 | `MATCH (n:VersificationRule {source:'STEPBible-TVTMS'}) RETURN count(n) AS n` | 1308 |
| 9 | STEPBible-TBESH | `ingest/lexical/stepbible_tbesh.py` | `BriefLexEntry {source:'STEPBible-TBESH', language:'hebrew'}` | A | 11682 (min 11682, max 11682) | exact: live == 11682 | `MATCH (n:BriefLexEntry {source:'STEPBible-TBESH', language:'hebrew'}) RETURN count(n) AS n` | 11682 |
| 10 | STEPBible-TBESG | `ingest/lexical/stepbible_tbesg.py` | `BriefLexEntry {source:'STEPBible-TBESG', language:'greek'}` | A | 11035 (min 11035, max 11035) | exact: live == 11035 | `MATCH (n:BriefLexEntry {source:'STEPBible-TBESG', language:'greek'}) RETURN count(n) AS n` | 11035 |
| 11 | STEPBible-TFLSJ | `ingest/lexical/stepbible_tflsj.py` | `LsjEntry {source:'STEPBible-TFLSJ'}` | A | 11034 (min 11034, max 11034) | exact: live == 11034 | `MATCH (n:LsjEntry {source:'STEPBible-TFLSJ'}) RETURN count(n) AS n` | 11034 |
| 12 | STEPBible-morph-codes | `ingest/lexical/stepbible_morph_codes.py` | `MorphCode {source:'STEPBible-morph-codes'}` | A | 2782 (min 2782, max 2782) | exact: live == 2782 | `MATCH (n:MorphCode {source:'STEPBible-morph-codes'}) RETURN count(n) AS n` | 2782 |
| 13 | STEPBible-proper-nouns | `ingest/lexical/stepbible_proper_nouns.py` | `ProperNoun {source:'STEPBible-proper-nouns'}` | A | 5468 (min 5468, max 5468) | exact: live == 5468 | `MATCH (n:ProperNoun {source:'STEPBible-proper-nouns'}) RETURN count(n) AS n` | 5468 |
| 14 | STEPBible-TTESV | `ingest/lexical/stepbible_ttesv.py` | `TaggedToken {source:'STEPBible-TTESV'}` | A | 31127 (min 31127, max 31127) | exact: live == 31127 | `MATCH (n:TaggedToken {source:'STEPBible-TTESV'}) RETURN count(n) AS n` | 31127 |
| 15 | OpenBible-cross-refs | `ingest/lexical/openbible.py` | edge `OPENBIBLE_CROSS_REF`; the catalog source-row gate is the edge count (node-less adapter). `source` property is `'OpenBible-cross-refs'` on the edge | A | 344799 (min 344799, max 344799) | exact: live == 344799 | `MATCH ()-[r:OPENBIBLE_CROSS_REF {source:'OpenBible-cross-refs'}]->() RETURN count(r) AS n` | 344799 |
| 16 | TSK | `ingest/lexical/tsk.py` | `CrossRef {source:'TSK'}` | A | 63682 (min 63682, max 63682) | exact: live == 63682 | `MATCH (n:CrossRef {source:'TSK'}) RETURN count(n) AS n` | 63682 |
| 17 | Theographic-Bible-Metadata | `ingest/lexical/theographic.py` | projected-entity set, all `{source:'Theographic-Bible-Metadata'}`: `Person` + `Place` + `Event` + `Group` + `Tribe` + derived `Period` | A | 4849 (min 4849, max 4849) | exact: live == 4849 (sum of the six labels) | `MATCH (n) WHERE n.source='Theographic-Bible-Metadata' AND (n:Person OR n:Place OR n:Event OR n:Group OR n:Tribe OR n:Period) RETURN count(n) AS n` | 4849 |
| 18 | ETCBC-BHSA | `ingest/lexical/bhsa.py` | `BhsaWord {source:'ETCBC-BHSA'}` | A | 426590 (min 426590, max 426590) | exact: live == 426590 | `MATCH (n:BhsaWord {source:'ETCBC-BHSA'}) RETURN count(n) AS n` | 426590 |
| 19 | ETCBC-parallels | `ingest/lexical/etcbc_parallels.py` | edge `PARALLEL_OF {source:'ETCBC-parallels'}` (node-less adapter; gate is the edge count) | A | 8246 (min 8246, max 8246) | exact: live == 8246 | `MATCH ()-[r:PARALLEL_OF {source:'ETCBC-parallels'}]->() RETURN count(r) AS n` | 8246 |
| 20 | ETCBC-phono | `ingest/lexical/etcbc_phono.py` | `BhsaWord` with non-null `phono` (no new node; enrichment property; `source` provenance `'ETCBC-phono'` is not stamped on BhsaWord, it enriches the BHSA node) | A | 426590 (min 426590, max 426590) | exact: live == 426590 | `MATCH (n:BhsaWord) WHERE n.phono IS NOT NULL AND trim(toString(n.phono)) <> "" RETURN count(n) AS n` | 426590 |
| 21 | open-cbgm-3-john | `ingest/lexical/open_cbgm_3_john.py` | node-only sum `{source:'open-cbgm-3-john'}`: `Witness` + `VariantUnit` + `Reading` | B | 728 (explicit envelope min 700, max 760) | envelope: 700 <= live <= 760 | `MATCH (n) WHERE n.source='open-cbgm-3-john' AND (n:Witness OR n:VariantUnit OR n:Reading) RETURN count(n) AS n` | 728 (pass band 700..760) |
| 22 | peshitta | `ingest/lexical/peshitta.py` | `SyriacWord {source:'peshitta'}` | C | null (procurement placeholder) | NO numeric gate. Contract-sanctioned placeholder slice. Assert only the Section 2 acceptance Cypher returns true (count > 0). Locked into a follow-on baseline commit at first ingest. | `MATCH (n:SyriacWord {source:'peshitta'}) RETURN count(n) AS n` | shape only: n > 0 (no fixed literal) |
| 23 | vulgate-clementine | `ingest/lexical/vulgate_clementine.py` | `VulgateVerse {source:'vulgate-clementine'}` | C | null (procurement placeholder) | NO numeric gate. Contract-sanctioned placeholder slice. Assert only the Section 2 acceptance Cypher returns true (count > 0). | `MATCH (n:VulgateVerse {source:'vulgate-clementine'}) RETURN count(n) AS n` | shape only: n > 0 (no fixed literal) |
| 24 | coptic-scriptorium | `ingest/lexical/coptic_scriptorium.py` | `CopticWord {source:'coptic-scriptorium'}` | C | null (procurement placeholder) | NO numeric gate. Contract-sanctioned placeholder slice. Assert only the Section 2 acceptance Cypher returns true (count > 0). | `MATCH (n:CopticWord {source:'coptic-scriptorium'}) RETURN count(n) AS n` | shape only: n > 0 (no fixed literal) |

Row count: 24 (the 20 in-scope adapters as enumerated in expected_counts.json
`sources`, plus the 3 procurement placeholders, plus open-cbgm; note
MACULA-Greek is one adapter file emitting two source rows, Nestle1904 and
SBLGNT, so 23 adapter files map to 24 catalog source rows).

Note A (MACULA-Hebrew): `macula_hebrew.py` emits `MaculaToken` enrichment
nodes and `HAS_MACULA_ENRICHMENT` edges from `Word {source:'OSHB-morphology'}`;
it does NOT stamp a distinct `source` slug onto a primary Word label of its
own. Its catalog `record_unit` is `morpheme` with expected 475911. The
`MaculaToken` node count is the cleanest live signal for the 475911 morpheme
enumeration; if `MaculaToken` carries `source='MACULA-Hebrew'` in the live
graph, prefer `MATCH (n:MaculaToken {source:'MACULA-Hebrew'}) RETURN count(n)`.
This is flagged as open item (Section 5, item 4): the adapter docstring
asserts `source='MACULA-Hebrew'` on Lemma/GreekLemma it produces but the
`MaculaToken` enrichment node's `source` property is not unambiguously stated
in the contract; the count query above is label-only as the safe form.

Reconciled tier-A targets locked in (explicit, from expected_counts.json
post [SCHEMA-REVISION] + AUDIT_phase_d_preflight_verification.md final GO):

- OSHB-morphology `Word` = 305507
- STEPBible-TAHOT `TaggedToken` = 283721 (audit GO baseline, NOT 283704 and
  NOT 283734; 283734 raw ref-rows minus exactly 13 faithful empty-Strong
  =Q(K) predicate drops == 283721 distinct == 283721 emitted, zero residual
  collisions, per docs/AUDIT_phase_d_preflight_verification.md)
- STEPBible-TAGNT `TaggedToken` = 142096
- STEPBible-TTESV `TaggedToken` = 31127
- STEPBible-proper-nouns `ProperNoun` = 5468
- Theographic projected-entity sum (Person+Place+Event+Group+Tribe+Period) = 4849
- open-cbgm-3-john node-only (Witness+VariantUnit+Reading) = 728 within 700..760 (tier B explicit envelope)

Procurement placeholders flagged (no count gate, shape-only):
peshitta, vulgate-clementine, coptic-scriptorium. Tier C, `expected_count`
null, contract-sanctioned placeholder slice. Their record count is
established at first ingest run and locked into a follow-on baseline commit;
Phase D asserts only the acceptance-Cypher `> 0` shape, never a fixed count.

---

## SECTION 2: Per-adapter acceptance Cypher (verbatim from phase_02)

Each block is copied verbatim from `docs/implementation_phases/phase_02_lexical_ingest.md`.
The pass condition is the final boolean column the query returns; it MUST be
true. Cross-adapter-join dependencies are flagged: those blocks may only be
evaluated AFTER the full ingest completes (not per-group), because the
endpoint they traverse to is written by a different adapter.

### 1. OSHB-morphology (phase_02 step 1). Dependency: none.
```cypher
MATCH (w:Word {source: 'OSHB-morphology'})
OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
WITH count(w) AS words, count(m) AS morphs
RETURN words, morphs, morphs >= words
```
Pass: third column `morphs >= words` is true and words > 0.

### 2. MACULA-Hebrew (phase_02 step 2). CROSS-ADAPTER JOIN: needs OSHB Words. Evaluate after full ingest.
```cypher
MATCH (w:Word {source: 'OSHB-morphology'})-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
WITH count(w) AS aligned
RETURN aligned, aligned > 0
```
Pass: `aligned > 0` is true.

### 3. MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT (phase_02 step 3). Dependency: none.
```cypher
MATCH (w:Word)
WHERE w.source IN ['MACULA-Greek-Nestle1904', 'MACULA-Greek-SBLGNT']
  AND w.ln IS NOT NULL
WITH count(w) AS with_ln
RETURN with_ln, with_ln > 0
```
Pass: `with_ln > 0` is true.

### 4. MorphGNT-SBLGNT (phase_02 step 4). CROSS-ADAPTER JOIN: PARSE_OF needs MACULA-Greek-SBLGNT Words. Evaluate after full ingest.
```cypher
MATCH (w:Word {source: 'MorphGNT-SBLGNT'})-[:PARSE_OF]->(g:Word {source: 'MACULA-Greek-SBLGNT'})
WITH count(w) AS pairs
RETURN pairs, pairs > 0
```
Pass: `pairs > 0` is true.

### 5. STEPBible-TAHOT (phase_02 step 5). Dependency: Verse, Lemma from Group 1 (but acceptance query is node-local).
```cypher
MATCH (t:TaggedToken {source: 'STEPBible-TAHOT'})
WHERE t.strong IS NOT NULL AND t.morph IS NOT NULL
WITH count(t) AS tokens
RETURN tokens, tokens > 0
```
Pass: `tokens > 0` is true.

### 6. STEPBible-TAGNT (phase_02 step 6). Dependency: Verse, GreekLemma from Group 1 (acceptance query node-local).
```cypher
MATCH (t:TaggedToken {source: 'STEPBible-TAGNT'})
WHERE size(t.meaning_variants) >= 0
WITH count(t) AS tokens
RETURN tokens, tokens > 0
```
Pass: `tokens > 0` is true.

### 7. STEPBible-TVTMS (phase_02 step 7). Dependency: none.
```cypher
MATCH (r:VersificationRule {source: 'STEPBible-TVTMS'})
WHERE r.rule_type IS NOT NULL
WITH count(r) AS rules
RETURN rules, rules > 0
```
Pass: `rules > 0` is true.

### 8. STEPBible-TBESH (phase_02 step 8). Dependency: Lemma from Group 1 (acceptance query node-local).
```cypher
MATCH (l:BriefLexEntry {source: 'STEPBible-TBESH', language: 'hebrew'})
WHERE l.strong_disambig IS NOT NULL AND l.definition IS NOT NULL
WITH count(l) AS entries
RETURN entries, entries > 0
```
Pass: `entries > 0` is true.

### 9. STEPBible-TBESG (phase_02 step 9). Dependency: GreekLemma from Group 1 (acceptance query node-local).
```cypher
MATCH (l:BriefLexEntry {source: 'STEPBible-TBESG', language: 'greek'})
WHERE l.greek IS NOT NULL
WITH count(l) AS entries
RETURN entries, entries > 0
```
Pass: `entries > 0` is true.

### 10. STEPBible-TFLSJ (phase_02 step 10). Dependency: GreekLemma from Group 1 (acceptance query node-local).
```cypher
MATCH (e:LsjEntry {source: 'STEPBible-TFLSJ'})
WHERE e.strong IS NOT NULL AND e.lemma IS NOT NULL
WITH count(e) AS entries
RETURN entries, entries > 0
```
Pass: `entries > 0` is true.

### 11. STEPBible-morph-codes (phase_02 step 11). Dependency: none.
```cypher
MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL
WITH count(m) AS codes
RETURN codes, codes > 0
```
Pass: `codes > 0` is true.

### 12. STEPBible-proper-nouns (phase_02 step 12). Dependency: Verse from Group 1 (acceptance query node-local).
```cypher
MATCH (p:ProperNoun {source: 'STEPBible-proper-nouns'})
WHERE p.proper_name_entry IS NOT NULL
WITH count(p) AS names
RETURN names, names > 0
```
Pass: `names > 0` is true.

### 13. STEPBible-TTESV (phase_02 step 13). Dependency: Lemma, GreekLemma, Verse from Group 1 (acceptance query node-local).
```cypher
MATCH (t:TaggedToken {source: 'STEPBible-TTESV'})
WHERE t.license = 'CC-BY-NC-4.0' AND t.redistribute = false
WITH count(t) AS tokens
RETURN tokens, tokens > 0
```
Pass: `tokens > 0` is true.

### 14. ETCBC-BHSA (phase_02 step 14). CROSS-LAYER JOIN within adapter (clause to phrase to word). Dependency: Verse for OSIS join.
```cypher
MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)-[:CONTAINS_WORD]->(w:BhsaWord)
WITH count(DISTINCT w) AS words
RETURN words, words > 0
```
Pass: `words > 0` is true.

### 15. ETCBC-parallels (phase_02 step 15). CROSS-ADAPTER JOIN: needs BHSA BhsaWord nodes. Evaluate after BHSA (step 14).
```cypher
MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord)
WHERE r.similarity IS NOT NULL
WITH count(r) AS pairs
RETURN pairs, pairs > 0
```
Pass: `pairs > 0` is true.

### 16. ETCBC-phono (phase_02 step 16). CROSS-ADAPTER JOIN: enriches BHSA BhsaWord. Evaluate after BHSA (step 14).
```cypher
MATCH (w:BhsaWord)
WHERE w.phono IS NOT NULL
WITH count(w) AS with_phono
RETURN with_phono, with_phono > 0
```
Pass: `with_phono > 0` is true.

### 17. OpenBible-cross-refs (phase_02 step 17). CROSS-ADAPTER JOIN: needs Verse nodes from Group 1. Evaluate after the text floor.
```cypher
MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse)
WHERE r.votes IS NOT NULL
WITH count(r) AS edges
RETURN edges, edges > 0
```
Pass: `edges > 0` is true.

### 18. TSK (phase_02 step 18). CROSS-ADAPTER JOIN: needs Verse nodes from Group 1. Evaluate after the text floor.
```cypher
MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
WHERE a.book_num IS NOT NULL
WITH count(r) AS edges
RETURN edges, edges > 0
```
Pass: `edges > 0` is true.

### 19. Theographic-Bible-Metadata (phase_02 step 19). Dependency: Verse from Group 1 (acceptance query node-local).
```cypher
MATCH (p:Person {source: 'Theographic-Bible-Metadata'})
WHERE p.entity_id IS NOT NULL AND p.display_name IS NOT NULL
WITH count(p) AS persons
RETURN persons, persons > 0
```
Pass: `persons > 0` is true.

### 20. peshitta (phase_02 step 20). Procurement. CROSS-ADAPTER JOIN: needs Verse, TVTMS. Evaluate after Groups 1 and 2.
```cypher
MATCH (s:SyriacWord {source: 'peshitta'})
WHERE s.lex IS NOT NULL AND s.verse_ref IS NOT NULL
WITH count(s) AS covered
RETURN covered, covered > 0
```
Pass: `covered > 0` is true. (This is the only assertion for peshitta;
no count gate.)

### 21. vulgate-clementine (phase_02 step 21). Procurement. CROSS-ADAPTER JOIN: needs TVTMS. Evaluate after Group 2.
```cypher
MATCH (v:VulgateVerse)
WHERE v.text_latin IS NOT NULL AND v.osis IS NOT NULL
WITH count(v) AS verses
RETURN verses, verses > 0
```
Pass: `verses > 0` is true. (Only assertion for vulgate-clementine.)

### 22. coptic-scriptorium (phase_02 step 22). Procurement. CROSS-ADAPTER JOIN: needs Verse, TVTMS. Evaluate after Groups 1 and 2.
```cypher
MATCH (c:CopticWord {source: 'coptic-scriptorium'})
WHERE c.lemma IS NOT NULL AND c.dialect IN ['sahidic', 'bohairic']
WITH count(c) AS coverage
RETURN coverage, coverage > 0
```
Pass: `coverage > 0` is true. (Only assertion for coptic-scriptorium.)

### 23. open-cbgm-3-john (phase_02 step 23). CROSS-ADAPTER JOIN: needs Verse nodes for 3 John from Group 1. Evaluate after the text floor.
```cypher
MATCH (w:Witness)-[:READS_AT]->(rd:Reading)-[:ATTESTED_BY]->(v:VariantUnit)
WHERE v.book = '3John' AND v.chapter = 1 AND v.verse >= 1 AND v.verse <= 15
WITH count(DISTINCT v) AS units
RETURN units, units > 0
```
Pass: `units > 0` is true.

Cross-adapter-join blocks that MUST wait for the full ingest before
evaluation: steps 2 (MACULA-Hebrew), 4 (MorphGNT PARSE_OF), 15
(ETCBC-parallels), 16 (ETCBC-phono), 17 (OpenBible), 18 (TSK), 20 (peshitta),
21 (vulgate), 22 (coptic), 23 (open-cbgm). Steps 1, 3, 5 to 14, 19 are
node-local to their own adapter slice and may be evaluated as soon as that
adapter has run, but the harness runs them all post-ingest for simplicity.

---

## SECTION 3: Per-edge correctness assertions (the FakeDriver-lossy gap)

The Phase C coverage-test FakeDriver is lossy-by-batch on per-edge identity:
it proves cardinality and field presence but does NOT prove that each edge
connects the correct two real endpoints. Per-edge correctness is therefore
UNPROVEN until live-graph assertion. Each assertion below samples K real
edges (K = 50, lower if the population is smaller; for CORRECTOR_OF sample
all), returns BOTH endpoint labels, the key identifying properties of each
endpoint, and any edge property, and states the invariant that must hold.
The point is to prove edge IDENTITY, not cardinality. Set `K` once at the
top of the run; all queries below use a literal 50, replace if needed.

Edge directions and properties were read from the adapter contracts:
PARSE_OF (a)->(b) Word to Word; INSTANCE_OF (a)->(b); IN_VERSE (a)->(b);
HAS_MORPHEME Word->Morpheme; IS_QERE_OF Reading->Word; NAMED_AT
ProperNoun->Verse; HAS_MACULA_ENRICHMENT Word->MaculaToken; CROSS_REF
CrossRef->Verse; OPENBIBLE_CROSS_REF Verse->Verse (votes int);
PARALLEL_OF BhsaWord->BhsaWord (similarity float); CONTAINS_PHRASE
BhsaClause->BhsaPhrase; CONTAINS_WORD BhsaPhrase->BhsaWord; READS_AT
Witness->Reading (variant_unit_id key prop); ATTESTED_BY Reading->VariantUnit;
CORRECTOR_OF Witness->Witness; LEX_FOR BriefLexEntry->Lemma or
BriefLexEntry->GreekLemma; LsjEntry LEX_FOR->GreekLemma.

### 3.1 PARSE_OF (MorphGNT Word -> MACULA-Greek-SBLGNT Word)
```cypher
MATCH (a:Word {source:'MorphGNT-SBLGNT'})-[r:PARSE_OF]->(b:Word {source:'MACULA-Greek-SBLGNT'})
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id, a.ref AS a_ref, a.source AS a_src,
       labels(b) AS b_labels, b.id AS b_id, b.ref AS b_ref, b.source AS b_src,
       type(r) AS rel
```
Invariant: every row has `a_labels` containing `Word`, `a_src` =
'MorphGNT-SBLGNT', `b_labels` containing `Word`, `b_src` =
'MACULA-Greek-SBLGNT', `rel` = 'PARSE_OF', `a_id` and `b_id` both non-null
and distinct, and `a_ref` = `b_ref` (same OSIS verse on both endpoints, since
PARSE_OF aligns a MorphGNT word to its SBLGNT word in the same verse).

### 3.2 INSTANCE_OF (Word/TaggedToken -> Lemma/GreekLemma)
```cypher
MATCH (a)-[r:INSTANCE_OF]->(b)
WHERE (a:Word OR a:TaggedToken OR a:MaculaToken) AND (b:Lemma OR b:GreekLemma)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, coalesce(a.id, a.osis_ref) AS a_key, a.source AS a_src, a.strong AS a_strong,
       labels(b) AS b_labels, coalesce(b.id, b.strong) AS b_key, b.source AS b_src, b.strong AS b_strong,
       type(r) AS rel
```
Invariant: `a_labels` is one of Word/TaggedToken/MaculaToken, `b_labels` is
Lemma or GreekLemma, `rel` = 'INSTANCE_OF', `a_key` and `b_key` non-null, and
the Strong identity resolves: `a_strong` equals `b_strong` (or `b_key`
carries the same Strong the token claims). Endpoints must not be the same
node.

### 3.3 IN_VERSE (token -> Verse)
```cypher
MATCH (a)-[r:IN_VERSE]->(b:Verse)
WHERE a:Word OR a:TaggedToken
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id, a.ref AS a_ref, a.source AS a_src,
       labels(b) AS b_labels, b.osisID AS b_osis, b.book AS b_book, b.chapter AS b_ch, b.verse AS b_v,
       type(r) AS rel
```
Invariant: `b_labels` contains `Verse`, `rel` = 'IN_VERSE', `b_osis`
non-null, and the verse the token claims (`a_ref`) resolves to the Verse
endpoint's `b_osis` (string-equal after OSIS normalization). `a_id` non-null.

### 3.4 HAS_MORPHEME (OSHB Word -> Morpheme), with morphs >= words
```cypher
MATCH (a:Word {source:'OSHB-morphology'})-[r:HAS_MORPHEME]->(b:Morpheme)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id, a.source AS a_src,
       labels(b) AS b_labels, b.id AS b_id, b.strong AS b_strong,
       type(r) AS rel
```
Plus the global cardinality invariant (also asserted in Section 2 step 1):
```cypher
MATCH (w:Word {source:'OSHB-morphology'})
OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
WITH count(DISTINCT w) AS words, count(m) AS morphs
RETURN words, morphs, morphs >= words AS ok
```
Invariant: per-sample `a_labels` Word, `b_labels` Morpheme, `rel` =
'HAS_MORPHEME', both ids non-null, the Morpheme id is prefixed by the parent
Word id (oshb-morph stable-id contains the parent word ref). Global: `ok`
true and `words` > 0.

### 3.5 IS_QERE_OF (OSHB Reading -> Word)
```cypher
MATCH (a:Reading {source:'OSHB-morphology'})-[r:IS_QERE_OF]->(b:Word {source:'OSHB-morphology'})
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.reading_id AS a_rid, a.source AS a_src,
       labels(b) AS b_labels, b.id AS b_id, b.ref AS b_ref,
       type(r) AS rel
```
Invariant: `a_labels` contains `Reading`, `b_labels` contains `Word`, `rel`
= 'IS_QERE_OF', `a_rid` and `b_id` non-null, and the Reading's verse matches
the Word's verse (`a_rid` encodes the same OSIS ref as `b_ref`). Endpoints
distinct.

### 3.6 NAMED_AT (ProperNoun -> Verse)
```cypher
MATCH (a:ProperNoun {source:'STEPBible-proper-nouns'})-[r:NAMED_AT]->(b:Verse)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.proper_name_entry AS a_name, a.first_occurrence AS a_first, a.source AS a_src,
       labels(b) AS b_labels, b.osisID AS b_osis,
       type(r) AS rel
```
Invariant: `a_labels` ProperNoun, `b_labels` Verse, `rel` = 'NAMED_AT',
`a_name` non-null, and `a_first` (the first_occurrence OSIS string) resolves
to the Verse endpoint `b_osis`. Edge is zero-or-one per ProperNoun, so a
sampled edge always has a resolvable first_occurrence.

### 3.7 HAS_MACULA_ENRICHMENT (OSHB Word -> MaculaToken)
```cypher
MATCH (a:Word {source:'OSHB-morphology'})-[r:HAS_MACULA_ENRICHMENT]->(b:MaculaToken)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id, a.ref AS a_ref, a.source AS a_src,
       labels(b) AS b_labels, b.id AS b_id, b.ref AS b_ref,
       type(r) AS rel
```
Invariant: `a_labels` Word with `a_src` = 'OSHB-morphology', `b_labels`
MaculaToken, `rel` = 'HAS_MACULA_ENRICHMENT', both ids non-null, and the
alignment join holds: `a_ref` equals `b_ref` (same OSIS verse; the
enrichment join is by OSIS plus lemma identity per the adapter contract).

### 3.8 CROSS_REF (TSK CrossRef -> Verse)
```cypher
MATCH (a:CrossRef {source:'TSK'})-[r:CROSS_REF {source:'TSK'}]->(b:Verse)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id, a.book_num AS a_bk, a.chapter AS a_ch, a.verse AS a_v,
       labels(b) AS b_labels, b.osisID AS b_osis,
       type(r) AS rel, r.source AS r_src
```
Invariant: `a_labels` CrossRef, `b_labels` Verse, `rel` = 'CROSS_REF',
`r_src` = 'TSK', `a_id` non-null, `a_bk` non-null int, and the target Verse
`b_osis` is a real distinct verse (the expanded reference target, not the
source verse of the CrossRef itself).

### 3.9 OPENBIBLE_CROSS_REF (Verse -> Verse with votes)
```cypher
MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.osisID AS a_osis,
       labels(b) AS b_labels, b.osisID AS b_osis,
       type(r) AS rel, r.votes AS votes, r.source AS r_src
```
Invariant: both endpoints `Verse`, `rel` = 'OPENBIBLE_CROSS_REF', `a_osis`
and `b_osis` non-null and distinct (no self cross-ref), `r_src` =
'OpenBible-cross-refs', `votes` present and integer-typed (votes >= 0 is
valid, votes = 0 is a legitimate retained low-confidence signal per the
adapter contract). Assert `r.votes IS NOT NULL` and
`toInteger(r.votes) = r.votes`.

### 3.10 PARALLEL_OF (BhsaWord -> BhsaWord with similarity)
```cypher
MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.id AS a_id,
       labels(b) AS b_labels, b.id AS b_id,
       type(r) AS rel, r.similarity AS sim, r.source AS r_src
```
Invariant: both endpoints `BhsaWord`, `rel` = 'PARALLEL_OF', `a_id` and
`b_id` non-null and distinct, `r_src` = 'ETCBC-parallels', `sim` present and
float-typed in a sane range. Assert `r.similarity IS NOT NULL` and
`r.similarity = toFloat(r.similarity)` and
`r.similarity >= 0.0 AND r.similarity <= 1.0` (similarity is the
right-hand fragment parsed from the packed target_and_value).

### 3.11 CONTAINS_PHRASE (BhsaClause -> BhsaPhrase) and CONTAINS_WORD (BhsaPhrase -> BhsaWord)
```cypher
MATCH (c:BhsaClause)-[r1:CONTAINS_PHRASE]->(p:BhsaPhrase)-[r2:CONTAINS_WORD]->(w:BhsaWord)
WITH c, p, w, r1, r2 LIMIT 50
RETURN labels(c) AS c_labels, c.id AS c_id,
       labels(p) AS p_labels, p.id AS p_id,
       labels(w) AS w_labels, w.id AS w_id,
       type(r1) AS rel1, type(r2) AS rel2
```
Invariant: `c_labels` BhsaClause, `p_labels` BhsaPhrase, `w_labels`
BhsaWord, `rel1` = 'CONTAINS_PHRASE', `rel2` = 'CONTAINS_WORD', all three ids
non-null and pairwise distinct, and the containment chain is well-formed
(clause to phrase to word, no label crossing). Note: phase_02 edge_counts
uses the name `HAS_CLAUSE` but the BHSA adapter emits the containment chain
as CONTAINS_PHRASE / CONTAINS_WORD; this naming divergence is flagged in
Section 5 item 3. The harness asserts the edges the adapter actually emits.

### 3.12 READS_AT (open-cbgm Witness -> Reading) + ATTESTED_BY (Reading -> VariantUnit)
```cypher
MATCH (w:Witness {source:'open-cbgm-3-john'})-[r1:READS_AT]->(rd:Reading {source:'open-cbgm-3-john'})-[r2:ATTESTED_BY]->(v:VariantUnit {source:'open-cbgm-3-john'})
WITH w, rd, v, r1, r2 LIMIT 50
RETURN labels(w) AS w_labels, w.siglum AS w_sig,
       labels(rd) AS rd_labels, rd.reading_id AS rd_id, rd.variant_unit_id AS rd_vu,
       labels(v) AS v_labels, v.variant_unit_id AS v_vu, v.book AS v_bk, v.chapter AS v_ch, v.verse AS v_v,
       type(r1) AS rel1, r1.variant_unit_id AS r1_vu, type(r2) AS rel2
```
Invariant: `w_labels` Witness, `rd_labels` Reading, `v_labels` VariantUnit,
`rel1` = 'READS_AT', `rel2` = 'ATTESTED_BY', `w_sig` non-null, `rd_id`
non-null, the READS_AT edge property `r1_vu` (variant_unit_id) equals the
Reading's `rd_vu` and the VariantUnit's `v_vu` (the variant-unit identity is
consistent across the edge property and both downstream nodes), and
`v_bk` = '3John', `v_ch` = 1, `v_v` between 1 and 15 inclusive.

### 3.13 CORRECTOR_OF (open-cbgm corrector-hand Witness -> base-hand Witness). Sample ALL (small population, 2 expected).
```cypher
MATCH (a:Witness {source:'open-cbgm-3-john'})-[r:CORRECTOR_OF]->(b:Witness {source:'open-cbgm-3-john'})
RETURN labels(a) AS a_labels, a.siglum AS a_sig,
       labels(b) AS b_labels, b.siglum AS b_sig,
       type(r) AS rel
```
Invariant: every row both endpoints `Witness`, `rel` = 'CORRECTOR_OF',
`a_sig` and `b_sig` non-null and distinct (a corrector hand and its base
hand are distinct Witness nodes, never collapsed into one), and `a_sig` is
the corrector form of `b_sig` (for example `<siglum>C` or `<siglum>*`
relating to the base `<siglum>`). Expected ~2 rows per the audit.

### 3.14 LEX_FOR (BriefLexEntry -> Lemma) and (BriefLexEntry/LsjEntry -> GreekLemma)
TBESH hebrew BriefLexEntry to Lemma:
```cypher
MATCH (a:BriefLexEntry {source:'STEPBible-TBESH', language:'hebrew'})-[r:LEX_FOR]->(b:Lemma)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.strong_disambig AS a_sd, a.base_strong AS a_bs,
       labels(b) AS b_labels, b.strong AS b_strong,
       type(r) AS rel
```
TBESG greek BriefLexEntry to GreekLemma:
```cypher
MATCH (a:BriefLexEntry {source:'STEPBible-TBESG', language:'greek'})-[r:LEX_FOR]->(b:GreekLemma)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.strong_disambig AS a_sd, a.base_strong AS a_bs,
       labels(b) AS b_labels, coalesce(b.id, b.strong) AS b_key,
       type(r) AS rel
```
TFLSJ LsjEntry to GreekLemma:
```cypher
MATCH (a:LsjEntry {source:'STEPBible-TFLSJ'})-[r:LEX_FOR]->(b:GreekLemma)
WITH a, b, r LIMIT 50
RETURN labels(a) AS a_labels, a.strong AS a_strong, a.lemma AS a_lemma,
       labels(b) AS b_labels, coalesce(b.id, b.strong) AS b_key,
       type(r) AS rel
```
Invariant (all three): `a_labels` is BriefLexEntry or LsjEntry, `b_labels`
is Lemma (Hebrew) or GreekLemma (Greek), `rel` = 'LEX_FOR', the base Strong
on the lex entry (`a_bs` / `a_strong`) equals the Strong identity on the
resolved Lemma/GreekLemma (`b_strong` / `b_key`), and endpoints are distinct
nodes. The join is by base_strong so all senses converge on the same Lemma.

Distinct edge types covered in Section 3: 16 (PARSE_OF, INSTANCE_OF,
IN_VERSE, HAS_MORPHEME, IS_QERE_OF, NAMED_AT, HAS_MACULA_ENRICHMENT,
CROSS_REF, OPENBIBLE_CROSS_REF, PARALLEL_OF, CONTAINS_PHRASE, CONTAINS_WORD,
READS_AT, ATTESTED_BY, CORRECTOR_OF, LEX_FOR).

---

## SECTION 4: Gate order and tooling

Run strictly in this sequence the moment the live ingest reports complete.

1. Immutability gate (pure CLI, no Cypher):
   `python tools/check_thresholds_immutable.py`
   MUST exit 0. This asserts the `tools/expected_counts.json` SHA-256 is
   unchanged from the A.4 commit except via a `[SCHEMA-REVISION]` subject.
   If exit != 0, STOP: the catalog moved illegitimately, the entire gate is
   void. Dispatchable to: orchestrator (CLI step), not an auditor agent.

2. Section 1 count gate (PURE CYPHER, dispatchable to an auditor-caste
   agent against the live read-only graph). Run all 24 concrete count
   queries. For each row apply the absolute tolerance rule in the table:
   tier A exact equality, tier B envelope `700 <= live <= 760` for
   open-cbgm, tier C placeholders skipped (shape-only, deferred to step 3).
   Any tier A mismatch is a hard FAIL; record live value, expected, delta.
   No re-running run.py.

3. Section 2 acceptance Cyphers (PURE CYPHER, dispatchable to an
   auditor-caste agent). Run all 23 blocks verbatim. Each returned boolean
   MUST be true. Cross-adapter-join blocks (steps 2, 4, 15, 16, 17, 18, 20,
   21, 22, 23) are only valid here because the full ingest has completed.
   The three procurement placeholders (peshitta 20, vulgate 21, coptic 22)
   are asserted ONLY here (shape `> 0`), since they have no Section 1 count
   gate. No re-running run.py.

4. Section 3 per-edge correctness (PURE CYPHER, dispatchable to an
   auditor-caste agent). Run all sampled-endpoint queries with K = 50
   (CORRECTOR_OF sample all). For each, verify the stated invariant on every
   returned row. Any endpoint-label mismatch, unresolved endpoint id,
   missing or mistyped edge property (similarity not float, votes not int),
   or self-edge where forbidden is a hard FAIL. This is the step that closes
   the FakeDriver-lossy gap; it proves edge IDENTITY not cardinality. No
   re-running run.py.

5. Triangle test (REQUIRES re-running run.py; NOT dispatchable to a
   pure-Cypher auditor agent; orchestrator-driven, reference RESEED_PLAN
   D.3). Sequence:
   a. `python tools/snapshot_counts.py --out p1`  (snapshot the live graph
      after the first ingest; produces the per-row presence-vector sorted
      SHA-256 list and an overall_hash)
   b. Idempotent re-ingest over identical source bytes:
      `python -m ingest.lexical.run --dataset all`  (MERGE-by-stable-id, so
      a second run over the same frozen bytes must not change the graph)
   c. `python tools/snapshot_counts.py --out p2`
   d. Assert `p1.overall_hash == p2.overall_hash` byte-for-byte. Any
      difference means a non-idempotent adapter (stable-id instability or a
      non-deterministic parse) and is a hard FAIL. This mirrors the
      determinism proof already done offline for stepbible_ttesv
      (sha256 6acbc7fb...448ec76) and stepbible_tahot (283721 across two
      runs) in docs/AUDIT_phase_d_preflight_verification.md.

Dispatch summary:
- Pure-Cypher, dispatchable to an auditor-caste agent against the live
  read-only graph: steps 2, 3, 4.
- Orchestrator CLI / requires re-running run.py: step 1 (CLI only) and
  step 5 (re-ingest). Step 5 is the only step that mutates the graph (an
  idempotent re-MERGE) and must be run by the orchestrator, never by a
  read-only auditor agent.

Overall PASS condition: step 1 exit 0 AND every Section 1 tier-A row exact
AND open-cbgm within 700..760 AND every Section 2 boolean true AND every
Section 3 invariant holds on every sampled row AND
p1.overall_hash == p2.overall_hash.

---

## SECTION 5: Inconsistencies found (flagged, NOT resolved)

1. `ingest/lexical/run.py` `--verify-only` block (lines 183 to 203) queries
   stale slug-style `source` strings: `{source:'macula-hebrew'}`,
   `{source:'macula-greek-sblgnt'}`, `{source:'morphgnt-sblgnt'}`,
   `[:CROSS_REF {source:'openbible'}]`, `[:CROSS_REF {source:'tsk'}]`. Every
   adapter's authoritative `SOURCE_SLUG` constant is inventory-name style
   (`MACULA-Hebrew`, `MACULA-Greek-SBLGNT`, `MorphGNT-SBLGNT`,
   `OpenBible-cross-refs` on an `OPENBIBLE_CROSS_REF` edge,
   `CROSS_REF {source:'TSK'}`). The run.py verify block would return 0 for
   every source against the real graph. The Section 1 gate deliberately does
   NOT use run.py `--verify-only`; it uses the adapter `SOURCE_SLUG`
   strings. Also the run.py in-code `EXPECTED_COUNTS` dict (lines 120 to 127)
   carries wide pre-reconciliation ranges (macula_hebrew Word 300000 to
   320000, openbible CrossRef 600000 to 620000, tsk CrossRef 590000 to
   610000) that contradict the reconciled `tools/expected_counts.json`
   (OSHB 305507, OpenBible 344799 edges, TSK 63682 nodes). Flag, do not
   resolve.

2. MACULA-Hebrew catalog `record_unit` is `morpheme` with `expected_count`
   475911, but the adapter emits `MaculaToken` enrichment nodes plus
   `HAS_MACULA_ENRICHMENT` edges off `Word {source:'OSHB-morphology'}` and
   does not stamp its own primary Word source slug. The 475911 is the MACULA
   morpheme element count; the live signal closest to it is the
   `MaculaToken` node count. Whether `MaculaToken` carries
   `source='MACULA-Hebrew'` is not unambiguous in the adapter contract
   (docstring asserts the slug on the Lemma/GreekLemma it produces, line
   113, but is silent on the MaculaToken node `source`). Section 1 row 2
   uses a label-only count as the safe form. Flag as ambiguity, do not
   resolve.

3. Edge-name divergence: `tools/expected_counts.json` edge_counts uses
   `HAS_CLAUSE` and `HAS_PHRASE`, and phase_02 Section "Edge floor" speaks of
   clause/phrase containment, but the ETCBC-BHSA adapter and the phase_02
   step-14 acceptance Cypher emit/traverse `CONTAINS_PHRASE` and
   `CONTAINS_WORD` (clause to phrase to word). There is no `HAS_CLAUSE` /
   `HAS_PHRASE` relationship in the adapter contract. The edge_counts keys
   `HAS_CLAUSE`/`HAS_PHRASE` appear to be node-count proxies for BhsaClause /
   BhsaPhrase, not literal relationship types. Section 3.11 asserts the
   relationships the adapter actually emits. Flag, do not resolve.

4. open-cbgm catalog reconciliation tension: `tools/expected_counts.json`
   sets open-cbgm-3-john `expected_count` 728 with tier B explicit envelope
   min 700 / max 760 and `catalog_source_index: null`.
   `docs/PHASE_D_CATALOG_RECONCILIATION.md` section 6 still describes the
   node-only-vs-node+edge definition as an open architect decision; the
   reconciled file has committed to node-only 728 (Witness + VariantUnit +
   Reading). `docs/AUDIT_phase_d_preflight_verification.md` independently
   reproduced exactly 728 nodes (142 Witness + 116 VariantUnit + 470
   Reading). The harness uses node-only 728 within 700..760 consistent with
   the final reconciled file. The reconciliation doc's "architect to confirm"
   wording is now stale relative to the committed file. Flag, do not resolve.

5. STEPBible-TAHOT triple-number tension across the three reconciliation
   sources: `docs/PHASE_D_CATALOG_RECONCILIATION.md` recommends 283704
   (option b, drop 30 rows). `tools/expected_counts.json` and
   `docs/AUDIT_phase_d_preflight_verification.md` final GO both lock 283721
   (283734 raw minus exactly 13 faithful empty-Strong predicate drops, with
   the 17 =L over =X collapse fixed in commit a277a96 so they are no longer
   dropped). The reconciliation doc predates the a277a96 collapse fix and
   the audit; expected_counts.json post [SCHEMA-REVISION] = 283721 is
   authoritative and is what Section 1 uses. The reconciliation doc's 283704
   recommendation is superseded but still in the doc. Flag, do not resolve.

6. ETCBC-phono has `expected_count` 426590 (equal to BHSA word count) and
   tier A tolerance 0, but the adapter writes no new node and no own `source`
   slug; it sets an optional `phono` property on existing `BhsaWord`. A
   tolerance-0 gate on "BhsaWord with non-null phono == 426590" assumes the
   phono feature is one-to-one with every BHSA word slot. The catalog
   tier_rationale claims exactly this one-to-one keying. Section 1 row 20
   gates on the non-null-phono count == 426590. If even one slot lacks a
   phono value the tier-A 0-tolerance gate fails; this is a known fragility
   of gating an enrichment property at tolerance 0. Flag, do not resolve.

---

End of harness.
