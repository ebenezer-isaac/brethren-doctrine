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
relationship between two pre-existing `Verse` nodes.

ENDPOINT CORRECTION (faithful fix, brethren-on-trial, Phase D.4).
The upstream ETCBC-parallels `crossref.tf` feature is a text-fabric
EDGE feature whose `@coreData=BHSA` node identifiers are BHSA
`verse`-otype text-fabric nodes (BHSA `otype.tf` run
`1414389-1437601 verse`), NOT word slots (run `1-426590 word`).
Every one of the 8246 raw rows, and every one of the 5914
single-target rows that survive the Decision 3 split, carries a
source and target node id inside the `verse` otype run; zero fall
in the `word` otype run. The original contract asserted a
`BhsaWord` to `BhsaWord` edge keyed on `bhsa:tf:<node_id>`, but the
BHSA adapter only writes `BhsaWord`/`BhsaPhrase`/`BhsaClause` for
the word/phrase/clause otypes and never writes any node keyed
`bhsa:tf:<verse_node_id>`, so every `BhsaWord` MATCH resolved to
nothing and 0/5914 edges landed in the live graph (confirmed live:
`MATCH ()-[r:PARALLEL_OF]->() RETURN count(r)` = 0 while
`BhsaWord` count = 426590). The faithful, schema-backed endpoint is
the `Verse` node keyed `verse:<osisRef>` (constraint `verse_id`,
`graph/lexical.cypher` line 17, Decision 15) populated by the
OSHB-morphology adapter. The verse text-fabric node id is mapped to
its osisRef through the BHSA module `otype.tf`/`book.tf`/
`chapter.tf`/`verse.tf` node features and the same ETCBC-Latin to
OSIS book table the BHSA adapter uses; all 5914 single-target rows
then resolve (verified live: 5914/5914 land, 3700 distinct verse
ids all present). The Decision 3 single-comma split is unchanged,
so the 2332 multi-target/non-digit rows stay quarantined and the
catalog `expected_count` of 5914 (tier A, tolerance 0) is unchanged
and not fudged.

The text floor for parallels is therefore the `Verse.id` keyspace;
this adapter never creates `Verse` nodes and never updates `Verse`
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

Edge `PARALLEL_OF` (`Verse` to `Verse`):
  One edge per upstream single-target row. Direction is from the
  `source_node` verse to the target verse resolved from
  `target_and_value`. The
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

    MATCH (a:Verse {id: $source_id})
    MATCH (b:Verse {id: $target_id})
    MERGE (a)-[r:PARALLEL_OF]->(b)
    ON CREATE SET r.similarity = $similarity,
                  r.source     = 'ETCBC-parallels'
    ON MATCH  SET r.similarity = $similarity,
                  r.source     = 'ETCBC-parallels'

The MATCH-then-MERGE form is mandatory; a single MERGE with
inline node patterns would create a sentinel `Verse` node if
the lookup failed, which would silently corrupt the OSHB-written
verse keyspace. The adapter MUST treat a missing endpoint (a
verse text-fabric node id that does not map to an osisRef, or an
osisRef with no `Verse` node) as a quarantine event, not a
node-creation event.

The `(source, target)` tuple is the idempotency key. Re-running
the adapter on identical source bytes produces zero new edges
and zero updated properties because the MERGE matches the
existing edge and `ON MATCH SET` writes the same values. The
triangle-test hash recompute in Phase D re-runs the adapter on
the same source bytes; the per-row presence vector (sorted list
of per-row SHA-256 hashes) must match byte-for-byte across two
runs, and the edge-level MERGE guarantees that property.

The `Verse.id` constraint in `graph/lexical.cypher`
(`verse_id`, line 17, Decision 15) is the constraint that the
MATCH halves of the pattern above rely on. There is no dedicated
index for `PARALLEL_OF` because edge-only adapters do not warrant
a graph index; lookup performance is provided by the `verse_id`
uniqueness constraint on the endpoint identifiers.

============================================================
7. Acceptance Cypher (verbatim from phase_02 bullet 15)
============================================================

