"""TSK adapter docstring contract (Phase C Wave 1).

This module implements Decision 5 of docs/SCHEMA_DECISIONS.md, the TSK
versification policy, narrowed in this file to the Treasury of Scripture
Knowledge cross-reference source. The companion adapter for
OpenBible-cross-refs lives in ingest/lexical/openbible.py and is governed
by the same Decision 5 rule with a strictly separate edge type so the
provenance separation between TSK and OpenBible stays mechanically
enforceable at query time. The legacy executable body of this file is
replaced by this single docstring expression per the
implementer-docstring caste boundary; the implementer-impl commit that
follows will reintroduce executable adapter code under a separate caste
trailer.

Source identity and counts
==========================
Source slug          : TSK
Inventory tier       : A (deterministic row count from one packed
                       SWORD-derived flat file, zero tolerance)
Record unit          : tsk_entry (one CrossRef node per per-word entry
                       carrying a packed xref_string payload)
Expected count       : 63682 rows / CrossRef nodes per
                       tools/expected_counts.json sources."TSK"
License              : public_domain per docs/LICENSE_TAGGING.md and
                       Decision 14 of docs/SCHEMA_DECISIONS.md, since
                       the 1880 Treasury of Scripture Knowledge by R. A.
                       Torrey is out of copyright and the upstream
                       SWORD TSK module redistributes it under that
                       status with no further restriction
Redistribute         : True (Source.redistribute is set true on the
                       single Source node registered for slug 'TSK' at
                       ingest start, before any record-level write, so
                       the source_slug uniqueness constraint in
                       graph/lexical.cypher rejects re-registration)
Upstream input path  : data/private/tskxref.txt (SWORD TSK module flat
                       file with one line per per-word entry, tab
                       separated into book_num, chapter, verse,
                       word_num, keyword, xref_string)

Label and edge surface
======================
CrossRef (source = 'TSK')

CROSS_REF : CrossRef to Verse, one edge per expanded reference inside
            xref_string. The edge MUST carry property source='TSK' and
            property osis_target (string, $pred_string(x)) holding the
            OSIS rendering of the resolved target verse, plus the
            inherited license and redistribute flags so the edge filter
            in Pipeline 2 can partition TSK contributions cleanly from
            OPENBIBLE_CROSS_REF without joining back through the
            CrossRef node. The CROSS_REF edge type is the one Decision
            5 reserves for TSK; OpenBible-cross-refs MUST use the
            parallel OPENBIBLE_CROSS_REF edge type, never CROSS_REF, so
            provenance filters in Pipeline 2 stay clean and the edge
            count in tools/expected_counts.json edge_counts
            HAS_CROSS_REF block is the TSK-only count.

CrossRef stable identifier
==========================
Key tuple            : (book_num, chapter, verse, word_num) per
                       Decision 5. The four integer columns at the
                       head of every TSK row uniquely identify the
                       per-word anchor that the upstream attaches the
                       cross-reference payload to. The crossref_id
                       constraint in graph/lexical.cypher requires
                       c.id IS UNIQUE for CrossRef nodes, so the
                       adapter MUST construct a string id from the
                       key tuple.
Stable-id format     : tsk:<book_num>.<chapter>.<verse>.<word_num>
                       where book_num is the integer book index in
                       the TSK numbering, chapter and verse are the
                       integer verse coordinates in the KJV scheme
                       carried by the upstream file, and word_num is
                       the one-indexed word position within the
                       anchor verse that the entry pins on. The colon
                       separator after the slug and the dot separators
                       between integers MUST be preserved verbatim so
                       the id remains a single canonical string per
                       key tuple.
Justifiable alt      : if a subsequent SWORD TSK module release adds a
                       sub-word anchor that the upstream signals via
                       an extra trailing column, the adapter MAY
                       extend the id with a fifth dot-separated
                       integer suffix on those rows alone, recording
                       the fallback per row in the snapshot ledger so
                       the triangle test hash diverges if the upstream
                       column shape shifts. The base four-tuple id is
                       the canonical form for the Phase A.4 baseline.
Uniqueness           : enforced by graph/lexical.cypher constraint
                       crossref_id (FOR (c:CrossRef) REQUIRE c.id IS
                       UNIQUE) per Decision 5. The crossref_from_ref
                       and crossref_to_ref indexes speed the per-verse
                       traversal that Pipeline 2 runs against TSK
                       cross-reference walks. The id is NOT the
                       (book_num, chapter, verse, word_num) tuple
                       directly because Neo4j uniqueness constraints
                       on Phase A.4 cypher target a single string
                       property, and serialising the tuple into a
                       canonical string keeps the constraint check
                       deterministic across re-ingest.

Per-field predicate type (CrossRef node, per Decision 5 TSK table)
==================================================================
| Field        | Type   | Predicate         | Nullability |
|--------------|--------|-------------------|-------------|
| book_num     | int    | $pred_int(x)      | not null    |
| chapter      | int    | $pred_int(x)      | not null    |
| verse        | int    | $pred_int(x)      | not null    |
| word_num     | int    | $pred_int(x)      | not null    |
| keyword      | string | $pred_string(x)   | not null    |
| xref_string  | string | $pred_string(x)   | not null    |
| from_ref     | string | $pred_string(x)   | not null    |
| to_ref       | string | $pred_string(x)   | not null    |

The from_ref property carries the OSIS rendering of the anchor verse
derived from the key tuple after TVTMS reconciliation; the to_ref
property carries the OSIS rendering of the first expanded reference in
xref_string and is provided as a denormalised hint for query traversal
even though the canonical per-target reference lives on the CROSS_REF
edge as osis_target. The xref_string field is preserved verbatim from
the upstream packed payload so the snapshot ledger can rehash it
byte-for-byte across two runs; the per-target expansion does NOT
overwrite this field. Predicate-type references resolve through
tools/predicates_by_type.cypher via tools/predicates.py.substitute at
verifier time per the runbook in
docs/implementation_phases/phase_02_lexical_ingest.md section
"Per-adapter acceptance pattern".

CROSS_REF edge properties
=========================
| Property      | Type   | Predicate          | Nullability |
|---------------|--------|--------------------|-------------|
| source        | string | $pred_string(x)    | not null    |
| osis_target   | string | $pred_string(x)    | not null    |
| license       | string | $pred_string(x)    | not null    |
| redistribute  | bool   | $pred_bool(x)      | not null    |

The source property MUST equal the literal string 'TSK' on every
CROSS_REF edge this adapter emits. The osis_target property MUST hold
the canonical OSIS rendering of the resolved target verse, which is
the join key Pipeline 2 walks back to the Verse node identified by the
matching osisID property under the verse_osisID uniqueness constraint.
The license property MUST equal 'public_domain' and the redistribute
property MUST equal true per Decision 14.

xref_string range expansion
===========================
The xref_string column packs one or more references in a compact form,
ranges such as 'Ps.119.1-176' commonly appear, and the adapter MUST
expand a range into one CROSS_REF edge per verse in the range, not a
single packed edge with hidden multiplicity. The expansion rule:

1. Split the xref_string on the semicolon separator to obtain one
   reference token per parsed entry.
2. For each token, recognise the book abbreviation prefix and the
   chapter colon verse suffix; recognise the dash range separator
   within the verse suffix when present.
3. When the verse suffix contains a range 'a-b', enumerate every
   integer v with a <= v <= b and emit one CROSS_REF edge with
   osis_target set to the resolved OSIS reference for that single v.
4. When the verse suffix contains a comma-separated list 'a,b,c',
   treat each element as an independent verse target and emit one
   CROSS_REF edge per element; combined range plus list forms such as
   'a-b,c' are expanded by applying rule 3 to the range token and
   rule 4 to the list separator.
5. The packed xref_string is preserved verbatim on the CrossRef node
   so the count-based acceptance query and Pipeline 2 graph-walk both
   see the true cardinality on the edges while the unexpanded payload
   stays auditable on the node.

The edge count after expansion lives in
tools/expected_counts.json edge_counts.HAS_CROSS_REF tier B, with
expected_min 100001 and expected_max 509456. The expected_min equals
the Decision 5 acceptance gate of one hundred thousand plus one. The
expected_max assumes an average of eight refs per parsed entry across
sixty-three thousand rows. The Phase D verifier asserts the edge
count falls within this two-percent-tolerance Tier B band per the
tier_policy block at the head of tools/expected_counts.json.

TVTMS reconciliation
====================
TSK numbers verses in the KJV scheme, and the canonical OSIS reference
space adopted by MACULA differs in places, particularly where the KJV
splits a verse the OSIS keeps whole, or where the KJV omits a verse
the OSIS includes by another sequence. Decision 5 directs every TSK
reference, anchor and target alike, through the STEPBible-TVTMS
rule_type reconciliation before key assignment.

The reconciliation rule:

1. Resolve the anchor verse (book_num, chapter, verse) into the OSIS
   reference space by looking up the TVTMS rule whose tradition_a is
   the KJV tradition slug and whose ref_a matches the anchor; the
   rule's tradition_b and ref_b columns give the OSIS reference.
2. Resolve each expanded target reference into the OSIS reference
   space by the same lookup, applied per single-verse expansion.
3. When the anchor verse number exceeds the canonical chapter length
   under MACULA's OSIS, the row reflects a KJV-only verse
   subdivision and the adapter MUST consult the TVTMS rule_type
   field to map it back. KJV-only subdivisions resolve via rule_type
   markers documented in the STEPBible-TVTMS README; the adapter
   records the rule_type that fired on each row in the snapshot
   ledger so re-ingest produces the same per-row resolution map.
4. Rows the TVTMS mapping cannot resolve MUST be tagged with a
   quarantine flag rather than silently dropped, so the rejection
   shows up in the snapshot ledger and the triangle test detects the
   coverage gap rather than masking it as a clean ingest. The
   quarantine flag MUST be a CrossRef property named
   tvtms_quarantine of type bool, set true only on the unresolved
   rows, and absent on resolved rows so $pred_bool(x) returns false
   in the resolved case and the rejection count is the only field
   the verifier needs to scan.

Distinction from OPENBIBLE_CROSS_REF
====================================
Decision 5 keeps TSK and OpenBible-cross-refs on strictly separate
edge types. The OpenBible adapter in ingest/lexical/openbible.py
emits OPENBIBLE_CROSS_REF between Verse nodes with a votes int
property derived from the upstream community vote count. The TSK
adapter in this file emits CROSS_REF from CrossRef to Verse with the
source='TSK' and osis_target properties documented above. The two
edge types MUST never collapse onto a single relationship type,
because Pipeline 2 evidence ranking weights TSK editorial picks and
OpenBible community votes differently, and merging would lose the
provenance signal the evidence schema relies on. Edge counts for
OpenBible-cross-refs live in
tools/expected_counts.json edge_counts.OPENBIBLE_CROSS_REF tier B,
distinct from HAS_CROSS_REF.

Edge cases handled
==================
The adapter implements every edge case Decision 5 enumerates for TSK:

1. Range expansion: TSK references frequently span ranges such as
   'Ps.119.1-176' and the adapter MUST expand the range into one
   edge per verse in the range so the count-based acceptance query
   and Pipeline 2 graph-walk both see the true cardinality rather
   than a single packed edge with hidden multiplicity. The packed
   form remains on the CrossRef node in the xref_string property for
   audit; the expansion lands on the CROSS_REF edges as one edge per
   resolved single-verse osis_target.

2. KJV-only verse subdivisions: a verse number in TSK that exceeds
   the canonical chapter length under MACULA's OSIS reflects a
   KJV-only verse subdivision, and the adapter MUST consult the
   STEPBible-TVTMS rule_type to map it back into the OSIS reference
   space. Rows the TVTMS mapping cannot resolve MUST be tagged with
   the tvtms_quarantine boolean property rather than silently
   dropped, so the rejection count is auditable from the snapshot
   ledger and the verifier can assert the quarantine count is small
   relative to the total row count.

3. Provenance separation from OpenBible: TSK CROSS_REF edges and
   OpenBible OPENBIBLE_CROSS_REF edges MUST live on distinct
   relationship types per Decision 5 even when the anchor and target
   verse pair coincide. The adapter MUST NOT emit OPENBIBLE_CROSS_REF
   from this file, and the OpenBible adapter MUST NOT emit
   CROSS_REF, so a single MATCH on either type returns the
   provenance-pure edge set without joining through the source
   property.

Dependencies
============
Group order             : Group 5 (Cross-references and metadata) of
                          the Phase 02 dispatch order in
                          docs/implementation_phases/phase_02_lexical_ingest.md
                          bullet 18
Pre-existing nodes      : Verse nodes from Group 1 (OSHB-morphology
                          and MorphGNT-SBLGNT adapters populate the
                          OT and NT Verse nodes per Decision 15,
                          including the canonical osisID property
                          under the verse_osisID uniqueness
                          constraint; the CROSS_REF edge target join
                          walks v.osisID equal to the edge's
                          osis_target string)
Pre-existing rules      : VersificationRule nodes from Group 2
                          (STEPBible-TVTMS adapter emits one node
                          per parsed rule with rule_type, tradition_a,
                          ref_a, tradition_b, ref_b populated; this
                          adapter loads the rule set into memory at
                          ingest start and queries it row by row
                          rather than walking the graph at write
                          time)
Snapshot ledger         : the adapter records its per-row hash list,
                          the TVTMS rule_type that fired on each
                          resolved row, the quarantine flag count
                          for unresolved rows, and the per-token
                          range-expansion fan-out to the per-source
                          ledger consumed by
                          tools/verify_adapter_<X>.py and the
                          triangle-test runner in Phase D

Idempotency
===========
The adapter is idempotent through MERGE-by-stable-id on CrossRef.id
using the tsk:<book_num>.<chapter>.<verse>.<word_num> namespace, and
through MERGE-by-canonical-tuple on the CROSS_REF edge keyed by the
(from_id, to_id, source, osis_target) tuple so a re-ingest does not
multiply edges. The wipe contract in tools/wipe_lexical.py deletes
every node and relationship in the lexical Neo4j before re-ingest so
MERGE writes start from an empty store and the crossref_id
constraint rejects any second-write attempt for the same identifier.
The per-row SHA-256 hash list produced by the snapshot ledger MUST
recompute byte-for-byte across two runs over identical inputs per the
triangle test in Phase D.

Network isolation
=================
The adapter reads only the local cache under data/private/tskxref.txt.
No HTTP, DNS, or socket access happens at ingest time; the AST scan
tools/check_adapter_purity.py rejects any import of subprocess,
socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn,
posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes,
or dynamic __import__ in this file. The TVTMS rule set is loaded
from the on-disk artefact written by the STEPBible-TVTMS adapter in
Group 2; the load is a file read against the local Docker volume,
not a network call.

Acceptance Cypher (verbatim from
docs/implementation_phases/phase_02_lexical_ingest.md Group 5 bullet 18)
=======================================================================

    MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
    WHERE a.book_num IS NOT NULL
    WITH count(r) AS edges
    RETURN edges, edges > 0

The Phase D verifier additionally executes the Decision 5 Cypher
acceptance query from docs/SCHEMA_DECISIONS.md against the same
ingest, asserting the TSK edge count exceeds one hundred thousand
and every emitted CROSS_REF edge carries a non-null osis_target so
the range-expansion fan-out is exercised on the live ingest rather
than collapsing into single packed edges.
"""
