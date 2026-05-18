# Phase D Master Coordinated Fix Ledger

Architect caste, single source of truth for the upcoming Phase D fix wave.
Branch main. Doctrinal frame brethren-on-trial: trust the faithful parse,
fix the wrong reference, never fudge an adapter to hit a wrong number. No em
or en dashes anywhere.

This file is NOT architect-glob-owned. It is intentionally left untracked /
uncommitted; the orchestrator integrates Phase D governance docs separately
(same handling as the prior PHASE_D_*.md governance docs). The two
architect-owned artifacts (the canonical Strong contract in
docs/SCHEMA_DECISIONS.md Decision 18, and the greek_lemma_strong index in
graph/lexical.cypher) are committed separately under the architect caste.

It reconciles, deduplicated, every Phase D defect across:
docs/PHASE_D_EDGE_PERF_MANIFEST.md, docs/PHASE_D_JOINKEY_AUDIT_A.md,
docs/PHASE_D_JOINKEY_AUDIT_B.md, docs/PHASE_D_TIERA_PREVERIFICATION.md,
docs/PHASE_D_PHONO_EVIDENCE.md, docs/PHASE_D_HARNESS_TRIAGE.md,
docs/PHASE_D_CATALOG_RECONCILIATION.md.

## 0. The canonical Strong contract (locked, Decision 18)

Owner decision, locked and now written into docs/SCHEMA_DECISIONS.md
Decision 18: ONE canonical Strong string per language, applied uniformly to
BOTH Greek and Hebrew lemma identity across all adapters, with a backing
index on the join key.

- Canonical Hebrew Strong: `H` + digits zero-padded to >= 4 + optional
  UPPERCASE sense suffix. Examples `H0430`, `H0001`, `H1254A`.
- Canonical Greek Strong: `G` + digits zero-padded to >= 4 + optional
  UPPERCASE sense suffix. Examples `G0040`, `G3056`.
- The single normaliser is `ingest.canonical_strongs.canonical_strongs(raw,
  lang=...)`; the canonical string is `canon[0]`. No adapter may hand-roll
  Strong normalisation.
- Producers: `macula_hebrew.Lemma.strong = canon[0]` (already correct, do
  not change). `macula_greek.GreekLemma.strong` MUST become the canonical
  STRING `canon[0]` (currently `int(strong)`; this is the only producer-side
  value/type change).
- Consumers: every Strong-keyed joiner matches the canonical `.strong`
  (NOT a hand-rolled value, NOT `.id` namespace, NOT an int).
- `Lemma.id` / `GreekLemma.id` namespacing is UNCHANGED. Only `.strong` is
  the canonical join key. The disjoint GreekLemma/Lemma population question
  (macula_hebrew vs macula_greek vs ttesv) is the separate E1/E2 data-model
  escalation and is explicitly NOT decided here.
- Index: `lemma_strong` UNIQUE constraint already backs `Lemma.strong` (do
  NOT duplicate). `greek_lemma_strong` index ADDED to graph/lexical.cypher
  for `GreekLemma.strong` (was missing).

## 1. Consolidated defect table (deduplicated across all audits)

Class legend: CATALOG-RECON (expected_counts revision), EDGE-PERF
(unlabeled-endpoint AllNodesScan), JOIN-KEY (value/type/format mismatch
resolves 0 edges), ORDERING (DATASETS run order), ADAPTER-BUG (loader /
contract violation), DATA-MODEL (escalation, owner decision required).

"Blocks relaunch?" = blocks the lexical ingest reseed from starting/finishing
correctly. "D.4 only" = does not block relaunch, only gates the post-ingest
Phase D.4 count/edge verification.

