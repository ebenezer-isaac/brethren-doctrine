# Phase D Harness Triage

Caste: auditor. READ-ONLY triage. Branch main, HEAD 02ebae8. Doctrinal
frame: brethren-on-trial. No em or en dashes anywhere.

Purpose: classify each of the 6 inconsistencies flagged in
`docs/PHASE_D_VERIFICATION_HARNESS.md` Section 5 as either COSMETIC
(doc/stale-text, no gate impact, note-only) or REAL DEFECT (will make a
Phase D gate produce a wrong verdict, must be fixed before D.4). The
Phase D.4 count gate and per-edge gate run as soon as the live lexical
ingest finishes, so each flag is classified for its impact on the gate
sequence in `docs/PHASE_D_VERIFICATION_HARNESS.md` Section 4.

Method: each flag verified independently from the bytes. Three-way
evidence per flag = catalog (`tools/expected_counts.json`) vs phase_02 /
harness acceptance Cypher vs adapter source. Gate tooling read directly:
`tools/snapshot_counts.py`, `tools/check_thresholds_immutable.py`,
`ingest/lexical/run.py`, and the per-adapter `SOURCE_SLUG` constants.

Key cross-cutting fact established up front (governs flags 1, 3):
the Phase D gate sequence in the harness Section 4 is

1. `tools/check_thresholds_immutable.py` (CLI, SHA of expected_counts).
2. Section 1 count gate: 24 hand-written concrete Cypher queries that
   use the adapter-authoritative `SOURCE_SLUG` strings (NOT run.py, NOT
   the expected_counts source-name keys mechanically).
3. Section 2 acceptance Cyphers, copied verbatim from phase_02.
4. Section 3 per-edge correctness, written against the edges the
   adapters actually emit.
5. Triangle test via `tools/snapshot_counts.py`, which enumerates
   labels through `db.labels()` and rel types through
   `db.relationshipTypes()` DYNAMICALLY and asserts
   p1.overall_hash == p2.overall_hash. It never reads a source-name
   string or an edge_counts key.

A full-repo search confirms `--verify-only` / `verify_only` appears in
NO file under `tools/` and NOT in
`docs/implementation_phases/phase_02_lexical_ingest.md`. The only
definition and only reference is inside `ingest/lexical/run.py` itself.
No Phase D gate step shells `run.py --verify-only`.

---

## Flag 1: run.py --verify-only stale slug strings + stale EXPECTED_COUNTS dict

### Three-way evidence

- Adapter source bytes (authoritative `SOURCE_SLUG` constants, read
  directly): `oshb.py` = `OSHB-morphology`; `macula_hebrew.py` =
  `MACULA-Hebrew`; `macula_greek.py` = `MACULA-Greek-Nestle1904` and
  `MACULA-Greek-SBLGNT` (one adapter, two edition slugs);
  `morphgnt.py` = `MorphGNT-SBLGNT`; `stepbible_tahot.py` =
  `STEPBible-TAHOT`; `stepbible_tagnt.py` = `STEPBible-TAGNT`;
  `stepbible_ttesv.py` = `STEPBible-TTESV`; `stepbible_proper_nouns.py`
  = `STEPBible-proper-nouns`; `theographic.py` =
  `Theographic-Bible-Metadata`; `openbible.py` = `OpenBible-cross-refs`
  (stamped on the `OPENBIBLE_CROSS_REF` edge, node-less adapter);
  `tsk.py` = `TSK` (on `CrossRef` nodes and the `CROSS_REF {source}`
  edge). These are inventory-name style verbatim.
