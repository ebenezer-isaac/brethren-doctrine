# Phase D Edge Performance Fix Manifest

Auditor caste, READ-ONLY definitive enumeration. Branch main, HEAD 02ebae8.
Doctrinal frame brethren-on-trial. No em or en dashes anywhere.

## Purpose

The Phase D lexical reseed stalls because several adapters write relationship
edges with UNLABELED endpoint MATCH, for example:

    MATCH (a {id: row.from_id}), (b {id: row.to_id}) MERGE (a)-[r:...]->(b)

With no node label Neo4j cannot use the per label `id` (or `osisID`,
`entity_id`, `siglum`, ...) uniqueness constraint index, so each endpoint
lookup becomes an AllNodesScan over the whole multi hundred thousand node
graph. The per batch cost is quadratic and the reseed never finishes.

`ingest/lexical/_common.py upsert_records` and `_REL_LABELS` are DEAD CODE
(zero callers, confirmed: the only references to `_common` import
`Settings`, `get_lexical_driver`; no adapter calls `upsert_records`). The
fix is therefore NOT in `_common.py`. Each `ingest/lexical/<X>.py` writes
its own raw Cypher and each NEEDS-FIX adapter must be fixed in place.

Every prescribed change is PERFORMANCE ONLY: it adds a node label token on
each endpoint MATCH (and, where the current key is functionally wrong, the
correct key, called out explicitly). It does NOT change which edges are
created, their direction, their properties, their count, or their stable
ids. The exception classes (heterogeneous, key correction, escalation) are
called out per adapter.

## Backing constraints/indexes present in graph/lexical.cypher

Confirmed from `graph/lexical.cypher` (read in full):

| (label, key)                         | constraint / index name        | line |
|--------------------------------------|---------------------------------|------|
| Lemma.id                             | lemma_id (UNIQUE)               | 12   |
| Lemma.strong                         | lemma_strong (UNIQUE)           | 13   |
| GreekLemma.id                        | greek_lemma_id (UNIQUE)         | 14   |
| Word.id                              | word_id (UNIQUE)                | 15   |
| Morpheme.id                          | morpheme_id (UNIQUE)            | 16   |
| Verse.id                             | verse_id (UNIQUE)               | 17   |
| Verse.osisID                         | verse_osisID (UNIQUE)           | 18   |
| Clause.id                            | clause_id (UNIQUE)              | 19   |
| Phrase.id                            | phrase_id (UNIQUE)              | 20   |
| BhsaClause.id                        | bhsa_clause_id (UNIQUE)         | 21   |
| BhsaPhrase.id                        | bhsa_phrase_id (UNIQUE)         | 22   |
| BhsaWord.id                          | bhsa_word_id (UNIQUE)           | 23   |
| Person.entity_id                     | person_id (UNIQUE)              | 24   |
| Place.entity_id                      | place_id (UNIQUE)               | 25   |
| Event.entity_id                      | event_id (UNIQUE)               | 26   |
| Period.entity_id                     | period_id (UNIQUE)              | 27   |
| Group.entity_id                      | group_id (UNIQUE)               | 28   |
| Tribe.entity_id                      | tribe_id (UNIQUE)               | 29   |
| Witness.ga_number                    | witness_ga (UNIQUE)             | 30   |
| Witness.siglum                       | witness_siglum (UNIQUE)         | 31   |
| VariantUnit.variant_unit_id          | variant_unit_id (UNIQUE)        | 32   |
| Reading.reading_id                   | reading_id (UNIQUE)             | 33   |
| Source.slug                          | source_slug (UNIQUE)            | 35   |
| Strong.id                            | strong_id (UNIQUE)              | 36   |
| CrossRef.id                          | crossref_id (UNIQUE)            | 37   |
| BriefLexEntry.strong_disambig        | brief_lex_entry_id (UNIQUE)     | 38   |
| LsjEntry.id                          | lsj_entry_id (UNIQUE)           | 39   |
| MorphCode.code                       | morph_code_unique (UNIQUE)      | 40   |
| ProperNoun.proper_name_entry         | proper_noun_entry (UNIQUE)      | 41   |
| TaggedToken.id                       | tagged_token_id (UNIQUE)        | 42   |
| LouwNidaDomain.id                    | louw_nida_id (UNIQUE)           | 43   |
| SyriacWord.id                        | syriac_word_id (UNIQUE)         | 44   |
| VulgateVerse.osis                    | vulgate_verse_osis (UNIQUE)     | 45   |
| CopticWord.id                        | coptic_word_id (UNIQUE)         | 46   |
| VersificationRule.id                 | versification_rule_id (UNIQUE)  | 47   |

NOT present (no constraint and no index): **GreekLemma.strong**. This is the
single missing index that blocks one NEEDS-FIX prescription (tflsj) and is
the data-correctness pivot for one MUST-ESCALATE (tagnt). See FIX WAVE PLAN.

## Node id namespace facts (source of truth = node producing adapter)

- oshb: Word.id = `oshb:<osisRef>.w<pos>`; Morpheme.id =
  `oshb-morph:<osisRef>.w<pos>.m<mm>`; Verse.id = `verse:<osisRef>`,
  Verse.osisID = `<osisRef>` (bare); Strong.id = bare Strong (`H1234`);
  Reading.reading_id = `oshb-reading:<osisRef>.w<pos>.qere`.
- morphgnt: Word.id = `morphgnt-sblgnt:...`; Verse.id = `verse:<osisRef>`.
  Does NOT create GreekLemma.
- macula_greek: GreekLemma.id = `<source>:strong-<NNNNN>` (e.g.
  `MACULA-Greek-Nestle1904:strong-00040`), 5 digit zero padded. It is the
  ONLY GreekLemma producer for the macula/morphgnt path.
- macula_hebrew: Lemma.id = `macula-hebrew-lemma:<strong>`.
- stepbible_ttesv: creates its OWN Lemma.id = bare H Strong and
  GreekLemma.id = bare G Strong (self consistent, see ttesv section).
- stepbible_tbesh: creates its OWN Lemma node keyed by `strong` (bare).

---

# Per adapter analysis (all 23)

## 1. oshb  -> NEEDS-FIX

Edge templates `ingest/lexical/oshb.py` lines 365 to 389. Row builders
lines 540 to 616. Node producers in same adapter (Word, Morpheme, Verse,
Strong, Reading). Group order: oshb is DATASETS[0], all endpoints produced
in this same run before the edge flush at lines 750 to 768; no new ordering
assumption introduced.

