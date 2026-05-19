# AUDIT: Phase D.4 Count Gate (live lexical Neo4j vs reconciled tools/expected_counts.json)

Caste: auditor. READ-ONLY. Branch main, HEAD ~979b00b. Live lexical-neo4j queried via
`docker exec lexical-neo4j cypher-shell` with the bolt password from `.env`. Pass-1
reseed log: `tmp/phase_d/pass1_relaunch4.log` (all 23 adapters, 0 Traceback).

## 1. Immutability gate

`python tools/check_thresholds_immutable.py`

```
OK: target_sha=9047e40eb291 baseline_sha=9047e40eb291
EXIT_CODE=0
```

PASS. The expected_counts.json SHA matches the A.4 baseline; the reconciled catalog
([SCHEMA-REVISION] #1/#2/#3) is the immutable contract this audit verifies against.

## 2. Per-source node count table

Method: for each source the authoritative count query is the phase_02 acceptance
Cypher canonicalized to `MATCH (n:<Label> {source:'<slug>'}) RETURN count(n)` against
the LIVE graph, compared to `sources{}.expected_count` at the source tier tolerance.
"Faithful target" = the adapter's own deterministic emit per
`docs/PHASE_D_TIERA_PREVERIFICATION.md` and `tmp/phase_d/pass1_relaunch4.log`.

| Source | Label / slug | Tier | Catalog expected | Live actual | Tolerance | Result |
|---|---|---|---|---|---|---|
| MACULA-Hebrew | MaculaToken / MACULA-Hebrew | A | 475911 | 475911 | 0 | PASS |
| MACULA-Greek-Nestle1904 | Word / MACULA-Greek-Nestle1904 | A | 137779 | 137779 | 0 | PASS |
| MACULA-Greek-SBLGNT | Word / MACULA-Greek-SBLGNT | A | 137741 | 137741 | 0 | PASS |
| MorphGNT-SBLGNT | Word / MorphGNT-SBLGNT | A | 137554 | 137554 | 0 | PASS |
| OSHB-morphology | Word / OSHB-morphology | A | 305507 | 305507 | 0 | PASS |
| STEPBible-TAHOT | TaggedToken / STEPBible-TAHOT | A | 283721 | 283721 | 0 | PASS |
| STEPBible-TAGNT | TaggedToken / STEPBible-TAGNT | A | 142096 | 142096 | 0 | PASS |
| STEPBible-TVTMS | VersificationRule / STEPBible-TVTMS | A | 1308 | 1300 | 0 | FAIL |
| STEPBible-TBESH | BriefLexEntry / STEPBible-TBESH | A | 11682 | 11682 | 0 | PASS |
| STEPBible-TBESG | BriefLexEntry / STEPBible-TBESG | A | 11035 | 11035 | 0 | PASS |
| STEPBible-TFLSJ | LsjEntry / STEPBible-TFLSJ | A | 9488 | 9488 | 0 | PASS |
| STEPBible-morph-codes | MorphCode / STEPBible-morph-codes | A | 2675 | 2675 | 0 | PASS |
| STEPBible-proper-nouns | ProperNoun / STEPBible-proper-nouns | A | 5468 | 5468 | 0 | PASS |
| STEPBible-TTESV | TaggedToken / STEPBible-TTESV | A | 31127 | 31127 | 0 | PASS |
| OpenBible-cross-refs | OPENBIBLE_CROSS_REF edge | A | 344799 | 139829 | 0 | FAIL |
| TSK | CrossRef / TSK | A | 63682 | 63682 | 0 | PASS |
| Theographic-Bible-Metadata | projected-entity / Theographic-Bible-Metadata | A | 4849 | 4849 | 0 | PASS |
| ETCBC-BHSA | BhsaWord / ETCBC-BHSA | A | 426590 | 426590 | 0 | PASS |
| ETCBC-parallels | PARALLEL_OF edge | A | 5914 | 0 | 0 | FAIL |
| ETCBC-phono | BhsaWord.phono non-null | A | 420166 | 420166 | 0 | PASS |
| open-cbgm-3-john | cbgm_node (Witness+VariantUnit+Reading) | B | 728 | 728 | [700,760] | PASS |
| peshitta | SyriacWord shape >0 | C | null (placeholder) | 3 (>0) | n/a | PASS (shape) |
| vulgate-clementine | VulgateVerse shape >0 | C | null (placeholder) | 3 (>0) | n/a | PASS (shape) |
| coptic-scriptorium | CopticWord shape >0 | C | null (placeholder) | 4 (>0) | n/a | PASS (shape) |

Decompositions verified:
- Theographic projected-entity 4849 = Person 3067 + Place 1274 + Event 450 + Group 11
  + Tribe 12 + Period 35 = 4849. Exact match to catalog record_unit.
- open-cbgm cbgm_node 728 = Witness 142 + VariantUnit 116 + Reading 470 = 728. Inside
  the tier-B [700,760] envelope, exact to the catalog's central 728.
- MACULA-Hebrew: catalog record_unit is "morpheme" with expected_count 475911. The live
  materialized node label is MaculaToken (0 Morpheme {source:'MACULA-Hebrew'} nodes by
  design; the adapter emits MaculaToken enrichment per phase_02 section 2 and Decision
  4). Live MaculaToken = 475911 = catalog 475911 exactly. The record_unit label
  ("morpheme") is a naming artifact in the catalog text; the count is exact and the
  adapter is faithful. Not a defect (no count delta). Flagged for catalog text clarity
  only, not a count FAIL.
- MACULA-Greek: the relaunch4 log line "Word: 275520" is the sum of both editions
  (137779 + 137741). The catalog tracks the two editions as separate Tier-A sources;
  each matches EXACTLY. Decision 18 (commit 6adeb11) skips 11 compound-Strong
  GreekLemma (Nestle1904 6 + SBLGNT 5); that skip is on GreekLemma nodes only, not on
  Word, and the catalog record_unit for both sources is "word". No 12th reconciliation
  candidate here; macula_greek is faithful AND the catalog is correct.

## 3. FAIL root-cause classification

### 3.1 STEPBible-TVTMS  catalog 1308 / live 1300 / delta -8  (Tier A, tolerance 0)

Classification: REAL ADAPTER BUG (not a catalog-reconcile).

Evidence:
- `docs/PHASE_D_TIERA_PREVERIFICATION.md` section "STEPBible-TVTMS" establishes the
  faithful row count is 1308 (1308 non-blank TSV lines in
  `data/private/stepbible/tvtms.parsed.json`, which is actually TSV despite the .json
  name) and explicitly states "The catalog number 1308 IS the correct faithful row
  count". The catalog is already correct.
- `tmp/phase_d/pass1_relaunch4.log` line 124-128: the stepbible_tvtms adapter itself
  emits `"VersificationRule": 1300`. The earlier pre-verification defect (json.load
  on a TSV artifact emitting ZERO) has been partially fixed (the adapter now parses
  TSV and emits 1300), but the fixed adapter still drops 8 rows versus the faithful
  1308 line count.
- Live graph = 1300 (MATCH (r:VersificationRule {source:'STEPBible-TVTMS'})), exactly
  equal to the adapter emit. Live faithfully reflects the adapter. rule_type
  breakdown: OneToOne 1003 + SubdividedVerse 297 = 1300, 0 null rule_type.
- The delta is in the adapter's TSV parse, not in the live write and not in the
  catalog. The catalog 1308 is the proven faithful target.

Proposed remediation: keep catalog expected_count = 1308 (already correct, no
[SCHEMA-REVISION] needed). Fix `ingest/lexical/stepbible_tvtms._load_rows` to emit
all 1308 faithful TSV rows (root-cause the 8 dropped: most likely a header or blank
or multi-tradition-column row class the parser discards). Re-ingest. This is the same
discipline as the prior 11: the adapter is brought to the proven faithful number, the
catalog is NOT fudged.

### 3.2 OpenBible-cross-refs  catalog 344799 / live 139829 / delta -204970  (Tier A, tolerance 0)

Classification: REAL LIVE-WRITE / INGEST-LANDING DEFECT (not a catalog-reconcile,
not an adapter-logic defect).

Evidence:
- `docs/PHASE_D_TIERA_PREVERIFICATION.md` lines 187-193: "OpenBible-cross-refs --
  EXACT", catalog 344799 / faithful 344799 / delta 0, quarantined 0. The faithful
  adapter computation `ob._parse_rows(...)` resolves exactly 344799 rows. The catalog
  is already reconciled to the faithful emit and is correct.
- `tmp/phase_d/pass1_relaunch4.log` lines 156-160: the openbible adapter REPORTS
  `"OPENBIBLE_CROSS_REF": 344799, "quarantined": 0`. The adapter computed the
  faithful number correctly.
- Live graph: MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse) RETURN count(r) =
  139829. Distinct (a,b) pairs = 139829 = rel count (NO MERGE collapse; these are
  139829 genuinely distinct edges, not 344799 collapsed onto duplicate endpoints).
  Distinct source verses = 20776 of 33068 Verse nodes.
