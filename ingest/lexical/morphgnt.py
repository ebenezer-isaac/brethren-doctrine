"""MorphGNT-SBLGNT lexical adapter docstring contract (Phase C Wave 1).

Caste: implementer-docstring. This module body is intentionally a single
expression docstring. The implementer-impl caste replaces the body with
code in a follow-on commit. No imports, no defs, no classes, and no
import directives of any kind may appear here.

Source slug
===========

``MorphGNT-SBLGNT``. Inventory catalog source index 3. Tier A per
``tools/expected_counts.json``: expected_count is 137554 with tolerance
zero, record_unit is ``word``. Upstream input lives at
``data/private/morphgnt`` as per-book ``.txt`` files named with the
``<NN>-<book>-morphgnt.txt`` pattern; each line is space-delimited with
seven whitespace tokens (``bcv``, ``pos``, ``parsing_code``, ``text``,
``word``, ``normalized``, ``lemma``).

Decisions implemented
=====================

Decision 15 (Verse.text population policy). This adapter is the canonical
populator of ``Verse.text`` for New Testament verses. The OSHB adapter is
the canonical populator for Old Testament verses. No other adapter writes
``Verse.text`` at ingest time.

Word fields and per-field predicate types (Decision 15, MorphGNT-SBLGNT
table)
======================================================================

| Field         | Type   | Predicate         |
|---------------|--------|-------------------|
| bcv           | string | $pred_string(x)   |
| pos           | string | $pred_string(x)   |
| parsing_code  | string | $pred_string(x)   |
| text          | string | $pred_string(x)   |
| word          | string | $pred_string(x)   |
| normalized    | string | $pred_string(x)   |
| lemma         | string | $pred_string(x)   |

``bcv`` is the six digit book-chapter-verse identifier as shipped by
MorphGNT (BB CC VV concatenated, zero padded). The adapter resolves the
book number to its OSIS book abbreviation using the standard NT mapping
(01 = Matt through 27 = Rev) so the OSIS reference takes the form
``<Book>.<chapter>.<verse>`` with chapter and verse as decimal integers
without zero padding.

``pos`` is the MorphGNT coarse part of speech tag. ``parsing_code`` is
the seven-character MorphGNT parse string. ``text`` is the surface form
including punctuation and editorial brackets exactly as shipped by
upstream. ``word`` is the surface form with punctuation stripped.
``normalized`` is the form with accents and breathings reduced per the
MorphGNT normalisation rules. ``lemma`` is the dictionary headword.

Verse fields and per-field predicate types (Decision 15, Verse node
table)
===================================================================

| Field         | Type   | Predicate         |
|---------------|--------|-------------------|
| osis          | string | $pred_string(x)   |
| text          | string | $pred_string(x)   |
| canon_section | string | $pred_string(x)   |

``osis`` is the canonical OSIS reference of the verse, formatted
``<Book>.<chapter>.<verse>``. ``text`` is the canonical surface text of
the verse as the adapter reconstructs it (see Verse.text population
below). ``canon_section`` is set to the literal string ``NT`` on every
``Verse`` node written by this adapter, since MorphGNT only covers the
Greek New Testament.

Emitted labels
==============

``Word {source: 'MorphGNT-SBLGNT'}``: one node per MorphGNT line.
``Verse``: one node per distinct OSIS reference observed across the
MorphGNT corpus. The Verse node is upserted by ``osis`` with the
properties listed above.

Emitted edges
=============

``PARSE_OF``: from each MorphGNT ``Word`` to the MACULA-Greek-SBLGNT
``Word {source: 'MACULA-Greek-SBLGNT'}`` that carries the same OSIS
reference and the same in-verse position ``word``. The join is keyed on
(``osis_ref``, ``word_position``). Cardinality is one to one when both
sides are present.

``IN_VERSE``: from each MorphGNT ``Word`` to its ``Verse`` node, keyed
by OSIS reference.

Stable-id format (idempotency)
==============================

Per the Idempotency section of
``docs/implementation_phases/phase_02_lexical_ingest.md``, the stable id
for every MorphGNT ``Word`` node is
``morphgnt-sblgnt:<osisRef>.w<pos>`` where ``<osisRef>`` is the OSIS
verse reference such as ``John.1.1`` and ``<pos>`` is the one-based
in-verse word position rendered with two-digit zero-padded integers
(``w01``, ``w02``, ..., ``w27``). The ``Verse`` node stable id matches
the format used by other Group 1 adapters: ``verse:<osisRef>``. The
adapter writes each record exactly once per (source-byte, osis-ref,
position) tuple, so a re-ingest over the same upstream bytes is a no-op
under the lexical uniqueness constraints in ``graph/lexical.cypher``.

Verse.text population
=====================

This adapter is the canonical NT populator of ``Verse.text``. The
adapter concatenates the per-word ``text`` field in document order,
separated by a single ASCII space (U+0020) between adjacent tokens, with
no normalisation of Greek diacritics, breathings, accents, or editorial
brackets. The persisted ``Verse.text`` is byte-identical to the upstream
surface tokens joined by single spaces. No leading or trailing
whitespace is added; the adapter trims any leading or trailing
whitespace that would otherwise appear at the verse boundary.

The adapter writes ``Verse.text`` exactly once per OSIS reference. When
two MorphGNT lines share the same ``bcv`` but the file order places them
in a single document run, the adapter accumulates the per-word ``text``
buffer until the OSIS reference changes, then upserts the ``Verse``
node with the concatenated text. Order within a verse is the
file-iteration order of the per-book ``.txt`` source, which MorphGNT
guarantees matches the canonical word order of the verse.

Other adapters (MACULA-Greek-SBLGNT, MACULA-Greek-Nestle1904, ETCBC-BHSA)
MUST NOT write ``Verse.text`` at any phase, to prevent ingest-order
races that would otherwise overwrite the canonical surface value.

Edge cases (Decision 15)
========================

Editorial brackets such as square brackets around doubtful pericopes
(for example the Pericope Adulterae at John 7.53 to 8.11 in some
witnesses) appear in the per-word ``text`` field with the bracket
characters intact, and the adapter MUST persist them verbatim. The
bracketed surface flows through into ``Verse.text`` unchanged, leaving
the decision to honour or strip the brackets to the consumer.

Lines whose ``bcv`` field is not six ASCII digits, or whose token count
is less than seven, are skipped without a write and recorded in the
snapshot ledger as malformed-row rejections so the triangle test does
not see them as silent drops.

Polytonic Greek characters in ``text``, ``word``, ``normalized``, and
``lemma`` are preserved without case folding or accent normalisation, so
the persisted strings round-trip exactly to the upstream MorphGNT
release bytes.

Acceptance Cypher (copied verbatim from phase_02 bullet 4)
==========================================================

```cypher
MATCH (w:Word {source: 'MorphGNT-SBLGNT'})-[:PARSE_OF]->(g:Word {source: 'MACULA-Greek-SBLGNT'})
WITH count(w) AS pairs
RETURN pairs, pairs > 0
```

Dependency on MACULA-Greek-SBLGNT
=================================

The ``PARSE_OF`` edge requires that ``Word {source: 'MACULA-Greek-SBLGNT'}``
nodes already exist in the lexical store before this adapter runs. Per
the Group 1 dispatch order in phase_02, the MACULA-Greek adapter
(``ingest/lexical/macula_greek.py``) populates those nodes alongside the
text-floor pass; this MorphGNT adapter runs within Group 1 after
``macula_greek.py`` so the join target set is materialised. When the
join target is missing for a given (osis_ref, word_position), the
adapter records the row in the snapshot ledger as an unresolved
``PARSE_OF`` join and writes the MorphGNT ``Word`` node without the
``PARSE_OF`` edge, so coverage gaps surface as edge-count shortfalls
rather than silent rejections.

License and redistribution (Decision 14)
========================================

The MorphGNT-SBLGNT corpus is licensed CC-BY-SA-3.0 per the inventory
catalog entry at source index 3. The MorphGNT morphology annotations
carry the Share-Alike obligation; derivative works that redistribute
must propagate the same license. The ``Source`` node registered by this
adapter sets ``slug = 'MorphGNT-SBLGNT'``, ``license = 'CC-BY-SA-3.0'``,
and ``redistribute = true`` (Share-Alike permits redistribution with
attribution and license propagation). The companion underlying SBLGNT
text is governed by its own SBLGNT End-User License; this adapter
persists only the MorphGNT-shipped surface and parse tokens, never the
raw SBLGNT critical-text edition bytes.

The Decision 14 ``Source`` uniqueness constraint on ``slug`` ensures the
adapter registers the source node exactly once at ingest start, before
any record-level write, so the constraint check runs against the
registered slug only.

Expected counts (Tier A, exact)
===============================

Per ``tools/expected_counts.json`` source ``MorphGNT-SBLGNT``:
``tier = A``, ``record_unit = word``, ``expected_count = 137554``,
``tolerance = 0``. The acceptance gate in Phase D asserts the ingested
``Word {source: 'MorphGNT-SBLGNT'}`` node count equals 137554 exactly,
since Tier A admits no tolerance band. The per-row hash recompute in
the triangle test runs the adapter twice over the same upstream bytes
and verifies the sorted per-row SHA-256 hash list is byte-identical
across both runs.

Network isolation
=================

The adapter reads only from ``data/private/morphgnt/`` and writes only
to the lexical Neo4j stack. No HTTP, DNS, or socket access is
permitted; the AST scan in ``tools/check_adapter_purity.py`` rejects
imports of ``subprocess``, ``socket``, ``httpx``, ``requests``,
``urllib``, ``aiohttp``, and other dynamic-loader paths.

Non-goals
=========

This adapter does not embed text, does not invoke Pipeline 2, does not
write to the cultural Neo4j, and does not produce evidence files. It
emits ``Word`` and ``Verse`` nodes plus ``PARSE_OF`` and ``IN_VERSE``
edges, and registers the ``Source`` node for the MorphGNT-SBLGNT slug.
"""
