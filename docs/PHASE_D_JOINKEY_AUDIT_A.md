# Phase D Join-Key Consistency Audit, SHARD A

Auditor caste, READ-ONLY exhaustive cross-adapter join-key audit. Branch
main, HEAD 02ebae8. Doctrinal frame brethren-on-trial. No em or en dashes
anywhere (periods, commas, "and", "but" only).

## Purpose and method

Phase C verified adapters against a lossy FakeDriver and a self-referential
catalog, never against each other in a real graph. The perf manifest
(docs/PHASE_D_EDGE_PERF_MANIFEST.md) fixed only the LABEL/INDEX problem and
explicitly deferred the join VALUE/TYPE/FORMAT correctness question (it
checked "is a label present", not "does the consumer-supplied key value
byte-match the producer-written key value"). This audit closes that gap for
SHARD A.

Method: for every relationship MERGEd/CREATEd by every SHARD A adapter, the
endpoint resolution was extracted (MATCH label, join property, exact value
and type and format as the consumer supplies it), the PRODUCING adapter for
that endpoint node label was located, and the exact value and type and
format it writes for that same property was read from the node-emission
Cypher and build code (not assumptions). The two were compared and each
edge endpoint classified MATCH-OK, KEY-MISMATCH, or LABEL-INDEX-GAP.

Sources read in full: graph/lexical.cypher, docs/SCHEMA_DECISIONS.md,
docs/implementation_phases/phase_02_lexical_ingest.md,
docs/PHASE_D_EDGE_PERF_MANIFEST.md, ingest/canonical_strongs.py, all eight
SHARD A adapters, ingest/lexical/run.py, plus byte samples of OSHB
wlc/Gen.xml osisID attributes, MACULA-Hebrew lowfat ref/xml:id attributes,
and MACULA-Greek SBLGNT TSV header and rows.

SHARD A scope: oshb, macula_hebrew, macula_greek, morphgnt, bhsa,
etcbc_parallels, etcbc_phono, open_cbgm_3_john.

## Node id / key namespace facts (ground truth = producing adapter code)

- oshb (DATASETS[0]): Word.id = `oshb:<osisRef>.w<NN>`; Word.ref =
  `<osisRef>` BARE OSIS DOTTED (= OSHB XML osisID attribute, e.g.
  `Gen.1.1`, confirmed from data/private/oshb/wlc/Gen.xml osisID="Gen.1.1");
  Word.source = `OSHB-morphology`. Morpheme.id =
  `oshb-morph:<osisRef>.w<NN>.m<MM>`. Verse.id = `verse:<osisRef>`,
  Verse.osisID = `<osisRef>` bare, Verse.osis = `<osisRef>` bare. Strong.id
  = bare canonical Strong with the disambig suffix STRIPPED OFF (oshb.py
  438-441, so `H1234` even when raw was `H1234A`). Reading.reading_id =
  `oshb-reading:<osisRef>.w<NN>.qere`.
- macula_hebrew (DATASETS[1]): MaculaToken.id = bare upstream `xml:id`
  (e.g. `o010010010011`). Lemma.id = `macula-hebrew-lemma:<strong>` where
  `<strong>` = canonical_strongs output WITH suffix retained
  (`canon[0]`, e.g. `H0001` or `H1234A`, zero-padded 4 digits).
  Lemma.strong = same canonical string. GreekLemma.id =
  `macula-hebrew-greek-lemma:<strong>` (e.g. `macula-hebrew-greek-lemma:G0001`).
- bhsa (DATASETS[2]): BhsaWord/BhsaPhrase/BhsaClause.id = `bhsa:tf:<node_id>`
  (text-fabric integer slot id). BhsaWord.ref = `<osis_book>.<ch>.<v>`
  integer form (ETCBC Latin book mapped to OSIS, e.g. `Gen.1.1`).
- etcbc_phono (DATASETS[3]): writes NO edges. MATCH (w:BhsaWord {id:
  `bhsa:tf:<node_id>`}) SET w.phono. Key-value matches bhsa exactly.
- etcbc_parallels (DATASETS[4]): no nodes. PARALLEL_OF endpoints
  `bhsa:tf:<token>` from the crossref TF feature integers.
- morphgnt (DATASETS[5]): Word.id = `morphgnt-sblgnt:<osisRef>.w<NN>`;
  Word.source = `MorphGNT-SBLGNT`. Verse.id = `verse:<osisRef>`, Verse.osis
  = `<osisRef>` bare. morphgnt writes NO Verse.osisID property.
- macula_greek (DATASETS[6]): the ONLY GreekLemma producer on the
  macula/morphgnt path. Word.id = `<source>:<xml:id>` where xml:id is the
  MACULA TEI token id (e.g. `MACULA-Greek-SBLGNT:n40001001001`, confirmed
  from the SBLGNT TSV). Word.source = `MACULA-Greek-SBLGNT` or
  `MACULA-Greek-Nestle1904`. GreekLemma.id = `<source>:strong-<NNNNN>`
  with NNNNN = `int(strong):05d` (5-digit zero-pad, e.g.
  `MACULA-Greek-SBLGNT:strong-00040`, macula_greek.py 519).
  GreekLemma.strong = `int(strong)` (INTEGER type, line 525). The
  docstring section 9 CLAIMS GreekLemma.id = `<edition>:<xml:id>` but the
  CODE writes `<source>:strong-<5digit>`; the code is ground truth.
- open_cbgm_3_john (DATASETS[19]): self-contained. Witness.siglum verbatim,
  Reading.reading_id = `<variant_unit_id>-<reading_name>`,
  VariantUnit.variant_unit_id = `3John.1.<v>/<unit_segment>`.

## Per-adapter per-edge join-key table

Legend: P = producing adapter of the endpoint node label. "consumer
value" = exact value/type/format the MATCH supplies. "producer value" =
exact value/type/format the producing adapter writes for that key.

### oshb (DATASETS[0]) -- all endpoints produced in-run by oshb

| edge | from endpoint: matched key / consumer value vs producer value | to endpoint: matched key / consumer value vs producer value | verdict | producer + file:line both sides | faithful fix |
|---|---|---|---|---|---|
| HAS_MORPHEME | `{id}` consumer `oshb:<ref>.w<NN>` vs oshb Word.id `oshb:<ref>.w<NN>` | `{id}` consumer `oshb-morph:<ref>.w<NN>.m<MM>` vs oshb Morpheme.id same | MATCH-OK (label gap only) | P=oshb oshb.py:524/563 ; edge oshb.py:367/578 | none (perf label add already in manifest) |
| IN_VERSE | `{id}` `oshb:<ref>.w<NN>` vs oshb Word.id same | `{id}` consumer `verse:<ref>` vs oshb Verse.id `verse:<ref>` | MATCH-OK (label gap only) | P=oshb oshb.py:524/628 ; edge oshb.py:372/540 | none (perf label add already in manifest) |
| INSTANCE_OF | `{id}` `oshb:<ref>.w<NN>` (Word) OR `oshb-morph:...` (Morpheme) vs oshb Word/Morpheme.id same | `{id}` consumer bare `H<digits>` vs oshb Strong.id bare `H<digits>` (suffix stripped both sides) | MATCH-OK (het split is perf-class) | P=oshb oshb.py:549/555/591 ; edge oshb.py:377 | none (perf het split already in manifest) |
| IS_QERE_OF | `{reading_id}` `oshb-reading:<ref>.w<NN>.qere` vs oshb Reading.reading_id same | `{id}` `oshb:<ref>.w<NN>` vs oshb Word.id same | MATCH-OK (label gap only) | P=oshb oshb.py:603/615 ; edge oshb.py:382 | none (perf label add already in manifest) |
| FROM_EDITION | `{id}` `oshb:<ref>.w<NN>` vs oshb Word.id same | `{slug}` `OSHB-morphology` vs oshb Source.slug `OSHB-morphology` | MATCH-OK (label gap only) | P=oshb oshb.py:711 ; edge oshb.py:387/542 | none (perf label add already in manifest) |

oshb is internally self-consistent on every key value and type. The only
open items are the perf-class label adds and the het INSTANCE_OF split,
all already enumerated in the perf manifest. No KEY-MISMATCH.

### macula_hebrew (DATASETS[1])

| edge | from endpoint | to endpoint | verdict | producer + file:line both sides | faithful fix |
|---|---|---|---|---|---|
| HAS_MACULA_ENRICHMENT | `Word {source:'OSHB-morphology', ref: row.osis_ref}` consumer ref value = `_osis_ref(MACULA ref)` = `GEN 1:1` (UPPER book, space, colon, `!`-stripped, NOT OSIS-dotted) vs oshb Word.ref producer value = `Gen.1.1` (mixed-case OSIS dotted, = OSHB XML osisID) | `MaculaToken {id: row.to_id}` consumer `o0100100100..` vs macula_hebrew MaculaToken.id same | **KEY-MISMATCH on from side** | from P=oshb oshb.py:534 (`"ref": osis_ref`, osis_ref = verse osisID `Gen.1.1`) ; consumer macula_hebrew.py:409 + 494-498 + 604-611 (`GEN 1:1`). to side P=macula_hebrew.py:509 | see DEFECT LEDGER A-1 |
| INSTANCE_OF | `MaculaToken {id: row.from_id}` vs macula_hebrew MaculaToken.id same | `Lemma {id: row.to_id}` `macula-hebrew-lemma:<strong>` vs macula_hebrew Lemma.id same | MATCH-OK | P=macula_hebrew.py:509/560 ; edge 417-419/616-618 | none |
| BRIDGES_LXX | `Lemma {id: row.from_id}` `macula-hebrew-lemma:<strong>` vs macula_hebrew Lemma.id same | `GreekLemma {id: row.to_id}` `macula-hebrew-greek-lemma:<strong>` vs macula_hebrew GreekLemma.id same | MATCH-OK within macula_hebrew (see structural note) | P=macula_hebrew.py:560/581 ; edge 424-425/626-633 | none (but see structural fragmentation note) |

Structural note (not a SHARD A zero-match, recorded for the data-model
follow-up): macula_hebrew creates its OWN GreekLemma nodes namespaced
`macula-hebrew-greek-lemma:G0001`, while macula_greek (the only GreekLemma
producer on the macula/morphgnt path) writes `MACULA-Greek-...:strong-00001`.
The two GreekLemma node sets are DISJOINT. macula_hebrew's BRIDGES_LXX is
self-consistent (it MERGEs the very node it points at), so it is MATCH-OK
for this adapter's own edge, but the two adapters' GreekLemma populations
never unify. This is a data-model fragmentation that surfaces downstream
(Decision 4 intends one GreekLemma keyspace); it is flagged MUST-ESCALATE
for the data-model owner, not auto-fixed, because choosing the canonical
GreekLemma key is a Decision 2/4 schema call (same family as the tagnt
escalation in Shard B's manifest).

### macula_greek (DATASETS[6]) -- all endpoints produced in-run

| edge | from endpoint | to endpoint | verdict | producer + file:line | faithful fix |
|---|---|---|---|---|---|
| INSTANCE_OF | `Word {id}` `<source>:<xml:id>` vs macula_greek Word.id same | `GreekLemma {id}` `<source>:strong-<5d>` vs macula_greek GreekLemma.id same | MATCH-OK | P=macula_greek.py:497/519 ; edge 418-419/617 | none |
| IN_DOMAIN | `Word {id}` same | `LouwNidaDomain {id}` `str(domain_code)` vs macula_greek LouwNidaDomain.id same | MATCH-OK | P=macula_greek.py:497/531 ; edge 426-427/640 | none |
| FROM_EDITION | `Word {id}` same | `Source {slug}` vs macula_greek Source.slug same | MATCH-OK | P=macula_greek.py:497/563-571 ; edge 437-438/608 | none |

macula_greek is internally self-consistent. No KEY-MISMATCH.

### morphgnt (DATASETS[5])

| edge | from endpoint | to endpoint | verdict | producer + file:line both sides | faithful fix |
|---|---|---|---|---|---|
| IN_VERSE | `Word {id: row.from_id}` `morphgnt-sblgnt:<ref>.w<NN>` vs morphgnt Word.id same | `Verse {id: row.to_id}` consumer `verse:<ref>` vs morphgnt Verse.id `verse:<ref>` (same-run producer) | MATCH-OK (label gap only) | P=morphgnt.py:360/376 ; edge 263-266/385 | none (already labeled, perf CLEAN) |
| PARSE_OF | `Word {id: row.from_id}` `morphgnt-sblgnt:<ref>.w<NN>` vs morphgnt Word.id same | `Word {id: row.to_id, source: row.target_source}` consumer id = `MACULA-Greek-SBLGNT:<ref>.w<NN>` (e.g. `MACULA-Greek-SBLGNT:John.1.1.w01`) vs macula_greek Word.id producer value = `MACULA-Greek-SBLGNT:<xml:id>` (e.g. `MACULA-Greek-SBLGNT:n40001001001`); source value `MACULA-Greek-SBLGNT` matches | **KEY-MISMATCH on to side (id value format) + CROSS-GROUP ORDERING HAZARD** | to P=macula_greek.py:497 (`f"{source}:{xml_id}"`, xml_id = MACULA TEI token id from SBLGNT TSV col `xml:id`=`n40001001001`) ; consumer morphgnt.py:389 (`f"{MACULA_GREEK_SLUG}:{osis_ref}.w{position:02d}"`) | see DEFECT LEDGER A-2 |

### bhsa (DATASETS[2])

| edge | from endpoint | to endpoint | verdict | producer + file:line both sides | faithful fix |
|---|---|---|---|---|---|
| CONTAINS_PHRASE | `{id}` `bhsa:tf:<clause_node>` vs bhsa BhsaClause.id same | `{id}` `bhsa:tf:<phrase_node>` vs bhsa BhsaPhrase.id same | MATCH-OK (label gap only) | P=bhsa.py:823/809 ; edge 405/875 | none (perf label add already in manifest) |
| CONTAINS_WORD | `{id}` `bhsa:tf:<phrase_node>` vs bhsa BhsaPhrase.id same | `{id}` `bhsa:tf:<word_node>` vs bhsa BhsaWord.id same | MATCH-OK (label gap only) | P=bhsa.py:809/792 ; edge 409/879 | none (perf label add already in manifest) |
| IN_VERSE | `{id}` `bhsa:tf:<word_node>` vs bhsa BhsaWord.id same | `{id}` consumer `verse:<osis_book>.<ch>.<v>` vs oshb Verse.id `verse:<osisRef>` (both `verse:Gen.1.1` form) | MATCH-OK on key value (label gap only) | from P=bhsa.py:792 ; to P=oshb oshb.py:628 ; edge bhsa.py:413/883 | none (perf label add already in manifest); see ordering note |

bhsa IN_VERSE to-side note: bhsa builds `verse:{ref}` with ref =
`f"{osis_book}.{chapter_int}.{verse_int}"` via the ETCBC-Latin to OSIS
book table (Genesis->Gen ...). oshb writes Verse.id = `verse:<OSHB
osisID>` = `verse:Gen.1.1`. For the 39-book Hebrew canon both render
`verse:<OSIS book>.<int ch>.<int v>` so the key VALUE matches. oshb
(DATASETS[0]) runs before bhsa (DATASETS[2]) so the Verse exists at flush
time. This edge is correct on value and ordering; only the perf label add
(already in the manifest) remains. MATCH-OK.

### etcbc_parallels (DATASETS[4])

| edge | from endpoint | to endpoint | verdict | producer + file:line | faithful fix |
|---|---|---|---|---|---|
| PARALLEL_OF | `BhsaWord {id: row.source_id}` `bhsa:tf:<tok>` vs bhsa BhsaWord.id `bhsa:tf:<node_id>` | `BhsaWord {id: row.target_id}` `bhsa:tf:<tok>` vs bhsa BhsaWord.id same | MATCH-OK | from/to P=bhsa.py:792 ; edge etcbc_parallels.py:337-338/441-442 | none (already labeled, perf CLEAN; bhsa[2] runs before etcbc_parallels[4]) |

### etcbc_phono (DATASETS[3])

No relationships emitted. The only MATCH is the SET pass `MATCH
(w:BhsaWord {id: 'bhsa:tf:<node_id>'}) SET w.phono`. Consumer key value
`bhsa:tf:<node_id>` byte-matches bhsa BhsaWord.id. No edge to audit;
property-attach key is consistent. Not classified (no relationship).

### open_cbgm_3_john (DATASETS[19]) -- all endpoints produced in-run

| edge | from endpoint | to endpoint | verdict | producer + file:line | faithful fix |
|---|---|---|---|---|---|
| READS_AT | `{siglum}` verbatim siglum vs open_cbgm Witness.siglum same | `{reading_id}` `<vu_id>-<rdg>` vs open_cbgm Reading.reading_id same | MATCH-OK (label gap only) | P=open_cbgm_3_john.py:493/502 ; edge 507-509 | none (perf label add already in manifest) |
| ATTESTED_BY | `{reading_id}` same | `{variant_unit_id}` `3John.1.<v>/<seg>` vs open_cbgm VariantUnit.variant_unit_id same | MATCH-OK (label gap only) | P=open_cbgm_3_john.py:502/498 ; edge 514-515 | none (perf label add already in manifest) |
| CORRECTOR_OF | `{siglum}` corrector siglum vs Witness.siglum same | `{siglum}` base siglum vs Witness.siglum same | MATCH-OK (label gap only) | P=open_cbgm_3_john.py:493 ; edge 521-522 | none (perf label add already in manifest) |

open_cbgm_3_john is internally self-consistent on every key value and
type. No KEY-MISMATCH.

## Edge audit tally (SHARD A)

Relationship endpoints audited across 8 adapters:

- oshb: 5 edges (HAS_MORPHEME, IN_VERSE, INSTANCE_OF, IS_QERE_OF,
  FROM_EDITION) = all MATCH-OK (perf-class label/het only).
- macula_hebrew: 3 edges (HAS_MACULA_ENRICHMENT, INSTANCE_OF,
  BRIDGES_LXX) = 1 KEY-MISMATCH (HAS_MACULA_ENRICHMENT), 2 MATCH-OK.
- macula_greek: 3 edges = all MATCH-OK.
- morphgnt: 2 edges (IN_VERSE, PARSE_OF) = 1 KEY-MISMATCH (PARSE_OF,
  also ordering hazard), 1 MATCH-OK.
- bhsa: 3 edges (CONTAINS_PHRASE, CONTAINS_WORD, IN_VERSE) = all
  MATCH-OK on key value (perf label gap only).
- etcbc_parallels: 1 edge (PARALLEL_OF) = MATCH-OK.
- etcbc_phono: 0 edges (property-attach only; key consistent).
- open_cbgm_3_john: 3 edges (READS_AT, ATTESTED_BY, CORRECTOR_OF) = all
  MATCH-OK (perf label gap only).

Total relationship edges audited: 23.
- MATCH-OK: 21 (of which 17 carry a separate perf-class LABEL-INDEX-GAP
  already enumerated in docs/PHASE_D_EDGE_PERF_MANIFEST.md and NOT
  re-reported here as defects).
- KEY-MISMATCH: 2 (macula_hebrew HAS_MACULA_ENRICHMENT, morphgnt
  PARSE_OF; PARSE_OF additionally carries a cross-group ordering hazard).
- LABEL-INDEX-GAP (perf-only, cross-referenced not double-reported): 17
  endpoints across oshb(5), bhsa(3), open_cbgm(3), plus the labeled-but
  edges; all already owned by the perf manifest's FIX WAVE PLAN.

Plus 1 MUST-ESCALATE structural item (GreekLemma keyspace fragmentation
between macula_hebrew and macula_greek; not a SHARD A zero-match for
either adapter's own edge, but defeats the Decision 4 unified-GreekLemma
intent).

## SHARD-A DEFECT LEDGER (every KEY-MISMATCH with the precise correctness fix)

### A-1. macula_hebrew HAS_MACULA_ENRICHMENT -- OSIS reference FORMAT divergence (tahot-class)

- Owning adapter file: `ingest/lexical/macula_hebrew.py`.
- Edge: `(:Word {source:'OSHB-morphology'})-[:HAS_MACULA_ENRICHMENT]->(:MaculaToken)`.
- Consumer match (macula_hebrew.py:407-414): `MATCH (w:Word
  {source:'OSHB-morphology', ref: row.osis_ref})`. `row.osis_ref` is built
  at macula_hebrew.py:604-611 from `_osis_ref(row["ref"])`; `_osis_ref`
  (macula_hebrew.py:494-498) only splits the upstream MACULA `ref` at `!`
  and strips whitespace. The MACULA-Hebrew lowfat upstream `ref` value is
  `GEN 1:1!1` (confirmed from
  data/private/macula-hebrew/WLC/lowfat/01-Gen-001-lowfat.xml), so
  `row.osis_ref` = `GEN 1:1` (UPPERCASE book, ASCII space, colon, no
  conversion to OSIS dotted form).
- Producer-written value (oshb.py:534, `"ref": osis_ref`; osis_ref =
  verse_elem.get("osisID"), oshb.py:624): oshb Word.ref = the OSHB XML
  `osisID` attribute = `Gen.1.1` (mixed-case OSIS book, dot separators).
  Confirmed from data/private/oshb/wlc/Gen.xml `osisID="Gen.1.1"`.
- Divergence: consumer expects `ref = "GEN 1:1"`, producer wrote
  `ref = "Gen.1.1"`. `"GEN 1:1" != "Gen.1.1"` for every row. Every
  HAS_MACULA_ENRICHMENT MERGE matches ZERO Word nodes and silently
  creates ZERO edges. This breaks the Decision 1 acceptance gate
  (alignment ratio >= 0.98) completely: it would compute 0/total.
- Type: both string; the defect is VALUE FORMAT (book case, separators,
  no OSIS canonicalisation), not type.
- Faithful fix (correctness, not cosmetic): macula_hebrew MUST normalise
  the MACULA upstream `ref` into the canonical OSIS dotted form that oshb
  writes for Word.ref before using it as the join key. Concretely, in
  `_osis_ref` (or a new helper called from the enrichment builder at
  macula_hebrew.py:604-611), convert `GEN 1:1` to `Gen.1.1`: map the
  uppercase MACULA book token to the OSIS book abbreviation oshb uses
  (the same OSIS book set OSHB's osisID attribute carries), replace the
  space and colon with dots, and drop the `!word` suffix (already done).
  The join key must become byte-identical to oshb Word.ref. The owning
  side is macula_hebrew (the consumer): oshb Word.ref is the canonical
  OSIS form per Decision 1 and Decision 15 (OSIS is the join key Pipeline
  2 walks) and must NOT change. This is a correctness fix: the intended
  target is the OSHB Word for that OSIS verse and that intent is
  currently never satisfied.

### A-2. morphgnt PARSE_OF -- MACULA-Greek Word.id VALUE FORMAT divergence + CROSS-GROUP ORDERING HAZARD (tahot/tagnt-class)

- Owning adapter file: `ingest/lexical/morphgnt.py` (id-format defect).
  Secondary owner for the ordering hazard: `ingest/lexical/run.py`
  DATASETS order.
- Edge: `(:Word {source:'MorphGNT-SBLGNT'})-[:PARSE_OF]->(:Word
  {source:'MACULA-Greek-SBLGNT'})`.
- Consumer match (morphgnt.py:268-272, target row built
  morphgnt.py:388-394): `MATCH (b:Word {id: row.to_id, source:
  row.target_source})` with `to_id = f"{MACULA_GREEK_SLUG}:{osis_ref}.w{position:02d}"`
  = e.g. `MACULA-Greek-SBLGNT:John.1.1.w01`; `target_source =
  "MACULA-Greek-SBLGNT"`.
- Producer-written value (macula_greek.py:497, `"id": f"{source}:{xml_id}"`,
  xml_id from the SBLGNT TSV `xml:id` column): macula_greek Word.id =
  `MACULA-Greek-SBLGNT:n40001001001` (the MACULA TEI token id, confirmed
  from data/private/macula-greek/SBLGNT/tsv/macula-greek-SBLGNT.tsv first
  data row xml:id=`n40001001001`). macula_greek Word.source =
  `MACULA-Greek-SBLGNT` (matches the consumer `source` filter).
- Divergence 1 (KEY-MISMATCH, id value format): consumer expects id
  `MACULA-Greek-SBLGNT:<osisRef>.w<NN>`, producer wrote id
  `MACULA-Greek-SBLGNT:<MACULA xml:id>`. The `<osisRef>.w<NN>` form is
  NEVER produced by macula_greek; macula_greek's id namespace is the TEI
  token id, not an OSIS+position string. Every PARSE_OF MERGE matches
  ZERO MACULA-Greek Word nodes. The `source` half of the composite key
  matches; only `id` diverges, but `id` alone defeats the match. This
  breaks the morphgnt acceptance gate (`(:Word {source:'MorphGNT-SBLGNT'})
  -[:PARSE_OF]->(:Word {source:'MACULA-Greek-SBLGNT'})` returns 0).
- Divergence 2 (CROSS-GROUP ORDERING HAZARD, independent and additive):
  run.py DATASETS orders morphgnt at index [5] and macula_greek at index
  [6], so morphgnt runs and flushes its PARSE_OF batch BEFORE macula_greek
  has created ANY MACULA-Greek Word node. Even with the id format fixed,
  zero target nodes exist at PARSE_OF flush time. phase_02_lexical_ingest.md
  bullet 4 and the morphgnt docstring (morphgnt.py:160-173) BOTH state
  morphgnt MUST run AFTER macula_greek ("this MorphGNT adapter runs within
  Group 1 after macula_greek.py so the join target set is materialised").
  run.py contradicts that documented dependency.
- Type: both string id; defect is VALUE FORMAT plus ORDERING.
- Faithful fix (correctness, not cosmetic), TWO parts both required:
  1. id format: morphgnt cannot reconstruct macula_greek's TEI token id
     (`n40001001001`) from `(osis_ref, position)` by string formatting;
     the MACULA xml:id encodes book+chapter+verse+word in a different
     scheme. The faithful join must key on a property both adapters
     agree on for the SBLGNT Greek word. The candidates are (a) join on
     the MACULA `ref`+position derived OSIS instead of id (macula_greek
     persists Word.ref = the MACULA `MAT 1:1!1` form, which is itself
     non-OSIS and would need the same normalisation as A-1), or (b) add
     a deterministic OSIS-position alias property on macula_greek Word
     (e.g. `osis_word_id = <osisRef>.w<NN>`) and have morphgnt PARSE_OF
     match on that alias. The canonical key choice (MACULA xml:id vs an
     OSIS+position alias) is a data-model decision because macula_greek's
     id namespace is contractually the TEI token id and morphgnt has no
     access to it from its own bytes. Mark MUST-ESCALATE for the key
     selection; do NOT guess. Owning adapter for whichever side changes:
     morphgnt.py (consumer) if an alias is added on macula_greek, or
     macula_greek.py if it must emit the alias property.
  2. ordering: move morphgnt AFTER macula_greek in run.py DATASETS (swap
     indices [5] and [6], or relocate `"morphgnt"` to follow
     `"macula_greek"`). This aligns run.py with the documented Group 1
     dependency. This part is unambiguous and is a straightforward
     correctness fix (not a guess), but run.py edits are out of THIS
     auditor's deliverable scope; recorded here for the implementer wave.

## MUST-ESCALATE items (do NOT guess; data-model decision required)

1. **morphgnt PARSE_OF canonical join key** (defect A-2 part 1): the
   correct shared key between morphgnt Word and macula_greek
   MACULA-Greek-SBLGNT Word is genuinely ambiguous from static analysis.
   macula_greek's Word.id is the MACULA TEI token id by contract;
   morphgnt cannot derive it. Whether to (a) add an OSIS+position alias
   property on macula_greek Word and re-key PARSE_OF onto it, or (b)
   normalise and join on a shared OSIS reference plus in-verse position,
   is a Decision 15 / Decision 2 schema call. ESCALATE.
2. **GreekLemma keyspace fragmentation** (macula_hebrew vs macula_greek):
   macula_hebrew writes GreekLemma.id = `macula-hebrew-greek-lemma:G0001`
   and GreekLemma.strong = string `G0001`; macula_greek writes
   GreekLemma.id = `MACULA-Greek-SBLGNT:strong-00001` and
   GreekLemma.strong = int `1`. Decision 4 intends ONE GreekLemma
   keyspace the Hebrew bridge can reach by Strong alone. macula_hebrew's
   BRIDGES_LXX is self-consistent (MATCH-OK for its own edge because it
   MERGEs the node it points at) so it is NOT a SHARD A zero-match, but
   the two GreekLemma node populations never unify and the int-vs-string
   GreekLemma.strong type split is the same class as the Shard B tagnt
   escalation. The canonical GreekLemma key (namespace + strong type) is
   a Decision 2/4 data-model decision. ESCALATE.

## Cross-group ordering hazard summary (SHARD A)

One hard ordering inversion inside SHARD A: **morphgnt (DATASETS[5])
flushes PARSE_OF before its target producer macula_greek (DATASETS[6])
runs.** This is independent of and additive to the A-2 id-format
KEY-MISMATCH: both must be fixed for a single PARSE_OF edge to be
created. The phase_02 runbook and the morphgnt docstring both require
morphgnt to run after macula_greek; run.py violates this. All other
SHARD A producer/consumer pairs are correctly ordered (oshb[0] before
macula_hebrew[1] and before bhsa[2]; bhsa[2] before etcbc_phono[3] and
etcbc_parallels[4]; oshb[0] before bhsa[2] IN_VERSE; open_cbgm_3_john
self-contained). Note: correct ordering does NOT rescue A-1, whose
defect is the ref VALUE FORMAT, not ordering (oshb runs first but the
`GEN 1:1` vs `Gen.1.1` value mismatch still yields zero matches).

## Adversarial conclusion

The bytes prove two NEW tahot/tagnt-class KEY-MISMATCH defects in SHARD A
that the perf manifest's label-only scan could not see, both on edges it
marked CLEAN:

- macula_hebrew HAS_MACULA_ENRICHMENT: OSIS-reference format divergence
  (`GEN 1:1` consumer vs `Gen.1.1` producer), zero edges, breaks the
  Decision 1 alignment gate. Owned by macula_hebrew.py.
- morphgnt PARSE_OF: MACULA-Greek Word.id value-format divergence
  (`MACULA-Greek-SBLGNT:John.1.1.w01` consumer vs
  `MACULA-Greek-SBLGNT:n40001001001` producer) PLUS a run.py ordering
  inversion. Zero edges. Owned by morphgnt.py (+ run.py for ordering).

Plus the GreekLemma keyspace fragmentation (data-model, MUST-ESCALATE).
Every other SHARD A join was traced to the producing adapter's emission
code and the key value, type, and format confirmed byte-consistent; the
remaining open items are the perf-class label/het/index adds already
owned by docs/PHASE_D_EDGE_PERF_MANIFEST.md and are not double-reported
here. The upcoming fix wave is now provably complete for SHARD A: 2
correctness KEY-MISMATCH fixes (1 mechanical on macula_hebrew, 1 split
into a mechanical run.py ordering swap plus a MUST-ESCALATE key choice)
and 2 MUST-ESCALATE data-model decisions.
