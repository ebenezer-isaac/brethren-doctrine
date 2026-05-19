# Phase D Verse-Key Systemic Audit

Caste: AUDITOR. Scope: READ-ONLY systemic audit of the lexical-graph Verse-key
defect class. Branch main, HEAD 979b00b. Live lexical Neo4j read-only
(bolt://localhost:7688, container lexical-neo4j) holds relaunch-4 data; queries
in this document are SELECT-only, no writes/ingest/wipe. One deliverable: this
file. No git commit.

This audit generalises the single-adapter failure FIX-OPENBIBLE found (commit
704523d) into the whole defect class so relaunch-5 does not serially fail one
adapter at a time at the D.4 / per-edge gate.

## 1. Defect class in one sentence

The lexical graph has THREE Verse producers writing DIFFERENT, partially-NULL
key sets, while EIGHT consumer adapters match the Verse endpoint on a property
that is NULL for an entire canon (NT) or on a property whose book vocabulary
diverges. The FakeDriver test harness never enforced endpoint existence, so
every broken consumer passes CI and silently lands ZERO edges for the affected
verses, only failing at the live D.4 gate.

## 2. Ground truth: producer property matrix

### 2.1 Producers (code-confirmed)

- `ingest/lexical/oshb.py` line 351 `MERGE (n:Verse {id: row.id}) SET n += row`,
  row built at lines 649-660. Canon OT only (`CANON_SECTION = "OT"`, line 333).
- `ingest/lexical/morphgnt.py` line 260 `MERGE (n:Verse {id: row.id}) SET n += row`,
  row built at `_verse_node_row` lines 392-399. Canon NT only
  (`CANON_SECTION = "NT"`, line 234).
- `ingest/lexical/stepbible_proper_nouns.py` line 352
  `MERGE (n:Verse {osisID: row.osisID}) RETURN count(n)` -- note NO `SET`,
  so it writes ONLY `osisID` and nothing else. Third producer; fabricates
  bare stub Verse nodes.

### 2.2 Property matrix (code intent x live-graph confirmation)

Live confirmation query (read-only, run at HEAD 979b00b):

```
MATCH (v:Verse) RETURN coalesce(v.canon_section,'<<NULL>>') AS canon,
  coalesce(v.source,'<<NULL>>') AS source, count(*) AS n,
  count(v.id), count(v.osisID), count(v.osis), count(v.book), count(v.text);
```

| Producer / cohort        | n     | id    | osisID | osis  | book/chapter/verse | text  | source | canon_section |
|--------------------------|-------|-------|--------|-------|--------------------|-------|--------|---------------|
| oshb.py (OT)             | 23213 | 23213 | 23213  | 23213 | 23213              | 23213 | NULL   | "OT"          |
| morphgnt.py (NT)         | 7927  | 7927  | **0**  | 7927  | **0**              | 7927  | 7927   | "NT"          |
| proper_nouns stub cohort | 1928  | **0** | 1928   | **0** | **0**              | **0** | NULL   | NULL          |
| TOTAL                    | 33068 | 31140 | 25141  | 31140 | 23213              | 31140 | 7927   | 31140 (real)  |

Reconciles to the prior FIX-OPENBIBLE finding exactly: 33068 total,
25141 non-null osisID, 7927 NULL osisID (all NT/MorphGNT). The earlier
"31140/31140 id universal" figure counts only the 31140 REAL verses
(23213 OT + 7927 NT); the extra 1928 are id-NULL phantom stubs.

### 2.3 Per-property verdict

- `Verse.id` = `verse:<osisRef>` : populated on ALL 31140 real verses
  (OT 23213 + NT 7927), OSIS-standard book vocabulary (`Gen`, `John`,
  `1Chr`, `1Kgs`), backed by UNIQUE constraint `verse_id`. **Only
  universally-sound join key.** (NULL on the 1928 phantom stubs, which
  carry no real verse text and should never be a join target anyway.)
- `Verse.osis` = `<osisRef>` (bare, no `verse:` prefix): also 31140,
  same OSIS vocabulary, but NOT constraint-backed and bare-formatted.
  Decision 15's own acceptance query keys on `v.osis`.
- `Verse.osisID` = `<osisRef>` : OT-only (23213) plus 1928 phantom
  stubs = 25141. **NULL for every one of the 7927 NT verses.** This is
  the defect-class root.
- `Verse.book` / `chapter` / `verse` : OT-only (23213). morphgnt writes
  NONE of these. Any consumer matching `Verse {book, chapter, verse}`
  is broken for ALL NT.
- `Verse.text` : 31140 (both producers, per Decision 15). Correct.
- `Verse.source` : NT-only (7927). oshb does not write Verse.source.
- `Verse.canon_section` : 31140 ("OT"/"NT"). Correct.

### 2.4 Contractual canonical key (Decision 15 / Decision 5)

- `docs/SCHEMA_DECISIONS.md` Decision 15 "Per-field predicate type ->
  Verse node" table (lines 542-547) lists ONLY `osis`, `text`,
  `canon_section`. It does NOT contractually enumerate `id`, `osisID`,
  `book`, `chapter`, `verse`.
- Decision 15 acceptance Cypher (lines 509-514) keys on `v.osis`
  (`v.osis STARTS WITH 'OT.'`).
- `graph/lexical.cypher` lines 17-18 declare BOTH `verse_id` (v.id
  UNIQUE) and `verse_osisID` (v.osisID UNIQUE), both annotated
  `/* Decision 15 */`, plus index `verse_book_ch_v` on
  (book, chapter, verse) line 75.
- Decision 5 (lines 157-168) governs cross-ref edges; its acceptance
  query is `(:CrossRef)-[:CROSS_REF]->(:Verse)` keyed by edge property
  `osis_target`, and mandates TVTMS reprojection of TSK KJV-numbering
  into "the canonical OSIS reference space adopted by MACULA". It does
  NOT name the Verse-node match property.

Reading: the ONLY Verse-node property Decision 15 contractually
guarantees on every verse is `osis` (bare osisRef). The stable id
`verse:<osisRef>` is the universal Group-1 idempotency id both real
producers actually write (oshb.py line 648, morphgnt.py line 394) and
is constraint-backed. `osisID` is NOT contractually guaranteed for NT
(Decision 15 table omits it; morphgnt was never specced to write it).
The faithful canonical join key is therefore `Verse.id` =
`verse:<osisRef>` (constraint-backed, universal, OSIS vocab),
exactly the reference exemplar fix the openbible commit applied.

## 3. Per-adapter Verse-endpoint table

Every edge in the lexical adapters whose endpoint MATCHes a `:Verse`
node. Classification rule (adversarial: assume BROKEN until the
producer matrix proves SAFE).

| # | File:line | Adapter | Rel | Verse-endpoint match key | Value supplied (format) | Resolves OT? | Resolves NT? | Verdict | Faithful fix |
|---|-----------|---------|-----|--------------------------|--------------------------|--------------|--------------|---------|--------------|
| 1 | oshb.py:375 | oshb (OT) | IN_VERSE | `Verse {id: row.to_id}` | `verse:<osisRef>` | YES (own producer) | n/a (OT only) | **SAFE** | none (reference key) |
| 2 | morphgnt.py:265 | morphgnt (NT) | IN_VERSE | `Verse {id: row.to_id}` | `verse:<osisRef>` | n/a (NT only) | YES (own producer) | **SAFE** | none (reference key) |
| 3 | bhsa.py:416 | bhsa (OT) | IN_VERSE | `Verse {id: row.to_id}` | `verse:<osisRef>` (line 426) | YES (oshb wrote id) | n/a (OT only) | **SAFE** | none |
| 4 | peshitta.py:228 | peshitta (NT) | IN_VERSE | `Verse {osisID: row.to_id}` | bare `<osisRef>` (verse_ref, line 379) | YES if OT row | **NO** (osisID NULL on NT) | **BROKEN-NT + BROKEN-FORMAT** | re-key to `Verse {id}`, value `'verse:'+verse_ref` |
| 5 | coptic_scriptorium.py:385 | coptic (NT-heavy) | IN_VERSE | `Verse {osisID: row.to_id}` | bare `<osisRef>` (verse_ref, line 576) | YES if OT row | **NO** (osisID NULL on NT) | **BROKEN-NT + BROKEN-FORMAT** | re-key to `Verse {id}`, value `'verse:'+verse_ref` |
| 6 | stepbible_tagnt.py:255 | stepbible_tagnt (NT) | IN_VERSE | `Verse {osisID: row.to_id}` | bare `<osisRef>` | n/a (NT corpus) | **NO** (osisID NULL on NT) | **BROKEN-NT** (loses entire adapter) | re-key to `Verse {id}`, value `'verse:'+osisRef` |
| 7 | stepbible_tahot.py:312 | stepbible_tahot (OT) | IN_VERSE | `Verse {osisID: row.to_id}` | bare `<osisRef>` | YES (osisID set on OT) | n/a (OT corpus) | **SAFE-BY-LUCK** (OT-only adapter, osisID populated for OT) | re-key to `Verse {id}` for class consistency + format hardening |
| 8 | stepbible_proper_nouns.py:358 | proper_nouns (OT+NT) | NAMED_AT | `Verse` WHERE `v.osisID = row.osisID` | bare `<osisRef>` | YES if OT | **NO** (osisID NULL on NT) | **BROKEN-NT**; also self-pollutes (line 352 MERGEs osisID-only stub Verses, the 1928 phantom cohort) | re-key NAMED_AT to `Verse {id}`; change line 352 producer MERGE to `Verse {id: 'verse:'+osisID}` or delete the stub MERGE |
| 9 | theographic.py:549 | theographic (OT+NT) | MENTIONS | `Verse {osisID: row.to_id}` | bare `<osisRef>` | YES if OT | **NO** (osisID NULL on NT) | **BROKEN-NT** (every NT Person/Place/Event mention lost) | re-key to `Verse {id}`, value `'verse:'+osisRef` |
| R | openbible.py:307 | openbible (OT+NT) | OPENBIBLE_CROSS_REF | `Verse {osisID: row.from_osis/to_osis}` | bare `<osisRef>` | YES if OT | **NO** (osisID NULL on NT) | **BROKEN-NT + BROKEN-FORMAT** -- REFERENCE EXEMPLAR. NOTE: fix commit 704523d is NOT on main (see section 5); the live HEAD code is still BROKEN | re-key to `Verse {id}` (the 704523d fix) -- must be re-landed on main |

### 3.1 Excluded (verified NOT Verse-endpoint)

- `macula_hebrew.py` HAS_MACULA_ENRICHMENT: joins OSHB `Word.ref`, not
  a `:Verse` node. Correctly excluded.
- `open_cbgm_3_john.py` READS_AT: Witness -> Reading, not Verse.
- `vulgate_clementine.py`: uses separate `:VulgateVerse` label
  (constraint `vulgate_verse_osis`), not `:Verse`. Not in this class.
- `oshb.py` IS_QERE_OF: Reading -> Word, not Verse.

### 3.2 Class tally

- Verse-endpoint sites total: **10** (9 in run-order adapters + 1
  openbible reference).
- **SAFE: 4** -- #1 oshb, #2 morphgnt, #3 bhsa (all match `Verse.id`);
  #7 stepbible_tahot (SAFE-BY-LUCK: OT-only corpus where osisID is
  populated, but still on the fragile key -- harden for class closure).