- run.py `--verify-only` block (lines 182 to 204) queries
  `{source:'macula-hebrew'}`, `{source:'macula-greek-sblgnt'}`,
  `{source:'morphgnt-sblgnt'}`, `[:CROSS_REF {source:'openbible'}]`,
  `[:CROSS_REF {source:'tsk'}]`. None of those slug-style strings is
  emitted by any adapter. Against the real graph this block returns 0
  for macula_hebrew_words, macula_greek_sblgnt_words, morphgnt_words,
  and openbible_crossrefs (note: tsk would coincidentally return 0 too
  because the slug is `'tsk'` not `'TSK'`, and the actual TSK edge type
  is `CROSS_REF` with `source:'TSK'`, so the lowercase literal misses).
- run.py in-code `EXPECTED_COUNTS` dict (lines 120 to 127) carries
  pre-reconciliation ranges (`macula_hebrew Word 300000..320000`,
  `openbible CrossRef 600000..620000`, `tsk CrossRef 590000..610000`)
  that contradict the reconciled `tools/expected_counts.json` (OSHB
  305507, OpenBible 344799 edges, TSK 63682 nodes). `_verify()` is only
  called inside the normal ingest path (line 216) and only for the 6
  keys in that dict; it prints `VERIFY FAIL` but the return value is
  discarded and `main()` returns 0 regardless. It is non-gating noise.
- The Phase D Section 1 count gate uses its own 24 concrete Cypher
  queries built on the authoritative `SOURCE_SLUG` strings, not run.py.
  The triangle test (`snapshot_counts.py`) does not import run.py's
  verify path; it dynamically enumerates labels and rel types.

### Classification: COSMETIC (latent dead code, zero gate impact)

The stale `--verify-only` block and the stale in-code `EXPECTED_COUNTS`
dict are NEVER on any Phase D acceptance path. No gate step invokes
`run.py --verify-only`. The normal-ingest `_verify()` print is
swallowed (return value unused, exit 0 unconditional). The harness
Section 1 deliberately bypasses run.py entirely. Therefore the gate
verdict is unaffected.

Residual risk note (not a D.4 blocker): the dead block is a future
foot-gun. If anyone later wires `run.py --verify-only` as a gate it
would report 0 for everything and false-pass nothing / false-fail
everything. Recommend an implementer cleanup commit AFTER D.4 to either
delete the `--verify-only` block and the stale `EXPECTED_COUNTS` dict or
align them to the reconciled slugs/counts. Owning caste: implementer
(code change, post-D.4, non-blocking). Doc-only note acceptable in the
interim.

### Exact source string each adapter writes (authoritative)

| Source | Node/edge it lands on | Exact `source` value |
|---|---|---|
| oshb | `Word` | `OSHB-morphology` |
| macula_hebrew | `MaculaToken`, `Lemma`, `GreekLemma` (and `BRIDGES_LXX` edge) | `MACULA-Hebrew` |
| macula_greek | `Word` | `MACULA-Greek-Nestle1904` and `MACULA-Greek-SBLGNT` |
| morphgnt | `Word` | `MorphGNT-SBLGNT` |
| stepbible_tahot | `TaggedToken` | `STEPBible-TAHOT` |
| stepbible_tagnt | `TaggedToken` | `STEPBible-TAGNT` |
| stepbible_ttesv | `TaggedToken` | `STEPBible-TTESV` |
| stepbible_proper_nouns | `ProperNoun` | `STEPBible-proper-nouns` |
| theographic | `Person`/`Place`/`Event`/`Group`/`Tribe`/`Period` | `Theographic-Bible-Metadata` |
| openbible | `OPENBIBLE_CROSS_REF` edge (node-less) | `OpenBible-cross-refs` |
| tsk | `CrossRef` node + `CROSS_REF` edge | `TSK` |

---

## Flag 2: MACULA-Hebrew record_unit ambiguity (475911 morpheme vs MaculaToken node)

### Three-way evidence

- Catalog: `sources["MACULA-Hebrew"]` tier A, tolerance 0, record_unit
  `morpheme`, expected_count 475911, min == max == 475911.