| rel_type | line | from MATCH (before -> after) | to MATCH (before -> after) | backing constraint | het? |
|---|---|---|---|---|---|
| HAS_MORPHEME | 367/368 | `(a {id: row.from_id})` -> `(a:Word {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Morpheme {id: row.to_id})` | word_id, morpheme_id | no |
| IN_VERSE | 372/373 | `(a {id: row.from_id})` -> `(a:Word {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Verse {id: row.to_id})` | word_id, verse_id | no |
| INSTANCE_OF | 377/378 | `(a {id: row.from_id})` -> SEE NOTE (Word OR Morpheme) | `(b {id: row.to_id})` -> `(b:Strong {id: row.to_id})` | strong_id (to side); word_id / morpheme_id (from side) | YES |
| IS_QERE_OF | 382/383 | `(a {reading_id: row.from_id})` -> `(a:Reading {reading_id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Word {id: row.to_id})` | reading_id, word_id | no |
| FROM_EDITION | 387/388 | `(a {id: row.from_id})` -> `(a:Word {id: row.from_id})` | `(b {slug: row.to_slug})` -> `(b:Source {slug: row.to_slug})` | word_id, source_slug | no |

HETEROGENEOUS NOTE (oshb INSTANCE_OF): `rows.edges_instance_of` is fed from
TWO call sites: line 554 to 555 `{from_id: word_id (oshb: prefix)}` ->
Strong, and line 590 to 591 `{from_id: morpheme_id (oshb-morph: prefix)}`
-> Strong. The to side is ALWAYS Strong. The from side is Word for
`oshb:`-prefixed ids and Morpheme for `oshb-morph:`-prefixed ids. A single
labeled MATCH on the from side would silently drop one subset.

Prescription for oshb INSTANCE_OF (edge preserving, two MATCH branches via
UNION over a single batch; key unchanged, only label added). Implementer
must replace the single template with a branched write keyed on the id
prefix, OR add a per row `from_label` discriminator at build time. The
correctness-safe Cypher only form (no row change) is:

    UNWIND $rows AS row
    CALL {
      WITH row
      MATCH (a:Word {id: row.from_id})
      MATCH (b:Strong {id: row.to_id})
      MERGE (a)-[r:`INSTANCE_OF`]->(b)
      RETURN count(r) AS c1
    }
    ...

This still scans because OR / disjunction over labels is not index backed.
The clean index backed fix is to partition `edges_instance_of` into a
Word sourced list and a Morpheme sourced list at build time (the call
sites already know which) and run two single label templates:

    -- Word branch
    UNWIND $rows AS row
    MATCH (a:Word {id: row.from_id}) MATCH (b:Strong {id: row.to_id})
    MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges
    -- Morpheme branch
    UNWIND $rows AS row
    MATCH (a:Morpheme {id: row.from_id}) MATCH (b:Strong {id: row.to_id})
    MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges

This requires a small row-builder split (the two append sites at lines 554
and 590 push into two distinct lists). Edge count, direction, properties,
ids are unchanged. NOT a MUST-ESCALATE (labels are unambiguous from the
call site); it is a NEEDS-FIX with a branched prescription.

## 2. macula_hebrew  -> CLEAN

`ingest/lexical/macula_hebrew.py` lines 407 to 431. All three edge
templates already label both endpoints:
- HAS_MACULA_ENRICHMENT 407 to 414: `(w:Word {source:'OSHB-morphology', ref: row.osis_ref})` -> `(m:MaculaToken {id: row.to_id})`. Word backed by word_ref index (line 49) on `ref`; MaculaToken has no listed constraint but this is the existing intended idiom and is label scoped (not an AllNodesScan). Endpoint labels present.
- INSTANCE_OF 415 to 421: `(m:MaculaToken {id: row.from_id})` -> `(l:Lemma {id: row.to_id})`. Lemma.id backed (lemma_id).
- BRIDGES_LXX 422 to 431: `(h:Lemma {id: row.from_id})` -> `(g:GreekLemma {id: row.to_id})`. Both backed.

All edge endpoints labeled. CLEAN.

## 3. macula_greek  -> CLEAN

`ingest/lexical/macula_greek.py` lines 416 to 441.
- INSTANCE_OF 416 to 422: `(w:Word {id: row.from_id})` -> `(l:GreekLemma {id: row.to_id})`. word_id, greek_lemma_id.
- IN_DOMAIN 424 to 433: `(w:Word {id: row.from_id})` -> `(d:LouwNidaDomain {id: row.to_id})`. word_id, louw_nida_id.
- FROM_EDITION 435 to 441: `(w:Word {id: row.from_id})` -> `(s:Source {slug: row.to_slug})`. word_id, source_slug.

All labeled+indexed. CLEAN.

## 4. morphgnt  -> CLEAN

`ingest/lexical/morphgnt.py` lines 263 to 272.
- IN_VERSE 263 to 267: `(a:Word{id: row.from_id})` -> `(b:Verse{id: row.to_id})`. word_id, verse_id.
- PARSE_OF 268 to 272: `(a:Word{id: row.from_id})` -> `(b:Word{id: row.to_id, source: row.target_source})`. word_id.

Both labeled+indexed. CLEAN.

## 5. bhsa  -> NEEDS-FIX

`ingest/lexical/bhsa.py` lines 404 to 415. Node producers same adapter
(BhsaClause, BhsaPhrase, BhsaWord, TFNode, Source). bhsa is DATASETS[2],
endpoints created in same run before edge flush; no new ordering
assumption. The to side of IN_VERSE is Verse, produced by oshb/morphgnt
which run earlier (DATASETS[0], [5]); group order already guarantees this.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| CONTAINS_PHRASE | 405/406 | `(a {id: row.from_id})` -> `(a:BhsaClause {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:BhsaPhrase {id: row.to_id})` | bhsa_clause_id, bhsa_phrase_id | no |
| CONTAINS_WORD | 409/410 | `(a {id: row.from_id})` -> `(a:BhsaPhrase {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:BhsaWord {id: row.to_id})` | bhsa_phrase_id, bhsa_word_id | no |
| IN_VERSE | 413/414 | `(a {id: row.from_id})` -> `(a:BhsaWord {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Verse {id: row.to_id})` | bhsa_word_id, verse_id | no |

From/to labels are fixed by the three layer containment shape (Decision 3,
docstring lines 245 to 251): BhsaClause CONTAINS_PHRASE BhsaPhrase
CONTAINS_WORD BhsaWord IN_VERSE Verse. Homogeneous, all backed. NEEDS-FIX
(label only, key unchanged).