- **BROKEN: 6** -- all because they match `Verse.osisID`:
  - BROKEN-NT (lose all NT edges): #6 stepbible_tagnt
    (`ingest/lexical/stepbible_tagnt.py:255`), #8 stepbible_proper_nouns
    (`ingest/lexical/stepbible_proper_nouns.py:358`), #9 theographic
    (`ingest/lexical/theographic.py:549`).
  - BROKEN-NT + BROKEN-FORMAT (NULL key on NT AND bare-vs-prefixed
    format): #4 peshitta (`ingest/lexical/peshitta.py:228`),
    #5 coptic_scriptorium (`ingest/lexical/coptic_scriptorium.py:385`),
    #R openbible (`ingest/lexical/openbible.py:307`, reference
    exemplar, fix stranded off-main).
- **Secondary pollution**: #8 proper_nouns line 352 producer MERGE on
  osisID-only is the source of the 1928 id-NULL phantom-stub Verse
  cohort with non-OSIS book abbreviations (`Exo`, `Luk`, `Est`, `1Ki`,
  `1Ch`, `Mat`, `Jdg` vs OSIS `Exod`, `Luke`, `Esth`, `1Kgs`, `1Chr`,
  `Matt`, `Judg`). These phantom stubs corrupt any future osisID match
  and inflate Verse count 33068 vs the true 31140.

