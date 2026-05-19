# Phase D edge_counts and source-count reconcile plan

Caste: architect. READ-ONLY investigation plus a single reconcile-plan
deliverable. Branch main, HEAD 979b00b. Neo4j NOT touched (relaunch-4 data
live; the live rel-type census is taken verbatim from the read-only
`docs/AUDIT_phase_d4_count_gate.md` section 4, which queried lexical-neo4j
under the auditor caste). No code, test, or `tools/expected_counts.json`
write performed here. The [SCHEMA-REVISION] delta below is the prescription
the orchestrator integrates ATOMICALLY with FIX-OPENBIBLE (704523d) and
FIX-PARALLELS (af75380); those two commits currently live on agent worktree
branches and are NOT yet ancestors of main HEAD 979b00b (verified
`git merge-base --is-ancestor`).

Doctrinal frame: brethren-on-trial. Trust the faithful real parse. Fix a
demonstrably-wrong catalog number to the proven faithful number. A real
unimplemented contracted edge type is a real defect and is escalated, never
fudged. No em or en dashes.

---

## Finding 1: sources["OpenBible-cross-refs"] 344799 vs faithful 342130

### Three numbers
- Catalog `expected_count` = 344799 (tier A, tol 0). The 344799 is the raw
  upstream CSV row count and is the documented faithful row total per
  `docs/PHASE_D_TIERA_PREVERIFICATION.md` (OpenBible "EXACT", faithful 344799,
  quarantined 0).
- FIX-OPENBIBLE 704523d faithful landed = 342130. The fix corrected two real
  adapter join defects (MATCH on `Verse.osisID` which is NULL on all 7927
  MorphGNT NT verses and carries non-OSIS abbrevs on a 1928 phantom-stub
  subset; and an unparsed two-part passage range in 88150 rows). Post-fix the
  id-key + range-anchor projection resolves 342130 of 344799 rows against the
  live `Verse.id` set.
- Residual 2669 = genuine KJV-vs-Hebrew versification shifts (Joel 2:28-32 KJV
  = Joel 3 Hebrew, Jonah 1:17 = Jonah 2:1, Deut 12:32 = Deut 13:1) that do not
  resolve through the consumed `data/private/stepbible/tvtms.parsed.json`.

### Investigation: faithful upstream limitation OR stepbible_tvtms procurement defect

DECISIVE BYTE EVIDENCE (read directly from the frozen upstream and the
consumed artifact):

1. The consumed artifact `data/private/stepbible/tvtms.parsed.json` is a
   1308-row TSV, every row tagged `english<TAB>ref_a<TAB>hebrew<TAB>ref_b<TAB>rule_type`.
   It contains **0 Joel rows, 0 Deut.12 rows, exactly 2 Jonah rows**. The
   Joel/Jonah/Deut KJV-Hebrew shift mappings are genuinely ABSENT from the
   artifact the adapters consume. Given ONLY this artifact, 342130 is the
   faithful resolvable count and the openbible adapter is faithful (it
   quarantines the 2669, never fabricates an inline KJV-to-OSIS map, per its
   contract).

2. HOWEVER the frozen raw upstream
   `data/private/stepbible/Versification/TVTMS - ... CC BY.txt` (5.8 MB,
   procured 2026-05-10, frozen) DOES contain those exact shift rows, and they
   are in the **Condensed section** (`#DataStart(Condensed)` line 162 to
   `#DataStart(Expanded)` line 4181) that the 1308 parsed rows were drawn
   from, not only the Expanded section:
   - `OneToOne<TAB>Jol.2:28-32<TAB>Jol.3:1-5<TAB>...` (under `$Jol.2:28--3:21`)
   - `OneToOne<TAB>Jon.1:17<TAB>Jon.2:1<TAB>...` (under `$Jon.1:17--2:10`)
   - Deut.12 KJV-Hebrew shift rows present (4 lines in Condensed).

3. The procurement parser that produced `tvtms.parsed.json`
   (`ingest/lexical/stepbible.parse_tvtms`) is QUARANTINED DEAD CODE (it
   carried the `int(pos)` canonical-overwrite defect, see
   `ingest/lexical/stepbible.py` and `docs/AUDIT_pos_collapse_blast_radius.md`).
   The artifact on disk is the only TVTMS rule source the live adapters read
   (`stepbible_tvtms.py`, `openbible.py`, `tsk.py` all `line.split("\t")` it).