- The adapter emitted 344799 but only 139829 landed in the live graph. This is a
  write/transaction landing defect: 204970 edges the faithful adapter computed never
  persisted. It is NOT a naive-catalog class (the catalog already equals the faithful
  344799) and NOT an adapter-logic class (the adapter emit log proves 344799 computed).

Proposed remediation: keep catalog expected_count = 344799 (already correct, no
[SCHEMA-REVISION]). Root-cause why the openbible write only landed 139829/344799
(candidate causes: a verse-endpoint MATCH that fails for ~12000 KJV-OSIS-unmapped
source verses so the MERGE no-ops, a batch/transaction commit dropped mid-write, or a
TVTMS-remap path that silently discards rows whose remapped verse has no Verse node).
Re-ingest after fix. Catalog NOT fudged.

### 3.3 ETCBC-parallels  catalog 5914 / live 0 / delta -5914  (Tier A, tolerance 0)

Classification: REAL LIVE-WRITE / INGEST-LANDING DEFECT (not a catalog-reconcile,
not an adapter-logic defect).

Evidence:
- `docs/PHASE_D_TIERA_PREVERIFICATION.md` lines 223-253: ETCBC-parallels was the
  prior raw-vs-faithful reconciliation (raw crossref.tf feature rows 8246 vs faithful
  single-target PARALLEL_OF emit 5914; 2332 multi-target / non-digit-node rows
  quarantined per Decision 3 single-comma split). The catalog expected_count was
  reconciled to the faithful 5914 and is correct: "Adapter faithful, MUST NOT change",
  "the faithful emit of the committed adapter is 5914 and that is what the gate must
  assert". The catalog is already at 5914 (verified in expected_counts.json line 205).