## 4. Faithful fix: Option P vs Option C

### Option P (producer fix): morphgnt also writes Verse.osisID

Make `osisID` universal by adding `osisID`, `book`, `chapter`, `verse`
to `morphgnt._verse_node_row` (lines 392-399). One producer edit;
every osisID-matching consumer then resolves NT.

REJECTED as the primary fix, for faithfulness reasons:

1. **Decision-15 non-sanction.** Decision 15's contractual Verse-node
   per-field table (`docs/SCHEMA_DECISIONS.md` lines 542-547) lists
   exactly `osis`, `text`, `canon_section`. It does NOT list `osisID`,
   `book`, `chapter`, `verse` for the MorphGNT producer. The MorphGNT
   docstring (`morphgnt.py` lines 55-70) is explicit that the NT Verse
   node carries `osis`, `text`, `canon_section` only. Making morphgnt
   write `osisID`/`book` ADDS Verse properties Decision 15 never
   sanctioned for the NT producer -- a data-model change, not a fix.
2. It does not remove the fragile dependency on a property whose
   presence varies by canon; it only papers over today's NULL. The
   next NT-only Verse producer would reintroduce the class.
3. It does not address BROKEN-FORMAT (bare osisRef vs `verse:`-prefixed)
   nor the 1928 phantom-stub pollution from proper_nouns line 352.