| id | class | owning file | faithful fix (before -> after) | owning caste | depends-on | blocks relaunch? |
|---|---|---|---|---|---|---|
| PERF-OSHB | EDGE-PERF | ingest/lexical/oshb.py | 4 non-het rels: add labels HAS_MORPHEME `(a:Word)`/`(b:Morpheme)`, IN_VERSE `(a:Word)`/`(b:Verse)`, IS_QERE_OF `(a:Reading)`/`(b:Word)`, FROM_EDITION `(a:Word)`/`(b:Source)` | implementer | none | YES (perf stall) |
| PERF-OSHB-IO | EDGE-PERF | ingest/lexical/oshb.py | INSTANCE_OF het split: partition edges_instance_of into Word-sourced (build site ~554) and Morpheme-sourced (~590) lists, two single-label templates `(a:Word)..(b:Strong)` and `(a:Morpheme)..(b:Strong)`. Edge count/ids unchanged | implementer | none | YES (perf stall) |
| PERF-BHSA | EDGE-PERF | ingest/lexical/bhsa.py | label add: CONTAINS_PHRASE `(a:BhsaClause)`/`(b:BhsaPhrase)`, CONTAINS_WORD `(a:BhsaPhrase)`/`(b:BhsaWord)`, IN_VERSE `(a:BhsaWord)`/`(b:Verse)` | implementer | none | YES (perf stall) |
| PERF-PESH | EDGE-PERF | ingest/lexical/peshitta.py | IN_VERSE label add `(a:SyriacWord)`/`(b:Verse {osisID})` | implementer | none | YES (perf stall) |
| PERF-COPT | EDGE-PERF | ingest/lexical/coptic_scriptorium.py | IN_VERSE label add `(a:CopticWord)`/`(b:Verse {osisID})` | implementer | none | YES (perf stall) |
| PERF-TSK | EDGE-PERF | ingest/lexical/tsk.py | CROSS_REF from-side label add `(a:CrossRef {id})`; to-side already `(b:Verse {osisID})` | implementer | none | YES (perf stall) |
| PERF-PN | EDGE-PERF | ingest/lexical/stepbible_proper_nouns.py | NAMED_AT label add `(p:ProperNoun)` / `(v:Verse)` on the WHERE-equality MATCHes | implementer | none | YES (perf stall) |
| PERF-CBGM | EDGE-PERF | ingest/lexical/open_cbgm_3_john.py | label add READS_AT `(w:Witness)`/`(rd:Reading)`, ATTESTED_BY `(rd:Reading)`/`(v:VariantUnit)`, CORRECTOR_OF `(c:Witness)`/`(b:Witness)` | implementer | none | YES (perf stall) |
| PERF-THEO | EDGE-PERF | ingest/lexical/theographic.py | het 6-label from-side: add `label` field to each mention/period/from_edition edge row at build site, dispatch 6 single-label templates `(a:<Label> {entity_id})`; to-side already labeled | implementer | none | YES (perf stall) |
| PERF-TTESV | EDGE-PERF | ingest/lexical/stepbible_ttesv.py | FROM_EDITION `(t:TaggedToken)`/`(s:Source)`; INSTANCE_OF Hebrew template `(t:TaggedToken)`/`(l:Lemma {id})`, Greek template `(t:TaggedToken)`/`(l:GreekLemma {id})`. Partition already exists Python-side; pure label add | implementer | none | YES (perf stall) |
| PERF-TBESH-LBL | EDGE-PERF | ingest/lexical/stepbible_tbesh.py | LEX_FOR `(b:BriefLexEntry)`/`(l:Lemma)`, FROM_EDITION `(b:BriefLexEntry)`/`(s:Source)` label add | implementer | none | YES (perf stall) |
| PERF-TAHOT-LBL | EDGE-PERF | ingest/lexical/stepbible_tahot.py | INSTANCE_OF `(a:TaggedToken)`/`(b:Lemma)` label add | implementer | none | YES (perf stall) |
| PERF-TAGNT-IV | EDGE-PERF | ingest/lexical/stepbible_tagnt.py | IN_VERSE `(a:TaggedToken)`/`(b:Verse {osisID})` label add (key already osisID, value already bare osis: MATCH-OK) | implementer | none | YES (perf stall) |
| KEY-TAHOT-IV | JOIN-KEY | ingest/lexical/stepbible_tahot.py | IN_VERSE: change `(b {id: row.to_id})` -> `(b:Verse {osisID: row.to_id})`. Bare osis never equals `verse:`-prefixed Verse.id; key id->osisID + label | implementer | none | D.4 only (0 edges, gate fails) |
| KEY-TAHOT-IO | JOIN-KEY | ingest/lexical/stepbible_tahot.py | INSTANCE_OF: replace `_normalize_strong` ad hoc `f"H{int(digits)}{lower sense}"` with `canonical_strongs(raw_dStrong,'hb')[0]`; match `(b:Lemma {strong: canon0})` (Decision 18). Was `macula-hebrew-lemma:H430`/`H1254a` on Lemma.id; resolved 0 for every Strong < 1000 and every suffixed Strong | implementer | Decision 18 | D.4 only (0 edges) |
| KEY-TAGNT-IO | JOIN-KEY | ingest/lexical/stepbible_tagnt.py | INSTANCE_OF: from `(a:TaggedToken {id})`; to `(b:GreekLemma {strong: canonical_strongs(raw_strong_id,'gk')[0]})` per Decision 18. Was bare `G0040` on GreekLemma.id (= `MACULA-...:strong-00040`), resolved 0. NO LONGER an open escalation: Decision 18 locks the canonical `.strong` join | implementer | Decision 18 + KEY-MG-STRONG | D.4 only (0 edges) |
| KEY-MG-STRONG | JOIN-KEY / DATA-MODEL | ingest/lexical/macula_greek.py | `_row_lemma_payload`: `GreekLemma.strong` int(strong) -> canonical STRING `canonical_strongs(str(strong),'gk')[0]`. `GreekLemma.id` namespacing UNCHANGED. Producer-side canonical authority per Decision 18 | implementer | Decision 18 | D.4 only (Greek joins 0 until fixed) |
| KEY-TBESH-LEMMA | JOIN-KEY | ingest/lexical/stepbible_tbesh.py | `base_strong` via `canonical_strongs(raw,'hb')[0]` before BOTH `_MERGE_LEMMA` and `_MERGE_LEX_FOR` payloads so tbesh touches the SAME Lemma macula_hebrew writes. Was `_strip_sense_suffix` raw `H430` (divergent duplicate Lemma) | implementer | Decision 18 | D.4 only (concordance miss) |
| KEY-TBESG-LEXFOR | JOIN-KEY | ingest/lexical/stepbible_tbesg.py | LEX_FOR: match `(g:GreekLemma {strong: canonical_strongs(raw_base_strong,'gk')[0]})`. Was raw `G40` on GreekLemma.id; resolved 0 | implementer | Decision 18 + KEY-MG-STRONG | D.4 only (0 edges) |
| KEY-TFLSJ-LEXFOR | JOIN-KEY | ingest/lexical/stepbible_tflsj.py | LEX_FOR: match `(g:GreekLemma {strong: canonical_strongs(raw_strong,'gk')[0]})`. Was raw str `G40` vs producer int 40; canonical string both sides + greek_lemma_strong index resolves it | implementer | Decision 18 + KEY-MG-STRONG + IDX-GLS | D.4 only (0 edges) |
| KEY-MH-ENRICH | JOIN-KEY | ingest/lexical/macula_hebrew.py | HAS_MACULA_ENRICHMENT: `_osis_ref` MUST normalise MACULA `GEN 1:1` upstream ref into the OSIS dotted form oshb writes for Word.ref (`Gen.1.1`): map uppercase MACULA book token to OSIS book abbrev, space/colon to dots, drop `!word` suffix. Was `GEN 1:1` consumer vs `Gen.1.1` producer -> 0 edges, breaks Decision 1 alignment gate | implementer | none | D.4 only (0 edges, Decision 1 gate 0/total) |
| KEY-MGNT-PARSEOF | JOIN-KEY / DATA-MODEL | ingest/lexical/morphgnt.py (or macula_greek.py) | PARSE_OF: consumer builds `MACULA-Greek-SBLGNT:<osisRef>.w<NN>`; producer Word.id is `MACULA-Greek-SBLGNT:<MACULA xml:id>`. morphgnt cannot reconstruct the TEI token id from (osis_ref, position). MUST-ESCALATE: add an OSIS+position alias on macula_greek Word and re-key, OR join on shared OSIS+position. Do NOT guess | owner decision then implementer | A2 escalation | D.4 only (0 PARSE_OF edges) |
| ORD-MGNT | ORDERING | ingest/lexical/run.py | DATASETS: morphgnt currently index [5], macula_greek index [6]; morphgnt flushes PARSE_OF before macula_greek produces any MACULA-Greek Word. phase_02 + morphgnt docstring require morphgnt AFTER macula_greek. Move `"morphgnt"` to follow `"macula_greek"` | implementer | none | YES (PARSE_OF 0; documented dependency violated) |
| ADAPTER-TVTMS | ADAPTER-BUG | ingest/lexical/stepbible_tvtms.py | `_load_rows` calls `json.load` on `tvtms.parsed.json` which is a 5-col TSV (1308 rows; the two sibling consumers already read it as TSV). Parse the 5-col TSV (or re-serialise artifact as JSON). CRIT-FIX-B commit 7eb0b7a already fixes the loader; real file confirmed 5-col TSV 1308 rows; needs integration + real-data verify | implementer (already landed 7eb0b7a) | none | YES until 7eb0b7a verified (VersificationRule 0) |
| RECON-PHONO | CATALOG-RECON | tools/expected_counts.json | ETCBC-phono not 1:1 with 426590 slots; faithful non-null phono = 420166 (6424 assimilated-article slots faithfully null). Owner per-source review pending: Option A re-baseline to 420166 tol-0; Option B gate slot-coverage 426590 like ETCBC-BHSA. Adapter faithful, do NOT change | owner decision then architect [SCHEMA-REVISION] | PHONO_EVIDENCE | D.4 only (Section 1 row 20 false-fail) |
| RECON-TFLSJ | CATALOG-RECON | tools/expected_counts.json | STEPBible-TFLSJ 11034 -> 9488 (naive raw line count vs faithful drops 1370 empty lemma/translit/pos + 176 dup ids). Adapter faithful | architect [SCHEMA-REVISION] (pending owner per-source review) | none | D.4 only (Section 1 false-fail) |
| RECON-MORPH | CATALOG-RECON | tools/expected_counts.json | STEPBible-morph-codes 2782 -> 2675 (naive population vs distinct section-parsed MorphCode after morph_code_unique dedup). Adapter faithful | architect [SCHEMA-REVISION] (pending owner per-source review) | none | D.4 only (Section 1 false-fail) |
| RECON-PARALLELS | CATALOG-RECON | tools/expected_counts.json | ETCBC-parallels 8246 -> 5914 (raw crossref.tf feature rows vs faithful single-target edges, 2332 multi-target/nondigit quarantined per Decision 3 split). Adapter faithful | architect [SCHEMA-REVISION] (pending owner per-source review) | none | D.4 only (Section 1 false-fail) |
| DM-GREEKLEMMA-POP | DATA-MODEL | (escalation) | E1: macula_hebrew (`macula-hebrew-greek-lemma:G0001`, strong str), macula_greek (`MACULA-...:strong-00001`, strong now canonical str post KEY-MG-STRONG), ttesv (`G0040`) are THREE disjoint GreekLemma populations. Decision 18 makes `.strong` a consistent join key WITHOUT forcing population unification; whether to merge into one GreekLemma per Strong is the open owner decision. Do NOT guess | owner decision | Decision 18 (partial) | D.4 only (does not block relaunch; Decision 18 unblocks the joins) |
| DM-LEMMA-POP | DATA-MODEL | (escalation) | E2: macula_hebrew (`macula-hebrew-lemma:H0430`), ttesv (`H0430`), tbesh (self `Lemma {strong:H430}` -> canonical post KEY-TBESH-LEMMA) hold multiple Lemma populations per Strong. Same class as E1; population unification is the owner decision, not auto-fixed | owner decision | Decision 18 (partial) | D.4 only |
| A2-MGNT-ESCALATE | DATA-MODEL | ingest/lexical/morphgnt.py + macula_greek.py | MUST-ESCALATE pending owner byte-evidence review of the PARSE_OF canonical join key (TEI xml:id vs OSIS+position alias). Do NOT prescribe a fix. Identical to KEY-MGNT-PARSEOF escalation half; listed separately so the owner reviews the byte evidence before any implementer touches PARSE_OF | owner decision | none | D.4 only (0 PARSE_OF edges) |
| CLEAN-NOTE-TFLSJ | EDGE-PERF (resolved by IDX) | graph/lexical.cypher | tflsj LEX_FOR endpoints already labeled; only the missing `GreekLemma.strong` index. Resolved by IDX-GLS below; no tflsj Cypher label change needed (the join VALUE fix is KEY-TFLSJ-LEXFOR) | architect (this commit) | none | D.4 only |
| IDX-GLS | DATA-MODEL (schema) | graph/lexical.cypher | ADD `CREATE INDEX greek_lemma_strong IF NOT EXISTS FOR (g:GreekLemma) ON (g.strong)`. `lemma_strong` UNIQUE constraint already backs Lemma.strong (do NOT duplicate) | architect (DONE this commit) | Decision 18 | YES if any GreekLemma.strong MATCH is to be index-backed at reseed |