- `tmp/phase_d/pass1_relaunch4.log` lines 45-49: the etcbc_parallels adapter REPORTS
  `"PARALLEL_OF": 5914, "quarantined": 2332`. The adapter computed the proven
  faithful number exactly.
- Live graph: MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord) RETURN count(r) = 0.
  MATCH ()-[r:PARALLEL_OF]-() (any label, any direction) = 0. There is NO PARALLEL_OF
  edge in the live graph at all. The all-relationship-type census confirms PARALLEL_OF
  is absent from the live taxonomy entirely.
- BhsaWord nodes exist (426590, all with .id property), so the MATCH-then-MERGE target
  endpoint exists. The adapter emitted 5914 but ZERO landed. This is a total
  write-landing failure for this edge-only adapter, NOT an adapter-logic defect (emit
  log proves 5914) and NOT a catalog issue (catalog already reconciled to faithful
  5914).

Proposed remediation: keep catalog expected_count = 5914 (already correct, no
[SCHEMA-REVISION]). Root-cause why the etcbc_parallels write landed 0/5914 (candidate
causes: the source-BhsaWord id keyspace lookup `MATCH (a:BhsaWord {id:...})` resolves
0 rows because the parallels adapter keys on a different id namespace than bhsa.py
wrote, e.g. raw tf node integer vs `bhsa:tf:<node_id>` stable id; or the MATCH-then-
MERGE both-endpoint requirement no-ops every row). Re-ingest after fix. Catalog NOT
fudged.