4. The phantom stubs already occupy osisID values with NON-OSIS
   vocabulary (`Mat.23.35`, `Luk.1.5`); writing real osisID from
   morphgnt under the `verse_osisID` UNIQUE constraint could now
   COLLIDE with a phantom stub of a divergent abbreviation, or worse
   merge a real NT verse onto a mis-abbreviated stub. Option P is
   actively risky against the current polluted live state.

### Option C (consumer fix): every broken consumer re-keys to Verse.id

Re-key every BROKEN consumer's Verse-endpoint MATCH from
`Verse {osisID: <bare>}` to `Verse {id: 'verse:' + <osisRef>}`.

**RECOMMENDED.** Decision-15 rationale:

- `Verse.id` = `verse:<osisRef>` is the universal stable id BOTH real
  producers actually write for every verse (oshb.py:648,
  morphgnt.py:394), it is the Group-1 idempotency id named in
  `docs/implementation_phases/phase_02_lexical_ingest.md` Idempotency
  section, and it is backed by the `verse_id` UNIQUE constraint
  (`graph/lexical.cypher` line 17, `/* Decision 15 */`). It carries
  consistent OSIS-standard book vocabulary on all 31140 real verses
  (live-confirmed: `verse:John.1.1`, `verse:Gen.1.1`).
- It is exactly the canonical key the openbible reference exemplar fix
  (commit 704523d) chose, with the same Decision-15 reasoning recorded
  in that commit message.
- It touches only consumer adapters (this audit's allowed-by-class
  surface), changes ZERO producer contracts, and does NOT add any
  Verse property Decision 15 omits.
- It simultaneously closes BROKEN-NT (id is non-NULL for NT),
  BROKEN-FORMAT (every consumer adopts the single `verse:`-prefixed
  OSIS form), and starves the phantom-stub pollution (consumers MATCH
  -- never MERGE -- so an unresolved id stays quarantined, never
  fabricated).

Decision-15 authorisation status: the Decision-15 Verse-node field
table does not name the consumer join key, but it sanctions `osis` and
the constraint layer sanctions `verse_id`; `verse:<osisRef>` is the
mechanical join form of the Decision-15 `osis` value under the
constraint-backed stable id. Option C is therefore the
**Decision-15-authorised faithful fix and is sanctioned** -- it does
not change the data model, only routes consumers to the
already-contractual universal key. No data-model-owner escalation is
required to adopt Option C.

## 5. MUST-ESCALATE items