### Verdict (item 1): TWO-PART

- The catalog number 344799 is the raw CSV row count, but the FAITHFUL
  LANDED edge count given the data the air-gapped ingest actually consumes
  is 342130. This is the SAME reconciliation class as the Phase D set
  (catalog holds the naive raw count, adapter faithfully emits fewer because
  the consumable upstream genuinely cannot resolve the residual). The 2669
  residual rows target verses that do not exist under the supplied KJV ref in
  the canon's Hebrew/OSIS versification, and the contract forbids inline
  hardcoded KJV-to-OSIS fabrication. RECONCILE sources["OpenBible-cross-refs"]
  to 342130 (faithful-given-available-TVTMS).

- SEPARATELY ESCALATE (MUST-ESCALATE, non-blocking for the D.4 source gate
  once reconciled, but a real procurement defect): the Joel/Jonah/Deut.12
  KJV-Hebrew shift rows EXIST in the frozen Condensed section of the raw
  upstream and were dropped by the (now-quarantined) procurement parser when
  it serialized `tvtms.parsed.json`. The artifact is incomplete relative to
  its own frozen upstream. A faithful tvtms-completeness fix would re-derive
  `tvtms.parsed.json` from the Condensed section INCLUDING range-bearing rows
  (`Jol.2:28-32`), and the consumer adapters (`openbible._load_tvtms_rules`,
  `tsk._load_tvtms_rules`) would need per-verse range expansion of the
  `ref_a`/`ref_b` cells. That is a multi-file producer+consumer change, not a
  one-line fix; it is NOT a 12th naive-catalog reconciliation and it does not
  block reconciling the catalog to 342130 now. It is logged for owner
  decision: reconcile-only (accept 342130 as the faithful number for the
  frozen-artifact era) is the recommended immediate action; the
  tvtms-completeness re-procurement is a follow-on that would later raise the
  faithful number toward 344799 and require its own [SCHEMA-REVISION] back up.

RECOMMENDATION: reconcile sources["OpenBible-cross-refs"] 344799 -> 342130
NOW (faithful-given-available-TVTMS, same class as the Phase D set); raise a
separate MUST-ESCALATE ticket for the stepbible_tvtms artifact incompleteness
(Condensed-section Joel/Jonah/Deut range rows dropped by the quarantined
procurement parser). Do NOT fudge the openbible adapter; it is faithful.

---

## Finding 2: sources["ETCBC-parallels"] 5914 vs faithful 5882

### Three numbers
- Catalog `expected_count` = 5914, record_unit `parallel_edge`, tier A tol 0.
  This was itself the Phase D reconciliation set #3 (raw crossref.tf rows 8246
  -> faithful single-target 5914 after the Decision 3 single-comma split
  quarantines 2332 multi-target/non-digit rows; 5914 + 2332 = 8246).
- FIX-PARALLELS af75380 faithful landed = 5882.
- Delta = 32 exact-duplicate directed verse-pairs.

### Decisive evidence of the 32 dups
The etcbc_parallels contract section 6 binds idempotency to MERGE on the
ordered tuple `(source, target)` with `ON CREATE SET`/`ON MATCH SET`
(last-write-wins on `similarity`); "Re-running the adapter on identical
source bytes produces zero new edges". crossref.tf contains 32 exact-duplicate
directed verse-tf-node pairs (fix-commit byte evidence: body lines 796 and
801 both yield `1416981 -> 1416649`, with similarities 0.83 and 0.94
respectively; the second SET overwrites the first, one edge survives). The
binding `(source, target)` MERGE key necessarily collapses each duplicate
pair to one edge: 5914 single-target rows -> 5882 distinct directed
(source, target) edges landed. This collapse is independent of the endpoint
label and was MASKED by the prior 0/5914 endpoint bug (the original
BhsaWord->BhsaWord MATCH resolved nothing, so the collapse never surfaced).
FIX-PARALLELS re-keyed the endpoints to the Verse node (`verse:<osisRef>`,
constraint verse_id, Decision 15) and verified live read-only that all 5914
single-target rows resolve and 5882 distinct edges land (the 32-collapse is
the only delta; 2332 multi-target/non-digit rows stay quarantined per
Decision 3, unchanged). The MERGE idempotency was deliberately NOT weakened
to inflate back to 5914. This is the IDENTICAL idempotent-MERGE-collapse
reconciliation class as the Phase D set: the adapter is faithful, the catalog
raw-derived number is one collapse-step stale.