- Adapter source (`macula_hebrew.py`): emits one `MaculaToken` node per
  `<w>` element in the WLC lowfat TEI (`_word_to_row`, `_iter_words`,
  `_collect_rows` deduped by verbatim `xml:id`). Every MaculaToken row
  carries `source = SOURCE_SLUG = "MACULA-Hebrew"` explicitly
  (`_word_to_row` sets `"source": SOURCE_SLUG`, and `_token_payload`
  keeps it because it does not start with `_`). So contrary to the
  harness Note A / Section 5 item 2 worry, the live `MaculaToken` node
  DOES carry `source = 'MACULA-Hebrew'`. The adapter does not emit a
  primary `Word` of its own; `HAS_MACULA_ENRICHMENT` hangs off
  `Word {source:'OSHB-morphology'}`. The morpheme enumeration the
  catalog calls 475911 is the MaculaToken node population.
- Harness Section 1 row 2 gates `MATCH (n:MaculaToken) RETURN count(n)`
  == 475911 (label-only, the safe form). Section 2 step 2 asserts
  `(:Word {source:'OSHB-morphology'})-[:HAS_MACULA_ENRICHMENT]->
  (:MaculaToken)` count > 0.

### Classification: COSMETIC (label-only count is correct; slug worry is unfounded)

The 475911 tier-A gate counts `MaculaToken` nodes. The adapter emits
exactly one `MaculaToken` per upstream `<w>` (deduped by `xml:id`),
which IS the MACULA-Hebrew morpheme enumeration the catalog
record_unit names. The harness label-only query
`MATCH (n:MaculaToken) RETURN count(n)` counts the right node type.
`MaculaToken` is a label unique to this adapter (no other adapter emits
it), so the label-only count cannot be polluted by another source.

Sub-finding correcting the harness Note A / Section 5 item 2: the
harness states the `MaculaToken` `source` property is "not
unambiguously stated in the contract". That ambiguity is resolved by
the executable body: `_word_to_row` stamps `"source": SOURCE_SLUG`
("MACULA-Hebrew") on every token row and `_token_payload` retains it.
The `MATCH (n:MaculaToken {source:'MACULA-Hebrew'}) RETURN count(n)`
form is therefore also valid and would be the slightly stricter gate.
Either form gives 475911 on a faithful ingest. No gate false-fails a
faithful ingest from this flag. Note-only; no fix required before D.4.

Caveat carried forward (not from this flag, see flag dependency note):
the 475911 figure itself is the catalog number. It is NOT one of the 7
reconciled sources in `PHASE_D_CATALOG_RECONCILIATION.md` and was not
independently re-derived in `AUDIT_phase_d_preflight_verification.md`.
Its correctness as the true upstream `<w>` count over the frozen
MACULA-Hebrew lowfat release is asserted by the catalog tier_rationale
("exact element count straight from the upstream file") but is NOT
auditor-reproduced in any doc on disk. This is a pre-existing catalog
trust gap, not a defect introduced by the flag, and is the same class
of "tier-A 0-tolerance on an un-reproduced upstream count" risk as
flag 6 but lower risk because MaculaToken is a 1:1 node emit per `<w>`
(deterministic element count, not an occurrence-rate enrichment). Noted
for the architect's awareness; does not block D.4 on the strength of
this flag alone.

---

## Flag 3: edge-name divergence HAS_CLAUSE / HAS_PHRASE vs CONTAINS_PHRASE / CONTAINS_WORD

### Three-way evidence

- Catalog: `edge_counts` block has keys `HAS_CLAUSE` (tier B, min
  71500, max 74500) and `HAS_PHRASE` (tier B, min 248000, max 256000).
  Their `tier_rationale` text explicitly says HAS_CLAUSE "comes from
  the clause otype feature, a join over the word-to-clause containment
  edges" and HAS_PHRASE "comes from the phrase otype feature". These
  describe NODE populations (BhsaClause count, BhsaPhrase count), not a
  literal relationship type.
