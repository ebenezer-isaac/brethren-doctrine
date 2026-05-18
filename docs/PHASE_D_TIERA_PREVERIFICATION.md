# Phase D Tier-A Pre-Verification Sweep

Caste: auditor. READ-ONLY. Branch main, HEAD 02ebae8. Doctrinal frame:
brethren-on-trial (trust the faithful parse; a catalog number that
disagrees with the faithful byte-derived emit is the artifact, not the
adapter). No em or en dashes. No Neo4j touched (the lexical Neo4j is
mid-ingest under bsof4dynu). No network. Pure offline parse of the
frozen upstream bytes via each adapter's own pure parse helpers (never
the ingest_* driver functions).

## Purpose

The original catalog reconciliation ([SCHEMA-REVISION] ceb3898 /
01e09c6, evidenced in docs/PHASE_D_CATALOG_RECONCILIATION.md) fixed 7
sources. A later harness triage (docs/PHASE_D_HARNESS_TRIAGE.md flag 6)
found an 8th, ETCBC-phono, that the original pass missed. That proves
the inventory-builder methodology is not exhaustive. This sweep
independently re-derives the faithful adapter emit for EVERY remaining
tier-A source (tolerance 0) that is not already reconciled and not
already triaged, so the Phase D.4 Section 1 count gate (which runs the
moment the in-flight ingest finishes) does not false-fail a faithful
ingest and no further surprise reconciliations are discovered at gate
time.

## Scope

Authoritative tier-A list read from tools/expected_counts.json.

Excluded as PREVIOUSLY RESOLVED (not re-reproduced here):

- OSHB-morphology 305507 (reconciled, PHASE_D_CATALOG_RECONCILIATION.md s2)
- STEPBible-TAHOT 283721 (reconciled, 01e09c6 + preflight audit)
- STEPBible-TAGNT 142096 (reconciled, PHASE_D_CATALOG_RECONCILIATION.md s3)
- STEPBible-TTESV 31127 (reconciled, PHASE_D_CATALOG_RECONCILIATION.md s4)
- STEPBible-proper-nouns 5468 (reconciled, PHASE_D_CATALOG_RECONCILIATION.md s1)
- Theographic-Bible-Metadata 4849 (reconciled, PHASE_D_CATALOG_RECONCILIATION.md s7)
- open-cbgm-3-john 728 (tier B, reconciled s6)
- ETCBC-phono 426590 (8th item, separate review PHASE_D_HARNESS_TRIAGE.md flag 6)

Targets re-reproduced (13 tier-A sources): MACULA-Hebrew,
MACULA-Greek-Nestle1904, MACULA-Greek-SBLGNT, MorphGNT-SBLGNT,
STEPBible-TVTMS, STEPBible-TBESH, STEPBible-TBESG, STEPBible-TFLSJ,
STEPBible-morph-codes, OpenBible-cross-refs, TSK, ETCBC-BHSA,
ETCBC-parallels.

Method: for each source, the exact record_unit the Phase D Section 1
count gate asserts is taken from docs/PHASE_D_VERIFICATION_HARNESS.md
Section 1 (the gate is a label-or-edge count filtered by the
adapter-authoritative SOURCE_SLUG, exact match, tolerance 0). The
faithful emit is computed by calling the adapter's pure build/parse
helper on the real frozen upstream and counting the gated record_unit.

Reproduction harness (read-only, deleted after run):
`python tmp_preverify.py` from repo root, importing each adapter's pure
helpers (`_collect_rows`, `_iter_tsv_rows` + `_row_word_payload`,
`_build_rows`, `_load_rows`, `_parse_rows`, `_build`,
`_load_dataset`, `_build_edge_rows`). No `ingest_*` function was called
so no Neo4j driver was constructed.

---

## Per-source results

### MACULA-Hebrew  -- EXACT