## 6. etcbc_phono  -> CLEAN

`ingest/lexical/etcbc_phono.py`. Writes NO relationships. Only node MERGE
`_MERGE_SOURCE` (`Source {slug}`) and a property attach pass
`_ATTACH_PHONO` line 304 to 307: `MATCH (w:BhsaWord {id: row.id}) SET
w.phono = ...`. The SET pass MATCH is already label scoped (`:BhsaWord`,
key `id`, backed by bhsa_word_id). No unlabeled MATCH anywhere. CLEAN.

## 7. etcbc_parallels  -> CLEAN

`ingest/lexical/etcbc_parallels.py` line 335 to 343. PARALLEL_OF:
`(a:BhsaWord {id: row.source_id})` -> `(b:BhsaWord {id: row.target_id})`.
Both labeled, bhsa_word_id backed. CLEAN.

## 8. stepbible_tahot  -> NEEDS-FIX (one rel also needs a KEY correction)

`ingest/lexical/stepbible_tahot.py` lines 305 to 314. Row builder
`_merge_batch` lines 466 to 475. Node producer for TaggedToken is this
adapter; Lemma produced by oshb / macula_hebrew (`macula-hebrew-lemma:`
namespace); Verse produced by oshb/morphgnt. tahot is DATASETS[8], all
producers run earlier; group order satisfied.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| INSTANCE_OF | 307/308 | `(a {id: row.from_id})` -> `(a:TaggedToken {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Lemma {id: row.to_id})` | tagged_token_id, lemma_id | no |
| IN_VERSE | 312/313 | `(a {id: row.from_id})` -> `(a:TaggedToken {id: row.from_id})` | `(b {id: row.to_id})` -> `(b:Verse {osisID: row.to_id})` KEY CHANGE | tagged_token_id, verse_osisID | no |

INSTANCE_OF to_id at line 469 = `macula-hebrew-lemma:<strong>` which IS the
Lemma.id namespace produced by macula_hebrew, so label `:Lemma`, key `id`,
backed by lemma_id. Homogeneous (always TaggedToken -> Lemma).

IN_VERSE KEY-CORRECTION (flagged, not silent): line 472 builds
`{to_id: t["osis"]}` where `t["osis"]` is the BARE OSIS ref (e.g.
`Gen.1.1`, `_parse_ref` group `osis`). The current cypher matches
`(b {id: row.to_id})`. Verse.id is `verse:<osisRef>` (oshb/morphgnt), so
the current key would not match even with a label added; the correct
endpoint is `(b:Verse {osisID: row.to_id})`. This mirrors the sibling
adapter stepbible_tagnt which already uses `{osisID: row.to_id}`. The fix
MUST add `:Verse` AND change the key from `id` to `osisID`. This is the
only place the key changes and it is a correctness fix surfaced by the
audit, not a behavioral change to which edges are intended (the intended
target is the verse, the current bare key was a latent defect masked by
the perf stall). Backed by verse_osisID.

## 9. stepbible_tagnt  -> NEEDS-FIX (INSTANCE_OF target is MUST-ESCALATE)

`ingest/lexical/stepbible_tagnt.py` lines 245 to 254. Row builders
`_merge_instance_edges` 382 to 392, `_merge_in_verse_edges` 395 onward.
tagnt is DATASETS[9]; producers run earlier.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| INSTANCE_OF | 247/248 | `(a {id: row.from_id})` -> `(a:TaggedToken {id: row.from_id})` | `(b {id: row.to_id})` -> SEE ESCALATION | tagged_token_id (from); to side ambiguous | escalate |
| IN_VERSE | 252/253 | `(a {id: row.from_id})` -> `(a:TaggedToken {id: row.from_id})` | `(b {osisID: row.to_id})` -> `(b:Verse {osisID: row.to_id})` | tagged_token_id, verse_osisID | no |

IN_VERSE: from TaggedToken, to Verse keyed by osisID (already the right
key). Pure label add on both sides. Backed. Safe.

INSTANCE_OF MUST-ESCALATE: line 384 builds `{to_id: t["strong_id"]}` where
`strong_id = _strong_from_grammar(...)` = the bare Greek Strong before the
first `=` (e.g. `G0040`). The docstring (lines 36 to 39) asserts the join
key is `GreekLemma.id`. But the ONLY GreekLemma producer on this path is
macula_greek, whose GreekLemma.id is `MACULA-Greek-Nestle1904:strong-00040`
(zero padded, namespaced), NOT bare `G0040`. morphgnt does not produce
GreekLemma. Therefore matching `(:GreekLemma {id: row.to_id})` with
to_id = `G0040` would match ZERO nodes and silently drop EVERY tagnt
INSTANCE_OF edge. Matching on `GreekLemma.strong` has NO backing
constraint/index (the only missing one in lexical.cypher) so it would
stay slow even if semantically intended. The from-side label is
unambiguous (`:TaggedToken`, key id). The to-side endpoint label is
`:GreekLemma` but the JOIN KEY/VALUE is genuinely ambiguous (docstring
says `id`, value provided cannot match macula_greek `id`; `strong` is
unindexed and may itself be int vs string typed). DO NOT GUESS. Escalate.

## 10. stepbible_tvtms  -> CLEAN

`ingest/lexical/stepbible_tvtms.py`. Emits only `Source {slug}` and
`VersificationRule {id}` nodes (lines 327 to 334). NO relationship edges
anywhere. CLEAN.

## 11. stepbible_tbesh  -> NEEDS-FIX

`ingest/lexical/stepbible_tbesh.py` lines 302 to 319. tbesh creates its
own Lemma node keyed by `strong` (line 302 to 305 `_MERGE_LEMMA`
`MERGE (n:Lemma {strong: row.base_strong})`); BriefLexEntry assumed from
tbesg (DATASETS[12] runs after tbesh DATASETS[11] -- see ordering note).

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| LEX_FOR | 308/310 | `(b {strong_disambig: row.strong_disambig})` -> `(b:BriefLexEntry {strong_disambig: row.strong_disambig})` | `(l {strong: row.base_strong})` -> `(l:Lemma {strong: row.base_strong})` | brief_lex_entry_id, lemma_strong | no |
| FROM_EDITION | 315/317 | `(b {strong_disambig: row.strong_disambig})` -> `(b:BriefLexEntry {strong_disambig: row.strong_disambig})` | `(s {slug: row.slug})` -> `(s:Source {slug: row.slug})` | brief_lex_entry_id, source_slug | no |