- Adapter source (`bhsa.py`): the only relationship types emitted are
  `CONTAINS_PHRASE` (BhsaClause -> BhsaPhrase), `CONTAINS_WORD`
  (BhsaPhrase -> BhsaWord), and `IN_VERSE` (BhsaWord -> Verse). There
  is NO `HAS_CLAUSE` and NO `HAS_PHRASE` relationship anywhere in
  `bhsa.py` (or any adapter). The bhsa.py docstring itself (lines 196
  to 198) says the floors "live at tools/expected_counts.json
  edge_counts.HAS_CLAUSE, edge_counts.HAS_PHRASE" and maps
  CONTAINS_PHRASE cardinality to `edge_counts.HAS_PHRASE` and
  CONTAINS_WORD count to the source expected_count 426590. So the
  adapter author already treats HAS_CLAUSE/HAS_PHRASE as proxy floors,
  not literal edge types.
- phase_02 step 14 / harness Section 2 step 14 acceptance Cypher
  traverses `(:BhsaClause)-[:CONTAINS_PHRASE]->(:BhsaPhrase)-
  [:CONTAINS_WORD]->(:BhsaWord)` (the names the adapter emits). Harness
  Section 3.11 asserts CONTAINS_PHRASE / CONTAINS_WORD.
- Gate tooling: the Section 1 count gate has NO row for HAS_CLAUSE or
  HAS_PHRASE (Section 1 is the 24 source rows only; the `edge_counts`
  block is not enumerated as a Section 1 tier-A gate). Section 2 and
  Section 3 use only CONTAINS_PHRASE / CONTAINS_WORD. The triangle test
  (`snapshot_counts.py`) enumerates rel types via
  `db.relationshipTypes()` dynamically and only diffs p1 vs p2 on
  whatever exists; it would record `CONTAINS_PHRASE` /
  `CONTAINS_WORD` (the real types) and never query `HAS_CLAUSE`.

### Classification: COSMETIC (edge_counts keys are node-count proxies, never gated as literal edges in Phase D)

No Phase D gate step issues `MATCH ()-[:HAS_CLAUSE]->()` or
`MATCH ()-[:HAS_PHRASE]->()`. The harness Section 4 gate sequence does
NOT gate the `edge_counts` block at tier-A: Section 1 is the 24 source
rows; Section 2 / Section 3 use the adapter-real CONTAINS_PHRASE /
CONTAINS_WORD names. The `edge_counts.HAS_CLAUSE` /
`edge_counts.HAS_PHRASE` keys are documentary node-population floors
(BhsaClause ~ 71500..74500, BhsaPhrase ~ 248000..256000) whose
rationale text describes otype node counts, not relationship traversal.
No faithful-ingest false-fail is produced by this flag in the harness
Section 4 sequence.

Residual risk note (not a D.4 blocker): the naming is a genuine
documentation trap. The keys `HAS_CLAUSE`/`HAS_PHRASE` read like
relationship types but mean BhsaClause/BhsaPhrase node counts. Any
future tool that mechanically iterates `expected_counts.json
edge_counts` and runs `MATCH ()-[:<key>]->()` would read 0 and
false-fail. Recommend a doc/architect [SCHEMA-REVISION] AFTER D.4 to
either rename the keys to node-count semantics (for example
`BhsaClause_nodes` / `BhsaPhrase_nodes`) or add an explicit
`semantics: "node_count"` discriminator. Owning caste: architect
[SCHEMA-REVISION] for the rename, or doc caste for a clarifying note;
non-blocking for D.4 because no D.4 gate consumes these keys.

---

## Flag 4: open-cbgm doc staleness (reconciliation "architect to confirm" vs committed 728 / 700..760)

### Three-way evidence

- Catalog: `sources["open-cbgm-3-john"]` is COMMITTED: tier B,
  expected_count 728, explicit envelope min 700 / max 760,
  `catalog_source_index: null`, tier_rationale states node-only
  (Witness + VariantUnit + Reading), explicitly records that "the prior
  hand-set 600 with 588 and 612 envelope had no derivation" and that
  catalog_source_index null is intentional (the previous index 3
  mis-pointed at MorphGNT). The old 600 / 588 / 612 numbers are NOT in
  the committed file anywhere.