Pre-existing ordering inversion noted, OUT OF SCOPE for the perf/key wave
(do NOT reorder under this wave): tbesh DATASETS[11] LEX_FOR/FROM_EDITION
presupposes BriefLexEntry from tbesg DATASETS[12] which runs AFTER tbesh.
The label/key fixes are ordering-neutral (the unlabeled MATCH already
required the node to pre-exist). Flagged for a separate follow-up so the
label fix is not blamed for the pre-existing zero-match. tbesh's own Hebrew
BriefLexEntry is self-produced so its LEX_FOR from-side is fine; only its
Lemma to-side (KEY-TBESH-LEMMA) is the join-value defect.

Defect count by class:
- CATALOG-RECON: 4 (RECON-PHONO, RECON-TFLSJ, RECON-MORPH, RECON-PARALLELS)
- EDGE-PERF: 14 (PERF-* across 12 adapters; oshb carries 2 rows)
- JOIN-KEY: 8 (KEY-TAHOT-IV, KEY-TAHOT-IO, KEY-TAGNT-IO, KEY-MG-STRONG,
  KEY-TBESH-LEMMA, KEY-TBESG-LEXFOR, KEY-TFLSJ-LEXFOR, KEY-MH-ENRICH;
  KEY-MGNT-PARSEOF is JOIN-KEY with a DATA-MODEL escalation half)