Both endpoint labels unambiguous. Lemma keyed by `strong` is backed by
lemma_strong (line 13). BriefLexEntry keyed by strong_disambig backed by
brief_lex_entry_id (line 38). NEEDS-FIX, label only, keys unchanged.

ORDERING NOTE: tbesh is DATASETS[11], tbesg (the BriefLexEntry producer)
is DATASETS[12], i.e. tbesg runs AFTER tbesh. tbesh's LEX_FOR/FROM_EDITION
MATCH on `BriefLexEntry` already (in the unlabeled form, by
strong_disambig) presupposes BriefLexEntry exists. This dependency exists
in the CURRENT code identically; adding the `:BriefLexEntry` label does
NOT introduce a new ordering assumption (the unlabeled MATCH already
required the node to exist). The label fix is ordering neutral. Flag for
the implementer: this pre-existing ordering inversion is OUT OF SCOPE for
the perf fix (do not reorder), but note it so a follow up does not blame
the label fix for a pre-existing zero-match.

## 12. stepbible_tbesg  -> CLEAN

`ingest/lexical/stepbible_tbesg.py` lines 305 to 310. LEX_FOR:
`MATCH (b:BriefLexEntry) WHERE b.strong_disambig = row.strong_disambig`
(labeled, brief_lex_entry_id backs the equality) ->
`(g:GreekLemma {id: row.base_strong})` (labeled, greek_lemma_id). Both
endpoints labeled. CLEAN.

(Caveat for downstream, not a perf defect: whether tbesg `base_strong`
value matches macula_greek GreekLemma.id namespace is the SAME data
question as tagnt; but tbesg's MATCH is already label scoped so it is not
a perf stall and is out of scope for this perf manifest. Listed here for
completeness only.)

## 13. stepbible_tflsj  -> NEEDS-INDEX (endpoints labeled, one key unindexed)

`ingest/lexical/stepbible_tflsj.py` lines 318 to 327. LEX_FOR:
`(e:LsjEntry{id: row.id})` -> `(g:GreekLemma{strong: row.strong})`. BOTH
endpoints are ALREADY labeled. LsjEntry.id backed by lsj_entry_id. BUT the
to side keys on `GreekLemma.strong`, which has NO uniqueness constraint
and NO index in graph/lexical.cypher. So even though the label is present,
the `GreekLemma.strong` lookup is a per label property scan (LabelScan +
filter), not an index seek. For a 5k+ LsjEntry batch joined against the
full GreekLemma set this is still slow (though not a whole graph
AllNodesScan).

Classification: the LABEL part is already CLEAN; this is a NEEDS-INDEX
item, not a per adapter Cypher change. The fix is an additional index in
graph/lexical.cypher:

    CREATE INDEX greek_lemma_strong IF NOT EXISTS
      FOR (g:GreekLemma) ON (g.strong);

(graph/lexical.cypher is NOT this auditor's deliverable; this is recorded
as a required schema add for the implementer wave, see FIX WAVE PLAN.)
No change to tflsj.py Cypher is required for correctness or for the label;
only the missing index. Listed in the master table as NEEDS-INDEX.

## 14. stepbible_morph_codes  -> CLEAN

`ingest/lexical/stepbible_morph_codes.py` lines 220 to 226. Emits only
`Source {slug}` and `MorphCode {code}` nodes. Docstring line 17 and 47:
"no outbound edges are emitted from this adapter". NO relationships.
CLEAN.

## 15. stepbible_proper_nouns  -> NEEDS-FIX

`ingest/lexical/stepbible_proper_nouns.py` lines 339 to 354. NAMED_AT:

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| NAMED_AT | 350/351 | `MATCH (p) WHERE p.proper_name_entry = row.proper_name_entry` -> `MATCH (p:ProperNoun) WHERE p.proper_name_entry = row.proper_name_entry` (or `(p:ProperNoun {proper_name_entry: row.proper_name_entry})`) | `MATCH (v) WHERE v.osisID = row.osisID` -> `MATCH (v:Verse) WHERE v.osisID = row.osisID` (or `(v:Verse {osisID: row.osisID})`) | proper_noun_entry, verse_osisID | no |

from = ProperNoun (this adapter is the producer, line 339 to 342
`MERGE (n:ProperNoun {proper_name_entry: ...})`), key proper_name_entry
backed by proper_noun_entry. to = Verse, key osisID backed by
verse_osisID; Verse produced by oshb/morphgnt earlier (proper_nouns is
DATASETS[14]). The adapter also does a bare `_MERGE_VERSE`
`MERGE (n:Verse {osisID: row.osisID})` (line 344 to 347) which is a
labeled node MERGE and is fine. NEEDS-FIX, label only on the NAMED_AT
endpoints, keys unchanged.

## 16. stepbible_ttesv  -> NEEDS-FIX (branched INSTANCE_OF, branch already Python side)

`ingest/lexical/stepbible_ttesv.py` lines 349 to 366. Row builders
`_split_lemmas` 520 to 545, `_instance_of_payloads` 548 to 562. ttesv
creates its OWN Lemma (id = bare H Strong) and GreekLemma (id = bare G
Strong) nodes at lines 530 to 544, so the `id` join is self consistent.
ttesv is DATASETS[10].

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| FROM_EDITION | 351/352 | `(t {id: row.token_id})` -> `(t:TaggedToken {id: row.token_id})` | `(s {slug: row.source_slug})` -> `(s:Source {slug: row.source_slug})` | tagged_token_id, source_slug | no |
| INSTANCE_OF (Hebrew branch) | 357/358 | `(t {id: row.token_id})` -> `(t:TaggedToken {id: row.token_id})` | `(l {id: row.lemma_id})` -> `(l:Lemma {id: row.lemma_id})` | tagged_token_id, lemma_id | YES (Python branched) |
| INSTANCE_OF (Greek branch) | 363/364 | `(t {id: row.token_id})` -> `(t:TaggedToken {id: row.token_id})` | `(l {id: row.lemma_id})` -> `(l:GreekLemma {id: row.lemma_id})` | tagged_token_id, greek_lemma_id | YES (Python branched) |

