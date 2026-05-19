# Phase D Profile Pre-Flight: Index-Backed Edge MERGE Verification

Auditor caste, READ-ONLY verification against the LIVE lexical Neo4j.
Repo HEAD c0b4b5964cf3b11bbd12ad18150896dea6958f0c on branch main.
Live db: lexical-neo4j (bolt://localhost:7688), partial graph from the
earlier stalled ingest. No writes were made to the graph. The only file
written is this document.

## Verdict

NO-GO.

Eleven of twelve representative edge endpoints across all audited adapters
plan an index-backed seek (NodeUniqueIndexSeek(Locking)). One edge type
fails the gate: the StepBible TAGNT (and by code-shared structure TBESG /
TFLSJ) INSTANCE_OF edge resolves its `(:GreekLemma {strong})` endpoint via
NodeByLabelScan + Filter, NOT an index seek, because the backing index
`greek_lemma_strong` declared in graph/lexical.cypher line 63 was never
created in the live database. A single unindexed endpoint on a ~70k-row
adapter is exactly the planner pathology that stalls a full reseed, so the
relaunch must NOT be committed until that index is created and verified
ONLINE.

The fix is small and isolated (apply the one missing index statement; no
adapter or schema-source change is required because the index is already
in graph/lexical.cypher). Re-run this pre-flight after the index is
created; everything else is GO.

## Live graph snapshot (read-only)

Total nodes: 759,821. Label counts:

| Label | Count |
|---|---|
| Morpheme | 421,224 |
| Word | 305,507 |
| Verse | 23,213 |
| Strong | 8,632 |
| Reading | 1,244 |
| Source | 1 |
| Lemma | 0 |
| GreekLemma | 0 |
| TaggedToken | 0 |
| CrossRef | 0 |
| BhsaWord/BhsaPhrase/BhsaClause | 0 |
| Person/Place/Period/Event/Group/Tribe | 0 |

The graph is the expected oshb-only partial. Producer nodes for the
KEY-* joins (Lemma from macula_hebrew, GreekLemma from macula_greek,
TaggedToken from the stepbible adapters) are NOT yet present. This
pre-flight proves the EXPLAIN operator plan is index-backed on the real
planner and that all backing indexes are ONLINE; full edge-resolution
counts are proven at relaunch when the producer nodes exist.

## Per-edge-type EXPLAIN plan (endpoint operators + backing index)

Representative `$rows` shaped per the adapter row builder. `EXPLAIN`
only, no execution. Plain entries are NodeUniqueIndexSeek(Locking)
against the named UNIQUE constraint unless flagged.

### ingest/lexical/oshb.py

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| HAS_MORPHEME | NodeUniqueIndexSeek(Locking) a:Word(id) | NodeUniqueIndexSeek(Locking) b:Morpheme(id) | INDEX |
| IN_VERSE | NodeUniqueIndexSeek(Locking) a:Word(id) | NodeUniqueIndexSeek(Locking) b:Verse(id) | INDEX |
| INSTANCE_OF (Word-sourced) | NodeUniqueIndexSeek(Locking) a:Word(id) | NodeUniqueIndexSeek(Locking) b:Strong(id) | INDEX |
| INSTANCE_OF (Morpheme-sourced) | NodeUniqueIndexSeek(Locking) a:Morpheme(id) | NodeUniqueIndexSeek(Locking) b:Strong(id) | INDEX |
| IS_QERE_OF | NodeUniqueIndexSeek(Locking) a:Reading(reading_id) | NodeUniqueIndexSeek(Locking) b:Word(id) | INDEX |
| FROM_EDITION | NodeUniqueIndexSeek(Locking) a:Word(id) | NodeUniqueIndexSeek(Locking) b:Source(slug) | INDEX |

The heterogeneous INSTANCE_OF from-side is correctly split by the adapter
into a Word-template and a Morpheme-template; both halves seek their own
constraint. No AllNodesScan, no NodeByLabelScan on any oshb endpoint.

### ingest/lexical/bhsa.py

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| CONTAINS_PHRASE | NodeUniqueIndexSeek(Locking) a:BhsaClause(id) | NodeUniqueIndexSeek(Locking) b:BhsaPhrase(id) | INDEX |
| CONTAINS_WORD | NodeUniqueIndexSeek(Locking) a:BhsaPhrase(id) | NodeUniqueIndexSeek(Locking) b:BhsaWord(id) | INDEX |
| IN_VERSE | NodeUniqueIndexSeek(Locking) a:BhsaWord(id) | NodeUniqueIndexSeek(Locking) b:Verse(id) | INDEX |

### ingest/lexical/theographic.py (6-label MENTIONS/FROM_EDITION dispatch)

The adapter dispatches one single-label template per source label. Person
and Place were profiled as MENTIONS representatives, Tribe as a
FROM_EDITION representative; the remaining labels (Period, Event, Group)
each carry an ONLINE entity_id constraint identical in shape, so the
planner picks the same NodeUniqueIndexSeek for every label.

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| MENTIONS (Person) | NodeUniqueIndexSeek(Locking) a:Person(entity_id) | NodeUniqueIndexSeek(Locking) b:Verse(osisID) | INDEX |
| MENTIONS (Place) | NodeUniqueIndexSeek(Locking) a:Place(entity_id) | NodeUniqueIndexSeek(Locking) b:Verse(osisID) | INDEX |
| FROM_EDITION (Tribe) | NodeUniqueIndexSeek(Locking) a:Tribe(entity_id) | NodeUniqueIndexSeek(Locking) b:Source(slug) | INDEX |

A single unlabeled `MATCH (a {entity_id: ...})` would have forced an
AllNodesScan; the per-label dispatch is confirmed to defeat that.

### ingest/lexical/stepbible_tahot.py (Decision 18 KEY-* join)

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| INSTANCE_OF -> :Lemma {strong} | NodeUniqueIndexSeek(Locking) a:TaggedToken(id) | NodeUniqueIndexSeek(Locking) b:Lemma(strong) | INDEX |
| IN_VERSE -> :Verse {osisID} | NodeUniqueIndexSeek(Locking) a:TaggedToken(id) | NodeUniqueIndexSeek(Locking) b:Verse(osisID) | INDEX |

Decision-18 Hebrew join is index-backed: the seek uses the
`lemma_strong` uniqueness constraint (UNIQUE b:Lemma(strong)). tahot
IN_VERSE now seeks `verse_osisID` (UNIQUE b:Verse(osisID)) as required.

### ingest/lexical/stepbible_tagnt.py (Decision 18 KEY-* join) -- FAIL

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| INSTANCE_OF -> :GreekLemma {strong} | NodeUniqueIndexSeek(Locking) a:TaggedToken(id) | NodeByLabelScan b:GreekLemma + Filter(b.strong = row.to_id) | NOT INDEX-BACKED |
| IN_VERSE -> :Verse {osisID} | NodeUniqueIndexSeek(Locking) a:TaggedToken(id) | NodeUniqueIndexSeek(Locking) b:Verse(osisID) | INDEX |

Full plan of the failing edge (EXPLAIN, exact cypher from
stepbible_tagnt.py `_MERGE_INSTANCE_OF`):

```
UNWIND $rows AS row
MATCH (a:`TaggedToken` {id: row.from_id}), (b:`GreekLemma` {strong: row.to_id})
MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges
```

```
+ProduceResults
+EagerAggregation     count(r) AS edges
+Apply
| +LockingMerge       CREATE (a)-[r:INSTANCE_OF]->(b), LOCK(a, b)
| +Expand(Into)       (a)-[r:INSTANCE_OF]->(b)
| +Argument           a, b
+Apply
| +CartesianProduct
| | +Filter           b.strong = row.to_id          <-- post-scan filter
| | +NodeByLabelScan  b:GreekLemma                   <-- NO INDEX SEEK
| +NodeUniqueIndexSeek(Locking)  UNIQUE a:TaggedToken(id) WHERE id = row.from_id
+Unwind               $rows AS row
```

The `b:GreekLemma` endpoint resolves with NodeByLabelScan + Filter, not a
seek. This is the NO-GO trigger. The same `_MERGE_INSTANCE_OF` matching
`(:GreekLemma {strong})` pattern is shared by the tbesg and tflsj
StepBible Greek adapters, so all three Greek adapters carry this stall.

Root cause: graph/lexical.cypher line 63 declares

```
CREATE INDEX greek_lemma_strong IF NOT EXISTS FOR (g:GreekLemma) ON (g.strong)
```

a deliberately NON-unique RANGE index (Decision 18: Greek strongs are not
unique across lemma senses, so there is no backing uniqueness constraint
and the plain index is required). That index statement was never applied
to the live lexical-neo4j instance. SHOW INDEXES on the live db returns
only `greek_lemma_id` for the GreekLemma label; there is no index on
GreekLemma(strong). With GreekLemma node count currently 0 the planner has
no index to seek and falls back to NodeByLabelScan; at relaunch with a
populated GreekLemma set this becomes a full label scan + filter on every
INSTANCE_OF batch (~70k rows per Greek adapter), the precise pathology the
Phase D perf fix exists to eliminate. Contrast: the Hebrew side
(`lemma_strong`) IS a uniqueness constraint, which auto-provides its
backing index, which is why tahot INSTANCE_OF seeks correctly and tagnt
does not. The fix is to create the missing `greek_lemma_strong` index
(already specified in graph/lexical.cypher; no source change needed) and
re-verify it ONLINE before relaunch.

### ingest/lexical/tsk.py

| Edge | from endpoint | to endpoint | Verdict |
|---|---|---|---|
| CROSS_REF | NodeUniqueIndexSeek(Locking) a:CrossRef(id) | NodeUniqueIndexSeek(Locking) b:Verse(osisID) | INDEX |

## Index-online table (backing indexes/constraints the fix relies on)

All checked via SHOW INDEXES / SHOW CONSTRAINTS on the live db.

| Backing object | Label/Type | Property | State | Used by |
|---|---|---|---|---|
| lemma_strong (UNIQUENESS) | Lemma | strong | ONLINE 100% | tahot INSTANCE_OF (Decision 18 Hebrew) |
| greek_lemma_strong (RANGE INDEX) | GreekLemma | strong | MISSING | tagnt/tbesg/tflsj INSTANCE_OF (Decision 18 Greek) |
| greek_lemma_id (UNIQUENESS) | GreekLemma | id | ONLINE 100% | (GreekLemma id seek; not the strong join key) |
| word_id (UNIQUENESS) | Word | id | ONLINE 100% | oshb edges |
| morpheme_id (UNIQUENESS) | Morpheme | id | ONLINE 100% | oshb HAS_MORPHEME |
| verse_id (UNIQUENESS) | Verse | id | ONLINE 100% | oshb/bhsa IN_VERSE |
| verse_osisID (UNIQUENESS) | Verse | osisID | ONLINE 100% | tahot/tagnt IN_VERSE, theographic MENTIONS, tsk CROSS_REF |
| strong_id (UNIQUENESS) | Strong | id | ONLINE 100% | oshb INSTANCE_OF |
| reading_id (UNIQUENESS) | Reading | reading_id | ONLINE 100% | oshb IS_QERE_OF |
| source_slug (UNIQUENESS) | Source | slug | ONLINE 100% | all FROM_EDITION |
| tagged_token_id (UNIQUENESS) | TaggedToken | id | ONLINE 100% | tahot/tagnt edges |
| crossref_id (UNIQUENESS) | CrossRef | id | ONLINE 100% | tsk CROSS_REF |
| bhsa_word_id (UNIQUENESS) | BhsaWord | id | ONLINE 100% | bhsa edges |
| bhsa_phrase_id (UNIQUENESS) | BhsaPhrase | id | ONLINE 100% | bhsa edges |
| bhsa_clause_id (UNIQUENESS) | BhsaClause | id | ONLINE 100% | bhsa CONTAINS_PHRASE |
| person_id (UNIQUENESS) | Person | entity_id | ONLINE 100% | theographic |
| place_id (UNIQUENESS) | Place | entity_id | ONLINE 100% | theographic |
| period_id (UNIQUENESS) | Period | entity_id | ONLINE 100% | theographic |
| event_id (UNIQUENESS) | Event | entity_id | ONLINE 100% | theographic |
| group_id (UNIQUENESS) | Group | entity_id | ONLINE 100% | theographic |
| tribe_id (UNIQUENESS) | Tribe | entity_id | ONLINE 100% | theographic |
| witness_siglum (UNIQUENESS) | Witness | siglum | ONLINE 100% | (witness adapters) |
| variant_unit_id (UNIQUENESS) | VariantUnit | variant_unit_id | ONLINE 100% | (variant adapters) |
| reading_variant_unit (RANGE) | Reading | variant_unit_id | ONLINE 100% | (witness readings) |
| brief_lex_entry_id (UNIQUENESS) | BriefLexEntry | strong_disambig | ONLINE 100% | (brief lexicon) |

Every backing object the audited edge set depends on is ONLINE and
POPULATED at 100% EXCEPT `greek_lemma_strong`, which is entirely absent
from the live database. No object is in a non-ONLINE / partially-populated
state; the single failure is a missing-index failure, not a
stale-population failure.

## Spot-check resolvability (data that exists: oshb partial)

Real ids sampled from the live graph, then resolved via the labeled+keyed
MATCH the relaunch will use. Each returned the real node, proving the
labeled MATCH binds real nodes (the relaunch will form the edge).

| Endpoint pattern | Sampled id | Resolved |
|---|---|---|
| (a:Word {id}) | oshb:1Chr.1.1.w01 | yes |
| (b:Morpheme {id}) | oshb-morph:1Chr.1.1.w01.m01 | yes |
| (b:Verse {id}) | verse:1Chr.1.1 | yes |
| (b:Strong {id}) | H0121 | yes |
| (a:Reading {reading_id}) | oshb-reading:1Chr.1.11.w04.qere | yes |
| (b:Source {slug}) | OSHB-morphology | yes |

EXPLAIN of the labeled Word lookup confirms NodeUniqueIndexSeek on
`a:Word(id)` for a literal id, not a scan.

KEY-* edge resolution counts (tahot -> :Lemma, tagnt -> :GreekLemma)
CANNOT be fully proven here because the producer nodes are absent
(macula_hebrew / macula_greek not yet ingested; Lemma=0, GreekLemma=0,
TaggedToken=0). The structural EXPLAIN plan plus index-online proof is the
pre-flight gate; full resolution is proven at relaunch when producers
exist. This limitation does NOT mask the tagnt failure: the failure is a
planner/operator failure (NodeByLabelScan vs seek) and a missing-index
fact, both observable now independent of node population.

## GO / NO-GO

NO-GO for committing to a full relaunch in the current state.

Blocking item (must be cleared before relaunch):

1. Create the `greek_lemma_strong` RANGE index on GreekLemma(strong)
   (already specified verbatim at graph/lexical.cypher line 63;
   `CREATE INDEX greek_lemma_strong IF NOT EXISTS FOR (g:GreekLemma) ON
   (g.strong)`). Then SHOW INDEXES must report it ONLINE 100%, and a
   re-run of the tagnt INSTANCE_OF EXPLAIN must show
   NodeIndexSeek on b:GreekLemma(strong) instead of NodeByLabelScan +
   Filter. The same fix clears tbesg and tflsj, which share the
   `(:GreekLemma {strong})` match pattern.

Once that single index is ONLINE and the tagnt EXPLAIN re-verifies as a
seek, every audited representative edge is index-backed on the live
planner and the integrated perf+key fix is safe to commit to a full
relaunch. No adapter code, schema source, or test change is required;
graph/lexical.cypher already contains the correct statement, it simply
was not applied to the live instance.