- ORDERING: 1 (ORD-MGNT)
- ADAPTER-BUG: 1 (ADAPTER-TVTMS, already landed 7eb0b7a, needs verify)
- DATA-MODEL: 4 escalations (DM-GREEKLEMMA-POP / E1, DM-LEMMA-POP / E2,
  A2-MGNT-ESCALATE, plus the KEY-MGNT-PARSEOF key-choice half) + 1 schema
  add (IDX-GLS, done this commit)

## 2. FIX WAVE PLAN (single-touch, parallel-safe)

Hard rule: each adapter file is edited EXACTLY ONCE by EXACTLY ONE
implementer in a single coordinated edit that lands ALL of that adapter's
defects together. No two agents touch one file. This makes the wave
parallel-safe. Every Strong-keyed change references Decision 18.

### 2.1 Per-adapter implementer tasks (one task = one file, all its defects)

| # | file | defects landed together in this single edit |
|---|---|---|
| T1 | ingest/lexical/oshb.py | PERF-OSHB (4 non-het label adds) + PERF-OSHB-IO (INSTANCE_OF het split into Word/Morpheme lists, two single-label templates) |
| T2 | ingest/lexical/bhsa.py | PERF-BHSA (3 label adds) |
| T3 | ingest/lexical/peshitta.py | PERF-PESH (IN_VERSE label add). Note: Decision 7 TVTMS projection absence (D7) is a SEPARATE contract item; flagged MUST-VERIFY (cached upstream verse_ref format), not bundled unless owner confirms scope |
| T4 | ingest/lexical/coptic_scriptorium.py | PERF-COPT (IN_VERSE label add). D8 TVTMS projection absence is the same MUST-VERIFY class as T3; not bundled unless owner confirms scope |
| T5 | ingest/lexical/tsk.py | PERF-TSK (from-side `:CrossRef` label add) |
| T6 | ingest/lexical/stepbible_proper_nouns.py | PERF-PN (NAMED_AT label add). Residual TIPNR book-spelling MUST-VERIFY (Sng/Song etc.) is data, not code |
| T7 | ingest/lexical/open_cbgm_3_john.py | PERF-CBGM (3 label adds) |
| T8 | ingest/lexical/theographic.py | PERF-THEO (6-label het from-side: add `label` field at build site, dispatch 6 single-label templates) |
| T9 | ingest/lexical/stepbible_ttesv.py | PERF-TTESV (FROM_EDITION + both INSTANCE_OF branch label adds; partition already Python-side, no row change). NO key change (ttesv self-consistent canonical) |
| T10 | ingest/lexical/stepbible_tbesh.py | PERF-TBESH-LBL (LEX_FOR + FROM_EDITION label adds) + KEY-TBESH-LEMMA (route base_strong through canonical_strongs before _MERGE_LEMMA and _MERGE_LEX_FOR, Decision 18) |
| T11 | ingest/lexical/stepbible_tahot.py | PERF-TAHOT-LBL (INSTANCE_OF label add) + KEY-TAHOT-IV (IN_VERSE key id->osisID + `:Verse` label) + KEY-TAHOT-IO (replace _normalize_strong with canonical_strongs, match `(b:Lemma {strong: canon0})`, Decision 18) |
| T12 | ingest/lexical/stepbible_tagnt.py | PERF-TAGNT-IV (IN_VERSE label add) + KEY-TAGNT-IO (from `(a:TaggedToken {id})`; to `(b:GreekLemma {strong: canonical_strongs(raw,'gk')[0]})`, Decision 18). NO LONGER blocked on escalation: Decision 18 locks the join |
| T13 | ingest/lexical/stepbible_tbesg.py | KEY-TBESG-LEXFOR (LEX_FOR match `(g:GreekLemma {strong: canonical_strongs(raw_base_strong,'gk')[0]})`, Decision 18). Endpoints already labeled (perf CLEAN) |
| T14 | ingest/lexical/stepbible_tflsj.py | KEY-TFLSJ-LEXFOR (LEX_FOR match `(g:GreekLemma {strong: canonical_strongs(raw_strong,'gk')[0]})`, Decision 18). Endpoints already labeled; the greek_lemma_strong index (this architect commit) backs it. NO tflsj label change needed |
| T15 | ingest/lexical/macula_greek.py | KEY-MG-STRONG (`_row_lemma_payload`: GreekLemma.strong int -> canonical string `canonical_strongs(str(strong),'gk')[0]`; GreekLemma.id namespacing UNCHANGED), Decision 18 producer authority |
| T16 | ingest/lexical/macula_hebrew.py | KEY-MH-ENRICH (`_osis_ref` / enrichment builder: normalise MACULA `GEN 1:1` upstream ref to OSIS dotted `Gen.1.1` so HAS_MACULA_ENRICHMENT join resolves). Lemma.strong already canonical (do NOT change) |
| T17 | ingest/lexical/morphgnt.py | PARSE_OF id-format fix half (KEY-MGNT-PARSEOF) IS BLOCKED on A2-MGNT-ESCALATE owner decision. This task is HELD until the owner resolves the canonical PARSE_OF key. Do NOT edit morphgnt.py for PARSE_OF until then. (morphgnt has no other defect) |
| T18 | ingest/lexical/run.py | ORD-MGNT only: relocate `"morphgnt"` to immediately AFTER `"macula_greek"` in DATASETS. Unambiguous, not blocked |
| T19 | ingest/lexical/stepbible_tvtms.py | ADAPTER-TVTMS already landed in commit 7eb0b7a (CRIT-FIX-B). NO new edit; this task is INTEGRATION + REAL-DATA VERIFY only (confirm loader parses the real 5-col TSV, 1308 VersificationRule nodes) |

