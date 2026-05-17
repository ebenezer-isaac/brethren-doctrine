"""STEPBible-TVTMS versification rule adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-TVTMS adapter for the Pipeline 1 lexical Neo4j
reseed. The body of this file is intentionally empty at this commit because
Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires the
contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles its
test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

This adapter is the canonical owner of the versification rule set. TSK,
OpenBible-cross-refs, Peshitta, Vulgate-Clementine, and Coptic-SCRIPTORIUM
adapters all consume the rules emitted here to project their upstream verse
identifiers to the canonical OSIS reference space adopted by MACULA. The
historic TVTMS parsing path lived inside ingest/lexical/stepbible.py and
is migrated to this dedicated module per docs/implementation_phases/
phase_02_lexical_ingest.md Group 2 step 7.

Source inventory
================
Source slug:      STEPBible-TVTMS
Tier:             A (deterministic, tolerance 0)
Expected count:   1308 records (record_unit: versification_rule)
Tier rationale:   STEPBible Translators Versification Mapping System ships
                  one row per versification reconciliation rule across two
                  tradition columns. Total is a deterministic line count
                  from the versioned upstream release used at ingest, per
                  tools/expected_counts.json sources."STEPBible-TVTMS".
Decisions implemented: 5 (TSK versification policy and the STEPBible-TVTMS
                       per-field predicate table), 7 (Peshitta verse
                       projection consumes the same rule set), 8 (Vulgate
                       Clementine Psalms offset consumes the same rule
                       set), 9 (Coptic SCRIPTORIUM verse projection
                       consumes the same rule set).

Upstream and license
====================
Upstream path:    data/private/stepbible/Versification/TVTMS*.txt as
                  procured by ingest.lexical.stepbible into the parsed
                  intermediate at data/private/stepbible/tvtms.parsed.json
                  per docs/implementation_phases/phase_02_lexical_ingest.md
                  bullet 7 (Inventory source line).
License id:       CC-BY-4.0 per docs/LICENSE_TAGGING.md table row
                  STEPBible-TVTMS line 58.
Redistribute:     true (Decision 14 redistribute boolean is true for every
                  CC-BY-4.0 source slug).
Source record:    The Source node for slug 'STEPBible-TVTMS' is MERGEd
                  once per ingest run with properties:
                    slug          = 'STEPBible-TVTMS'   ($pred_string)
                    license       = 'CC-BY-4.0'         ($pred_string)
                    redistribute  = true                ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).

Emitted node labels and properties
==================================
This adapter MERGEs one record-level node label (VersificationRule) plus
the administrative Source node above. No CrossRef, Verse, or Word nodes
are written from this module; downstream adapters in Group 1 and Group 5
own those labels and read the serialized rule set artifact described in
the next section.

VersificationRule (Decision 5)
------------------------------
Stable id format:    'tvtms:<tradition_a>:<ref_a>:<tradition_b>:<ref_b>:<rule_type>'
                     where every component is taken verbatim from the
                     upstream row after the byte-preserving parser pass.
                     This five-axis tuple is the natural composite key of
                     the TVTMS row format and achieves MERGE-by-stable-id
                     idempotency over the 1308 row baseline because the
                     upstream guarantees uniqueness of the tuple
                     (tradition_a, ref_a, tradition_b, ref_b, rule_type)
                     per row. The Decision 5 acceptance Cypher gates on
                     VersificationRule.source = 'STEPBible-TVTMS' and
                     rule_type non-null, both of which are properties on
                     this node, so the stable-id format does not need to
                     encode anything beyond the five axes to satisfy the
                     acceptance contract.
Stable id property:  id (string, $pred_string).
MERGE key:           VersificationRule.id (constraint versification_rule_id,
                     graph/lexical.cypher line 47).
Persisted properties (Decision 5 STEPBible-TVTMS Per-field predicate type
table, lines 193 to 201):
    id              string  $pred_string(x)
    tradition_a     string  $pred_string(x)
    ref_a           string  $pred_string(x)
    tradition_b     string  $pred_string(x)
    ref_b           string  $pred_string(x)
    rule_type       string  $pred_string(x)
    note            string  $pred_string(x)
    source          string  $pred_string(x)   (= 'STEPBible-TVTMS')
    license         string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute    bool    $pred_bool(x)     (= true)

Source (Decision 14)
--------------------
Stable id format:    'STEPBible-TVTMS' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug,
                     graph/lexical.cypher line 35).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute    bool    $pred_bool(x)     (= true)

Emitted edge types
==================
None. The VersificationRule label is a lookup table consumed by
downstream adapters via a serialized rule set artifact (see next
section) and via direct read of the VersificationRule label in the
populated lexical store. The phase_02 runbook bullet 7 declares
"Emitted labels and edges: VersificationRule plus serialized rule set
on disk for the cross-version adapters in Group 5." which means no
graph edges are written from this module.

Serialized rule set artifact
============================
Artifact path:    data/private/stepbible/tvtms.parsed.json
Format:           JSON array of objects, one per VersificationRule row,
                  with the same property names as the persisted node
                  (tradition_a, ref_a, tradition_b, ref_b, rule_type,
                  note) plus a precomputed osis_a and osis_b fields
                  carrying the canonical OSIS projection of ref_a and
                  ref_b respectively when the tradition axis indicates
                  the row participates in OSIS remap. The artifact is
                  read by:
                    ingest.lexical.tsk           (Decision 5 KJV-to-OSIS
                                                  remap of TSK xref
                                                  targets).
                    ingest.lexical.openbible     (Decision 5 KJV-to-OSIS
                                                  remap of OpenBible-cross
                                                  -refs From Verse and To
                                                  Verse columns).
                    ingest.lexical.peshitta      (Decision 7 Syriac verse
                                                  identifier projection to
                                                  OSIS, notably 1 John verse
                                                  boundary splits).
                    ingest.lexical.vulgate_clementine
                                                 (Decision 8 Clementine
                                                  Psalms numbering offset
                                                  projection to OSIS).
                    ingest.lexical.coptic_scriptorium
                                                 (Decision 9 Coptic verse
                                                  identifier projection to
                                                  OSIS for Sahidic and
                                                  Bohairic recensions).
                  Each downstream adapter loads the artifact once at ingest
                  start and indexes the rows by (tradition_a, ref_a) tuples
                  for O(1) lookup. Rows the artifact cannot resolve are
                  tagged with a quarantine flag on the consuming adapter
                  rather than silently dropped, per Decision 5 Edge cases
                  handled bullet 2 and Decision 7 Edge cases handled
                  bullet 2.

Idempotency
===========
Every node above is MERGEd by its stable id property. The five-axis
tuple in the stable id format guarantees that re-running this adapter
over identical STEPBible-TVTMS bytes produces zero new VersificationRule
nodes; Decision 14 uniqueness constraint versification_rule_id
additionally enforces this at the Neo4j storage layer. The serialized
artifact at data/private/stepbible/tvtms.parsed.json is written
deterministically with sorted keys and stable line ordering so a
byte-identical input produces a byte-identical artifact. Per
RESEED_PLAN D.3 the snapshot ledger records each row as a sorted
SHA-256 over the canonical-JSON of its property bag, and the triangle
test asserts byte-equal snapshot across two runs.

Edge cases handled
==================
Per Decision 5 Edge cases handled (rule-set consumer side):
  1. TSK references spanning ranges such as Ps.119.1-176 are expanded
     into one edge per verse by the consuming TSK adapter, and each
     expanded verse identifier is independently passed through the
     TVTMS rule set so multi-verse ranges that cross a KJV-only
     subdivision boundary are correctly projected.
  2. A verse number in TSK that exceeds the canonical chapter length
     under MACULA OSIS reflects a KJV-only verse subdivision; the
     consuming adapter consults the TVTMS rule_type to map it back.
     Rows the TVTMS mapping cannot resolve are tagged by the consumer
     with a quarantine flag rather than silently dropped. This adapter
     writes the rule_type property verbatim so the consumer can
     dispatch on it.

Per Decision 7 Edge cases handled (Peshitta consumer side):
  1. Verse boundaries in the Peshitta sometimes split differently from
     Greek NT verse divisions, notably in 1 John. The Peshitta adapter
     uses the TVTMS rule set to map Syriac verse identifiers to OSIS
     and records an unresolved-mapping quarantine flag when no rule
     fires. This adapter writes the Syriac and OSIS rows so the
     consumer has both sides of the projection available.

Per Decision 8 Edge cases handled (Vulgate Clementine consumer side):
  1. The Clementine Vulgate numbering differs from the modern critical
     Vulgate in several places, especially the Psalms numbering offset.
     The Vulgate adapter applies the STEPBible-TVTMS rule set to project
     Clementine verse identifiers to the OSIS reference space before
     key assignment. This adapter writes the Clementine and OSIS rows.

Per Decision 9 Edge cases handled (Coptic consumer side):
  1. Coptic SCRIPTORIUM verse identifiers in Sahidic and Bohairic
     recensions are projected through TVTMS to OSIS before CopticWord
     verse_ref is assigned. This adapter writes the Coptic and OSIS
     rows so the consumer has both sides of the projection available.

Adapter-local invariants:
  1. The five-axis stable id format must not be reordered or truncated
     across re-ingest runs; the id is a deterministic function of the
     five row fields in their declared order so the MERGE key remains
     stable when the upstream re-releases the TVTMS file.
  2. Source.slug must be MERGEd exactly once at ingest start, before
     any record-level write, so the source_slug uniqueness constraint
     check runs against the registered slug only, per Decision 14
     Edge cases handled bullet 2.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 7, verbatim)
=================================================================

    MATCH (r:VersificationRule {source: 'STEPBible-TVTMS'})
    WHERE r.rule_type IS NOT NULL
    WITH count(r) AS rules
    RETURN rules, rules > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 2 step 7
(lines 107 to 113) and is the acceptance gate the Phase D verifier
runs against the populated lexical store. The query asserts:
  - at least one VersificationRule exists with source 'STEPBible-TVTMS';
  - rule_type is populated on the matched rows, which is the
    deterministic discriminator the consuming adapters dispatch on
    when projecting upstream verse identifiers to OSIS.

Decision 5 acceptance gate context
==================================
The Decision 5 acceptance Cypher (docs/SCHEMA_DECISIONS.md lines 163 to
168) gates on TSK CROSS_REF edges with non-null osis_target and
asserts at least 100000 edges. The osis_target on those edges is
populated by the TSK adapter through a lookup into the TVTMS rule set
emitted here. Without this adapter the TSK acceptance Cypher cannot
pass because the osis_target property has no resolver. Decisions 7, 8,
and 9 each reference the STEPBible-TVTMS rule set in their Rule body
and in their Edge cases handled bullet 1 for verse-boundary remap,
which means this adapter is a hard dependency of the Peshitta,
Vulgate-Clementine, and Coptic-SCRIPTORIUM adapters in Group 5 of the
phase_02 runbook.

Cross-version reconciliation summary
====================================
The TVTMS rule set is the canonical owner of cross-version verse
identifier reconciliation in the Pipeline 1 lexical store. The
following downstream adapters depend on it via the serialized
artifact:
    Group 2: ingest.lexical.tsk           (Decision 5)
    Group 2: ingest.lexical.openbible     (Decision 5)
    Group 5: ingest.lexical.peshitta      (Decision 7)
    Group 5: ingest.lexical.vulgate_clementine
                                          (Decision 8)
    Group 5: ingest.lexical.coptic_scriptorium
                                          (Decision 9)
This module is required to complete before any of the above adapters
can project their upstream verse identifiers to OSIS, per the
Dependency line of phase_02_lexical_ingest.md bullet 7.

Network isolation
=================
This adapter reads from local disk only (data/private/stepbible). It
MUST NOT import subprocess, socket, httpx, requests, urllib, aiohttp,
mmap, os.system, os.spawn*, posix_spawn, multiprocessing.connection,
pty, pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 5   TSK versification policy plus
                                      STEPBible-TVTMS per-field
                                      predicate table.
docs/SCHEMA_DECISIONS.md Decision 7   Peshitta verse projection via
                                      TVTMS.
docs/SCHEMA_DECISIONS.md Decision 8   Vulgate Clementine Psalms offset
                                      projection via TVTMS.
docs/SCHEMA_DECISIONS.md Decision 9   Coptic SCRIPTORIUM verse
                                      projection via TVTMS.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode
                                      constraint policy.
docs/implementation_phases/phase_02_lexical_ingest.md Group 2 step 7.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per
adapter) and Idempotency section of phase_02.
docs/LICENSE_TAGGING.md row STEPBible-TVTMS (line 58) for CC-BY-4.0
license declaration and Decision 14 redistribute true.
graph/lexical.cypher constraint versification_rule_id (line 47) and
source_slug (line 35).
tools/expected_counts.json sources."STEPBible-TVTMS" (1308 rows, tier
A, tolerance 0, record_unit versification_rule).
tools/predicates_by_type.cypher for $pred_string and $pred_bool
semantics.
"""