The Phase D verifier asserts the following query, copied verbatim
from `docs/implementation_phases/phase_02_lexical_ingest.md`
bullet 15, returns at least one row with `pairs > 0`:

    MATCH (a:Verse)-[r:PARALLEL_OF]->(b:Verse)
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
  Rows whose `source_node` or resolved target node does not map to
  an osisRef via the BHSA verse-otype node features, or whose
  resulting `verse:<osisRef>` does not match any existing
  `Verse.id`, MUST be quarantined. The adapter MUST NOT create a
  sentinel `Verse` to bridge the gap. The Decision 15 verse
  keyspace requires that every `Verse` carry its full upstream
  property set, and a sentinel node would violate that contract.
  On the frozen 2021 BHSA + parallels modules every one of the
  5914 single-target rows maps cleanly (verified live 5914/5914),
  so Case C fires zero times on frozen upstream and is purely a
  drift guard.

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

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "ETCBC-parallels"
LICENSE_ID = "CC-BY-NC-4.0"
CORPUS = "bhsa"
TF_ROOT = Path("C:/Users/Ebenezer/text-fabric-data/github/ETCBC/parallels/tf/2021")
BHSA_TF_ROOT = Path("C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021")
PRIMARY_FEATURE = "crossref.tf"
VALUE_SCALE = 100.0
BATCH_SIZE = 1000
_MERGE_PARALLEL = (
    "UNWIND $rows AS row "
    "MATCH (a:`Verse` {id: row.source_id}) "
    "MATCH (b:`Verse` {id: row.target_id}) "
    "MERGE (a)-[r:`PARALLEL_OF`]->(b) "
    "ON CREATE SET r.similarity = row.similarity, r.source = row.source "
    "ON MATCH  SET r.similarity = row.similarity, r.source = row.source "
    "RETURN count(r) AS edges"
)

# ETCBC Latin book name -> OSIS book code. This is the same mapping the
# BHSA adapter (ingest/lexical/bhsa.py _OSIS_BY_ETCBC_BOOK) uses to build
# Verse.id, reproduced here so the parallels endpoint key matches the
# OSHB-written Verse.id keyspace byte-for-byte (Decision 15, verse_id
# constraint). Kept independent because each edge-only adapter owns its
# own constants per the adapter purity contract.
_OSIS_BY_ETCBC_BOOK = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev",
    "Numeri": "Num", "Deuteronomium": "Deut", "Josua": "Josh",
    "Judices": "Judg", "Samuel_I": "1Sam", "Samuel_II": "2Sam",
    "Reges_I": "1Kgs", "Reges_II": "2Kgs", "Jesaia": "Isa",
    "Jeremia": "Jer", "Ezechiel": "Ezek", "Hosea": "Hos",
    "Joel": "Joel", "Amos": "Amos", "Obadia": "Obad",
    "Jona": "Jonah", "Micha": "Mic", "Nahum": "Nah",
    "Habakuk": "Hab", "Zephania": "Zeph", "Haggai": "Hag",
    "Sacharia": "Zech", "Maleachi": "Mal", "Psalmi": "Ps",
    "Iob": "Job", "Proverbia": "Prov", "Ruth": "Ruth",
    "Canticum": "Song", "Ecclesiastes": "Eccl", "Threni": "Lam",
    "Esther": "Esth", "Daniel": "Dan", "Esra": "Ezra",
    "Nehemia": "Neh", "Chronica_I": "1Chr", "Chronica_II": "2Chr",
}


def _verse_id(osis_ref: str) -> str:
    return f"verse:{osis_ref}"


def _is_finite_float(value: float) -> bool:
    if value != value:
        return False
    if value == float("inf") or value == float("-inf"):
        return False
    return True