1. **The openbible reference fix is NOT on main.** Commit 704523d
   ("fix: openbible OPENBIBLE_CROSS_REF resolves all faithful Verse
   endpoints") exists only on detached worktree branch
   `worktree-agent-a6f84b20e3c4378d4`; it is NOT in main's history
   (HEAD 979b00b). The live `ingest/lexical/openbible.py:307` on main
   STILL reads `MATCH (a:Verse {osisID: row.from_osis}), (b:Verse
   {osisID: row.to_osis})` -- i.e. the exemplar everyone is treating as
   "already fixed" is in fact still broken on the branch relaunch-5
   will ship from. ESCALATE: the 704523d fix must be cherry-picked /
   re-landed on main, or relaunch-5 reproduces the original openbible
   failure verbatim.

2. **`verse_osisID` UNIQUE constraint is a latent secondary defect.**
   `graph/lexical.cypher` line 18 declares `verse_osisID` UNIQUE on
   `v.osisID`. Live: 7927 NT Verse nodes have `osisID IS NULL`
   (confirmed: `MATCH (v:Verse) WHERE v.osisID IS NULL RETURN
   count(v)` = 7927). Neo4j UNIQUE constraints DO NOT apply to NULL
   property values, so 7927 NULLs do not violate it and no error ever
   surfaces -- which is precisely why this class stayed invisible. Net
   effect: the `verse_osisID` constraint provides ZERO uniqueness or
   presence protection for the entire NT canon and actively masks the
   defect. This is latent, not a crash, but it means the constraint is
   misleading as written. ESCALATE for a data-model decision: either
   (a) drop/replace `verse_osisID` (canonical identity is already
   `verse_id`), or (b) if osisID must be a first-class universal key,
   that is a Decision-15 amendment plus Option P -- a data-model-owner
   call, not an adapter fix. Recommendation: drop reliance on
   `verse_osisID`; `verse_id` is the sound constraint.

3. **1928 phantom-stub Verse nodes already in the live graph.**
   id-NULL, osis-NULL, text-NULL, non-OSIS abbreviation osisID
   (`Exo`/`Luk`/`Mat`/`1Ch`...). Source: osisID-only MERGEs, primarily
   `stepbible_proper_nouns.py:352`. Live (relaunch-4) data is
   read-only per constraints so this audit does not clean it, but
   relaunch-5 must (a) fix proper_nouns line 352 to stop producing
   them and (b) start from a clean reseed so the 33068 vs true 31140
   discrepancy and the abbreviation collision risk do not persist.
   Flag for the relaunch-5 reseed plan.

## 6. FIX WAVE (single-touch, one task per file)

Option C. Each task is one file, the Verse-endpoint MATCH re-keyed to
`Verse {id: 'verse:' + <osisRef>}` and the supplied value prefixed
with `verse:` (if not already). Re-ingest is required for the live
fix to take effect (relaunch-5 reseed). No producer file is touched
except proper_nouns (its line 352 IS a producer defect inside the
class).

1. `ingest/lexical/openbible.py` -- re-land commit 704523d (re-key
   `_MERGE_EDGE` line 307 to `Verse {id}` with `verse:`-prefixed
   from_id/to_id; the full faithful fix already exists on
   `worktree-agent-a6f84b20e3c4378d4`). HIGHEST PRIORITY: it is the
   exemplar and is currently broken on main.
2. `ingest/lexical/peshitta.py` -- `_MERGE_IN_VERSE` line 228:
   `Verse {osisID: row.to_id}` -> `Verse {id: row.to_id}`; build
   `to_id` as `verse:<verse_ref>` (line 379).
3. `ingest/lexical/coptic_scriptorium.py` -- `_MERGE_IN_VERSE` line
   385: same re-key; build `to_id` as `verse:<verse_ref>` (line 576).
4. `ingest/lexical/stepbible_tagnt.py` -- `_MERGE_IN_VERSE` line 255:
   re-key to `Verse {id}`; prefix supplied value with `verse:`.
5. `ingest/lexical/stepbible_tahot.py` -- `_MERGE_IN_VERSE` line 312:
   re-key to `Verse {id}`; prefix with `verse:`. (SAFE-BY-LUCK today
   but harden for class closure and format consistency.)
6. `ingest/lexical/theographic.py` -- `_MERGE_MENTIONS_TEMPLATE` line
   549: `Verse {{osisID: row.to_id}}` -> `Verse {{id: row.to_id}}`;
   prefix supplied value with `verse:`.
7. `ingest/lexical/stepbible_proper_nouns.py` -- TWO changes in the
   one file: (a) `_MERGE_NAMED_AT` line 358
   `WHERE v.osisID = row.osisID` -> `WHERE v.id = row.id` with
   `verse:`-prefixed value; (b) `_MERGE_VERSE` line 352
   `MERGE (n:Verse {osisID: row.osisID})` -> delete this stub-producer
   MERGE entirely (Verse nodes are produced by oshb/morphgnt; this
   adapter should MATCH only, never create stubs) OR, if a stub is
   genuinely required, MERGE on `Verse {id: 'verse:'+osisID}` so it
   joins the canonical key space instead of fabricating non-OSIS
   phantoms.
8. (Verification, not a code task) After the wave, re-run the live
   confirmation queries post-reseed: expect `count(v) = 31140`
   (no phantoms), `count(v.id) = 31140`, every IN_VERSE / NAMED_AT /
   MENTIONS / CROSS_REF / OPENBIBLE_CROSS_REF NT edge count > 0.
9. (Escalation tasks, owner-gated, NOT in this code wave) Re-land
   704523d on main (section 5 item 1); decide `verse_osisID`
   constraint disposition (section 5 item 2); ensure relaunch-5
   reseeds from clean to purge the 1928 phantom stubs (section 5
   item 3).

Closing this 7-file wave (plus the 3 escalations) closes the entire
Verse-key class before relaunch-5, so relaunch-5 does not serially
fail per-adapter at D.4 the way openbible did.