DISCRIMINATOR (explicit): `canonical_strong.startswith("H")` -> Hebrew
branch (to label `:Lemma`); `canonical_strong.startswith("G")` -> Greek
branch (to label `:GreekLemma`). The partition is ALREADY done in Python:
`_instance_of_payloads` returns `hebrew_edges` and `greek_edges`, each fed
to its own template via `_merge_instance_of` (lines 608 to 614). So the
two MATCH branches map exactly one-to-one onto the two existing templates;
the fix is a pure label add on the already correct branch (NO ambiguity,
NO row change needed, NO MUST-ESCALATE). Hebrew template gets `:Lemma`,
Greek template gets `:GreekLemma`, both keyed `id` (the ttesv self created
Lemma/GreekLemma both keyed by `id` = bare Strong, backed by lemma_id /
greek_lemma_id). NEEDS-FIX, branched but fully prescribable.

## 17. openbible  -> CLEAN

`ingest/lexical/openbible.py` lines 305 to 312. OPENBIBLE_CROSS_REF:
`(a:Verse {osisID: row.from_osis})` -> `(b:Verse {osisID: row.to_osis})`.
Both labeled, verse_osisID backed. CLEAN.

## 18. tsk  -> NEEDS-FIX (from side only)

`ingest/lexical/tsk.py` lines 619 to 630. tsk creates CrossRef nodes in
the same run (line 619 to 622 `MERGE (n:CrossRef {id: row.id})`). tsk is
DATASETS[21]; Verse produced by oshb/morphgnt much earlier.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| CROSS_REF | 625 | `(a {id: row.from_id})` -> `(a:CrossRef {id: row.from_id})` | `(b:Verse {osisID: row.osis_target})` (already labeled) | crossref_id, verse_osisID | no |

from_id at line 605 = `node_id` = `tsk:<book>.<ch>.<v>...` which is the
CrossRef.id namespace (line 564 to 585). to side already labeled+indexed.
Only the from side needs `:CrossRef`. NEEDS-FIX, label only on from,
key unchanged.

## 19. theographic  -> NEEDS-FIX (HETEROGENEOUS from side, requires row builder change)

`ingest/lexical/theographic.py` lines 497 to 510. Row builders:
`_mention_edges` 677 to 682, period edges 672 to 673, `from_edition`
737 to 741. theographic is DATASETS[22] (last); Verse and Source produced
earlier; entity nodes produced in this same run before the edge flush
(lines 750 to 753). Group order satisfied.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| MENTIONS | 503 | `(a {entity_id: row.from_id})` -> SEE NOTE (one of 6 labels) | `(b:Verse {osisID: row.to_id})` (already labeled) | person/place/event/period/group/tribe _id; verse_osisID | YES |
| FROM_EDITION | 508 | `(a {entity_id: row.from_id})` -> SEE NOTE (one of 6 labels) | `(b:Source {slug: row.slug})` (already labeled) | as above; source_slug | YES |

HETEROGENEOUS NOTE: the from node is one of SIX labels: Person, Place,
Period, Event, Group, Tribe (docstring lines 89 to 90; `by_label` dict
lines 719 to 731). All six are keyed by `entity_id`, each with its OWN
uniqueness constraint (person_id, place_id, event_id, period_id, group_id,
tribe_id). The edge rows (`mention_edges`, `from_edition`) are FLATTENED
across all six labels with NO per-row label tag (lines 733 to 741 carry
only `from_id` / `to_id` / `slug`). The to side (Verse, Source) is already
labeled.

A single labeled MATCH cannot cover all rows (would drop 5 of 6 label
subsets). A label disjunction `MATCH (a) WHERE (a:Person OR a:Place OR
...) AND a.entity_id = row.from_id` is correctness safe but NOT index
backed (Neo4j does not use the per label index under an OR of labels), so
it does not solve the perf stall. The only index backed, edge preserving
fix is to TAG each edge row with its source label at build time and run
SIX single label templates (or one parameterized-label template invoked
six times):

    -- per label L in {Person,Place,Period,Event,Group,Tribe}
    UNWIND $rows AS row
    MATCH (a:`<L>` {entity_id: row.from_id})
    MATCH (b:Verse {osisID: row.to_id})
    MERGE (a)-[r:`MENTIONS`]->(b) RETURN count(r) AS edges
    -- analogous for FROM_EDITION to (b:Source {slug: row.slug})

The label is available at build time: `_mention_edges` is called per
label inside the `for label in (...)` loop (lines 734 to 735) and period
edges are all `Period`; `from_edition` iterates `by_label.items()`
(lines 737 to 741) so the label is in scope there too. Implementer must
add a `label` field to each edge row and dispatch per label. This is an
edge preserving change (same from_id, to_id, slug, rel_type, direction,
count) and the labels are UNAMBIGUOUS from the build site (NOT a
MUST-ESCALATE). NEEDS-FIX, branched, requires a row builder change (not a
pure in place Cypher swap).

## 20. peshitta  -> NEEDS-FIX

`ingest/lexical/peshitta.py` lines 221 to 229. peshitta creates
SyriacWord in same run (lines 221 to 224). peshitta is DATASETS[16];
Verse produced by oshb/morphgnt earlier.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| IN_VERSE | 227 | `(a {id: row.from_id})` -> `(a:SyriacWord {id: row.from_id})` | `(b {osisID: row.to_id})` -> `(b:Verse {osisID: row.to_id})` | syriac_word_id, verse_osisID | no |

to_id is the projected OSIS ref joining `Verse.osisID` (docstring line
101). Key already correct (`osisID`), only labels missing on both sides.
NEEDS-FIX, label only, keys unchanged.

## 21. vulgate_clementine  -> CLEAN

`ingest/lexical/vulgate_clementine.py` lines 303 to 309. Emits only
`Source {slug}` and `VulgateVerse {osis}` nodes. NO relationship edges.
CLEAN.

## 22. coptic_scriptorium  -> NEEDS-FIX

`ingest/lexical/coptic_scriptorium.py` lines 374 to 386. coptic creates
CopticWord in same run (lines 378 to 381). coptic is DATASETS[17]; Verse
produced earlier.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| IN_VERSE | 384 | `(a {id: row.from_id})` -> `(a:CopticWord {id: row.from_id})` | `(b {osisID: row.to_id})` -> `(b:Verse {osisID: row.to_id})` | coptic_word_id, verse_osisID | no |

to side keys `Verse.osisID` (docstring line 147). Key already correct,
only labels missing on both sides. NEEDS-FIX, label only.

## 23. open_cbgm_3_john  -> NEEDS-FIX

`ingest/lexical/open_cbgm_3_john.py` lines 505 to 525. Node producers
same adapter (Witness, Reading, VariantUnit); open_cbgm is DATASETS[19],
all three endpoint labels produced in this run before the edge flush.