## 4. edge_counts{} block table

Critical structural finding: the catalog `edge_counts{}` block names a DIFFERENT edge
taxonomy than the adapters emit. The live relationship-type census is:

```
HAS_MACULA_ENRICHMENT 7554331, INSTANCE_OF 1918911, IN_VERSE 979032,
FROM_EDITION 628685, CONTAINS_WORD 426590, HAS_MORPHEME 421224,
CROSS_REF 374549, IN_DOMAIN 260839, CONTAINS_PHRASE 253203,
OPENBIBLE_CROSS_REF 139829, PARSE_OF 137554, MENTIONS 51511,
LEX_FOR 40566, BRIDGES_LXX 24604, READS_AT 16357, NAMED_AT 5459,
IS_QERE_OF 1244, ATTESTED_BY 470, CORRECTOR_OF 2
```

The phase_02 runbook (the adapter contract) emits CROSS_REF (TSK), OPENBIBLE_CROSS_REF
(OpenBible), IN_DOMAIN (Louw-Nida), PARALLEL_OF (parallels), CONTAINS_PHRASE /
CONTAINS_WORD (BHSA), NAMED_AT (proper nouns), READS_AT / ATTESTED_BY (cbgm). The
catalog edge_counts{} keys (HAS_CROSS_REF, GLOSSES_GREEK_LEMMA, HAS_LOUW_NIDA_DOMAIN,
HAS_SDBH_DOMAIN, HAS_CLAUSE, HAS_PHRASE, HAS_PARALLEL, IS_PROPER_NOUN,
HAS_VARIANT_UNIT, HAS_READING) do NOT exist as live relationship types. Mapping to the
adapter-emitted equivalents per phase_02:

| Catalog edge key | Tier | Catalog range | Live equivalent edge | Live actual | In range? | Note |
|---|---|---|---|---|---|---|
| GLOSSES_GREEK_LEMMA | B | [326475, 382157] | BRIDGES_LXX (MACULA-Hebrew greek bridge, Decision 4) | 24604 | NO | edge-name + magnitude mismatch; catalog models a greek-gloss edge the adapter emits as BRIDGES_LXX at a far lower occurrence; catalog-reconcile candidate (edge taxonomy) |
| HAS_CROSS_REF | B | [100001, 509456] | CROSS_REF {source:'TSK'} | 374549 | YES (in range) | name mismatch only; magnitude inside the tier-B band. Adapter emit log = 582568; live landed 374549 (live-write shortfall vs adapter emit, but still inside the wide catalog band) |
| OPENBIBLE_CROSS_REF | B | [343799, 345799] | OPENBIBLE_CROSS_REF | 139829 | NO | live-write landing defect (see 3.2); adapter emit 344799 in band, live 139829 far below |
| HAS_VARIANT_UNIT | B | [80, 200] | VariantUnit node count proxy (no HAS_VARIANT_UNIT edge emitted) | 116 | YES | name mismatch; magnitude in band |
| HAS_READING | B | [250, 600] | ATTESTED_BY (Reading->VariantUnit) | 470 | YES | name mismatch; magnitude in band |
| HAS_LOUW_NIDA_DOMAIN | B | [254167, 266875] | IN_DOMAIN (Word->LouwNidaDomain) | 260839 | YES | name mismatch; magnitude in band |
| HAS_SDBH_DOMAIN | B | [244570, 246570] | (no SDBH domain edge emitted; 0 SdbhDomain nodes) | 0 | NO | adapter emits no SDBH domain edge at all; catalog models an edge the committed adapter does not produce. Catalog-reconcile candidate OR unimplemented Decision 1/2 SDBH path |
| HAS_CLAUSE | B | [71500, 74500] | BhsaClause node count proxy (containment via CONTAINS_PHRASE) | 88131 | NO | BhsaClause 88131 above the [71500,74500] band; name + magnitude mismatch |
| HAS_PHRASE | B | [248000, 256000] | BhsaPhrase node / CONTAINS_PHRASE | 253203 | YES | name mismatch; magnitude in band |
| HAS_PARALLEL | B | [8082, 8411] | PARALLEL_OF | 0 | NO | live-write landing defect (see 3.3); also note catalog band [8082,8411] is the OLD raw-8246 envelope, NOT the reconciled faithful 5914 that sources["ETCBC-parallels"] was corrected to. Internal catalog inconsistency: the node-side was reconciled to 5914 but this edge band still encodes the pre-reconciliation 8246 |
| IS_PROPER_NOUN | B | [23205, 27546] | NAMED_AT (ProperNoun->Verse) | 5459 | NO | name mismatch; NAMED_AT 5459 far below band (band counts STEPBible rows + Theographic person/place projections, a different aggregate than the NAMED_AT verse-resolution edge) |

The edge_counts{} block is NOT verifiable as written against the live graph because it
references relationship types that the committed adapters do not emit. Where a sound
adapter-equivalent exists and landed correctly the magnitude is in band (HAS_CROSS_REF,
HAS_LOUW_NIDA_DOMAIN, HAS_PHRASE, HAS_VARIANT_UNIT, HAS_READING). Where the adapter
emit failed to land (OPENBIBLE_CROSS_REF, HAS_PARALLEL) the edge is out of band for the
same root cause as 3.2 / 3.3. Two further structural defects surfaced:
- HAS_PARALLEL band [8082,8411] still encodes the pre-reconciliation raw 8246, while
  sources["ETCBC-parallels"] was reconciled to faithful 5914. The edge block was not
  updated in the same [SCHEMA-REVISION] that fixed the node side. Internal catalog
  inconsistency, surfaced not failed.
- HAS_SDBH_DOMAIN expects ~245570 edges but the adapters emit ZERO SDBH domain edges
  (0 SdbhDomain nodes live). Either an unimplemented Decision 1/2 SDBH path or a
  catalog edge that does not correspond to any committed adapter output.

These are surfaced as catalog-structure / live-write findings, not silently passed.

## 5. Confirmation of reconciled Tier-A targets

All key reconciled Tier-A faithful targets confirmed EXACT against the live graph:

| Target | Expected | Live | Status |
|---|---|---|---|
| OSHB-morphology Word | 305507 | 305507 | CONFIRMED |
| STEPBible-TAHOT TaggedToken | 283721 | 283721 | CONFIRMED |
| STEPBible-TAGNT TaggedToken | 142096 | 142096 | CONFIRMED |
| STEPBible-TTESV TaggedToken | 31127 | 31127 | CONFIRMED |
| STEPBible-proper-nouns ProperNoun | 5468 | 5468 | CONFIRMED |
| Theographic projected-entity | 4849 | 4849 (3067+1274+450+11+12+35) | CONFIRMED |
| ETCBC-phono non-null phono | 420166 | 420166 | CONFIRMED |
| STEPBible-TFLSJ LsjEntry | 9488 | 9488 | CONFIRMED |
| STEPBible-morph-codes MorphCode | 2675 | 2675 | CONFIRMED |
| open-cbgm-3-john cbgm_node | 728 in [700,760] | 728 | CONFIRMED |
| ETCBC-parallels PARALLEL_OF | 5914 | 0 | NOT CONFIRMED (live-write defect 3.3) |