Single-touch guarantee: T1..T19 each name exactly one file; no file appears
in two tasks. KEY-* and PERF-* defects that share an adapter are bundled into
that adapter's single task (T10, T11, T12). The architect-owned schema/doc
changes (Decision 18, greek_lemma_strong index) are this commit, separate
from the implementer .py wave, so no .py task touches docs/ or graph/.

### 2.2 run.py ordering fix (ORD-MGNT, exact)

Current DATASETS (run.py 43..67), morphgnt at index 5 BEFORE macula_greek
at index 6:

```
oshb, macula_hebrew, bhsa, etcbc_phono, etcbc_parallels, morphgnt,
macula_greek, stepbible_morph_codes, stepbible_tahot, stepbible_tagnt,
stepbible_ttesv, stepbible_tbesh, stepbible_tbesg, stepbible_tflsj,
stepbible_proper_nouns, stepbible_tvtms, peshitta, coptic_scriptorium,
vulgate_clementine, open_cbgm_3_john, openbible, tsk, theographic
```

Corrected DATASETS (move `"morphgnt"` to immediately AFTER `"macula_greek"`):

```
oshb, macula_hebrew, bhsa, etcbc_phono, etcbc_parallels,
macula_greek, morphgnt, stepbible_morph_codes, stepbible_tahot,
stepbible_tagnt, stepbible_ttesv, stepbible_tbesh, stepbible_tbesg,
stepbible_tflsj, stepbible_proper_nouns, stepbible_tvtms, peshitta,
coptic_scriptorium, vulgate_clementine, open_cbgm_3_john, openbible,
tsk, theographic
```