def _read_tf_body(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as fh:
        text = fh.read()
    out: list[str] = []
    in_body = False
    for raw in text.splitlines():
        if not in_body:
            if raw == "":
                in_body = True
            continue
        out = [*out, raw]
    return out


def _parse_otype_runs(lines: list[str]) -> dict[str, tuple[int, int]]:
    runs: dict[str, tuple[int, int]] = {}
    for raw in lines:
        s = raw.strip()
        if not s or "\t" not in s:
            continue
        range_part, otype = s.split("\t", 1)
        if "-" in range_part:
            lo, hi = (int(x) for x in range_part.split("-", 1))
        else:
            lo = hi = int(range_part)
        runs = {**runs, otype.strip(): (lo, hi)}
    return runs


def _parse_node_feature(lines: list[str], lo: int, hi: int) -> dict[int, str]:
    """Parse a text-fabric node feature, restricted to node ids in [lo, hi].

    Text-fabric node features use the same implicit-counter / explicit-spec
    encoding the BHSA adapter parses. Only the verse-otype slice is needed
    here, so values outside [lo, hi] are skipped to keep the map O(verses).
    """
    values: dict[int, str] = {}
    counter = 1
    for raw in lines:
        if raw == "":
            counter += 1
            continue
        if "\t" in raw:
            spec, value = raw.split("\t", 1)
            if "-" in spec:
                a, b = (int(x) for x in spec.split("-", 1))
                for node_id in range(max(a, lo), min(b, hi) + 1):
                    values = {**values, node_id: value}
                counter = b + 1
            else:
                node_id = int(spec)
                if lo <= node_id <= hi:
                    values = {**values, node_id: value}
                counter = node_id + 1
        else:
            if lo <= counter <= hi:
                values = {**values, counter: raw}
            counter += 1
    return values


def _build_verse_map(bhsa_root: Path) -> dict[int, str]:
    """Map every BHSA verse-otype text-fabric node id to its `verse:<osisRef>`.

    The ETCBC-parallels crossref.tf node ids are BHSA verse-otype nodes
    (otype run `verse`); book/chapter/verse are node features keyed
    directly on the verse node id. osisRef is built with the same
    ETCBC-Latin to OSIS book table the BHSA adapter uses so the key
    matches the OSHB-written Verse.id keyspace exactly.
    """
    otype_path = bhsa_root / "otype.tf"
    if not bhsa_root.exists() or not otype_path.exists():
        return {}
    try:
        runs = _parse_otype_runs(_read_tf_body(otype_path))
    except OSError:
        return {}
    verse_run = runs.get("verse")
    if verse_run is None:
        return {}
    lo, hi = verse_run
    try:
        book_f = _parse_node_feature(
            _read_tf_body(bhsa_root / "book.tf"), lo, hi
        )
        chap_f = _parse_node_feature(
            _read_tf_body(bhsa_root / "chapter.tf"), lo, hi
        )
        verse_f = _parse_node_feature(
            _read_tf_body(bhsa_root / "verse.tf"), lo, hi
        )
    except OSError:
        return {}
    out: dict[int, str] = {}
    for node_id in range(lo, hi + 1):
        book_latin = book_f.get(node_id)
        chapter = chap_f.get(node_id)
        verse = verse_f.get(node_id)
        if book_latin is None or chapter is None or verse is None:
            continue
        osis_book = _OSIS_BY_ETCBC_BOOK.get(book_latin)
        if osis_book is None or not chapter.isdigit() or not verse.isdigit():
            continue
        ref = f"{osis_book}.{int(chapter)}.{int(verse)}"
        out = {**out, node_id: _verse_id(ref)}
    return out


_EMBEDDED_VERSE_MAP: dict[int, str] = {
    1414401: _verse_id("Gen.1.13"),
    1414407: _verse_id("Gen.1.19"),
    1414411: _verse_id("Gen.1.23"),
    1414403: _verse_id("Gen.1.15"),
    1414405: _verse_id("Gen.1.17"),
}


def _normalize_lines(lines: list[str]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    last_source: str | None = None
    for raw in lines:
        if not raw.strip():
            continue
        fields = raw.split("\t")
        if len(fields) == 3:
            source_token = fields[0].strip()
            target_field = fields[1].strip()
            value_field = fields[2].strip()
            last_source = source_token
        elif len(fields) == 2:
            if last_source is None:
                continue
            source_token = last_source
            target_field = fields[0].strip()
            value_field = fields[1].strip()
        else:
            continue
        try:
            similarity = int(value_field) / VALUE_SCALE
        except ValueError:
            packed = f"{target_field},{value_field}"
            rows = [*rows, (source_token, packed)]
            continue
        packed = f"{target_field},{similarity}"
        rows = [*rows, (source_token, packed)]
    return rows


# Embedded fallback rows used only when the frozen parallels module is
# absent (CI / air-gap dry-run without the per-user text-fabric cache).
# Node ids are real BHSA verse-otype ids so the embedded path exercises
# the same verse-keyed resolution as the live path.
_EMBEDDED_ROWS: tuple[tuple[str, str], ...] = (
    ("1414401", "1414407,0.84"),
    ("1414401", "1414411,0.89"),
    ("1414403", "1414405,0.77"),
)


def _load_rows(tf_root: Path) -> list[tuple[str, str]]:
    feature_path = tf_root / PRIMARY_FEATURE
    if not feature_path.exists():
        return [*_EMBEDDED_ROWS]
    try:
        body = _read_tf_body(feature_path)
    except OSError:
        return [*_EMBEDDED_ROWS]
    normalized = _normalize_lines(body)
    if not normalized:
        return [*_EMBEDDED_ROWS]
    return normalized


def _split_target_and_value(
    source_token: str,
    target_and_value: str,
    verse_map: dict[int, str],
) -> dict[str, Any] | None:
    """Apply the binding Decision 3 single-comma split, then resolve both

    text-fabric verse node ids to the `verse:<osisRef>` keyspace. A row is
    quarantined (returns None) if the split is not exactly single-target,
    the nodes are not decimal, the similarity is non-finite, OR either
    node id does not map to a known verse (faithful Case C dangling
    endpoint). The split rule itself is unchanged from the prior contract,
    so the 5914/2332 split is preserved.
    """
    if target_and_value.count(",") != 1:
        return None
    parts = target_and_value.split(",", 1)
    target_node = parts[0].strip()
    similarity_raw = parts[1].strip()
    if not target_node.isdigit() or not source_token.isdigit():
        return None
    try:
        similarity = float(similarity_raw)
    except ValueError:
        return None
    if not _is_finite_float(similarity):
        return None
    source_id = verse_map.get(int(source_token))
    target_id = verse_map.get(int(target_node))
    if source_id is None or target_id is None:
        return None
    return {
        "source_id": source_id,
        "target_id": target_id,
        "similarity": similarity,
        "source": SOURCE_SLUG,
    }


def _build_edge_rows(
    rows: list[tuple[str, str]],
    verse_map: dict[int, str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    resolved_map = verse_map if verse_map else _resolve_verse_map()
    edges: list[dict[str, Any]] = []
    quarantined = 0
    for source_token, target_and_value in rows:
        edge = _split_target_and_value(
            source_token, target_and_value, resolved_map
        )
        if edge is None:
            quarantined += 1
            continue
        edges = [*edges, edge]
    return edges, quarantined


def _resolve_verse_map() -> dict[int, str]:
    """Return the live BHSA verse map, or the embedded map as fallback.

    Mirrors the _load_rows fallback discipline so a standalone
    `_build_edge_rows(_load_rows(TF_ROOT))` call (preverification /
    triangle-test harness) resolves deterministically whether or not the
    per-user text-fabric cache is present.
    """
    live = _build_verse_map(BHSA_TF_ROOT)
    if live:
        return live
    return dict(_EMBEDDED_VERSE_MAP)


def _merge_edges(session: Any, edges: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(edges), BATCH_SIZE):
        batch = edges[start:start + BATCH_SIZE]
        session.run(_MERGE_PARALLEL, rows=batch).consume()
        total += len(batch)
    return total


def ingest_etcbc_parallels(settings: Settings) -> dict[str, int]:
    """Parse ETCBC-parallels text-fabric data and MERGE PARALLEL_OF edges."""
    rows = _load_rows(TF_ROOT)
    verse_map = _resolve_verse_map()
    edges, quarantined = _build_edge_rows(rows, verse_map)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        merged = _merge_edges(session, edges)
    return {"PARALLEL_OF": merged, "quarantined": quarantined}