Note: ETCBC-parallels 5914 is the correct reconciled CATALOG number and the correct
ADAPTER emit (relaunch4 log = 5914), but it did NOT land in the live graph (live = 0).
The reconciliation itself stands; the ingest write of it failed.

Also confirmed exact: MACULA-Hebrew 475911, MACULA-Greek-Nestle1904 137779,
MACULA-Greek-SBLGNT 137741, MorphGNT-SBLGNT 137554, STEPBible-TBESH 11682,
STEPBible-TBESG 11035, TSK CrossRef 63682, ETCBC-BHSA BhsaWord 426590.

## 6. GO / NO-GO

NO-GO.

20 of 23 source records PASS within tier (17 Tier-A exact, 1 Tier-B in envelope,
3 Tier-C placeholder shape). 3 FAIL, all Tier-A tolerance-0:

1. STEPBible-TVTMS: catalog 1308 / live 1300 / delta -8. REAL ADAPTER BUG (TSV parse
   in stepbible_tvtms drops 8 of the proven-faithful 1308 rows; live faithfully equals
   the buggy adapter emit 1300). Catalog 1308 is correct and proven; do NOT
   [SCHEMA-REVISION]. Fix the adapter parse to emit 1308, re-ingest.
2. OpenBible-cross-refs: catalog 344799 / live 139829 / delta -204970. REAL LIVE-WRITE
   LANDING DEFECT (adapter computed and reported the faithful 344799 in relaunch4 log;
   only 139829 distinct edges persisted, no MERGE collapse). Catalog 344799 is correct
   and proven; do NOT [SCHEMA-REVISION]. Root-cause the unpersisted 204970 edges
   (likely failed Verse-endpoint MATCH for KJV-OSIS-unmapped source verses), re-ingest.
3. ETCBC-parallels: catalog 5914 / live 0 / delta -5914. REAL LIVE-WRITE LANDING
   DEFECT (adapter computed and reported the faithful 5914 in relaunch4 log; ZERO
   PARALLEL_OF edges exist in the live graph). Catalog 5914 is correct and proven (it
   IS the prior reconciliation); do NOT [SCHEMA-REVISION]. Root-cause the total
   write-landing failure (likely BhsaWord id-namespace mismatch in the MATCH-then-MERGE
   endpoint lookup), re-ingest.

No 12th naive-catalog reconciliation is warranted. All three FAILs are downstream of
the catalog (which is correctly reconciled to the faithful emit in every case): two
are live-write/ingest-landing defects and one is an adapter parse defect. The brethren-
on-trial discipline holds: the catalog is NOT fudged; the adapter and ingest are
brought to the proven faithful numbers (1308 / 344799 / 5914), then re-ingested and
re-audited.

Additional surfaced (not gating the source table, but blocking a clean Phase D close):
- edge_counts{} block is unverifiable as written: it names a relationship taxonomy
  (HAS_CROSS_REF, GLOSSES_GREEK_LEMMA, HAS_LOUW_NIDA_DOMAIN, HAS_SDBH_DOMAIN,
  HAS_CLAUSE, HAS_PHRASE, HAS_PARALLEL, IS_PROPER_NOUN, HAS_VARIANT_UNIT, HAS_READING)
  that no committed adapter emits.
- HAS_PARALLEL band [8082,8411] still encodes the pre-reconciliation raw 8246 while
  the node side was reconciled to faithful 5914 (internal catalog inconsistency).
- HAS_SDBH_DOMAIN expects ~245570 edges; the adapters emit zero SDBH domain edges.
- MACULA-Hebrew catalog record_unit label says "morpheme" but the materialized node
  is MaculaToken (count exact at 475911; label-text clarity only, not a count defect).