### record_unit / tier_rationale correction (PARALLEL_OF is Verse->Verse)
FIX-PARALLELS established crossref.tf node ids are BHSA `verse`-otype
text-fabric nodes (otype.tf run 1414389-1437601 verse), NOT word slots
(run 1-426590 word); zero rows fall in the word run (byte-verified in the
fix). The faithful schema-backed endpoint is the `Verse` node, so PARALLEL_OF
is a Verse->Verse parallel-passage edge.

- The catalog `record_unit` for sources["ETCBC-parallels"] is `parallel_edge`
  which is endpoint-agnostic and remains CORRECT (a parallel-passage edge is
  a verse-to-verse relation; "parallel_edge" does not assert a word endpoint).
  No record_unit text change is strictly required, but for clarity the
  tier_rationale SHOULD state the endpoint is Verse->Verse to match the fixed
  adapter and prevent a future reader re-deriving the stale BhsaWord contract.
- PRESCRIBE tier_rationale rewrite for sources["ETCBC-parallels"] (see delta
  below): change the count to 5882, state the endpoint is Verse->Verse, and
  attribute the additional 32-edge collapse to the binding `(source, target)`
  idempotent MERGE per Decision 3 / contract section 6.

RECOMMENDATION: [SCHEMA-REVISION] sources["ETCBC-parallels"]
5914 -> 5882 (same idempotent-MERGE-collapse class as the Phase D set);
adapter faithful, NOT changed. Endpoint clarification in tier_rationale only;
record_unit stays `parallel_edge`.

---

## Finding 3: edge_counts{} taxonomy does not match emitted rel-types

The catalog `edge_counts{}` keys name a relationship taxonomy that NO
committed adapter emits. The live rel-type census (read-only, from
`docs/AUDIT_phase_d4_count_gate.md` section 4, lexical-neo4j relaunch-4) is:

```
HAS_MACULA_ENRICHMENT 7554331, INSTANCE_OF 1918911, IN_VERSE 979032,
FROM_EDITION 628685, CONTAINS_WORD 426590, HAS_MORPHEME 421224,
CROSS_REF 374549, IN_DOMAIN 260839, CONTAINS_PHRASE 253203,
OPENBIBLE_CROSS_REF 139829 (pre-fix; post-FIX-OPENBIBLE = 342130 faithful),
PARSE_OF 137554, MENTIONS 51511, LEX_FOR 40566, BRIDGES_LXX 24604,
READS_AT 16357, NAMED_AT 5459, IS_QERE_OF 1244, ATTESTED_BY 470,
CORRECTOR_OF 2; PARALLEL_OF 0 (pre-fix; post-FIX-PARALLELS = 5882 faithful)
```

Per-key mapping, live count, classification, and prescribed action:

| edge_counts key | meant-to-gate emitted rel-type | live count | catalog band | classification | prescribed action |
|---|---|---|---|---|---|
| HAS_CROSS_REF | CROSS_REF {source:'TSK'} | 374549 | [100001, 509456] | in-band, taxonomy-rename-needed | rename key HAS_CROSS_REF -> CROSS_REF; band wide enough, keep |
| GLOSSES_GREEK_LEMMA | BRIDGES_LXX (MACULA-Hebrew Decision 4 greek bridge) | 24604 | [326475, 382157] | out-of-band, taxonomy-rename + stale-band | rename -> BRIDGES_LXX; the [326k,382k] band was modeled on a per-morpheme greek/greekstrong occurrence, but the adapter emits BRIDGES_LXX once per distinct (Hebrew Lemma, GreekLemma) pair (deduplicated in `_build` via `bridge_seen`), so the faithful magnitude is the distinct-pair count 24604, not a per-morpheme count. Re-derive band from the faithful BRIDGES_LXX emit (see escalation note) |
| HAS_LOUW_NIDA_DOMAIN | IN_DOMAIN (Word->LouwNidaDomain, Decision 2) | 260839 | [254167, 266875] | in-band, taxonomy-rename-needed | rename -> IN_DOMAIN; band correct, keep |
| HAS_SDBH_DOMAIN | NO-ADAPTER-EMITS-THIS | 0 | [244570, 246570] | NO-ADAPTER-EMITS-THIS (real unimplemented contracted edge) | see Finding 4 |
| HAS_CLAUSE | BhsaClause node (no HAS_CLAUSE edge; containment is CONTAINS_PHRASE) | BhsaClause 88131 | [71500, 74500] | out-of-band, stale-band | the band was modeled on a clause-otype estimate; live BhsaClause is 88131. Re-base to the faithful BhsaClause count or drop (no HAS_CLAUSE edge exists; CONTAINS_PHRASE is the real containment edge). Recommend rename HAS_CLAUSE -> BhsaClause node-count gate, band re-based to 88131 +/- tierB |
| HAS_PHRASE | CONTAINS_PHRASE / BhsaPhrase | 253203 | [248000, 256000] | in-band, taxonomy-rename-needed | rename -> CONTAINS_PHRASE; band correct, keep |
| HAS_PARALLEL | PARALLEL_OF | 0 pre-fix / 5882 post-fix | [8082, 8411] | out-of-band, stale-band, internally inconsistent | rename -> PARALLEL_OF; the [8082,8411] band still encodes the pre-reconciliation raw 8246 while sources["ETCBC-parallels"] was reconciled to 5914 and is now further reconciled to 5882. Re-base band to the faithful node-side number 5882 (see delta) |
| IS_PROPER_NOUN | NAMED_AT (ProperNoun->Verse) | 5459 | [23205, 27546] | out-of-band, stale-band | the band counts STEPBible raw rows (23205, itself the naive count already reconciled to 5468 in sources["STEPBible-proper-nouns"]) plus Theographic projections, a different aggregate than the NAMED_AT verse-resolution edge. Rename -> NAMED_AT and re-base band to the faithful NAMED_AT emit, OR retire the key (it duplicates the already-reconciled proper-noun source count under a wrong aggregate) |
| HAS_VARIANT_UNIT | VariantUnit node (no HAS_VARIANT_UNIT edge) | 116 | [80, 200] | in-band, taxonomy-rename-needed | rename -> VariantUnit node-count gate; band correct, keep |
| HAS_READING | ATTESTED_BY (Reading->VariantUnit) | 470 | [250, 600] | in-band, taxonomy-rename-needed | rename -> ATTESTED_BY; band correct, keep |
| (OPENBIBLE_CROSS_REF, already correctly named) | OPENBIBLE_CROSS_REF | 139829 pre-fix / 342130 post-fix | [343799, 345799] | out-of-band, stale-band | the band is modeled on raw 344799; reconcile to the faithful post-FIX 342130. Re-base band around 342130 (see delta) |

Net structural conclusion: the edge_counts block is unverifiable as written
(eight of ten keys name rel-types no committed adapter emits). Three defects
must be fixed in the [SCHEMA-REVISION]: (a) rename every key to the rel-type
the committed adapters actually emit; (b) re-base the HAS_PARALLEL band off
the pre-reconciliation raw 8246 to the faithful node-side 5882 and the
OPENBIBLE_CROSS_REF band off raw 344799 to the faithful 342130, so the edge
block is internally consistent with the reconciled source counts; (c)
resolve HAS_SDBH_DOMAIN per Finding 4.

---

## Finding 4: HAS_SDBH_DOMAIN expects ~245570, ZERO SDBH edges live

### Decisive evidence
1. The catalog `edge_counts["HAS_SDBH_DOMAIN"]` band is [244570, 246570],
   tier_rationale: "Derived from MACULA-Hebrew morphemes whose sdbh field is
   non-null at occurrence rate 0.516 per Decision 1 and Decision 2".

2. The frozen MACULA-Hebrew upstream DOES carry the `sdbh` attribute. Counted
   directly from all `data/private/macula-hebrew/WLC/lowfat/*-lowfat.xml`
   bytes: TOTAL `<w>` = 475911 (exactly the MaculaToken / catalog
   MACULA-Hebrew expected_count), `sdbh` non-empty = **244734**, occurrence
   rate = **0.514243**. The real sdbh-non-null count 244734 falls INSIDE the
   catalog band [244570, 246570]. The band magnitude is NUMERICALLY ACCURATE
   and the upstream data genuinely exists to build ~244734 SDBH edges.