This satisfies the phase_02 runbook and morphgnt docstring requirement that
morphgnt run AFTER macula_greek so PARSE_OF's MACULA-Greek Word targets are
materialised. (The PARSE_OF id-format half remains separately escalated:
ordering alone does not rescue it.)

### 2.3 tvtms status (ADAPTER-TVTMS)

CRIT-FIX-B commit 7eb0b7a already fixes the loader (`stepbible_tvtms`
`_load_rows` JSON->TSV). The real file is confirmed a 5-column TSV with 1308
rows; expected_count stays 1308 (NOT a [SCHEMA-REVISION]). Remaining work:
INTEGRATION + REAL-DATA VERIFY only (assert the fixed loader yields exactly
1308 VersificationRule nodes on the real artifact and the two sibling TSV
consumers stay consistent). No further code edit prescribed.

### 2.4 catalog [SCHEMA-REVISION] #3 set (RECON-*)

Four catalog reconciliations, ALL flagged PENDING OWNER PER-SOURCE REVIEW.
They GATE Phase D.4 (Section 1 count gate) but do NOT block the ingest
relaunch:

- ETCBC-phono 420166 (faithful non-null; 6424 assimilated-article slots
  faithfully null). Owner picks Option A (re-baseline 420166 tol-0) or
  Option B (slot-coverage 426590 like ETCBC-BHSA, drop separate non-null
  gate). Per PHASE_D_PHONO_EVIDENCE.md.