| rel_type | line | from (before -> after) | to (before -> after) | backing | het? |
|---|---|---|---|---|---|
| READS_AT | 507/508 | `(w {siglum: row.siglum})` -> `(w:Witness {siglum: row.siglum})` | `(rd {reading_id: row.reading_id})` -> `(rd:Reading {reading_id: row.reading_id})` | witness_siglum, reading_id | no |
| ATTESTED_BY | 514/515 | `(rd {reading_id: row.reading_id})` -> `(rd:Reading {reading_id: row.reading_id})` | `(v {variant_unit_id: row.variant_unit_id})` -> `(v:VariantUnit {variant_unit_id: row.variant_unit_id})` | reading_id, variant_unit_id | no |
| CORRECTOR_OF | 521/522 | `(c {siglum: row.corrector_siglum})` -> `(c:Witness {siglum: row.corrector_siglum})` | `(b {siglum: row.base_siglum})` -> `(b:Witness {siglum: row.base_siglum})` | witness_siglum (both) | no |

All endpoint labels unambiguous (docstring lines 50, 76 to 147), all keys
already correct and constraint backed. NEEDS-FIX, label only, keys
unchanged.

---

# Master table

| adapter | rel_type | file:line | from before->after | to before->after | backing in lexical.cypher? | heterogeneous/branched? | class |
|---|---|---|---|---|---|---|---|
| oshb | HAS_MORPHEME | oshb.py:367/368 | {id} -> Word{id} | {id} -> Morpheme{id} | yes (word_id, morpheme_id) | no | NEEDS-FIX |
| oshb | IN_VERSE | oshb.py:372/373 | {id} -> Word{id} | {id} -> Verse{id} | yes (word_id, verse_id) | no | NEEDS-FIX |
| oshb | INSTANCE_OF | oshb.py:377/378 | {id} -> Word{id} OR Morpheme{id} | {id} -> Strong{id} | yes (word_id/morpheme_id, strong_id) | YES branched (id prefix) | NEEDS-FIX |
| oshb | IS_QERE_OF | oshb.py:382/383 | {reading_id} -> Reading{reading_id} | {id} -> Word{id} | yes (reading_id, word_id) | no | NEEDS-FIX |
| oshb | FROM_EDITION | oshb.py:387/388 | {id} -> Word{id} | {slug} -> Source{slug} | yes (word_id, source_slug) | no | NEEDS-FIX |
| macula_hebrew | HAS_MACULA_ENRICHMENT | macula_hebrew.py:407 | Word (labeled) | MaculaToken (labeled) | n/a (already labeled) | no | CLEAN |
| macula_hebrew | INSTANCE_OF | macula_hebrew.py:415 | MaculaToken (labeled) | Lemma{id} (labeled) | yes (lemma_id) | no | CLEAN |
| macula_hebrew | BRIDGES_LXX | macula_hebrew.py:422 | Lemma{id} (labeled) | GreekLemma{id} (labeled) | yes | no | CLEAN |
| macula_greek | INSTANCE_OF | macula_greek.py:416 | Word{id} (labeled) | GreekLemma{id} (labeled) | yes | no | CLEAN |
| macula_greek | IN_DOMAIN | macula_greek.py:424 | Word{id} (labeled) | LouwNidaDomain{id} (labeled) | yes | no | CLEAN |
| macula_greek | FROM_EDITION | macula_greek.py:435 | Word{id} (labeled) | Source{slug} (labeled) | yes | no | CLEAN |
| morphgnt | IN_VERSE | morphgnt.py:263 | Word{id} (labeled) | Verse{id} (labeled) | yes | no | CLEAN |
| morphgnt | PARSE_OF | morphgnt.py:268 | Word{id} (labeled) | Word{id} (labeled) | yes | no | CLEAN |
| bhsa | CONTAINS_PHRASE | bhsa.py:405/406 | {id} -> BhsaClause{id} | {id} -> BhsaPhrase{id} | yes | no | NEEDS-FIX |
| bhsa | CONTAINS_WORD | bhsa.py:409/410 | {id} -> BhsaPhrase{id} | {id} -> BhsaWord{id} | yes | no | NEEDS-FIX |
| bhsa | IN_VERSE | bhsa.py:413/414 | {id} -> BhsaWord{id} | {id} -> Verse{id} | yes | no | NEEDS-FIX |
| etcbc_phono | (none) | n/a | n/a | n/a | n/a | no | CLEAN |
| etcbc_parallels | PARALLEL_OF | etcbc_parallels.py:335 | BhsaWord{id} (labeled) | BhsaWord{id} (labeled) | yes | no | CLEAN |
| stepbible_tahot | INSTANCE_OF | stepbible_tahot.py:307/308 | {id} -> TaggedToken{id} | {id} -> Lemma{id} | yes | no | NEEDS-FIX |
| stepbible_tahot | IN_VERSE | stepbible_tahot.py:312/313 | {id} -> TaggedToken{id} | {id} -> Verse{osisID} KEY CHANGE | yes (verse_osisID) | no | NEEDS-FIX |
| stepbible_tagnt | INSTANCE_OF | stepbible_tagnt.py:247/248 | {id} -> TaggedToken{id} | {id} -> GreekLemma{??} | from: yes; to: AMBIGUOUS | MUST-ESCALATE | NEEDS-FIX/ESCALATE |
| stepbible_tagnt | IN_VERSE | stepbible_tagnt.py:252/253 | {id} -> TaggedToken{id} | {osisID} -> Verse{osisID} | yes | no | NEEDS-FIX |
| stepbible_tvtms | (none) | n/a | n/a | n/a | n/a | no | CLEAN |
| stepbible_tbesh | LEX_FOR | stepbible_tbesh.py:308/310 | {strong_disambig} -> BriefLexEntry{strong_disambig} | {strong} -> Lemma{strong} | yes (brief_lex_entry_id, lemma_strong) | no | NEEDS-FIX |
| stepbible_tbesh | FROM_EDITION | stepbible_tbesh.py:315/317 | {strong_disambig} -> BriefLexEntry{strong_disambig} | {slug} -> Source{slug} | yes | no | NEEDS-FIX |
| stepbible_tbesg | LEX_FOR | stepbible_tbesg.py:305 | BriefLexEntry (labeled) | GreekLemma{id} (labeled) | yes | no | CLEAN |
| stepbible_tflsj | LEX_FOR | stepbible_tflsj.py:322 | LsjEntry{id} (labeled) | GreekLemma{strong} (labeled, key UNINDEXED) | NO index on GreekLemma.strong | no | NEEDS-INDEX |
| stepbible_morph_codes | (none) | n/a | n/a | n/a | n/a | no | CLEAN |
| stepbible_proper_nouns | NAMED_AT | stepbible_proper_nouns.py:350/351 | (unlabeled) -> ProperNoun{proper_name_entry} | (unlabeled) -> Verse{osisID} | yes (proper_noun_entry, verse_osisID) | no | NEEDS-FIX |
| stepbible_ttesv | FROM_EDITION | stepbible_ttesv.py:351/352 | {id} -> TaggedToken{id} | {slug} -> Source{slug} | yes | no | NEEDS-FIX |
| stepbible_ttesv | INSTANCE_OF (Heb) | stepbible_ttesv.py:357/358 | {id} -> TaggedToken{id} | {id} -> Lemma{id} | yes (lemma_id) | YES (Python branched, H prefix) | NEEDS-FIX |
| stepbible_ttesv | INSTANCE_OF (Grk) | stepbible_ttesv.py:363/364 | {id} -> TaggedToken{id} | {id} -> GreekLemma{id} | yes (greek_lemma_id) | YES (Python branched, G prefix) | NEEDS-FIX |
| openbible | OPENBIBLE_CROSS_REF | openbible.py:305 | Verse{osisID} (labeled) | Verse{osisID} (labeled) | yes | no | CLEAN |
| tsk | CROSS_REF | tsk.py:625 | {id} -> CrossRef{id} | Verse{osisID} (already labeled) | yes (crossref_id, verse_osisID) | no | NEEDS-FIX |
| theographic | MENTIONS | theographic.py:503 | {entity_id} -> one of 6 entity labels | Verse{osisID} (already labeled) | yes (6 *_id constraints) | YES branched, needs row label tag | NEEDS-FIX |
| theographic | FROM_EDITION | theographic.py:508 | {entity_id} -> one of 6 entity labels | Source{slug} (already labeled) | yes | YES branched, needs row label tag | NEEDS-FIX |
| peshitta | IN_VERSE | peshitta.py:227 | {id} -> SyriacWord{id} | {osisID} -> Verse{osisID} | yes (syriac_word_id, verse_osisID) | no | NEEDS-FIX |
| vulgate_clementine | (none) | n/a | n/a | n/a | n/a | no | CLEAN |
| coptic_scriptorium | IN_VERSE | coptic_scriptorium.py:384 | {id} -> CopticWord{id} | {osisID} -> Verse{osisID} | yes (coptic_word_id, verse_osisID) | no | NEEDS-FIX |
| open_cbgm_3_john | READS_AT | open_cbgm_3_john.py:507/508 | {siglum} -> Witness{siglum} | {reading_id} -> Reading{reading_id} | yes | no | NEEDS-FIX |
| open_cbgm_3_john | ATTESTED_BY | open_cbgm_3_john.py:514/515 | {reading_id} -> Reading{reading_id} | {variant_unit_id} -> VariantUnit{variant_unit_id} | yes | no | NEEDS-FIX |
| open_cbgm_3_john | CORRECTOR_OF | open_cbgm_3_john.py:521/522 | {siglum} -> Witness{siglum} | {siglum} -> Witness{siglum} | yes | no | NEEDS-FIX |