- `PHASE_D_CATALOG_RECONCILIATION.md` section 6 still says "architect
  to confirm the node-only definition" and frames node-only vs
  node+edge as an open decision. That doc predates the committed
  [SCHEMA-REVISION].
- `AUDIT_phase_d_preflight_verification.md` independently reproduced
  728 nodes (142 Witness + 116 VariantUnit + 470 Reading) from
  `tmp/poc/cbgm` via `_parse_units` / `_build_payloads`.
- Harness Section 1 row 21 gates `700 <= live <= 760` (tier B explicit
  envelope) on the node-only sum, consistent with the committed file,
  not the old 600/612.

### Classification: COSMETIC (pure doc staleness; the committed catalog and the harness already use 728 / 700..760)

The only thing stale is the prose in `PHASE_D_CATALOG_RECONCILIATION.md`
section 6 ("architect to confirm"). The actual gate input
(`expected_counts.json`) and the harness both use the committed
node-only 728 within 700..760, independently reproduced by the audit.
No Phase D gate reads 600 / 588 / 612 (those literals are absent from
the committed file). No faithful-ingest false-fail. Note-only; the
reconciliation doc can be updated post-D.4 to record the decision as
closed. Owning caste: doc (post-D.4, non-blocking).

---

## Flag 5: STEPBible-TAHOT triple-number tension (283704 vs 283721 vs 283734)

### Three-way evidence

- Catalog: `sources["STEPBible-TAHOT"]` tier A, tolerance 0,
  expected_count 283721, min == max == 283721. tier_rationale states
  283734 raw minus 13 empty-Strong Q(K) predicate drops == 283721, and
  that the =X-over-=L stable-id collapse was fixed in commit a277a96.
- `PHASE_D_CATALOG_RECONCILIATION.md` section 5 recommends 283704
  (option b, drop 30 rows). That doc predates the a277a96 collapse fix
  and the preflight audit; it is explicitly superseded.
- `AUDIT_phase_d_preflight_verification.md` independently re-derived
  from the frozen TAHOT bytes: emit 283721, distinct 283721, collisions
  0; raw qualifying ref-rows 283734; 283734 - 13 faithful empty-Strong
  =Q(K) predicate drops == 283721; drop forensics show 13 drops all
  `pred:ketiv+strong+morph`, 0 dedup drops; the 17 =L words formerly
  overwritten by 17 =X are now distinct ids (a277a96 took). Final GO:
  baseline expected_count = 283721. Determinism: 283721 across two
  runs.
- Harness Section 1 row 6 gates `MATCH (n:TaggedToken
  {source:'STEPBible-TAHOT'}) RETURN count(n)` == 283721 exactly.

### Classification: COSMETIC (only the superseded reconciliation doc still shows 283704; every gate uses 283721)

The single number any Phase D gate uses is 283721 (from
`expected_counts.json`, harness Section 1 row 6). The live adapter
emits 283721 deterministically per the independent auditor
reproduction. 283704 exists only as the superseded option-b
recommendation in `PHASE_D_CATALOG_RECONCILIATION.md` (which itself
documents it as predating a277a96). 283734 is the raw line count, used
nowhere as a gate target. No gate reads 283704 or 283734. No
faithful-ingest false-fail. Note-only; the reconciliation doc should be
marked superseded post-D.4. Owning caste: doc (post-D.4, non-blocking).

---

## Flag 6: ETCBC-phono tier-A 0-tolerance on non-null-phono BhsaWord == 426590

### Three-way evidence (highest risk; verified from adapter bytes + audit docs + frozen-upstream contract)