- STEPBible-TFLSJ 9488 (11034 naive line count; faithful drops 1370 empty
  lemma/translit/pos + 176 dup ids).
- STEPBible-morph-codes 2675 (2782 naive population; faithful distinct
  section-parsed MorphCode after morph_code_unique dedup).
- ETCBC-parallels 5914 (8246 raw crossref.tf rows; faithful single-target
  edges, 2332 multi-target/nondigit quarantined per Decision 3 split).

All four: adapter is faithful and MUST NOT change; resolution is an
architect [SCHEMA-REVISION] on tools/expected_counts.json AFTER owner
per-source review, in the same family as the original 7 reconciliations.
They gate D.4, not relaunch.

### 2.5 A2 morphgnt PARSE_OF (A2-MGNT-ESCALATE)

MUST-ESCALATE, pending owner byte-evidence review. macula_greek Word.id is
contractually the MACULA TEI token id (`MACULA-Greek-SBLGNT:n40001001001`);
morphgnt builds `MACULA-Greek-SBLGNT:<osisRef>.w<NN>` and cannot reconstruct
the TEI id from (osis_ref, position). The canonical PARSE_OF join key (add an
OSIS+position alias property on macula_greek Word and re-key, vs join on a
shared normalised OSIS+position) is a Decision 15 / Decision 2 schema call.
NO fix is prescribed here. The owner must review the byte evidence (audit A,
defect A-2) and decide before T17 is unblocked. The run.py ordering half
(ORD-MGNT) is unambiguous and proceeds independently as T18.