---

# Adapter classification summary

CLEAN (10): macula_hebrew, macula_greek, morphgnt, etcbc_phono,
etcbc_parallels, stepbible_tvtms, stepbible_tbesg, stepbible_morph_codes,
openbible, vulgate_clementine.

NEEDS-FIX (12): oshb, bhsa, stepbible_tahot, stepbible_tagnt,
stepbible_tbesh, stepbible_proper_nouns, stepbible_ttesv, tsk,
theographic, peshitta, coptic_scriptorium, open_cbgm_3_john.

NEEDS-INDEX (1, label already clean, missing backing index): stepbible_tflsj.

Total adapters audited: 23 (10 + 12 + 1).

---

# FIX WAVE PLAN (single source of truth for the parallel implementer wave)

Each item below is one implementer task. Every prescription is performance
only (label/key scope), preserves edge identity/direction/properties/count,
and introduces NO new ordering assumption (the unlabeled MATCH already
required the endpoint to pre-exist; the DATASETS order in
ingest/lexical/run.py already guarantees producers run before consumers,
confirmed per adapter above).

### A. Pure label add, single template, keys unchanged (lowest risk)

1. **bhsa.py** lines 405/406, 409/410, 413/414:
   - 405/406: `(a:BhsaClause {id: row.from_id})`, `(b:BhsaPhrase {id: row.to_id})`
   - 409/410: `(a:BhsaPhrase {id: row.from_id})`, `(b:BhsaWord {id: row.to_id})`
   - 413/414: `(a:BhsaWord {id: row.from_id})`, `(b:Verse {id: row.to_id})`
2. **peshitta.py** line 227: `(a:SyriacWord {id: row.from_id})`, `(b:Verse {osisID: row.to_id})`.
3. **coptic_scriptorium.py** line 384: `(a:CopticWord {id: row.from_id})`, `(b:Verse {osisID: row.to_id})`.
4. **tsk.py** line 625: from `(a:CrossRef {id: row.from_id})`; to already `(b:Verse {osisID: row.osis_target})`.
5. **stepbible_proper_nouns.py** lines 350/351: `MATCH (p:ProperNoun) WHERE p.proper_name_entry = row.proper_name_entry`, `MATCH (v:Verse) WHERE v.osisID = row.osisID`.
6. **stepbible_tbesh.py** lines 308/310 and 315/317:
   - LEX_FOR: `(b:BriefLexEntry {strong_disambig: row.strong_disambig})`, `(l:Lemma {strong: row.base_strong})`
   - FROM_EDITION: `(b:BriefLexEntry {strong_disambig: row.strong_disambig})`, `(s:Source {slug: row.slug})`
   - (Pre-existing tbesh->tbesg ordering inversion noted; do NOT reorder under this perf fix.)
7. **open_cbgm_3_john.py** lines 507/508, 514/515, 521/522:
   - READS_AT: `(w:Witness {siglum: row.siglum})`, `(rd:Reading {reading_id: row.reading_id})`
   - ATTESTED_BY: `(rd:Reading {reading_id: row.reading_id})`, `(v:VariantUnit {variant_unit_id: row.variant_unit_id})`
   - CORRECTOR_OF: `(c:Witness {siglum: row.corrector_siglum})`, `(b:Witness {siglum: row.base_siglum})`