- Catalog: `sources["ETCBC-phono"]` tier A, tolerance 0,
  expected_count 426590, min == max == 426590. tier_rationale: "ETCBC
  phonetic transcription ships one phono value per BHSA word slot ...
  Total equals the BHSA word slot count exactly because the feature is
  keyed one-to-one with word identifiers."
- Adapter docstring (`etcbc_phono.py`) directly CONTRADICTS the catalog
  tier_rationale. It states REPEATEDLY and explicitly that phono is NOT
  1:1: lines 61 to 66 "ETCBC-phono ships a single 'phono' field at
  0.984 occurrence rate ... the 1.6 percent null rate reflects
  ketiv-only slots with no spoken realisation"; lines 100 to 111 phono
  is "NULLABLE per Decision 3 ... 1.6 percent of word slots are
  ketiv-only and have no spoken realisation, so the property is set to
  null"; lines 201 to 211 "no fallback substitution ... so
  $pred_string(phono) returns false on the ketiv-only slots honestly".
  The bhsa.py docstring lines 99 to 105 and 266 to 273 agree: phono is
  attached "at 0.984 occurrence rate" and "the 1.6 percent null rate
  reflects ketiv-only slots".
- Adapter executable body (`etcbc_phono.py` lines 320 to 356):
  `_parse_phono_feature` builds a `dict[int,str]` only for node ids
  that actually appear in the phono text-fabric feature. Then
  `_load_phono_rows` iterates EVERY word slot
  `range(WORD_NODE_MIN=1, WORD_NODE_MAX+1=426591)` and emits
  `{"id": f"bhsa:tf:{node_id}", "phono": _phono_value(values.get(
  node_id, ""))}`. `_phono_value(raw)` returns `raw if raw.strip()
  != "" else None`. So for every ketiv-only slot missing from the
  feature (`values.get(node_id, "")` -> `""`), the adapter SETs
  `w.phono = None`. The `_ATTACH_PHONO` Cypher does
  `SET w.phono = row.phono`; setting a Neo4j property to `None`
  REMOVES the property (leaves it null / IS NULL).
- Harness Section 1 row 20 gate:
  `MATCH (n:BhsaWord) WHERE n.phono IS NOT NULL AND
  trim(toString(n.phono)) <> "" RETURN count(n)` compared `== 426590`
  exactly, tier A tolerance 0.
- Audit docs: `AUDIT_phase_d_preflight_verification.md` does NOT
  reproduce the phono count at all (its four commits are tahot, run.py
  wiring, dead-module quarantine, ttesv). `PHASE_D_CATALOG_RECONCILIATION.md`
  covers 7 sources; ETCBC-phono is NOT one of them. There is NO doc on
  disk that independently re-derives the non-null phono count from the
  frozen text-fabric phono module.

### Classification: REAL DEFECT (tier/tolerance misclassification; tol-0 gate will false-fail a faithful ingest)

Phono is provably NOT one-to-one with all 426590 BHSA word slots. The
adapter's own contract and executable body state and implement a 0.984
occurrence rate: roughly 1.6 percent of word slots (on the order of
~6800 ketiv-only slots) are faithfully written with `phono = null`.
A faithful ingest will therefore land approximately 0.984 x 426590
~= 419774 BhsaWord nodes with non-null phono, NOT 426590.

The harness Section 1 row 20 gate asserts non-null-phono count ==
426590 at tier A tolerance 0. On a perfectly faithful ingest this gate
computes roughly 419774 != 426590 and HARD FAILS. This is exactly the
fragility flagged, now confirmed from the bytes: the catalog
tier_rationale's "keyed one-to-one" claim is FALSE per the adapter's
own Decision 3 contract. The 426590 is the BHSA word SLOT count
(correct for `sources["ETCBC-BHSA"]` row 18, which counts BhsaWord
nodes), but it is the WRONG target for "BhsaWord with non-null phono".

