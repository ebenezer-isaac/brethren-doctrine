"""STEPBible-proper-nouns adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-proper-nouns adapter for the Pipeline 1 lexical
Neo4j reseed. The body of this file is intentionally empty at this commit
because Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires
the contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles its
test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      STEPBible-proper-nouns
Tier:             A (deterministic, tolerance 0)
Expected count:   23205 records (record_unit: proper_name)
Tier rationale:   STEPBible proper nouns reference table ships one row per
                  proper-name entry across Hebrew and Greek sections.
                  Total is a deterministic line count from the versioned
                  upstream release used at ingest time.
Decisions implemented: 17.

Upstream and license
====================
Upstream path:    data/private/stepbible/Proper Nouns/TI... (TSV table; one
                  row per proper-name entry, headline column
                  proper_name_entry plus eight populated detail columns
                  and thirty sparse residual columns the inventory pass
                  flags at occurrence rate zero or near-zero).
License id:       CC-BY-4.0 (STEPBible reference tables) per Decision 14
                  Source policy and docs/LICENSE_TAGGING.md.
Source record:    The Source node for slug 'STEPBible-proper-nouns' is
                  MERGEd once per ingest run with properties:
                    slug          = 'STEPBible-proper-nouns'  ($pred_string)
                    license       = 'CC-BY-4.0'               ($pred_string)
                    redistribute  = true                       ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).
                  The Source node is MERGEd at ingest start, before any
                  record-level write, per Decision 14 Edge cases handled
                  bullet 2.

Emitted node labels and properties
==================================
The adapter MERGEs one node label by stable id. Sparse residual columns in
the upstream TSV are NOT persisted; only columns with occurrence > 0 in the
docs/data_inventory_catalog.json inventory sample enter the node per
Decision 17 Rule (last sentence: "Sparse columns are not persisted; only
columns with occurrence > 0 in the inventory catalog enter the node.").

ProperNoun (Decision 17 populated projection)
---------------------------------------------
Stable id format:    The verbatim headline column value
                     (proper_name_entry) from the upstream row. The
                     headline carries the canonical name plus any
                     STEPBible disambiguator suffix so each row's
                     proper_name_entry is unique within the upstream
                     table. Pre-MERGE the adapter validates uniqueness
                     across the parsed rows and records any collision in
                     the snapshot ledger so re-ingest of an upstream
                     revision that introduces a duplicate headline
                     surfaces as a hard fail rather than a silent
                     overwrite.
Stable id property:  proper_name_entry (string, $pred_string).
MERGE key:           ProperNoun.proper_name_entry (constraint
                     proper_noun_entry, graph/lexical.cypher line 41).
                     The graph constraint is UNIQUE on
                     proper_name_entry, so any second-write attempt for
                     the same headline is rejected at the storage layer.
Persisted properties (Decision 17 STEPBible-proper-nouns populated
projection Per-field predicate type table):
    proper_name_entry   string  $pred_string(x)
    transliteration     string  $pred_string(x)
    meaning             string  $pred_string(x)
    strong              string  $pred_string(x)   (canonical Strong key, joins to Strong.id)
    pos                 string  $pred_string(x)
    language            string  $pred_string(x)   (= 'hebrew' or 'greek', Decision 17 Edge cases handled bullet 2)
    verse_count         int     $pred_int(x)      (nullable; Decision 17 Edge cases handled bullet 3)
    first_occurrence    string  $pred_string(x)   (OSIS reference of the first occurrence)
    source              string  $pred_string(x)   (= 'STEPBible-proper-nouns')

Language discriminator
======================
The proper-nouns table contains both Hebrew and Greek names in distinct
sections of the upstream TSV. The adapter MUST tag each ProperNoun node
with a `language` discriminator derived from the section the row was
parsed from per Decision 17 Edge cases handled bullet 2, because the
headline field (proper_name_entry) alone does not disambiguate
cross-language homographs. The section boundary is detected from the
upstream file structure as documented in the STEPBible Proper Nouns
README, not inferred from the headline string. Recognised values are
the lowercase tokens 'hebrew' and 'greek'. Rows whose section cannot be
attributed to either language are recorded in the snapshot ledger as a
quarantine entry rather than persisted with a guessed language value.

Emitted edge types
==================
Every edge below has src and dst labels fixed and is MERGEd by the
src+dst+rel_type tuple so re-ingest over identical input does not
multiply edges.

NAMED_AT (Decision 17, phase_02_lexical_ingest.md Group 3 step 12)
    src: ProperNoun       dst: Verse
    properties:           (none)
    cardinality:          zero or one per ProperNoun. The edge is
                          emitted when the first_occurrence field
                          resolves through OSIS reference lookup to a
                          Verse node populated by Group 1
                          (OSHB-morphology for OT verses,
                          MorphGNT-SBLGNT for NT verses per Decision
                          15). When the OSIS reference resolution
                          fails (because first_occurrence is empty,
                          malformed, or addresses a Verse not yet
                          populated by Group 1 at adapter run time),
                          the edge is suppressed and the per-row
                          condition is recorded in the snapshot ledger
                          so the triangle test surfaces unresolved
                          first_occurrence rows. The ProperNoun node
                          still merges; only the edge is suppressed.
                          The target Verse is joined by its osisID
                          (constraint verse_osisID, graph/lexical.cypher
                          line 18) or by its id property under the
                          'verse:<osisRef>' stable-id convention emitted
                          by the OSHB and MorphGNT adapters.

Idempotency
===========
Every ProperNoun node is MERGEd by proper_name_entry. Every NAMED_AT
edge is MERGEd on the (ProperNoun.proper_name_entry, Verse.osisID,
'NAMED_AT') tuple. Re-running this adapter over identical upstream TSV
bytes produces zero new nodes and zero new edges; the Decision 17
proper_noun_entry uniqueness constraint additionally enforces this at
the Neo4j storage layer. Per RESEED_PLAN D.3 the snapshot ledger
records each row as a sorted SHA-256 over the canonical-JSON of its
property bag, and the triangle test asserts byte-equal snapshot across
two runs over identical inputs.

Edge cases handled
==================
Per Decision 17 Edge cases handled (rows 1 through 3 of the decision
block; row 1 governs the sibling MorphCode adapter and is recorded
here for completeness):
  1. (MorphCode adapter scope, not this adapter.) A handful of morph
     codes resolve to multiple expansions because the upstream
     documents alternative analyses; the STEPBible-morph-codes
     adapter persists all expansions in an `expansions` list-typed
     property. This proper-nouns adapter does not emit MorphCode
     nodes and the rule is restated only so the cross-decision
     boundary is documented in one place.
  2. The proper-nouns table contains both Hebrew and Greek names in
     distinct sections. The adapter MUST tag each ProperNoun node
     with a `language` discriminator derived from the section the row
     was parsed from, because the headline field alone does not
     disambiguate cross-language homographs (for example, a Greek
     transliteration of a Hebrew theophoric name shares the surface
     form across sections). The language values are 'hebrew' and
     'greek'; any other value is treated as a parse error and the row
     is recorded in the snapshot ledger for triangle-test inspection.
  3. A small subset of proper-noun entries carry a numeric verse_count
     column with a non-numeric placeholder when the upstream count is
     uncertain. The adapter MUST coerce non-numeric placeholders to a
     null integer rather than rejecting the row, so $pred_int(
     verse_count) accurately reports the uncertainty without dropping
     a legitimate proper-name row. Row rejection is forbidden for this
     case; only the verse_count property is set to null. The
     $pred_int predicate from tools/predicates_by_type.cypher returns
     false on null (the canonical predicate is `x IS NOT NULL`), so
     the verifier ratio for verse_count honestly reflects the
     uncertainty fraction in the upstream table.

Sparse residual columns policy
==============================
The inventory catalog (docs/data_inventory_catalog.json) records the
upstream TSV as carrying eight populated detail columns and thirty
sparse residual columns. Per Decision 17 Rule the adapter persists
only the eight populated detail columns (proper_name_entry,
transliteration, meaning, strong, pos, language, verse_count,
first_occurrence) as ProperNoun node properties. The thirty sparse
residual columns are NOT persisted on the node; the adapter reads
them so the snapshot ledger can record their occurrence rate per row
for triangle-test drift detection, but no node property is written
for those columns. If a later upstream release populates a residual
column to non-zero occurrence in the inventory pass, that column
SHALL be added to this projection only via a SCHEMA-REVISION commit
to docs/SCHEMA_DECISIONS.md (Decision 17) and to
docs/data_inventory_catalog.json (the populated_columns array for
STEPBible-proper-nouns); this adapter MUST NOT silently expand the
projection without that revision commit.

Acceptance Cypher (phase_02_lexical_ingest.md Group 3 step 12, verbatim)
========================================================================

    MATCH (p:ProperNoun {source: 'STEPBible-proper-nouns'})
    WHERE p.proper_name_entry IS NOT NULL
    WITH count(p) AS names
    RETURN names, names > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 12
and is the acceptance gate the Phase D verifier runs against the
populated lexical store. The query asserts:
  - at least one ProperNoun exists with source 'STEPBible-proper-nouns';
  - every counted ProperNoun has a non-null proper_name_entry, which
    is the stable id and the MERGE key.

Decision 17's own acceptance Cypher is the MorphCode adapter's gate
and is reproduced here for cross-reference; this adapter does not
write MorphCode nodes:

    MATCH (m:MorphCode {source: 'STEPBible-morph-codes'})
    WHERE m.code IS NOT NULL AND m.expansion IS NOT NULL AND size(m.code) > 0
    WITH count(m) AS codes
    RETURN codes, codes > 100

The Phase D ratio-of-non-empty-fields verifier (tools/verify_adapter_*.py)
additionally runs the standard predicate ratio template against this
adapter, substituting the populated detail columns through
tools/predicates_by_type.cypher:

    :include tools/predicates_by_type.cypher

    MATCH (n:ProperNoun {source: 'STEPBible-proper-nouns'})
    WITH count(n) AS total,
         count(CASE WHEN $pred_string(n.proper_name_entry) THEN 1 END) AS with_pne,
         count(CASE WHEN $pred_int(n.verse_count) THEN 1 END) AS with_vc
    RETURN total,
           with_pne * 1.0 / total AS ratio_pne,
           with_vc * 1.0 / total AS ratio_vc

The Tier A tolerance is exact match (0 records of drift) against the
expected_count of 23205 per tools/expected_counts.json
sources."STEPBible-proper-nouns".

Dependencies
============
This adapter depends on Verse nodes from Group 1 (text floor). The
NAMED_AT edge cannot resolve unless the OSHB-morphology adapter and
the MorphGNT-SBLGNT adapter have already populated Verse nodes for
the OSIS references the first_occurrence column addresses. The
adapter MUST be dispatched in Group 3 (lexicons) after the Group 1
adapters have committed their writes per
docs/implementation_phases/phase_02_lexical_ingest.md Dispatch order.
When the adapter runs and a first_occurrence reference does not
resolve to an existing Verse, the edge is suppressed and the row is
recorded in the snapshot ledger; the ProperNoun node still merges.

Network isolation
=================
This adapter reads from local disk only (data/private/stepbible/
Proper Nouns/). It MUST NOT import subprocess, socket, httpx,
requests, urllib, aiohttp, mmap, os.system, os.spawn*, posix_spawn,
multiprocessing.connection, pty, pipes, winreg, ctypes, or dynamic
__import__, per tools/check_adapter_purity.py and RESEED_PLAN C.4.
The Phase C dry-run executes the adapter inside Docker with
--network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 17  STEPBible morph-codes and proper-nouns reference tables.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy (Source node MERGE rule).
docs/SCHEMA_DECISIONS.md Decision 15  Verse.text population policy (Verse target shape for NAMED_AT).
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 12 (this adapter).
docs/implementation_phases/phase_02_lexical_ingest.md Group 1 (Verse dependency).
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraint proper_noun_entry (line 41), constraint source_slug (line 35), constraint verse_id (line 17), constraint verse_osisID (line 18).
tools/expected_counts.json sources."STEPBible-proper-nouns" (tier A, expected_count 23205, record_unit proper_name, tolerance 0).
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool semantics.
"""