3. NO adapter emits any SDBH node or edge. `ingest/lexical/macula_hebrew.py`
   reads `lemma, morph, pos, gloss, stronglemma, strongnumberx,
   transliteration, greek, greekstrong` from each `<w>` and NEVER reads the
   `sdbh` attribute. There is no `SdbhDomain` label, no `HAS_SDBH_DOMAIN`
   edge, no `IN_DOMAIN` from the Hebrew stream anywhere in the adapter. The
   docstring explicitly states the adapter "MUST NOT create LouwNidaDomain
   nodes from the Hebrew morpheme stream" and references `sdbh` only as
   "when present" with NO binding to emit anything.

4. `docs/SCHEMA_DECISIONS.md` contains ZERO occurrences of "sdbh"/"SDBH"
   across all 18 decisions. Decision 1 (OSHB-to-MACULA alignment) governs
   `lemma/morph/pos/gloss/stronglemma/strongnumberx` only. Decision 2 binds
   Louw-Nida (`ln`/`domain`) to the GREEK editions and creates
   LouwNidaDomain + IN_DOMAIN. NEITHER Decision 1 NOR Decision 2 contracts
   any SDBH domain edge. The catalog tier_rationale's "per Decision 1 and
   Decision 2" backreference is UNFOUNDED: those decisions do not contract
   SDBH output.

5. `graph/lexical.cypher` has a `louw_nida_id` constraint and a
   `louw_nida_code` index (Decision 2) but NO SdbhDomain constraint and NO
   HAS_SDBH_DOMAIN provisioning. The schema layer never provisioned SDBH.

6. Repo-wide, `SdbhDomain`/`HAS_SDBH_DOMAIN` appears ONLY in
   `tools/expected_counts.json` and `docs/AUDIT_phase_d4_count_gate.md`
   (the audit that surfaced this). It is a catalog-only string with no
   adapter, no Decision, and no schema constraint behind it.

### Verdict (item 4): REAL MISSING-EDGE DEFECT, catalog-contracted-but-unimplemented

This is NOT a catalog-artifact-to-delete: the data genuinely exists
(244734 sdbh-non-null morphemes in the frozen upstream, INSIDE the catalog
band), so the band is a faithful numeric target, not a fabricated number. It
is a contracted-by-catalog edge type whose adapter implementation was NEVER
written and whose Decision was NEVER authored. Two faithful resolutions; the
owner must choose:

- (A, build) Implement the SDBH domain edge as a real new edge type: author
  a Decision (mirroring Decision 2's Louw-Nida pattern but for the Hebrew
  `sdbh` field), add a `SdbhDomain` node label + uniqueness constraint to
  `graph/lexical.cypher`, extend `ingest/lexical/macula_hebrew.py` to read
  the `<w>` `sdbh` attribute and emit `(:MaculaToken)-[:IN_SDBH_DOMAIN]->
  (:SdbhDomain)` (or `HAS_SDBH_DOMAIN`) at the proven ~244734 rate, and add
  the verifier. Scope: NEW Decision + new node label + new constraint + new
  adapter edge emit + new verifier + re-ingest. This is a multi-file
  new-edge-type BUILD, NOT a one-line fix. MUST-ESCALATE.

- (B, retire) If the SDBH domain edge is out of scope for v1 (Decision 2
  deliberately scoped semantic-domain encoding to Greek Louw-Nida only, and
  no Decision was ever written to extend it to Hebrew SDBH), then
  HAS_SDBH_DOMAIN is a catalog aspiration that was never contracted to any
  adapter or Decision. Retire the `edge_counts["HAS_SDBH_DOMAIN"]` key in
  the [SCHEMA-REVISION] and record the SDBH-edge build as a deferred v1.x
  scope item, so the edge_counts block only gates rel-types the committed
  adapters actually emit.