## 3. Relaunch vs D.4 gating summary

BLOCKS THE INGEST RELAUNCH (must land before the lexical reseed is re-run
to completion):
- All EDGE-PERF defects (PERF-*): without the labels the reseed AllNodesScans
  and never finishes. T1..T14 perf portions + the perf-only adapters.
- ORD-MGNT (run.py order): documented dependency violation; morphgnt must
  run after macula_greek.
- ADAPTER-TVTMS: until 7eb0b7a is integration-verified, VersificationRule
  emits 0 (the loader crashed pre-fix).

GATES POST-INGEST D.4 ONLY (do NOT block relaunch; the reseed can run, but
D.4 verification will false-fail or under-count until resolved):
- All JOIN-KEY defects (KEY-*): edges resolve to 0 / wrong but the ingest
  still completes; D.4 Section 3 per-edge and Section 2 acceptance gates
  fail until canonicalised per Decision 18.
- All CATALOG-RECON (RECON-*): D.4 Section 1 count gate false-fails until
  the architect [SCHEMA-REVISION] lands (pending owner review).
- All DATA-MODEL escalations (E1/E2, A2-MGNT-ESCALATE, KEY-MGNT-PARSEOF key
  half): do not block relaunch; they leave specific edges at 0 until the
  owner decides. Decision 18 already removes the tagnt/tbesg/tflsj escalation
  by locking the canonical `.strong` join; only the GreekLemma/Lemma
  population-unification question and the morphgnt PARSE_OF key remain open.

Net: the relaunch is unblocked once the EDGE-PERF wave + ORD-MGNT land and
7eb0b7a is verified. D.4 trust additionally requires the JOIN-KEY wave
(Decision 18 conformance), the four [SCHEMA-REVISION]s (owner review), and
the morphgnt PARSE_OF escalation resolved.

## 4. Fix-wave status (orchestrator-maintained)

T1 oshb LANDED f32da6c wt-agent-a373d15e13204fc70 | T2 bhsa LANDED 0fc6881 wt-agent-ae9b305ecad1db7ca | T3 peshitta RE-DISPATCHED | T4 coptic LANDED 0b6e584 wt-agent-aa24cffea8d5d723d (D8 procurement-gated; 3 FakeDriver-harness test artifacts for verifier) | T5 tsk RE-DISPATCHED | T6 proper_nouns RE-DISPATCHED | T7 open_cbgm RE-DISPATCHED | T8 theographic RE-DISPATCHED | T9 ttesv LANDED eeaa9ff wt-agent-a119c4c47a27828d4 (1 FakeDriver-harness test artifact for verifier) | T10 tbesh RE-DISPATCHED | T11 tahot RE-DISPATCHED | T12 tagnt RE-DISPATCHED | T13 tbesg LANDED 6025a73 wt-agent-a2679f81d7712b866 | T14 tflsj LANDED d6edca3 wt-agent-a50cf67f251268eb5 | T15 macula_greek LANDED 204ebb1 wt-agent-ad2c9c1036cce3b99 | T16 macula_hebrew LANDED dba15e8 wt-agent-a2adeeef9ee0456c0 | T17 morphgnt HELD on A2 owner decision | T18 run.py RE-DISPATCHED | T19 tvtms CRIT-FIX-B 7eb0b7a needs integration+real-data verify. Note: LANDED = committed on the named isolated worktree branch, NOT yet integrated to main; integration is a later orchestrated step.