- Gate (harness row 2): `MATCH (n:MaculaToken) RETURN count(n)` == 475911.
- catalog 475911 / faithful 475911 / delta 0.
- Command: `mh._collect_rows(data/private/macula-hebrew)` -> len = 475911.
- One MaculaToken per `<w>` in WLC/lowfat/*-lowfat.xml, deduped by
  verbatim `xml:id`. Byte-deterministic element count. EXACT.

### MACULA-Greek-Nestle1904  -- EXACT

- Gate (harness row 3): `Word {source:'MACULA-Greek-Nestle1904'}` == 137779.
- catalog 137779 / faithful 137779 / delta 0.
- Command: iterate `mg._iter_tsv_rows(Nestle1904/tsv/macula-greek-Nestle1904.tsv)`,
  count `mg._row_word_payload` rows whose `id` is not None -> 137779. EXACT.

### MACULA-Greek-SBLGNT  -- EXACT

- Gate (harness row 4): `Word {source:'MACULA-Greek-SBLGNT'}` == 137741.
- catalog 137741 / faithful 137741 / delta 0.
- Command: same as above against SBLGNT/tsv/macula-greek-SBLGNT.tsv -> 137741. EXACT.

### MorphGNT-SBLGNT  -- EXACT

- Gate (harness row 5): `Word {source:'MorphGNT-SBLGNT'}` == 137554.
- catalog 137554 / faithful 137554 / delta 0.
- Command: `mgn._build_rows(data/private/morphgnt)` -> len(word_rows) = 137554. EXACT.

### STEPBible-TVTMS  -- MISMATCH (adapter/artifact format defect)

- Gate (harness row 8): `VersificationRule {source:'STEPBible-TVTMS'}` == 1308.
- catalog 1308 / faithful 0 / delta -1308.
- Command: `tvtms._load_rows(data/private/stepbible)` raises
  `json.decoder.JSONDecodeError`.
- Decisive byte-level cause: the adapter `stepbible_tvtms._load_rows`
  opens `data_root / "tvtms.parsed.json"` and calls `json.load(fh)`.
  The on-disk artifact `data/private/stepbible/tvtms.parsed.json` is
  NOT JSON; it is a 5-column tab-separated file (first bytes:
  `english\tGen.3.1\thebrew\tGen.3.1\tOneToOne\t\r\n ...`), exactly
  1308 non-blank lines, one row per versification rule. `json.load`
  fails on byte 0, so the adapter emits ZERO VersificationRule nodes.
  The sibling consumers `openbible.py._load_tvtms_rules` and
  `tsk.py._load_tvtms_rules` read this same path with `.split("\t")`
  (TSV), so they are consistent with the on-disk format and the
  contract docstring also describes a TSV. Only the TVTMS adapter's
  own loader expects JSON. The catalog number 1308 IS the correct
  faithful row count (1308 non-blank TSV lines); the artifact is
  byte-correct. The defect is the adapter loader (JSON vs TSV) plus
  the `.json` filename. The gate will hard-fail at 0 != 1308.
- Proposed faithful expected_count: 1308 (unchanged; the catalog
  number is correct). This is NOT a catalog reconciliation. It is an
  adapter loader / artifact-format defect: either
  `stepbible_tvtms._load_rows` must parse the 5-column TSV (matching
  the on-disk artifact and the two sibling consumers) or the artifact
  must be re-serialised as JSON. Owning caste: implementer (adapter
  body fix) and/or the artifact producer; NOT a [SCHEMA-REVISION] on
  expected_counts.json. Hard pre-D.4 blocker for this row.

### STEPBible-TBESH  -- EXACT

- Gate (harness row 9): `BriefLexEntry {source:'STEPBible-TBESH', language:'hebrew'}` == 11682.
- catalog 11682 / faithful 11682 / delta 0.
- Command: `tbesh._load_rows(data/private/stepbible)` -> 11682. EXACT.

### STEPBible-TBESG  -- EXACT

- Gate (harness row 10): `BriefLexEntry {source:'STEPBible-TBESG', language:'greek'}` == 11035.
- catalog 11035 / faithful 11035 / delta 0.
- Command: `tbesg._load_rows(data/private/stepbible)` -> 11035. EXACT.

### STEPBible-TFLSJ  -- MISMATCH (naive line count, same class as the original 7)

- Gate (harness row 11): `LsjEntry {source:'STEPBible-TFLSJ'}` == 11034.
- catalog 11034 / faithful 9488 / delta -1546.
- Command: `tflsj._load_rows(data/private/stepbible/Lexicons)` -> 9488.
- Decisive byte-level cause: catalog 11034 equals exactly the raw
  data-row count across the two TFLSJ files
  (`TFLSJ  0-5624 ...txt` + `TFLSJ extra ...txt`) counting only rows
  with >= 8 tab columns and a G/H Strong, with NO field-population
  guard and NO id dedup (independently reproduced: 11034). The
  faithful adapter emit applies `tflsj._parse_row`'s populated-field
  guard `if not lemma or not transliteration or not pos: return None`
  (drops 1 row in the 0-5624 file and 1369 rows in the `extra` file,
  total 1370; the `extra` file is a residual/cross-reference sheet
  whose lemma/translit/pos columns are predominantly blank), then
  `_load_rows` collapses 176 duplicate `tflsj:<strong>:<lemma>`
  stable ids (the `lsj_entry_id` uniqueness constraint). 11034 - 1370
  guarded - 176 dedup = 9488. Exactly the naive-tab-line-count vs
  de-duplicated-populated-emit class of the original
  STEPBible-proper-nouns / TTESV reconciliations.
- Proposed faithful expected_count: 9488, tier A tolerance 0,
  record_unit clarified to "de-duplicated LsjEntry with populated
  lemma, transliteration, and pos (lsj_entry_id stable id)". Requires
  an architect [SCHEMA-REVISION] on tools/expected_counts.json
  sources["STEPBible-TFLSJ"]. The adapter is faithful and MUST NOT be
  changed. NEW reconciliation item.

### STEPBible-morph-codes  -- MISMATCH (naive count vs deduped code emit)

- Gate (harness row 12): `MorphCode {source:'STEPBible-morph-codes'}` == 2782.
- catalog 2782 / faithful 2675 / delta -107.
- Command: `smc._load_rows(data/private/stepbible)` -> 2675.
- Decisive byte-level cause: the adapter parses the BRIEF and FULL
  sections of TEHMC (Hebrew) and TEGMC (Greek). Faithful parse yields
  brief 92 + full 922 (Hebrew) and brief 18 + full 1645 (Greek) =
  2677 collected, minus 2 duplicate `code` values dropped by the
  `morph_code_unique` dedup in `_load_rows` = 2675 distinct MorphCode
  nodes. The catalog 2782 is 107 higher than the deterministic
  distinct-code emit over the frozen TEHMC/TEGMC bytes; it does not
  match the adapter's section-parse-plus-dedup record_unit (the
  catalog appears to have counted a raw line population that includes
  rows the Decision 17 section parser legitimately does not nodify).
  Reproducible at 2675 across the byte parse.
  (Sub-note: `smc._load_rows` takes the `stepbible` root and appends
  `Morphology codes` internally; passing the already-resolved
  `Morphology codes` dir yields 0, a path foot-gun but not the gate
  input. The gate-relevant call `smc._load_rows(.../stepbible)`
  deterministically yields 2675.)
- Proposed faithful expected_count: 2675, tier A tolerance 0,
  record_unit "distinct MorphCode (morph_code_unique stable code)".
  Requires an architect [SCHEMA-REVISION] on
  sources["STEPBible-morph-codes"]. Adapter faithful, MUST NOT change.
  NEW reconciliation item.

### OpenBible-cross-refs  -- EXACT

- Gate (harness row 15): `()-[r:OPENBIBLE_CROSS_REF {source:'OpenBible-cross-refs'}]->()` == 344799.
- catalog 344799 / faithful 344799 / delta 0 (quarantined 0).
- Command: `ob._parse_rows(cross_references.txt, ob._load_tvtms_rules(...))`
  -> 344799 resolved rows, 0 quarantined. The TVTMS rule file is read
  as TSV by openbible's own loader (consistent with the on-disk
  artifact), so projection resolves cleanly. One edge per upstream
  data row. EXACT.

### TSK  -- EXACT

- Gate (harness row 16): `CrossRef {source:'TSK'}` == 63682.
- catalog 63682 / faithful 63682 / delta 0.
- Command: `tsk._build(tsk._rows_from_lines(tsk._read_lines(tskxref.txt)),
  tsk._load_tvtms_rules(...))` -> 63682 CrossRef nodes (raw lines
  63682; 662 of those nodes carry tvtms_quarantine=True but are STILL
  emitted as CrossRef nodes per the adapter contract, so the gated
  node population is the full 63682; 582568 CROSS_REF edges, a tier-B
  HAS_CROSS_REF concern not gated tier-A). The Section 1 gate counts
  CrossRef nodes, which equals the raw row count exactly. EXACT.

### ETCBC-BHSA  -- EXACT

- Gate (harness row 18): `BhsaWord {source:'ETCBC-BHSA'}` == 426590.
- catalog 426590 / faithful 426590 / delta 0.
- Command: `bhsa._load_dataset(bhsa.TF_ROOT)` over the frozen
  text-fabric module
  `C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021`
  -> words 426590 (phrases 253203, clauses 88131). The word otype run
  in otype.tf yields exactly 426590 word slots. EXACT. (Note: this
  also confirms the ETCBC-phono flag-6 arithmetic baseline; the
  426590 BHSA word-slot count is correct for ETCBC-BHSA row 18 and is
  NOT the right target for the separate non-null-phono ETCBC-phono
  row, which remains the flag-6 8th-item blocker handled separately.)

### ETCBC-parallels  -- MISMATCH (raw feature rows vs single-target edge emit)

- Gate (harness row 19): `()-[r:PARALLEL_OF {source:'ETCBC-parallels'}]->()` == 8246.
- catalog 8246 / faithful 5914 / delta -2332.
- Command: `ep._build_edge_rows(ep._load_rows(ep.TF_ROOT))` over
  `C:/Users/Ebenezer/text-fabric-data/github/ETCBC/parallels/tf/2021/crossref.tf`
  -> 5914 PARALLEL_OF edges, 2332 quarantined.
- Decisive byte-level cause: `crossref.tf` body has exactly 8246
  non-blank value lines (catalog 8246 == raw upstream feature row
  count). But the upstream feature packs MULTIPLE comma-separated
  target nodes on a single source row (sample:
  `1414407 -> 1414401,1414411,0.84` ;
  `1414498 -> 1414507,1414670,1414672,0.75`). The adapter's Decision-3
  split rule `_split_target_and_value` quarantines any
  `target_and_value` whose `count(",") != 1` (2314 multi-target rows)
  plus 18 non-digit-node rows = 2332 quarantined; only the 5914
  single-target rows become PARALLEL_OF edges. The catalog counted
  raw upstream feature rows; the adapter faithfully emits one edge
  only per single-target row and quarantines multi-target rows per
  its binding split contract (the contract explicitly forbids a
  heuristic / lossy multi-target split). Reproducible at 5914.
- Proposed faithful expected_count: 5914, tier A tolerance 0,
  record_unit "PARALLEL_OF edge from a single-target crossref.tf row
  (multi-target rows quarantined per Decision 3 split rule)".
  Requires an architect [SCHEMA-REVISION] on
  sources["ETCBC-parallels"]. Adapter faithful, MUST NOT change.
  (Architect alternative, same class as flag-6 option-b: if the
  intent is to count every parallel relation, the adapter split rule
  itself is the open design question and would need a
  [SCHEMA-REVISION] to authorise a multi-target fan-out; until then
  the faithful emit of the committed adapter is 5914 and that is what
  the tol-0 gate must use.) NEW reconciliation item.

---

## SWEEP SUMMARY

| Source | catalog | faithful-emit | match? | proposed count + cause |
|---|---|---|---|---|
| MACULA-Hebrew | 475911 | 475911 | EXACT | -- |
| MACULA-Greek-Nestle1904 | 137779 | 137779 | EXACT | -- |
| MACULA-Greek-SBLGNT | 137741 | 137741 | EXACT | -- |
| MorphGNT-SBLGNT | 137554 | 137554 | EXACT | -- |
| STEPBible-TVTMS | 1308 | 0 | MISMATCH | keep 1308; FIX ADAPTER/ARTIFACT: loader does json.load on a TSV artifact (1308 TSV rows); not a catalog revision |
| STEPBible-TBESH | 11682 | 11682 | EXACT | -- |
| STEPBible-TBESG | 11035 | 11035 | EXACT | -- |
| STEPBible-TFLSJ | 11034 | 9488 | MISMATCH | 9488; 11034 is naive raw G/H line count, faithful drops 1370 empty lemma/translit/pos rows + 176 dup ids |
| STEPBible-morph-codes | 2782 | 2675 | MISMATCH | 2675; 2782 is naive population, faithful is distinct section-parsed MorphCode after morph_code_unique dedup |
| OpenBible-cross-refs | 344799 | 344799 | EXACT | -- |
| TSK | 63682 | 63682 | EXACT | -- |
| ETCBC-BHSA | 426590 | 426590 | EXACT | -- |
| ETCBC-parallels | 8246 | 5914 | MISMATCH | 5914; 8246 is raw crossref.tf feature rows, faithful quarantines 2332 multi-target/nondigit rows per Decision 3 split |

EXACT: 9 (MACULA-Hebrew, MACULA-Greek-Nestle1904, MACULA-Greek-SBLGNT,
MorphGNT-SBLGNT, STEPBible-TBESH, STEPBible-TBESG, OpenBible-cross-refs,
TSK, ETCBC-BHSA).

MISMATCH: 4 (STEPBible-TVTMS, STEPBible-TFLSJ, STEPBible-morph-codes,
ETCBC-parallels).

## NEW reconciliation / defect items found (beyond the original 7 + ETCBC-phono 8th)

These are NEW, in addition to the 8 already known. Each WILL false-fail
the Phase D Section 1 count gate on a faithful ingest the moment the
in-flight ingest finishes, and each must be resolved before D.4 can be
trusted.

1. STEPBible-TFLSJ. catalog 11034 vs faithful 9488 (delta -1546).
   One-line cause: 11034 is the naive raw tab-line count; the faithful
   adapter drops 1370 rows with empty lemma/translit/pos and collapses
   176 duplicate lsj_entry_id stable ids. Class: same as the original
   7 (naive line count vs de-duplicated populated emit). Fix: architect
   [SCHEMA-REVISION] on tools/expected_counts.json
   sources["STEPBible-TFLSJ"] -> 9488. Adapter faithful, do not touch.

2. STEPBible-morph-codes. catalog 2782 vs faithful 2675 (delta -107).
   One-line cause: 2782 is a naive population; the faithful adapter
   emits 2675 distinct MorphCode nodes from the BRIEF+FULL section
   parse after the morph_code_unique dedup. Class: same as the
   original 7. Fix: architect [SCHEMA-REVISION] on
   sources["STEPBible-morph-codes"] -> 2675. Adapter faithful.

3. ETCBC-parallels. catalog 8246 vs faithful 5914 (delta -2332).
   One-line cause: 8246 is the raw crossref.tf feature-row count; the
   faithful adapter emits 5914 PARALLEL_OF edges and quarantines 2332
   rows that pack multiple comma-separated targets (per the binding
   Decision 3 single-comma split rule). Class: same as the original 7
   (raw upstream count vs faithful record_unit). Fix: architect
   [SCHEMA-REVISION] on sources["ETCBC-parallels"] -> 5914 (or an
   explicit Decision 3 multi-target fan-out revision; until then the
   committed adapter's faithful emit is 5914). Adapter faithful.

4. STEPBible-TVTMS. catalog 1308 vs faithful 0 (delta -1308).
   DISTINCT CLASS: this is NOT a catalog artifact. The catalog 1308
   is the correct row count (1308 non-blank TSV lines in the
   byte-correct artifact). The defect is in the adapter / artifact
   contract: `stepbible_tvtms._load_rows` calls `json.load` on
   `tvtms.parsed.json`, which on disk is a 5-column TSV (the format
   the two sibling consumers openbible.py and tsk.py already read),
   so the adapter crashes and emits 0 VersificationRule nodes. Fix:
   implementer change to `stepbible_tvtms._load_rows` to parse the
   5-column TSV (or re-serialise the artifact as JSON). NOT a
   [SCHEMA-REVISION]; expected_count stays 1308. Hard pre-D.4 blocker.

## Conclusion

Of the 13 remaining tier-A sources swept, 9 match the catalog exactly
and are safe for the Phase D.4 Section 1 count gate. 4 will false-fail
a faithful ingest:

- 3 are catalog-artifact reconciliations of the SAME class as the
  original 7 (TFLSJ 11034->9488, morph-codes 2782->2675,
  parallels 8246->5914) and each requires an architect
  [SCHEMA-REVISION] on tools/expected_counts.json before D.4.
- 1 (TVTMS) is a distinct adapter/artifact format defect (json.load
  on a TSV artifact -> 0 emitted) requiring an implementer adapter
  fix, not a catalog change; expected_count 1308 is correct.

Combined with the already-known ETCBC-phono 8th item
(PHASE_D_HARNESS_TRIAGE.md flag 6), there are now at least 4 unresolved
tier-A blockers (phono + TFLSJ + morph-codes + parallels as
[SCHEMA-REVISION] items, plus TVTMS as an adapter defect) that MUST be
resolved before the Phase D.4 count gate can be trusted. The
inventory-builder methodology is confirmed systemically non-exhaustive:
the original 7-source pass missed at least these 4 additional tier-A
mismatches in addition to ETCBC-phono.
