"""STEPBible-TTESV adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the STEPBible-TTESV (Tagged Translation ESV) adapter for the
Pipeline 1 lexical Neo4j reseed. The body of this file is intentionally empty
at this commit because Phase C.1 of the RESEED_PLAN (verifier-caste
architecture) requires the contract to be committed BEFORE any implementation
body and BEFORE the Verifier-caste subagent writes its coverage tests. The
Verifier compiles its test queries against this docstring plus the matching
sections of docs/SCHEMA_DECISIONS.md without reading the implementation body.
The function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      STEPBible-TTESV
Tier:             A (deterministic, tolerance 0)
Expected count:   31272 records (record_unit: tagged_word)
Tier rationale:   STEPBible Tagged Translation ESV ships one row per tagged
                  English surface word with Strong key and morph code. Total
                  is a deterministic line count from the versioned upstream
                  release used at ingest time.
Decisions implemented: 14, 15.

Upstream and license
====================
Upstream path:    data/private/stepbible/Tagged-Bibles/T... (TSV files).
License id:       CC-BY-NC-4.0. This license is restrictive (personal use
                  only, non-commercial). The Source node MUST therefore carry
                  redistribute = false so any Pipeline 2 evidence emission
                  pathway can short-circuit redistribution of TTESV bytes
                  while still using them as a tagging input for the local
                  graph store. The NC clause is the binding constraint per
                  upstream STEPBible licensing notice.
Source record:    The Source node for slug 'STEPBible-TTESV' is MERGEd once
                  per ingest run with properties (Decision 14 Per-field
                  predicate type table):
                    slug          = 'STEPBible-TTESV'    ($pred_string)
                    license       = 'CC-BY-NC-4.0'       ($pred_string)
                    redistribute  = false                ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).
                  The Source node is MERGEd exactly once at ingest start,
                  before any record-level write, so the source_slug
                  uniqueness constraint check runs against the registered
                  slug only (Decision 14 Edge cases handled bullet 2).

Emitted node label and properties
=================================
The adapter MERGEs a single record-level node label, TaggedToken, plus the
administrative Source node above. Each row below quotes its persisted
property name, the primitive type the value carries, and the matching
predicate from tools/predicates_by_type.cypher.

TaggedToken (Decision 14, Decision 15)
--------------------------------------
Stable id format:    'stepbible-ttesv:<osisRef>.w<pos>' where <osisRef> is
                     the canonical OSIS reference (e.g. 'Gen.1.1') and <pos>
                     is the 1-based English surface word position within the
                     verse, zero-padded to two digits. Namespacing on the
                     'stepbible-ttesv:' prefix keeps these identifiers
                     disjoint from the STEPBible-TAHOT and STEPBible-TAGNT
                     TaggedToken identifiers which use 'stepbible-tahot:'
                     and 'stepbible-tagnt:' prefixes respectively, so the
                     tagged_token_id constraint (graph/lexical.cypher line
                     42) never collides across the three TTESV/TAHOT/TAGNT
                     adapters.
Stable id property:  id (string, $pred_string).
MERGE key:           TaggedToken.id (constraint tagged_token_id,
                     graph/lexical.cypher line 42).
Persisted properties (per the upstream TTESV TSV column set, expressed
under the Decision 14 Per-field predicate type discipline; string columns
use $pred_string and any int-typed Strong key uses $pred_int):
    id                string  $pred_string(x)
    ref_eng           string  $pred_string(x)   (= upstream OSIS verse ref column)
    english_surface   string  $pred_string(x)   (= tagged English surface word)
    strong            string  $pred_string(x)   (canonical Strong id; joins to Lemma.strong or GreekLemma.id)
    morph             string  $pred_string(x)   (STEPBible morph code; joins to MorphCode.code)
    lemma             string  $pred_string(x)   (Hebrew or Greek dictionary lemma)
    normalized        string  $pred_string(x)   (normalised English form)
    source            string  $pred_string(x)   (= 'STEPBible-TTESV')
    license           string  $pred_string(x)   (= 'CC-BY-NC-4.0' mirrored from Source for fast filtering)
    redistribute      bool    $pred_bool(x)     (= false; CC-BY-NC-4.0 personal use only)
    osis_ref          string  $pred_string(x)   (canonical OSIS verse ref, derived from ref_eng)
    position          int     $pred_int(x)      (1-based surface word position)
    language          string  $pred_string(x)   ('hebrew' or 'greek' inferred from strong prefix)

If the upstream emits an integer-typed Strong code rather than a string with
'H' or 'G' prefix, the adapter MUST coerce it to the canonical prefixed
string form via ingest.canonical_strongs.canonical_strongs(raw, lang=...)
before persisting. The Decision 14 Per-field predicate type table treats
Strong.id as string, so the persisted strong property is string-typed and
the $pred_int predicate is reserved for any residual upstream int columns
the adapter may pass through (e.g. the raw greekstrong column on
MACULA-Hebrew rows which is not applicable here but is documented as a
type hint for the Verifier-caste subagent: int Strong columns use
$pred_int and string Strong columns use $pred_string).

Emitted edge types
==================
Every edge below has src and dst labels fixed and is MERGEd by the
src+dst+rel_type tuple so re-ingest over identical input does not multiply
edges.

INSTANCE_OF (Decision 14)
    src: TaggedToken     dst: Lemma  OR  GreekLemma
    properties:          (none)
    cardinality:         exactly one per TaggedToken with a resolvable
                         Strong identifier. The target label is selected
                         from the Strong language discriminator:
                           - if the canonical Strong starts with 'H'
                             (Hebrew or Aramaic), the edge points to
                             Lemma (constraint lemma_strong,
                             graph/lexical.cypher line 13);
                           - if the canonical Strong starts with 'G'
                             (Greek), the edge points to GreekLemma
                             (constraint greek_lemma_id, line 14).
                         When the row has no Strong (rare; functional
                         English glue tokens that the upstream did not
                         tag), the adapter MUST skip the INSTANCE_OF
                         edge but still MERGE the TaggedToken so the
                         row count matches expected_count 31272 exactly
                         under tier A tolerance 0. This mirrors the
                         Decision 1 functional-particle edge-case
                         treatment.

FROM_EDITION (Decision 14)
    src: TaggedToken     dst: Source
    properties:          (none)
    cardinality:         exactly one per TaggedToken. The Source node is
                         the singleton MERGEd at ingest start with slug
                         'STEPBible-TTESV', license 'CC-BY-NC-4.0',
                         redistribute false. Pipeline 2 provenance
                         filters MUST be able to walk this edge to
                         confirm the license and redistribute flags on
                         every TaggedToken without re-reading the node
                         property bag.

Verse.text policy (Decision 15)
===============================
This adapter is NOT permitted to write Verse.text. Per Decision 15, the
only authorised Verse.text writers are the OSHB-morphology adapter (OT
verses) and the MorphGNT-SBLGNT adapter (NT verses). STEPBible-TTESV
emits an English ESV-derived surface, not the canonical Hebrew or Greek
surface, so writing it into Verse.text would shadow the canonical OT/NT
surface and violate the byte-identical-upstream rule the canonical
adapters enforce. The TTESV adapter MAY read Verse nodes for OSIS join
purposes (to confirm the ref_eng column resolves to an existing Verse.id)
but MUST NOT set or update any Verse property. If a Pipeline 2 consumer
needs the ESV surface, it reads TaggedToken.english_surface concatenated
in document order per verse, never Verse.text.

Idempotency
===========
Every TaggedToken node is MERGEd by id, every Source node is MERGEd by
slug, and every edge is MERGEd on the (src.id, dst.id, rel_type) tuple.
Re-running this adapter over identical TTESV TSV bytes produces zero new
nodes and zero new edges; Decision 14 uniqueness constraints on
TaggedToken.id and Source.slug additionally enforce this at the Neo4j
storage layer. Per RESEED_PLAN D.3 the snapshot ledger records each row
as a sorted SHA-256 over the canonical-JSON of its property bag, and the
triangle test asserts byte-equal snapshot across two runs.

Edge cases handled
==================
Per Decision 14 Edge cases handled:
  1. Strong identifier with a sense suffix (e.g. 'H1234A' or 'G2532A')
     MUST resolve to the base Strong under the strong_id uniqueness
     constraint. The suffix is stored on the Strong node's
     disambig_suffix property by whichever adapter first MERGEs the
     Strong; this adapter calls
     ingest.canonical_strongs.canonical_strongs(raw, lang=<inferred>)
     which returns the (base_id, suffix) tuple and persists the suffix
     on the Strong side, never concatenated into Strong.id.
  2. The Source node is MERGEd exactly once at ingest start, before any
     record-level write, so the source_slug uniqueness constraint check
     runs against the registered slug 'STEPBible-TTESV' only.

Per Decision 15 Edge cases handled (read-side):
  1. Maqqef joining two Hebrew words into one surface unit on OT verses
     is preserved verbatim by the OSHB-morphology adapter; the TTESV
     adapter MUST NOT split or rejoin the English surface around the
     maqqef-equivalent in ESV (typically a hyphen in compound proper
     names). The english_surface field is persisted as the upstream
     emits it.
  2. Editorial bracket characters in ESV (e.g. brackets around John
     7:53 to 8:11) are persisted verbatim in english_surface. The TTESV
     adapter does not interpret the brackets and does not write
     anything into Verse.text where they would otherwise appear.

Adapter-local edge cases:
  1. A small number of TTESV rows are translator-supplied English words
     with no Strong key (e.g. articles inserted for English readability
     that have no Hebrew or Greek backing token). The adapter MUST
     persist these TaggedToken nodes with strong = '' and skip the
     INSTANCE_OF edge so the row count remains tier A exact at 31272
     while the $pred_string(strong) predicate honestly reports the gap.
  2. The language discriminator is derived from the canonical Strong
     prefix, not from the book context, because TTESV does not ship
     a separate language column. Rows whose canonical Strong starts
     with 'H' carry language = 'hebrew', rows starting with 'G' carry
     language = 'greek', and rows without a Strong carry language = ''
     so the $pred_string predicate accurately reports the gap.
  3. The ref_eng column occasionally contains a multi-verse span on
     ESV section headings; the adapter MUST resolve such a span to the
     first verse in the range for OSIS join purposes and record the
     span endpoints in a quarantine field on the snapshot ledger
     rather than fabricating multiple TaggedToken rows.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 13, verbatim)
==================================================================

    MATCH (t:TaggedToken {source: 'STEPBible-TTESV'})
    WHERE t.license = 'CC-BY-NC-4.0' AND t.redistribute = false
    WITH count(t) AS tokens
    RETURN tokens, tokens > 0

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 13
(Lexicons group) and is the acceptance gate the Phase D verifier runs
against the populated lexical store. The query asserts:
  - at least one TaggedToken exists with source 'STEPBible-TTESV';
  - every such TaggedToken carries the CC-BY-NC-4.0 license stamp;
  - every such TaggedToken carries redistribute = false.

In addition, Decision 14's own acceptance Cypher is the Source slug
uniqueness gate Phase D runs across all adapters:

    MATCH (s:Strong)
    WITH s.id AS sid, count(*) AS dup_count
    WHERE dup_count > 1 AND sid IS NOT NULL
    WITH collect(sid) AS duplicates
    MATCH (src:Source)
    WITH duplicates, count(DISTINCT src.slug) AS slug_count, count(src) AS src_total
    RETURN size(duplicates) = 0 AND slug_count = src_total

The TTESV adapter satisfies this by MERGEing Source by slug exactly once
at ingest start and by calling canonical_strongs so the Strong nodes it
participates in joining never carry a sense suffix in their id.

Dependency
==========
This adapter runs in Phase C Wave 1 after Group 1 (text floor) has
populated:
  - Lemma nodes (from MACULA-Hebrew per Decision 1 and Decision 4);
  - GreekLemma nodes (from MACULA-Greek-Nestle1904 and
    MACULA-Greek-SBLGNT per Decision 2 and Decision 4);
  - Verse nodes (from OSHB-morphology for OT and MorphGNT-SBLGNT for
    NT per Decision 15).
The INSTANCE_OF edges this adapter emits require Lemma or GreekLemma
targets to already exist, and the OSIS ref join for stable-id
construction requires Verse nodes to already exist. Running TTESV before
Group 1 completes is a contract violation that the Phase D verifier
detects via missing-edge counts against the expected_count baseline.

Stable-id namespace recap
=========================
Stable id format (re-stated for clarity): 'stepbible-ttesv:<osisRef>.w<pos>'.
This prefix is disjoint from every other TaggedToken-emitting adapter
('stepbible-tahot:' for STEPBible-TAHOT, 'stepbible-tagnt:' for
STEPBible-TAGNT), so the tagged_token_id constraint never rejects a
legitimate TTESV row on collision grounds. The 'stepbible-ttesv:' prefix
also signals provenance to any text-grep audit of the lexical store.

Network isolation
=================
This adapter reads from local disk only
(data/private/stepbible/Tagged-Bibles/T...). It MUST NOT import
subprocess, socket, httpx, requests, urllib, aiohttp, mmap, os.system,
os.spawn*, posix_spawn, multiprocessing.connection, pty, pipes, winreg,
ctypes, or dynamic __import__, per tools/check_adapter_purity.py and
RESEED_PLAN C.4. The Phase C dry-run executes the adapter inside Docker
with the network=none flag.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy.
docs/SCHEMA_DECISIONS.md Decision 15  Verse.text population policy (this adapter is excluded from Verse.text writers).
docs/implementation_phases/phase_02_lexical_ingest.md Group 3 step 13 (STEPBible-TTESV).
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints tagged_token_id (line 42), source_slug (line 35), strong_id (line 36), lemma_strong (line 13), greek_lemma_id (line 14), verse_id (line 17), verse_osisID (line 18) and index tagged_token_strong (line 65).
tools/expected_counts.json sources."STEPBible-TTESV" (tier A, expected_count 31272, record_unit tagged_word, tolerance 0).
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool, $pred_list semantics.
"""
