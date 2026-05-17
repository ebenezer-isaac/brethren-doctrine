"""ETCBC parallels lexical adapter docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-up commit by the implementer-impl
caste. This file freezes the upstream field contract, edge contract,
stable identifier strategy, license posture, and acceptance Cypher
block so the verifier caste can build conformance tests against a
stable specification.

============================================================
1. Scope and source slug
============================================================

Source slug `ETCBC-parallels`:
  tier A, record unit `parallel_edge`, expected count 8246, tolerance
  0, minimum 8246, maximum 8246. Tier A means the count is a
  deterministic feature count from the upstream frozen text-fabric
  module and any deviation fails the acceptance gate. The ETCBC
  parallels module ships one row per pre-derived parallel-passage
  edge with packed `source_node` and `target_and_value` fields, so
  the row total equals the upstream feature count exactly.

This adapter is edge-only. It emits zero new node labels. Every row
in the upstream module resolves to one outbound `PARALLEL_OF`
relationship between two pre-existing `BhsaWord` nodes that were
already written to the lexical store by the BHSA adapter
(`ingest/lexical/bhsa.py`, Group 4 step 14, Decision 3). The text
floor for parallels is therefore the `BhsaWord.id` keyspace; this
adapter never creates `BhsaWord` nodes and never updates `BhsaWord`
properties.

============================================================
2. Decision implemented (Decision 3)
============================================================

Decision 3: ETCBC syntax tree shape.
  The applicable Decision 3 sub-rule for this adapter is the
  ETCBC-parallels edge-case bullet: "ETCBC-parallels supplies pairs
  of text-fabric node identifiers in `source_node` and
  `target_and_value`, where `target_and_value` packs the target node
  and a similarity score in one string, and the adapter MUST split
  it on the delimiter before persisting a `PARALLEL_OF` edge with a
  `similarity` float property."

  The companion text-fabric node identifier rule from Decision 14
  also applies indirectly: BhsaWord identifiers are unique within
  the BHSA corpus, and that uniqueness is what makes the
  source-to-target MERGE on the relationship safe. The TFNode tuple
  constraint `(corpus, node_id)` in `graph/lexical.cypher` is
  enforced by the BHSA adapter; this adapter trusts that contract
  rather than re-asserting it.

============================================================
3. Upstream fields (Decision 3 ETCBC-parallels per-field table)
============================================================

The Decision 3 per-field predicate table for ETCBC-parallels lists
exactly two fields. Both are strings and both are checked with the
`$pred_string(x)` predicate from `tools/predicates_by_type.cypher`.

| Field             | Type   | Predicate         |
|-------------------|--------|-------------------|
| source_node       | string | $pred_string(x)   |
| target_and_value  | string | $pred_string(x)   |

Field semantics:

`source_node`:
  A text-fabric node identifier (integer encoded as string in the
  upstream module) pointing at a `BhsaWord` slot in the BHSA module
  that the parallels module was derived from. The adapter resolves
  this identifier by lookup against the `BhsaWord.id` keyspace
  written by the BHSA adapter. Rows whose `source_node` does not
  resolve to a known `BhsaWord` MUST be quarantined in the snapshot
  ledger (per the wider Phase 02 quarantine convention) rather than
  silently dropped, so the triangle test detects upstream drift.

`target_and_value`:
  A composite string packing the target text-fabric node identifier
  and a similarity score in a single field. The packing format is
  fixed by the upstream module and the adapter MUST split it before
  persistence; storing the packed string verbatim on the edge is
  forbidden because Pipeline 2 semantic-neighbor queries cannot
  filter by similarity without parsing strings at query time.

============================================================
4. Split rule for `target_and_value`
============================================================

Chosen delimiter: comma (`,`).

Format expected on every row:
  `target_and_value = "<target_node>,<similarity>"`

where `<target_node>` is a text-fabric node identifier (integer
encoded as string, decimal digits only) and `<similarity>` is a
float in the closed interval [0.0, 1.0] encoded in dotted decimal
notation. The adapter splits on the first comma only; any further
commas in the right-hand fragment cause the row to be quarantined
rather than truncated, because Decision 3 does not authorise lossy
parsing.

The two resulting fragments are coerced to their typed forms
before edge persistence:

  parts          = target_and_value.split(",", 1)
  target_node    = parts[0].strip()             # string keyspace lookup
  similarity_raw = parts[1].strip()             # float coercion candidate
  similarity     = float(similarity_raw)        # may raise ValueError

Rows that fail `float()` coercion or whose `similarity` value is
not finite (NaN, positive infinity, negative infinity) MUST be
quarantined rather than written. The `$pred_float(x)` predicate
from `tools/predicates_by_type.cypher` is the authoritative
non-empty check on the edge property and matches the same
finite-and-not-NaN rule:

  $pred_float(x) := x IS NOT NULL AND NOT (x <> x)
                    AND x < (1.0/0.0) AND x > -(1.0/0.0)

If a subsequent upstream revision switches the delimiter (for example
to a colon), the change MUST be reflected here under a
`[SCHEMA-REVISION]` commit prefix as required by Decision header
in `docs/SCHEMA_DECISIONS.md`; the adapter implementation MUST NOT
silently tolerate a different delimiter.

============================================================
5. Emitted edge
============================================================

Edge `PARALLEL_OF` (`BhsaWord` to `BhsaWord`):
  One edge per upstream row. Direction is from the `source_node`
  word to the target word resolved from `target_and_value`. The
  edge carries exactly one persisted property plus a `source`
  provenance slot:

  | Edge property | Type   | Predicate         |
  |---------------|--------|-------------------|
  | similarity    | float  | $pred_float(x)    |
  | source        | string | $pred_string(x)   |

  `similarity` is the float parsed from the right-hand fragment
  of `target_and_value` per section 4.

  `source` is the literal string `ETCBC-parallels`, recorded on
  the edge so Pipeline 2 provenance filters can isolate ETCBC
  parallels from any other parallel-edge source without joining
  on the endpoint nodes.

No other edge types are emitted. In particular this adapter does
NOT write `CONTAINS_PHRASE`, `CONTAINS_WORD`, `IN_VERSE`, or any
`TFNode`-related edges; those belong to the BHSA adapter (Group 4
step 14).

============================================================
6. Stable identifier strategy and MERGE pattern
============================================================

This adapter creates no new nodes, so there is no node-level
stable id to declare. Idempotency is achieved at the edge level
by MERGE on the ordered tuple `(source BhsaWord.id, target
BhsaWord.id)`. The Cypher MERGE pattern the implementer-impl
caste MUST use is:

    MATCH (a:BhsaWord {id: $source_id})
    MATCH (b:BhsaWord {id: $target_id})
    MERGE (a)-[r:PARALLEL_OF]->(b)
    ON CREATE SET r.similarity = $similarity,
                  r.source     = 'ETCBC-parallels'
    ON MATCH  SET r.similarity = $similarity,
                  r.source     = 'ETCBC-parallels'

The MATCH-then-MERGE form is mandatory; a single MERGE with
inline node patterns would create a sentinel `BhsaWord` node if
the lookup failed, which would silently corrupt the BHSA
keyspace. The adapter MUST treat a missing endpoint as a
quarantine event, not a node-creation event.

The `(source, target)` tuple is the idempotency key. Re-running
the adapter on identical source bytes produces zero new edges
and zero updated properties because the MERGE matches the
existing edge and `ON MATCH SET` writes the same values. The
triangle-test hash recompute in Phase D re-runs the adapter on
the same source bytes; the per-row presence vector (sorted list
of per-row SHA-256 hashes) must match byte-for-byte across two
runs, and the edge-level MERGE guarantees that property.

The `BhsaWord.id` constraint in `graph/lexical.cypher`
(`bhsa_word_id`) is the constraint that the MATCH halves of the
pattern above rely on. There is no dedicated index for
`PARALLEL_OF` because edge-only adapters do not warrant a graph
index; lookup performance is provided by the `bhsa_word_id`
uniqueness constraint on the endpoint identifiers.

============================================================
7. Acceptance Cypher (verbatim from phase_02 bullet 15)
============================================================

The Phase D verifier asserts the following query, copied verbatim
from `docs/implementation_phases/phase_02_lexical_ingest.md`
bullet 15, returns at least one row with `pairs > 0`:

    MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord)
    WHERE r.similarity IS NOT NULL
    WITH count(r) AS pairs
    RETURN pairs, pairs > 0

In addition, the Decision 3 acceptance query in
`docs/SCHEMA_DECISIONS.md` is unaffected by this adapter because
it walks `BhsaClause` to `BhsaPhrase` to `BhsaWord`; the
`PARALLEL_OF` edges this adapter writes are orthogonal to that
containment hierarchy.

============================================================
8. Edge cases (from Decision 3 ETCBC-parallels bullet)
============================================================

Case A: malformed `target_and_value`.
  Rows whose `target_and_value` field does not split into exactly
  two fragments on the comma delimiter (zero commas or two or
  more commas) MUST be quarantined. The adapter MUST NOT fall
  back to a heuristic split, MUST NOT take the first or last
  fragment alone, and MUST NOT default the similarity to a
  sentinel value. Decision 3 records the split rule as binding.

Case B: non-finite similarity.
  Rows whose right-hand fragment parses to NaN, positive
  infinity, or negative infinity MUST be quarantined. The
  `$pred_float(x)` predicate in
  `tools/predicates_by_type.cypher` rejects those values at the
  predicate level, so persisting them would surface as a false
  positive in the acceptance ratio and fail the Phase D verifier.

Case C: dangling endpoint.
  Rows whose `source_node` or resolved target node does not match
  any existing `BhsaWord.id` MUST be quarantined. The adapter MUST
  NOT create a sentinel `BhsaWord` to bridge the gap. The
  Decision 3 syntactic-context bundle requires that every
  `BhsaWord` carry its full upstream property set, and a sentinel
  node would violate that contract.

Case D: self-parallel.
  Rows where the resolved target identifier equals the source
  identifier MUST still be persisted as a `(a)-[:PARALLEL_OF]->(a)`
  self-loop, because the upstream module occasionally records such
  edges as a degenerate placeholder. Pipeline 2 consumers MAY
  filter self-loops at query time; the ingest layer is not the
  place to drop them.

============================================================
9. License and redistribute (Decision 14)
============================================================

Per Decision 14, the adapter does NOT register a new `Source`
node because Source nodes are registered by the corpus owner.
The corpus owner for ETCBC-parallels is the BHSA adapter, which
already writes a `Source` node with slug aligned to the upstream
text-fabric module identifier. ETCBC-parallels itself ships under
the same `CC-BY-NC-4.0` license as ETCBC-BHSA (the upstream
LICENSE file is shared across the ETCBC text-fabric modules), and
Decision 14 records `redistribute = false` for that license slug.

If a downstream Pipeline 2 evidence file cites a `PARALLEL_OF`
edge, the citation slug is `ETCBC-parallels` per the source slug
table in `docs/phase_prompts/pipeline2_verdict.md`. The
implementer-impl caste commit that adds the runnable body MUST
record the slug on the edge `source` property for every emitted
relationship; section 5 above codifies the property contract.

============================================================
10. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md`
bullet 15, this adapter runs in Group 4 after BHSA Group 4 step
14 has written the `BhsaWord` nodes the edges target. The join
key is the text-fabric node identifier carried on `BhsaWord.id`;
the BHSA adapter MUST complete before this adapter begins so that
the MATCH halves of the MERGE pattern in section 6 resolve
without quarantining valid rows.

The wipe contract in `tools/wipe_lexical.py` deletes every node
and relationship in the lexical Neo4j before re-ingest, so MERGE
writes start from an empty store and the BHSA adapter populates
`BhsaWord` nodes before this adapter populates the parallels
edges over them.

============================================================
11. Network isolation and AST purity
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md`,
adapter dry-runs execute inside Docker with `--network=none`,
which forbids any HTTP, DNS, or socket access during ingest. The
AST scan `tools/check_adapter_purity.py` rejects any adapter that
imports `subprocess`, `socket`, `httpx`, `requests`, `urllib`,
`aiohttp`, `mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`,
or dynamic `__import__`. The implementer-impl caste commit that
adds the runnable adapter body MUST satisfy that purity scan; the
local text-fabric module cache under
`C:/Users/Ebenezer/text-fabric-data/github/ETCBC/parallels/`
is the only input.

============================================================
12. Idempotency
============================================================

MERGE on the `(source BhsaWord.id, target BhsaWord.id)` tuple
per section 6 is the idempotency guarantee. Re-running the
adapter on identical source bytes produces zero new edges and
zero new nodes; `ON MATCH SET` re-writes `similarity` and
`source` to the same values, leaving the graph byte-identical.
The per-row presence vector for the triangle-test in Phase D
hashes each upstream row by SHA-256 over the canonical bytes of
`(source_node, target_node, similarity)` after the split rule
in section 4; the sorted vector must match byte-for-byte across
two runs over identical inputs.
"""