ARCHITECT RECOMMENDATION: option (B) for the immediate [SCHEMA-REVISION]
(retire the unverifiable key so Phase D.4 has an internally consistent edge
taxonomy), WITH a MUST-ESCALATE owner ticket recording that the data exists
(244734 sdbh-non-null at rate 0.514, inside the old band) and that
implementing the SDBH domain edge is a real, scoped, faithful enhancement
deferred from v1, NOT silently abandoned. Rationale: the brethren-on-trial
discipline says do not fudge, and there is nothing to fudge here (no adapter
emits it, no Decision contracts it, the band number is honest); the faithful
action is to stop gating a non-existent edge AND to record the genuine
build scope so it is not lost. If the owner rules SDBH in-scope for v1,
option (A) and HAS_SDBH_DOMAIN BLOCKS a clean Phase D.4 close until the new
edge type is built and re-ingested.

### Does HAS_SDBH_DOMAIN block D.4?
- Under option (B) (recommended): NO, it does not block once the key is
  retired and the build is escalated as a tracked deferral. D.4's source-count
  gate (the 23-source table) is unaffected; HAS_SDBH_DOMAIN is an edge_counts
  key, not a source.
- Under option (A) (owner rules SDBH in-scope for v1): YES, a real
  unimplemented contracted edge type BLOCKS a clean Phase D close until built
  and re-ingested. This is the one item in this deliverable that can be a
  hard Phase-D blocker, and only if the owner rules it in v1 scope.

---

## The exact [SCHEMA-REVISION] tools/expected_counts.json delta

Single `[SCHEMA-REVISION]`-subject commit, integrated ATOMICALLY by the
orchestrator with FIX-OPENBIBLE 704523d and FIX-PARALLELS af75380. Every
key old -> new:

### sources{}

1. `sources["OpenBible-cross-refs"].expected_count`: 344799 -> 342130
2. `sources["OpenBible-cross-refs"].min`: 344799 -> 342130
3. `sources["OpenBible-cross-refs"].max`: 344799 -> 342130
4. `sources["OpenBible-cross-refs"].tier_rationale`: replace with
   "The count is the faithful landed OPENBIBLE_CROSS_REF edge emit against
   the air-gapped consumable upstream. The prior 344799 was the raw upstream
   CSV row count; FIX-OPENBIBLE (704523d) corrected two real adapter join
   defects (Verse.osisID null on all 7927 MorphGNT NT verses; 88150 unparsed
   two-part passage ranges) and resolves 342130 rows against the canonical
   Verse.id keyspace. The residual 2669 are genuine KJV-vs-Hebrew
   versification shifts (Joel 2:28-32 = Joel 3 Hebrew, Jonah 1:17 = Jonah
   2:1, Deut 12:32 = Deut 13:1) whose mappings are absent from the consumed
   data/private/stepbible/tvtms.parsed.json artifact; the contract forbids
   inline KJV-to-OSIS fabrication so they are faithfully quarantined. Same
   class as the Phase D reconciliation set; the adapter is faithful and is
   NOT changed. A separate escalated tvtms-completeness item tracks that
   these rows exist in the frozen raw TVTMS Condensed section but were
   dropped by the quarantined procurement parser."

5. `sources["ETCBC-parallels"].expected_count`: 5914 -> 5882
6. `sources["ETCBC-parallels"].min`: 5914 -> 5882
7. `sources["ETCBC-parallels"].max`: 5914 -> 5882
8. `sources["ETCBC-parallels"].tier_rationale`: replace with
   "The count is the faithful landed Verse-to-Verse PARALLEL_OF edge emit.
   The prior 8246 was the raw crossref.tf feature-row count; the binding
   Decision 3 single-comma split quarantines 2332 multi-target/non-digit
   rows leaving 5914 single-target rows, and the binding (source, target)
   idempotent MERGE (contract section 6) further collapses 32 exact-duplicate
   directed verse-pairs, leaving 5882 distinct edges. FIX-PARALLELS
   (af75380) established crossref.tf node ids are BHSA verse-otype
   text-fabric nodes (not word slots) and re-keyed the endpoints to the
   canonical Verse node (verse:<osisRef>, constraint verse_id, Decision 15);
   record_unit stays parallel_edge (endpoint-agnostic). Same idempotent-MERGE
   -collapse class as the Phase D reconciliation set; the adapter is faithful
   and is NOT changed (the MERGE idempotency was deliberately not weakened to
   inflate back to 5914)."
   (record_unit stays "parallel_edge"; no record_unit value change.)

### edge_counts{}

