# Phase D Defect A-2: PARSE_OF Join-Key Byte Evidence

Auditor caste, READ-ONLY static byte evidence for owner decision. Branch
main. Doctrinal frame brethren-on-trial. No em or en dashes anywhere
(periods, commas, "and", "but" only). This document does NOT recommend a
fix; it lays out the bytes and the two candidate options neutrally for
owner review.

Defect under examination: every
`(:Word {source:'MorphGNT-SBLGNT'})-[:PARSE_OF]->(:Word {source:'MACULA-Greek-SBLGNT'})`
edge resolves zero target nodes, because morphgnt builds the target key
as an OSIS+position string while macula_greek writes the MACULA TEI
xml:id as the key. (Defect A-2, docs/PHASE_D_JOINKEY_AUDIT_A.md lines
249-309.)

Sources read in full for this evidence: ingest/lexical/morphgnt.py,
ingest/lexical/macula_greek.py (both docstrings and code bodies),
docs/SCHEMA_DECISIONS.md Decisions 2 and 15,
docs/PHASE_D_JOINKEY_AUDIT_A.md defect A-2, plus the real upstream bytes
data/private/macula-greek/SBLGNT/tsv/macula-greek-SBLGNT.tsv (20,981,023
bytes, header + 137,741 data rows) and data/private/morphgnt/*.txt (27
per-book files, 137,554 data lines).

---

## 1. How macula_greek constructs SBLGNT Word.id

### The code (ground truth, the docstring section 9 is contradicted by it)

`ingest/lexical/macula_greek.py` line 497, inside `_row_word_payload`:

```python
xml_id = _coerce_string(fields.get("xml:id", ""))
source = _EDITION_TO_SOURCE[edition]      # "MACULA-Greek-SBLGNT"
payload = {
    "id": f"{source}:{xml_id}" if xml_id else None,
    ...
}
```

So `Word.id = "MACULA-Greek-SBLGNT:" + <verbatim TSV xml:id column>`.
`xml:id` is column 1 of the SBLGNT TSV (header read at line 539-542,
`_iter_tsv_rows` zips header names to values). No transformation is
applied to the xml:id beyond `_coerce_string` (trim + n/a coercion).

### 5 real example ids from the real upstream (John 1:1, first 5 tokens)

Bytes from data/private/macula-greek/SBLGNT/tsv/macula-greek-SBLGNT.tsv
(TSV columns: 1=`xml:id`, 2=`ref`, 9=`text`, 11=`lemma`, 12=`normalized`,
13=`strong`):

| TSV xml:id   | TSV ref     | TSV text | macula_greek Word.id (line 497)          |
|--------------|-------------|----------|------------------------------------------|
| n43001001001 | JHN 1:1!1   | Ἐν       | `MACULA-Greek-SBLGNT:n43001001001`       |
| n43001001002 | JHN 1:1!2   | ἀρχῇ     | `MACULA-Greek-SBLGNT:n43001001002`       |
| n43001001003 | JHN 1:1!3   | ἦν       | `MACULA-Greek-SBLGNT:n43001001003`       |
| n43001001004 | JHN 1:1!4   | ὁ        | `MACULA-Greek-SBLGNT:n43001001004`       |
| n43001001005 | JHN 1:1!5   | λόγος    | `MACULA-Greek-SBLGNT:n43001001005`       |

### Decoding the TEI xml:id and what positional info macula_greek has

The xml:id `n43001001001` decomposes (verified against the `ref` column
across every John 1:1 row, and the Pericope rows JHN 7:53):

```
n 43      001       001     001
^ book    chapter   verse   in-verse word position (1-based, 3 digits)
```

- The trailing 3 digits of the xml:id are EXACTLY the 1-based in-verse
  word position. Verified byte-for-byte: `n43001001001`..`n43001001017`
  line up 1:1 with `JHN 1:1!1`..`JHN 1:1!17`.
- macula_greek ALSO reads the `ref` column into `Word.ref`
  (macula_greek.py line 498, `"ref": _coerce_string(fields.get("ref",""))`).
  The raw `ref` value is the MACULA form `JHN 1:1!1` (uppercase 3-letter
  book token, space, `chapter:verse`, `!`, 1-based position). This is
  the SAME non-OSIS form flagged in defect A-1 for macula_hebrew.
- Therefore at Word-build time macula_greek HAS, losslessly and cheaply,
  both (a) the MACULA book/chapter/verse/position via the `ref` column
  and (b) the same position redundantly encoded in the xml:id tail. It
  does NOT currently emit any OSIS-dotted reference nor any
  OSIS+position alias property. It could compute one with no information
  loss (the book token maps deterministically to an OSIS book; chapter,
  verse, and position are integers already present). Max in-verse
  position in the whole SBLGNT corpus is 58 (REV 20:4), so a 2-digit or
  3-digit zero-padded position never overflows.

---

## 2. How morphgnt constructs its PARSE_OF target key

### The code

`ingest/lexical/morphgnt.py` lines 388-394, `_parse_of_edge_row`:

```python
def _parse_of_edge_row(word_id, osis_ref, position):
    target_id = f"{MACULA_GREEK_SLUG}:{osis_ref}.w{position:02d}"
    return {"from_id": word_id,
            "to_id": target_id,
            "target_source": MACULA_GREEK_SLUG}     # "MACULA-Greek-SBLGNT"
```

`osis_ref` is built by `_osis_ref` (lines 282-290) from the 6-digit
`bcv`: book index `int(bcv[:2])` indexes `OSIS_BOOKS`, then
`f"{book}.{int(bcv[2:4])}.{int(bcv[4:6])}"`. `position` is the 1-based
enumeration index within the verse group (lines 418-424,
`for idx, rec in enumerate(words, start=1)`). The MATCH that consumes
this key is line 270: `MATCH (b:Word{id: row.to_id, source: row.target_source})`.

NB: in the MorphGNT upstream the `bcv` book field for John is `04`
(file is named `64-Jn-morphgnt.txt` but the in-line bcv is `040101`);
`OSIS_BOOKS[4-1] = "John"`, so `_osis_ref("040101") = "John.1.1"`.

### 5 real example keys from the real MorphGNT bytes (John 1:1, first 5)

Bytes from data/private/morphgnt/64-Jn-morphgnt.txt (space-delimited:
`bcv pos parse text word normalized lemma`):

| MorphGNT bcv | text  | word  | normalized | lemma  | morphgnt expected PARSE_OF target key   |
|--------------|-------|-------|------------|--------|-----------------------------------------|
| 040101       | Ἐν    | Ἐν    | ἐν         | ἐν     | `MACULA-Greek-SBLGNT:John.1.1.w01`      |
| 040101       | ἀρχῇ  | ἀρχῇ  | ἀρχῇ       | ἀρχή   | `MACULA-Greek-SBLGNT:John.1.1.w02`      |
| 040101       | ἦν    | ἦν    | ἦν         | εἰμί   | `MACULA-Greek-SBLGNT:John.1.1.w03`      |
| 040101       | ὁ     | ὁ     | ὁ          | ὁ      | `MACULA-Greek-SBLGNT:John.1.1.w04`      |
| 040101       | λόγος,| λόγος | λόγος      | λόγος  | `MACULA-Greek-SBLGNT:John.1.1.w05`      |

Identifiers morphgnt has at edge-build time: `osis_ref` (e.g.
`John.1.1`, derived), 1-based in-verse `position`, the SBLGNT surface
token `text` (with punctuation, e.g. `λόγος,`), the punctuation-stripped
`word`, the `normalized` form, and the `lemma`. It does NOT have, and
cannot reconstruct from these bytes, the MACULA TEI xml:id
`n43001001001` (the `n` + 2-digit book + 3-digit ch + 3-digit v +
3-digit pos scheme is a MACULA-internal encoding morphgnt never sees).

---

## 3. Side-by-side, same 5 verse-positions, and reconcilability

| OSIS pos    | macula_greek Word.id (producer, line 497) | morphgnt expected key (consumer, line 389) | byte-equal? |
|-------------|-------------------------------------------|--------------------------------------------|-------------|
| John 1:1 w01| `MACULA-Greek-SBLGNT:n43001001001`        | `MACULA-Greek-SBLGNT:John.1.1.w01`         | NO          |
| John 1:1 w02| `MACULA-Greek-SBLGNT:n43001001002`        | `MACULA-Greek-SBLGNT:John.1.1.w02`         | NO          |
| John 1:1 w03| `MACULA-Greek-SBLGNT:n43001001003`        | `MACULA-Greek-SBLGNT:John.1.1.w03`         | NO          |
| John 1:1 w04| `MACULA-Greek-SBLGNT:n43001001004`        | `MACULA-Greek-SBLGNT:John.1.1.w04`         | NO          |
| John 1:1 w05| `MACULA-Greek-SBLGNT:n43001001005`        | `MACULA-Greek-SBLGNT:John.1.1.w05`         | NO          |

Why they cannot be reconciled from morphgnt's bytes alone: the producer
key is `<slug>:<MACULA TEI xml:id>`. The xml:id `n43001001001` is a
MACULA-internal token id. morphgnt's inputs are `(bcv, pos, parse, text,
word, normalized, lemma)`. There is no function from
`(osis_ref, position)` to `n43001001001` available to morphgnt: the
book code 43 (MACULA's John) is not the MorphGNT bcv book code 04, and
the zero-pad widths differ (MACULA 3-digit chapter/verse/position vs
morphgnt 2-digit position). morphgnt would have to embed the entire
MACULA book-numbering table and xml:id scheme, which is exactly the
MACULA-internal contract macula_greek owns. The `source` half of the
composite key (`MACULA-Greek-SBLGNT`) DOES match; only `id` diverges,
but `id` alone defeats the MATCH.

### Is a shared (osisRef, word-position) tuple reliably derivable on BOTH sides?

YES, and this is provable from the bytes. Both sides expose a 1-based
in-verse position and a book/chapter/verse:

- morphgnt: position is `enumerate(words, start=1)` over the verse group
  (line 418); osis_ref from bcv.
- macula_greek: position is the trailing 3 digits of the xml:id AND the
  integer after `!` in the `ref` column (both verified identical); the
  book/chapter/verse are in the `ref` column.

The pivotal question for Option B is whether MACULA in-verse position
and MorphGNT in-verse position are the SAME position for the SAME word,
i.e. whether the two tokenizations align 1:1 per verse. This was tested
against the real bytes corpus-wide (all 27 books, both full datasets):

**Per-verse word-count alignment (corpus-wide):**

- MorphGNT total words: 137,554. MACULA-Greek-SBLGNT total words:
  137,741. Corpus delta: 187 words.
- Distinct verses: MorphGNT 7,927; MACULA 7,939.
- Shared verses (present in both): 7,927.
- Shared verses where MorphGNT word count != MACULA word count: **0**.
  Every one of the 7,927 shared verses has an identical word count on
  both sides (max delta = 0).
- Verses present only in MACULA, never in MorphGNT: **12**, and they are
  exactly the Pericope Adulterae: John 7:53, 8:1, 8:2, 8:3, 8:4, 8:5,
  8:6, 8:7, 8:8, 8:9, 8:10, 8:11. MorphGNT emits zero lines for bcv
  040753 (the pericope is bracketed out of the MorphGNT SBLGNT edition
  entirely). These 12 verses account for the bulk of the 187-word
  corpus delta and have NO MorphGNT source word at all, so no PARSE_OF
  edge is possible for them under any option.
- Verses present only in MorphGNT, never in MACULA: 0.

**Per-position token alignment (corpus-wide, the stronger test):**

Equal counts alone do not prove positional alignment (two verses could
have equal counts yet differ in where a split falls). So every shared
verse was checked position-by-position, comparing MorphGNT `word`
(punctuation-stripped surface) against MACULA `text` (surface), with
Unicode accents/breathings and punctuation/elision marks normalised
away (NFD, drop combining marks, strip `’ ' . , ; : ! ? ( ) [ ]` etc.):

- Verses fully position-aligned on surface: **7,927 of 7,927** (100% of
  shared verses).
- Verses with at least one positional surface divergence: **0**.
- Total positional surface divergences across the whole corpus: **0**.

Tokenization edge cases verified explicitly against the bytes:

- Elision: John 1:3 position 2 is MorphGNT `δι’` vs MACULA `δι` (one
  token each, same position). Aligned.
- Crasis: Luke 1:3 position 2 is `κἀμοὶ` on BOTH sides as a single token
  (neither side splits the crasis). Aligned.
- Movable-nu / variant spelling differs in the `normalized` column
  (MACULA `normalized` follows a different convention, e.g. lemma-like
  forms, and is NOT a reliable cross-source key) but the SURFACE tokens
  and their COUNT and ORDER are identical. The earlier normalized-column
  comparison showed 4,700 verses differing, which is a column-semantics
  difference, NOT a tokenization difference: the surface comparison is 0
  divergences.

**Conclusion for Option B safety:** within the 7,927 shared verses the
(osisRef, in-verse position) tuple is provably 1:1 between the two
datasets from the real bytes (zero count mismatches, zero positional
surface divergences). The ONLY non-aligning class is the 12 Pericope
Adulterae verses that exist solely in MACULA and have no MorphGNT word
to originate a PARSE_OF edge, so they cannot mis-link (there is no
source row). No verse exists where a MorphGNT word would silently bind
to the wrong MACULA word under a position join. The misalignment risk
that would make Option B unsafe (a shared verse where positions diverge)
does not occur anywhere in this corpus.

---

## 4. The two candidate fixes, with concrete graph deltas filled in

Both options assume the independent run.py ordering inversion (defect
A-2 part 2: morphgnt at DATASETS[5] flushes before macula_greek at
DATASETS[6]) is also fixed; that ordering swap is out of this evidence
doc's scope but is required for ANY option to produce edges. The
options below address only the join-key value.

### Option A: macula_greek emits an OSIS+position alias property; morphgnt matches on it

What macula_greek would add (ingest/lexical/macula_greek.py
`_row_word_payload`, around line 492-510): compute an alias from the
`ref` column it already reads. `ref = "JHN 1:1!1"` -> map `JHN` to OSIS
`John` via a MACULA-3-letter to OSIS book table, take chapter, verse,
and the post-`!` integer position, render
`osis_wpos = f"{osis_book}.{chapter}.{verse}.w{position:02d}"` =
`John.1.1.w01`. Add one new payload key, for example:

```python
payload["osis_wpos"] = f"{osis_book}.{int(ch)}.{int(vs)}.w{pos:02d}"
```

written through the existing `MERGE (n:Word {id: row.id}) SET n += row`
(macula_greek.py line 397), so it lands as a property on the same Word
node with no new write path.

New backing index (graph/lexical.cypher, a one-line add, exact text
subject to that file's existing index DSL):

```cypher
CREATE INDEX word_osis_wpos IF NOT EXISTS
FOR (w:Word) ON (w.source, w.osis_wpos);
```

morphgnt match change (ingest/lexical/morphgnt.py): keep
`_parse_of_edge_row` building `John.1.1.w01` but route it to the alias,
and change `_MERGE_PARSE_OF` (line 268-272) from
`MATCH (b:Word{id: row.to_id, source: row.target_source})` to
`MATCH (b:Word{source: row.target_source, osis_wpos: row.to_wpos})`
with `to_wpos = f"{osis_ref}.w{position:02d}"`.

Graph delta concretely, John 1:1 w01:

- macula_greek Word node gains property
  `osis_wpos = "John.1.1.w01"` (id unchanged:
  `MACULA-Greek-SBLGNT:n43001001001`).
- morphgnt PARSE_OF MERGE matches
  `(:Word {source:'MACULA-Greek-SBLGNT', osis_wpos:'John.1.1.w01'})`
  and resolves the node. Edge created.

Faithfulness of the alias (from step 1): macula_greek can produce
`osis_wpos` with NO information loss. The position is already present
twice in the upstream (xml:id tail and the `ref` post-`!` integer, both
byte-verified equal); the book/chapter/verse are in the `ref` column;
the MACULA-to-OSIS book mapping is a fixed 27-entry table (the same
mapping morphgnt's OSIS_BOOKS implies). No upstream byte is dropped or
guessed. The alias is a redundant projection of data macula_greek
already holds.

Pros:
- The canonical macula_greek Word.id stays the contractual MACULA TEI
  xml:id (docstring section 3 / 9 honoured); no identity renamespacing.
- The change to the join is on the consumer side
  (morphgnt) plus a derived property on the producer; macula_greek's
  node identity and constraints are untouched.
- Alias is loss-free and deterministic per step 1.

Cons / faithfulness risk:
- macula_greek now carries a derived, denormalised property that
  duplicates position info; it must stay consistent with xml:id (low
  risk since both come from the same row, but it is a second source of
  truth for position).
- macula_greek must own a MACULA-3-letter to OSIS book table; an error
  there silently produces a non-matching alias (fails closed: edge just
  does not form, surfaces as an edge-count shortfall, not a mis-link).
- The 12 Pericope verses get an `osis_wpos` on the MACULA side but no
  MorphGNT source exists, so they remain unlinked by construction (not
  a defect of the option, an upstream corpus fact).

### Option B: both sides reduce to a normalized (osisRef, word-position) composite; PARSE_OF matches on that

Exact shared derivation (must be byte-identical on both sides):

- osisRef: OSIS book + `.` + integer chapter + `.` + integer verse, no
  zero padding (e.g. `John.1.1`). morphgnt already builds exactly this
  (`_osis_ref`). macula_greek would derive it from the `ref` column
  (`JHN 1:1` -> `John.1.1`) via the same 27-entry MACULA-to-OSIS table.
- word-position: 1-based in-verse integer, rendered identically on both
  sides, for example `w{position:02d}` (2 digits is safe: max in-verse
  position in the corpus is 58 on both sides, never exceeds 99).
- composite key: `f"{osisRef}.w{position:02d}"` = `John.1.1.w01`.

This is effectively Option A's value without keeping the TEI xml:id as
the node identity if the owner chose to also re-key the node; at
minimum it is a shared computed MATCH property on both sides. The
concrete graph delta is identical to Option A's match
(`John.1.1.w01` resolves John 1:1 word 1).

Risk from step 3, quantified against the real bytes: the risk that
makes Option B unsafe is a shared verse where MorphGNT position k and
MACULA position k are different words (a silent mis-link). Corpus-wide
this was measured: 7,927 shared verses, 0 with count mismatch, 0 with
any positional surface divergence. So **0 of the 7,927 sampled (in
fact, all) shared verses would mis-align**. The only non-1:1 class is
the 12 MACULA-only Pericope Adulterae verses, which have no MorphGNT
source word and therefore cannot mis-link (no edge originates). Under
this corpus Option B does not silently mis-link anywhere.

Pros:
- Symmetric, simplest mental model: one computed composite, no node
  carries a second identity property beyond what the join needs.
- No dependence on MACULA's internal xml:id scheme at all.

Cons / faithfulness risk:
- Correctness depends entirely on the 1:1 positional-alignment
  invariant. It holds for THIS frozen corpus (proven, 0 divergences),
  but it is an invariant about upstream tokenization, not a structural
  guarantee. If a future MACULA or MorphGNT release changed a single
  verse's tokenization (e.g. split one crasis form differently), every
  word after that point in that verse would silently bind to the wrong
  neighbour with NO error (the counts could even still match). Option A
  has the same exposure ONLY at the alias-derivation step, but Option B
  bakes the positional assumption into the join itself with no
  xml:id anchor to fall back on.
- If the owner chose to also re-key macula_greek Word.id to the
  composite (full normalization), that breaks the docstring contract
  that Word.id is `<edition>:<xml:id>` and the
  macula_hebrew/macula_greek GreekLemma keyspace discussion, and would
  need a Decision 2 / Decision 15 schema amendment.
- The 12 Pericope verses are unlinkable for the same upstream reason as
  Option A.

---

## Summary of the pivotal fact

The positional alignment IS determinable from the bytes and it is
clean: across all 7,927 verses shared by MorphGNT-SBLGNT and
MACULA-Greek-SBLGNT, the (osisRef, in-verse position) tuple is 1:1 with
zero word-count mismatches and zero positional surface-token
divergences. The single non-aligning class is the 12 MACULA-only
Pericope Adulterae verses (John 7:53 to 8:11), which carry no MorphGNT
source word and so cannot produce or mis-produce a PARSE_OF edge. Both
Option A (loss-free derived alias on macula_greek, match on it) and
Option B (shared computed composite on both sides) are technically
viable under this corpus. The canonical-key selection is a Decision 2 /
Decision 15 data-model call and is left to the owner; this document does
not pre-decide it.