8. **oshb.py** lines 367/368, 372/373, 382/383, 387/388 (the four NON
   heterogeneous oshb rels):
   - HAS_MORPHEME: `(a:Word {id: row.from_id})`, `(b:Morpheme {id: row.to_id})`
   - IN_VERSE: `(a:Word {id: row.from_id})`, `(b:Verse {id: row.to_id})`
   - IS_QERE_OF: `(a:Reading {reading_id: row.from_id})`, `(b:Word {id: row.to_id})`
   - FROM_EDITION: `(a:Word {id: row.from_id})`, `(b:Source {slug: row.to_slug})`

### B. Label add + KEY correction (correctness fix surfaced by audit)

9. **stepbible_tahot.py** line 312/313 IN_VERSE: change
   `(b {id: row.to_id})` to `(b:Verse {osisID: row.to_id})` (label add AND
   key id -> osisID; the bare osis value never matched Verse.id). Also
   line 307/308 INSTANCE_OF: pure label add
   `(a:TaggedToken {id: row.from_id})`, `(b:Lemma {id: row.to_id})`.

### C. Branched / heterogeneous (label unambiguous, needs per branch write)

10. **oshb.py** lines 377/378 INSTANCE_OF: split
    `rows.edges_instance_of` into a Word sourced list (append site
    line 554/555) and a Morpheme sourced list (append site line 590/591),
    run two single label templates:
    `(a:Word {id})...(b:Strong {id})` and
    `(a:Morpheme {id})...(b:Strong {id})`. Edge count/ids unchanged.
11. **stepbible_ttesv.py** lines 357/358 and 363/364: the two existing
    templates `_MERGE_INSTANCE_OF_HEBREW_CYPHER` and
    `_MERGE_INSTANCE_OF_GREEK_CYPHER` are ALREADY fed Python partitioned
    hebrew_edges / greek_edges. Add labels: Hebrew template
    `(t:TaggedToken {id: row.token_id})`, `(l:Lemma {id: row.lemma_id})`;
    Greek template `(t:TaggedToken {id})`,
    `(l:GreekLemma {id: row.lemma_id})`. Also line 351/352 FROM_EDITION:
    `(t:TaggedToken {id})`, `(s:Source {slug: row.source_slug})`. No row
    builder change needed (partition already exists). NOT ambiguous.
12. **theographic.py** lines 503 and 508: heterogeneous from side over
    SIX labels (Person, Place, Period, Event, Group, Tribe), no per row
    label tag exists. Implementer MUST add a `label` field to each
    `mention_edges` / period edge / `from_edition` row at build time
    (the build sites at lines 672/673, 681, 734/735, 737/741 all know the
    label) and dispatch SIX single label templates per rel:
    `(a:`<Label>` {entity_id: row.from_id})`, to side already labeled
    (`(b:Verse {osisID})` / `(b:Source {slug})`). Edge identity unchanged.
    Labels are unambiguous from build site (NOT escalation).

### D. NEEDS-INDEX (schema add, no adapter Cypher change)

13. **graph/lexical.cypher** (NOT this auditor's deliverable; required
    schema add for the wave): add
    `CREATE INDEX greek_lemma_strong IF NOT EXISTS FOR (g:GreekLemma) ON (g.strong);`
    so **stepbible_tflsj.py** line 322 LEX_FOR
    `(g:GreekLemma{strong: row.strong})` becomes index backed. tflsj.py
    itself needs NO change (both endpoints already labeled).

### E. MUST-ESCALATE (do NOT guess; blocks one rel)

14. **stepbible_tagnt.py** line 247/248 INSTANCE_OF to side. From side is
    unambiguous (`(a:TaggedToken {id: row.from_id})`, apply that). The to
    side endpoint LABEL is `:GreekLemma`, but the JOIN KEY/VALUE is
    genuinely ambiguous and CANNOT be resolved by static analysis without
    a decision:
    - to_id value = bare Greek Strong (e.g. `G0040`).
    - macula_greek (the only GreekLemma producer on this path) sets
      GreekLemma.id = `MACULA-Greek-Nestle1904:strong-00040` (namespaced,
      zero padded). So `(:GreekLemma {id: row.to_id})` matches ZERO nodes
      and would silently drop EVERY tagnt INSTANCE_OF edge.
    - `(:GreekLemma {strong: row.to_id})` has NO backing index (would
      stay slow) AND GreekLemma.strong is written by macula_greek as an
      int (`int(strong)`, macula_greek line 523) while tagnt to_id is a
      string `G0040`; type/format mismatch on top of the missing index.
    The correct resolution (transform tagnt to_id into the macula_greek
    id namespace, OR add a GreekLemma.strong string-normalized index, OR
    re-key) is a data-model decision, not a mechanical perf relabel.
    ESCALATE before any implementer touches this rel. The tagnt IN_VERSE
    rel (line 252/253) is NOT escalated and can be fixed under task A
    style: `(a:TaggedToken {id: row.from_id})`, `(b:Verse {osisID: row.to_id})`.

### Ordering / dependency confirmation

DATASETS order in ingest/lexical/run.py lines 43 to 67 (verified):
oshb, macula_hebrew, bhsa, etcbc_phono, etcbc_parallels, morphgnt,
macula_greek, stepbible_morph_codes, stepbible_tahot, stepbible_tagnt,
stepbible_ttesv, stepbible_tbesh, stepbible_tbesg, stepbible_tflsj,
stepbible_proper_nouns, stepbible_tvtms, peshitta, coptic_scriptorium,
vulgate_clementine, open_cbgm_3_john, openbible, tsk, theographic.

For every NEEDS-FIX prescription the endpoint producer runs at or before
the consumer (Verse from oshb[0]/morphgnt[5]; Lemma from
oshb[0]/macula_hebrew[1]; GreekLemma from macula_greek[6]; BhsaWord/Phrase/
Clause from bhsa[2] same-run; CrossRef/CopticWord/SyriacWord/TaggedToken/
ProperNoun/Witness/Reading/VariantUnit/entity nodes produced in their own
adapter's same run before its edge flush). Adding a label to a MATCH does
NOT add a new ordering requirement: the unlabeled MATCH already required
the endpoint to exist. ONE pre-existing ordering inversion exists OUTSIDE
the scope of this perf fix (tbesh[11] LEX_FOR/FROM_EDITION presupposes
BriefLexEntry produced by tbesg[12], which runs after tbesh); the label
fix is ordering neutral and must NOT attempt to reorder. Flagged for a
separate follow up, not for the perf wave.