Taxonomy rename + band reconcile so the block only gates rel-types the
committed adapters emit and is internally consistent with the reconciled
source counts. Recommended single coherent rewrite of the `edge_counts{}`
block:

9.  rename key `HAS_CROSS_REF` -> `CROSS_REF` (band [100001, 509456] kept;
    in-band, wide).
10. rename key `HAS_LOUW_NIDA_DOMAIN` -> `IN_DOMAIN` (band [254167, 266875]
    kept; live 260839 in-band).
11. rename key `HAS_PHRASE` -> `CONTAINS_PHRASE` (band [248000, 256000] kept;
    live 253203 in-band).
12. rename key `HAS_VARIANT_UNIT` -> `VARIANT_UNIT_NODE` (node-count gate;
    band [80, 200] kept; live 116 in-band).
13. rename key `HAS_READING` -> `ATTESTED_BY` (band [250, 600] kept; live
    470 in-band).
14. rename key `GLOSSES_GREEK_LEMMA` -> `BRIDGES_LXX`; re-base band off the
    faithful distinct-pair BRIDGES_LXX emit (live 24604) instead of the
    per-morpheme [326475, 382157]; set expected_min/expected_max to a tierB
    band around the faithful BRIDGES_LXX adapter emit (orchestrator to read
    the relaunch BRIDGES_LXX emit count; live landed = 24604, band e.g.
    [24112, 25096] = 24604 +/- 2 percent). tier_rationale: "BRIDGES_LXX is
    emitted once per distinct (Hebrew Lemma, GreekLemma) pair (deduplicated
    in macula_hebrew._build), not per morpheme; band is the faithful
    distinct-pair emit per Decision 4."
15. rename key `HAS_PARALLEL` -> `PARALLEL_OF`; re-base band off the
    reconciled faithful 5882 (was the stale pre-reconciliation raw-8246
    envelope [8082, 8411]). Set expected_min/expected_max to a tol-0-aligned
    band on 5882 (tier B 2 percent: [5764, 6000], or tighter [5882, 5882]
    to mirror the tol-0 node side). tier_rationale: "PARALLEL_OF is the
    faithful Verse-to-Verse landed edge count, equal to the reconciled
    sources[ETCBC-parallels] 5882 (5914 single-target rows minus 32
    idempotent-MERGE-collapsed exact-duplicate pairs). Internally consistent
    with the reconciled source count."
16. rename key `HAS_CLAUSE` -> `BHSA_CLAUSE_NODE`; re-base band off the live
    BhsaClause node count 88131 (was the stale clause-otype-estimate
    [71500, 74500]). Band e.g. [86368, 89894] = 88131 +/- 2 percent.
    tier_rationale: "BhsaClause node count per Decision 3; no HAS_CLAUSE
    edge is emitted (containment is CONTAINS_PHRASE). Band is the faithful
    clause-otype node count."
17. rename key `IS_PROPER_NOUN` -> `NAMED_AT`; re-base band off the faithful
    NAMED_AT emit (live 5459) instead of the raw-23205-plus-Theographic
    aggregate (which duplicates the already-reconciled
    sources[STEPBible-proper-nouns] under a wrong aggregate). Band e.g.
    [5350, 5568] = 5459 +/- 2 percent. tier_rationale: "NAMED_AT is the
    faithful ProperNoun-to-Verse resolution edge per Decision 10; the prior
    [23205, 27546] re-counted the already-reconciled proper-noun source rows
    under a different aggregate."
18. `edge_counts["OPENBIBLE_CROSS_REF"]` (key name already correct):
    re-base band off the reconciled faithful 342130 (was raw-344799 envelope
    [343799, 345799]). Set expected_min/expected_max to a band around 342130
    (e.g. [341130, 343130] = 342130 +/- 1000, or tol-0-aligned
    [342130, 342130] to mirror the reconciled tol-0 source). tier_rationale:
    "Edge count equals the faithful landed OPENBIBLE_CROSS_REF count,
    consistent with the reconciled sources[OpenBible-cross-refs] 342130."
19. `edge_counts["HAS_SDBH_DOMAIN"]`: RETIRE the key (recommended option B).
    No committed adapter emits any SDBH edge, no Decision contracts it, no
    schema constraint provisions it. Removing it makes the edge_counts block
    gate only rel-types the committed adapters emit. (If the owner instead
    rules SDBH in-scope for v1, do NOT retire; option A build required and
    Phase D.4 BLOCKS until the new edge type is built and re-ingested.)