This is the same class as the original 7 catalog reconciliations
(catalog number does not match the adapter's faithful record_unit),
and it is a hard pre-D.4 blocker because Phase D Section 4 step 2 runs
the Section 1 gate the moment ingest completes and any tier-A mismatch
is a hard FAIL that voids the gate verdict.

Note the harness internal tension that corroborates the defect: harness
Section 2 step 16 (the phase_02 acceptance Cypher) is the PERMISSIVE
`with_phono > 0` form, and the etcbc_phono.py docstring lines 240 to
243 explicitly say the acceptance gate is intentionally permissive
"so the Tier A deterministic count of 426590 ... is the binding floor,
not this acceptance query". The binding floor is precisely the
mis-set number.

### Exact gate that breaks, exact fix, owning caste, blocking status

- Gate that breaks: `docs/PHASE_D_VERIFICATION_HARNESS.md` Section 1
  row 20 (ETCBC-phono), driven by
  `tools/expected_counts.json sources["ETCBC-phono"]` tier A,
  expected_count 426590, tolerance 0. Phase D Section 4 step 2.
- Exact fix (architect [SCHEMA-REVISION] on `tools/expected_counts.json`,
  same change class and same commit family as
  PHASE_D_CATALOG_RECONCILIATION.md): ETCBC-phono must NOT be gated as
  tier A tolerance 0 against 426590. Two architect-legitimate options,
  mirroring the reconciliation doc's pattern:
  (a) Re-baseline expected_count to the faithful non-null phono emit
      (the deterministic count of word slots present in the frozen
      phono.tf feature, which an auditor must reproduce offline from
      `C:/Users/Ebenezer/text-fabric-data/github/ETCBC/phono/tf/2021/
      phono.tf` before the number is set), keep tier A tolerance 0,
      record_unit clarified to "word slot with spoken realisation
      (non-null phono)". This is the option-b analogue and keeps a
      0-tolerance gate.
  (b) Keep 426590 as the SLOT-coverage target but gate ETCBC-phono on
      total BhsaWord touched (every slot is written, ~1.6 percent with
      explicit null), i.e. gate `MATCH (n:BhsaWord) RETURN count(n)`
      == 426590 (which is already what ETCBC-BHSA row 18 gates), and
      drop the separate non-null-phono tier-A 0 gate, or move
      ETCBC-phono to a tier with an explicit envelope that brackets the
      0.984 rate. The harness Section 1 row 20 Cypher would then change
      from the non-null filter to a slot-coverage assertion.
  The architect must pick the definition and (for option a) an auditor
  must reproduce the exact non-null count from the frozen phono.tf
  before the number is committed. The fix MUST NOT touch the adapter
  (the adapter is faithful: it honestly writes null for ketiv-only
  slots per Decision 3, exactly as the original brethren-on-trial
  reconciliations protect faithful parses).
- Owning caste: architect [SCHEMA-REVISION] on
  `tools/expected_counts.json` (the catalog), plus an auditor offline
  reproduction of the true frozen-upstream non-null phono count to
  supply the number. Verifier/harness then updates Section 1 row 20
  Cypher to match the chosen definition.
- Blocks D.4: YES. Hard pre-D.4 blocker. The Section 1 count gate runs
  the moment ingest finishes; with the catalog unchanged this row is a
  guaranteed false-fail on a faithful ingest, and a tier-A mismatch
  hard-fails and voids the overall gate verdict. Must be reconciled
  before the Phase D count gate can be trusted, in the same
  [SCHEMA-REVISION] family as the original 7 (it is an 8th
  reconciliation item that the 7-source doc missed).

---

## TRIAGE SUMMARY

| Flag | Class | Gate impact | Blocks D.4? | Owning caste | Fix one-liner |
|---|---|---|---|---|---|
| 1 run.py --verify-only stale slugs + EXPECTED_COUNTS dict | COSMETIC (latent dead code) | None: no gate invokes run.py --verify-only; harness uses authoritative SOURCE_SLUG | No | implementer (post-D.4) | Delete or realign the dead --verify-only block and stale EXPECTED_COUNTS dict |
| 2 MACULA-Hebrew record_unit / MaculaToken source ambiguity | COSMETIC (ambiguity resolved by adapter body) | None: MaculaToken label-only count is correct and unique; adapter does stamp source='MACULA-Hebrew' | No | doc (note) | Note that MaculaToken carries source='MACULA-Hebrew'; label-only count == 475911 is correct |
| 3 HAS_CLAUSE/HAS_PHRASE vs CONTAINS_PHRASE/CONTAINS_WORD | COSMETIC (edge_counts keys are node-count proxies) | None: no D.4 gate queries HAS_CLAUSE/HAS_PHRASE as edges | No | architect [SCHEMA-REVISION] or doc (post-D.4) | Rename edge_counts keys to node-count semantics or add semantics discriminator |
| 4 open-cbgm reconciliation "architect to confirm" staleness | COSMETIC (pure doc staleness) | None: committed catalog + harness already use 728 / 700..760 | No | doc (post-D.4) | Mark PHASE_D_CATALOG_RECONCILIATION.md section 6 decision as closed |
| 5 TAHOT 283704 vs 283721 vs 283734 | COSMETIC (only superseded doc shows 283704) | None: every gate uses 283721; adapter emits 283721 | No | doc (post-D.4) | Mark reconciliation doc section 5 option-b as superseded by 283721 |
| 6 ETCBC-phono non-null-phono == 426590 tier A tol 0 | REAL DEFECT (tier/tolerance misclassification) | Section 1 row 20 hard-FAILS a faithful ingest (~419774 != 426590) | YES | architect [SCHEMA-REVISION] on expected_counts.json + auditor reproduces true count | Re-baseline ETCBC-phono off 426590 tol-0 (phono is 0.984 not 1:1; ketiv-only slots are faithfully null) |

### Counts

- REAL DEFECT: 1 (flag 6).
- COSMETIC: 5 (flags 1, 2, 3, 4, 5).

### Hard blockers that MUST be resolved before the Phase D count gate can be trusted

1. Flag 6 (ETCBC-phono). HARD BLOCKER. The catalog gates non-null-phono
   `BhsaWord` at tier A tolerance 0 against 426590, but the
   etcbc_phono.py contract AND its executable body prove phono is a
   0.984-occurrence-rate optional property: roughly 1.6 percent of word
   slots (ketiv-only) are faithfully written `phono = null`. A faithful
   ingest yields about 419774 non-null, not 426590, so harness Section
   1 row 20 is a guaranteed false-fail and a tier-A mismatch voids the
   whole gate verdict. This is an 8th catalog-reconciliation item of
   the SAME class as the original 7 in
   PHASE_D_CATALOG_RECONCILIATION.md and was missed by that 7-source
   pass.

   Recommended caste action: architect issues a [SCHEMA-REVISION] on
   `tools/expected_counts.json` for `sources["ETCBC-phono"]` BEFORE
   Phase D.4 runs, choosing either (a) re-baseline to the auditor-
   reproduced faithful non-null phono count at tier A tol 0 with
   record_unit clarified, or (b) gate phono on total BhsaWord slot
   coverage (== 426590, identical to ETCBC-BHSA row 18) and drop the
   separate non-null tier-A-0 gate. An auditor must reproduce the exact
   non-null phono count offline from the frozen
   `ETCBC/phono/tf/2021/phono.tf` before any number is committed. The
   adapter is faithful and MUST NOT be changed. Until this
   [SCHEMA-REVISION] lands, the Phase D Section 1 count gate cannot be
   trusted (it will hard-fail a correct ingest on row 20).

No other flag is a hard blocker. Flags 1 to 5 are documentary or
latent-dead-code and can be cleaned up after D.4 without affecting any
gate verdict. Flag 6 is the single gate-breaking defect and is in the
same reconciliation class as the original seven.

End of triage.