Note on band tightening: items 14-18 give both a tierB-percentage band and a
tol-0-aligned option. Where the underlying source is tier A tol-0
(OPENBIBLE_CROSS_REF, PARALLEL_OF mirror the reconciled tol-0 source counts)
the orchestrator should prefer the tol-0-aligned exact band so the edge gate
is internally consistent with the reconciled tier-A source gate. The
orchestrator should read the actual relaunch adapter emit for BRIDGES_LXX to
set item 14 precisely (live landed 24604 is the read-only anchor).

---

## Summary of verdicts

| Item | Finding | Verdict | Catalog action | Adapter | Escalation |
|---|---|---|---|---|---|
| 1 OpenBible | catalog 344799, faithful-given-available-TVTMS 342130; 2669 residual are real KJV-Hebrew shifts absent from consumed tvtms.parsed.json | RECONCILE to 342130 (Phase D class) | expected_count/min/max 344799 -> 342130 + tier_rationale | openbible FAITHFUL, not changed (FIX-OPENBIBLE 704523d) | MUST-ESCALATE: tvtms.parsed.json incomplete vs frozen Condensed section (Joel/Jonah/Deut range rows dropped by quarantined procurement parser); follow-on producer+consumer fix, NOT a 12th naive reconcile, does NOT block reconciling to 342130 now |
| 2 ETCBC-parallels | catalog 5914, faithful 5882; 32 exact-dup directed pairs collapsed by binding (source,target) idempotent MERGE | [SCHEMA-REVISION] 5914 -> 5882 (idempotent-MERGE-collapse class) | expected_count/min/max 5914 -> 5882 + tier_rationale (Verse->Verse); record_unit stays parallel_edge | etcbc_parallels FAITHFUL, not changed (FIX-PARALLELS af75380) | none |
| 3 edge_counts taxonomy | 8/10 keys name rel-types no adapter emits; HAS_PARALLEL band encodes stale raw 8246; OPENBIBLE band encodes stale raw 344799 | rename all keys to emitted rel-types; re-base HAS_PARALLEL->PARALLEL_OF to 5882 and OPENBIBLE_CROSS_REF to 342130 for internal consistency | items 9-18 above | n/a | none |
| 4 HAS_SDBH_DOMAIN | catalog band [244570,246570] is numerically faithful (real upstream sdbh-non-null = 244734, rate 0.514) but ZERO SDBH edges emitted; no adapter, no Decision, no schema constraint | REAL MISSING-EDGE DEFECT (contracted-by-catalog, unimplemented). Recommend option B: retire the key now + MUST-ESCALATE the real build scope | retire edge_counts["HAS_SDBH_DOMAIN"] (option B) | macula_hebrew never reads `sdbh` (option A = new Decision + SdbhDomain label + constraint + adapter edge emit + verifier + re-ingest) | MUST-ESCALATE: option A is a multi-file new-edge-type build; BLOCKS clean Phase D.4 close ONLY if owner rules SDBH in-scope for v1 |

MUST-ESCALATE list (owner decisions, both real, neither fudged):
- E1 (Finding 1): stepbible_tvtms `tvtms.parsed.json` is incomplete relative
  to its own frozen Condensed upstream (Joel/Jonah/Deut KJV-Hebrew range
  rows dropped by the now-quarantined procurement parser). Reconcile to
  342130 now; tvtms-completeness re-procurement is a separate follow-on that
  would later raise the faithful number toward 344799.
- E2 (Finding 4): HAS_SDBH_DOMAIN is a real contracted-but-unimplemented
  edge type. The upstream data exists (244734 sdbh-non-null morphemes,
  inside the catalog band). Recommended retire-now + tracked deferral
  (option B); owner may instead rule it v1-in-scope (option A build), which
  is the single item here that can hard-block a clean Phase D.4 close.

Brethren-on-trial held throughout: every reconciled number is the proven
faithful parse (342130, 5882) read from the bytes, never an adapter fudged
to a wrong catalog number; the one genuinely missing contracted edge type
(SDBH) is surfaced as a real defect with quantified scope, not silently
passed or silently deleted.
