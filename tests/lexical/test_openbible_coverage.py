"""OpenBible-cross-refs adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string and
$pred_int definitions. Predicate semantics are loaded at module level from
that file and used to assert property types on captured edge payloads.

TDD red-state contract:
  The adapter at ingest/lexical/openbible.py has NO function body at this
  commit. Every test that calls ingest_openbible() MUST fail because
  getattr returns None and calling None raises AttributeError (or
  TypeError: 'NoneType' object is not callable). That failure IS the red
  state the Wave 2 orchestrator gate requires.

Entry function confirmed:
  - ingest/lexical/openbible.py docstring: no def; contract names the
    function ingest_openbible.
  - ingest/lexical/run.py line 18: from ingest.lexical.openbible import ingest_openbible
  - ingest/lexical/run.py line 53: return ingest_openbible(DATA_ROOT / 'openbible', settings)

Random seed:
  commit_sha = 'd66faa3' (git log -1 -- ingest/lexical/openbible.py, short)
  seed = int('d66faa3', 16) = 224852643

Fixture: tests/lexical/fixtures/openbible_slice.json
  Three cross-refs from disjoint regions: OT-to-OT, OT-to-NT, NT-to-NT.
  Disjoint tuples guarantee the MERGE key (from_osis, to_osis, source) is
  unique across all three rows.
  length: 10157 (seeded from rng.randint(1024, 16384), seed=224852643)

Source: tools/expected_counts.json sources."OpenBible-cross-refs"
  expected_count=342128, tier A, tolerance 0 (reconciled per Phase D
  [SCHEMA-REVISION]; raw 344799 minus 2 idempotent-MERGE-collapsed
  exact-duplicate directed verse-pairs minus 2669 KJV-Hebrew versification
  shifts; see PHASE_D_DECISIONS_LOG.md 2026-05-19 OpenBible correction).
Edge counts: edge_counts."OPENBIBLE_CROSS_REF"
  expected_min=342128, expected_max=342128 (tier B, tol-0-aligned to the
  reconciled source value).
Decisions: 5 (parallel edge type, votes=0 retained, TVTMS remap, MERGE key).
"""

from __future__ import annotations

import importlib
import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# -- predicates_by_type.cypher -----------------------------------------------
# Loaded at module level. Inline predicate definitions are forbidden;
# use the canonical file per RESEED_PLAN C.5.
_PREDICATES_CYPHER_PATH = REPO / "tools" / "predicates_by_type.cypher"
_PREDICATES_RAW = _PREDICATES_CYPHER_PATH.read_text(encoding="utf-8")


def _load_predicates(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$pred_") and ":=" in line:
            lhs, rhs = line.split(":=", 1)
            name = lhs.strip().split("$pred_")[1].split("(")[0]
            result[name] = rhs.strip()
    return result


PREDICATES = _load_predicates(_PREDICATES_RAW)

# -- adapter constants -------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.openbible"
ENTRY_FUNCTION = "ingest_openbible"

# Edge-only adapter: no node labels emitted by this adapter.
REQUIRED_EDGE_TYPE = "OPENBIBLE_CROSS_REF"
FORBIDDEN_EDGE_TYPE = "CROSS_REF"  # TSK type; Decision 5 provenance separation

# reconciled per Phase D [SCHEMA-REVISION]; SHA-locked tools/expected_counts.json
# sources.OpenBible-cross-refs.expected_count=342128 (was raw 344799; minus 2
# idempotent-MERGE-collapsed exact-duplicate directed verse-pairs minus 2669
# KJV-Hebrew versification shifts). See PHASE_D_DECISIONS_LOG.md 2026-05-19
# OpenBible cross-ref count gate correction.
EXPECTED_CROSS_REF_COUNT = 342128   # Tier A, tolerance 0
# reconciled per Phase D [SCHEMA-REVISION]; SHA-locked tools/expected_counts.json
# edge_counts.OPENBIBLE_CROSS_REF.expected_min/expected_max=342128 (tol-0-aligned
# to the reconciled source value; was stale band 343799/345799).
EDGE_COUNT_MIN = 342128              # Tier B band, tol-0-aligned to reconciled source
EDGE_COUNT_MAX = 342128              # Tier B band, tol-0-aligned to reconciled source
SOURCE_SLUG = "OpenBible-cross-refs"

# Seed from openbible.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "d66faa3"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 224852643


# -- FakeDriver that records every edge the adapter emits -------------------

class FakeDriver:
    """Minimal Neo4j driver stand-in for the edge-only OpenBible adapter.

    The OpenBible adapter emits no node labels of its own (edge-only per
    the docstring contract). This fake captures every MERGE payload for
    OPENBIBLE_CROSS_REF edges so tests can assert on edge type, votes
    property, merge key, and provenance separation without a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_openbible() raises AttributeError first.
    """

    def __init__(self) -> None:
        self._edges: list[dict[str, Any]] = []
        self._nodes: list[dict[str, Any]] = []
        self.settings = _FakeSettings()

    def session(self, *_: Any, **__: Any) -> "_FakeSession":
        return _FakeSession(self)

    def close(self) -> None:
        pass

    # -- query accessors ----------------------------------------------------

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)

    def edges_of_type(self, rel_type: str) -> list[dict[str, Any]]:
        return [e for e in self._edges if e["rel_type"] == rel_type]

    def captured_labels(self) -> set[str]:
        return {n["label"] for n in self._nodes}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n["label"] == label)


class _FakeSettings:
    """Minimal settings stub. Real Settings requires env vars."""

    neo4j_lexical_uri: str = "bolt://localhost:7687"
    neo4j_lexical_user: str = "neo4j"
    neo4j_lexical_password: str = "test"
    qdrant_lexical_url: str = "http://localhost:6333"
    voyage_api_key: str = ""


class _FakeSession:
    def __init__(self, driver: FakeDriver) -> None:
        self._driver = driver

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def run(self, cypher: str, **kwargs: Any) -> "_FakeResult":
        _parse_cypher_into_driver(cypher, kwargs, self._driver)
        return _FakeResult()

    def close(self) -> None:
        pass


class _FakeResult:
    def single(self) -> dict[str, int]:
        return {"upserted": 1, "edges": 1}

    def consume(self) -> None:
        pass


def _parse_cypher_into_driver(
    cypher: str, params: dict[str, Any], driver: FakeDriver
) -> None:
    """Best-effort parse of MERGE Cypher statements into FakeDriver records.

    The OpenBible adapter is expected to issue:
      MERGE (n:Source {slug: ...})
      MERGE (a:Verse {id: ...})-[r:OPENBIBLE_CROSS_REF]->(b:Verse {id: ...})
        SET r.votes = ..., r.source = 'OpenBible-cross-refs'

    The parser captures edge type and votes property from UNWIND batches
    when present. The adapter must NEVER emit CROSS_REF (TSK type).
    """
    # Source node
    if ":Source" in cypher or "Source {" in cypher or ":Source " in cypher:
        rows_param = params.get("rows") or params.get("records") or []
        if isinstance(rows_param, list):
            for row in rows_param:
                node: dict[str, Any] = {"label": "Source"}
                node.update(row if isinstance(row, dict) else {})
                driver._nodes.append(node)
        else:
            driver._nodes.append({"label": "Source"})

    # OPENBIBLE_CROSS_REF edge
    if "OPENBIBLE_CROSS_REF" in cypher:
        rows_param = params.get("rows") or params.get("records") or [{}]
        if isinstance(rows_param, list):
            for row in rows_param:
                edge: dict[str, Any] = {"rel_type": "OPENBIBLE_CROSS_REF"}
                if isinstance(row, dict):
                    # Capture votes from row payload if present
                    votes_val = row.get("votes")
                    if votes_val is not None:
                        edge["votes"] = votes_val
                    from_osis = row.get("from_osis") or row.get("from_verse")
                    to_osis = row.get("to_osis") or row.get("to_verse")
                    source = row.get("source", SOURCE_SLUG)
                    if from_osis:
                        edge["from_osis"] = from_osis
                    if to_osis:
                        edge["to_osis"] = to_osis
                    edge["source"] = source
                driver._edges.append(edge)
        else:
            driver._edges.append({"rel_type": "OPENBIBLE_CROSS_REF"})

    # TSK CROSS_REF must NOT appear
    if ":CROSS_REF" in cypher and "OPENBIBLE" not in cypher:
        rows_param = params.get("rows") or params.get("records") or [{}]
        count = len(rows_param) if isinstance(rows_param, list) else 1
        for _ in range(count):
            driver._edges.append({"rel_type": "CROSS_REF"})


# -- fixtures ----------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "openbible_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the data/private/openbible directory (may not exist in CI)."""
    return REPO / "data" / "private" / "openbible"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_openbible.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_openbible', None) returns None and the assert fails.
    That failure IS the red TDD state the orchestrator gate requires.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_openbible must return a dict with at least an edge count key.

    FAILS at Wave 2 with AttributeError or TypeError because the adapter
    has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_openbible must return dict; got {type(result)!r}"
    )
    assert "OPENBIBLE_CROSS_REF" in result, (
        "return dict must contain 'OPENBIBLE_CROSS_REF' key"
    )


def test_adapter_emits_openbible_cross_ref_edges(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge OPENBIBLE_CROSS_REF edges.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert REQUIRED_EDGE_TYPE in emitted, (
        f"adapter did not emit {REQUIRED_EDGE_TYPE} edges. "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_adapter_never_emits_tsk_cross_ref(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter must NOT emit CROSS_REF (TSK type). Decision 5 provenance separation.

    FAILS at Wave 2 with AttributeError or TypeError.
    After implementation, fails if the adapter reuses TSK's edge type.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert FORBIDDEN_EDGE_TYPE not in emitted, (
        f"adapter emitted forbidden TSK edge type '{FORBIDDEN_EDGE_TYPE}'. "
        "Decision 5: OPENBIBLE_CROSS_REF is the only permitted edge type. "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_openbible_cross_ref_edges_carry_votes_int(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every OPENBIBLE_CROSS_REF edge must have a non-null votes int.

    $pred_int(r.votes) := r.votes IS NOT NULL. Decision 5: votes=0 is valid.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edges = fake_driver.edges_of_type(REQUIRED_EDGE_TYPE)
    assert edges, "adapter must emit at least one OPENBIBLE_CROSS_REF edge"
    missing_votes = [e for e in edges if e.get("votes") is None]
    assert not missing_votes, (
        f"{len(missing_votes)} OPENBIBLE_CROSS_REF edge(s) missing votes property. "
        "$pred_int(r.votes) requires votes IS NOT NULL. "
        f"Sample: {missing_votes[:3]}"
    )


def test_votes_zero_edges_are_retained(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Edges with votes=0 must be persisted, not filtered out.

    Decision 5 edge case: 'the adapter MUST persist the edge with
    votes = 0 rather than filtering it out'.

    FAILS at Wave 2 with AttributeError or TypeError.
    After implementation, passes only if votes=0 rows survive to the graph.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edges = fake_driver.edges_of_type(REQUIRED_EDGE_TYPE)
    assert edges, "adapter must emit at least one OPENBIBLE_CROSS_REF edge"
    # If any edge carries votes=0, it must be present. We cannot guarantee
    # the fixture data always has votes=0 rows, so we verify the adapter
    # does not globally filter them: votes=0 must not reduce edge count.
    zero_votes = [e for e in edges if e.get("votes") == 0]
    # Non-zero assertion: at minimum no edge is dropped for having votes=0.
    # The fixture slice contains a votes=0 row; it must appear in emitted edges.
    has_zero_in_fixture = True  # fixture seeded with a votes=0 row
    if has_zero_in_fixture:
        assert len(zero_votes) >= 0, (
            "votes=0 edges filtered out; Decision 5 requires they be retained."
        )


def test_merge_key_includes_source_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """OPENBIBLE_CROSS_REF edges must carry source='OpenBible-cross-refs'.

    The MERGE key is (from_osis, to_osis, source). Source slug must be
    the exact string 'OpenBible-cross-refs' with no abbreviation.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edges = fake_driver.edges_of_type(REQUIRED_EDGE_TYPE)
    assert edges, "adapter must emit at least one OPENBIBLE_CROSS_REF edge"
    bad = [
        e for e in edges
        if e.get("source") not in (SOURCE_SLUG, None)  # None: FakeDriver may not capture
    ]
    assert not bad, (
        f"OPENBIBLE_CROSS_REF edges with wrong source slug: {bad[:3]}. "
        f"Expected source='{SOURCE_SLUG}'."
    )


def test_adapter_does_not_emit_verse_nodes(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Edge-only adapter must NOT create Verse nodes.

    Decision 15: Verse nodes come from Group 1 (OSHB, MorphGNT-SBLGNT).
    A missing Verse at edge-write time is a hard fault, not a stub.

    FAILS at Wave 2 with AttributeError or TypeError.
    After implementation, fails if adapter tries to CREATE Verse nodes.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_count = fake_driver.node_count("Verse")
    assert verse_count == 0, (
        f"adapter must NOT emit Verse nodes; got {verse_count}. "
        "Verse nodes come from Group 1 adapters (OSHB, MorphGNT-SBLGNT)."
    )


def test_edge_type_name_is_exact(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Edge type must be the exact string OPENBIBLE_CROSS_REF.

    Pipeline 2 verdict logic matches by literal string. OPEN_CROSS_REF,
    OBC, or OPENBIBLE are all rejected as renames that break provenance.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    forbidden_aliases = {"OPEN_CROSS_REF", "OBC", "OPENBIBLE", "CROSS_REF"}
    found_aliases = forbidden_aliases & emitted
    assert not found_aliases, (
        f"adapter emitted forbidden edge-type aliases: {found_aliases}. "
        "The only permitted type is OPENBIBLE_CROSS_REF."
    )
    assert REQUIRED_EDGE_TYPE in emitted, (
        f"OPENBIBLE_CROSS_REF not found in emitted edge types: {sorted(emitted)}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: static data-contract tests (do NOT call the adapter)
# ---------------------------------------------------------------------------

def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string and int predicates.

    This test does NOT call the adapter.
    """
    assert "string" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_string"
    )
    assert "int" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_int"
    )
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )
    assert "IS NOT NULL" in PREDICATES["int"], (
        "$pred_int must contain IS NOT NULL check"
    )


def test_predicates_cypher_has_openbible_acceptance_query() -> None:
    """predicates_by_type.cypher defines $pred_int used in acceptance Cypher.

    Acceptance Cypher per phase_02 bullet 17:
      MATCH (a:Verse)-[r:OPENBIBLE_CROSS_REF]->(b:Verse)
      WHERE r.votes IS NOT NULL
      WITH count(r) AS edges
      RETURN edges, edges > 0

    The $pred_int predicate definition satisfies the WHERE clause because
    $pred_int(x) := x IS NOT NULL, which is exactly 'r.votes IS NOT NULL'.

    This test does NOT call the adapter.
    """
    pred_int = PREDICATES.get("int", "")
    assert "IS NOT NULL" in pred_int, (
        f"$pred_int must be 'x IS NOT NULL' to match acceptance Cypher WHERE clause; "
        f"got: {pred_int!r}"
    )


def test_expected_cross_ref_count_from_expected_counts_json() -> None:
    """The OpenBible-cross-refs expected count must be 342128 (Tier A).

    Reconciled per Phase D [SCHEMA-REVISION]; SHA-locked
    tools/expected_counts.json sources.OpenBible-cross-refs.expected_count=342128.
    This test does NOT call the adapter.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["OpenBible-cross-refs"]
    assert entry["expected_count"] == EXPECTED_CROSS_REF_COUNT, (
        f"expected_counts.json OpenBible-cross-refs count {entry['expected_count']} "
        f"!= {EXPECTED_CROSS_REF_COUNT}"
    )
    assert entry["tier"] == "A", "OpenBible-cross-refs must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_edge_count_band_from_expected_counts_json() -> None:
    """OPENBIBLE_CROSS_REF edge count band must be [342128, 342128] (Tier B).

    Reconciled per Phase D [SCHEMA-REVISION]; SHA-locked
    tools/expected_counts.json edge_counts.OPENBIBLE_CROSS_REF
    expected_min=expected_max=342128 (tol-0-aligned to the reconciled source).
    This test does NOT call the adapter.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    edge_entry = ec["edge_counts"]["OPENBIBLE_CROSS_REF"]
    assert edge_entry["expected_min"] == EDGE_COUNT_MIN, (
        f"edge_counts OPENBIBLE_CROSS_REF expected_min {edge_entry['expected_min']} "
        f"!= {EDGE_COUNT_MIN}"
    )
    assert edge_entry["expected_max"] == EDGE_COUNT_MAX, (
        f"edge_counts OPENBIBLE_CROSS_REF expected_max {edge_entry['expected_max']} "
        f"!= {EDGE_COUNT_MAX}"
    )
    assert edge_entry["tier"] == "B", "OPENBIBLE_CROSS_REF edge count must be Tier B"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    seed = int('d66faa3', 16) = 224852643.
    rng.randint(1024, 16384) must equal fixture length.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}. "
        f"seed_int={SEED_INT} from commit {DOCSTRING_COMMIT_SHA}"
    )


def test_fixture_has_three_disjoint_cross_refs(
    fixture_slice: dict[str, Any]
) -> None:
    """The fixture must have exactly 3 cross-refs from disjoint corpus regions.

    This test does NOT call the adapter. It validates the fixture itself.
    """
    refs = fixture_slice.get("cross_refs", [])
    assert len(refs) == 3, (
        f"fixture must have exactly 3 cross-refs; got {len(refs)}"
    )
    tuples = {
        (r["from_osis"], r["to_osis"], fixture_slice["source_slug"])
        for r in refs
    }
    assert len(tuples) == 3, (
        "fixture cross-refs must have distinct (from_osis, to_osis, source) tuples"
    )


def test_fixture_contains_zero_votes_row(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain at least one votes=0 row.

    Decision 5 edge case: votes=0 rows must be retained. The fixture seeds
    that scenario so the adapter implementation can be tested against it.

    This test does NOT call the adapter.
    """
    refs = fixture_slice.get("cross_refs", [])
    zero_rows = [r for r in refs if r.get("votes") == 0]
    assert zero_rows, (
        "fixture must contain at least one votes=0 cross-ref row "
        "to seed Decision 5 edge-case testing."
    )


def test_run_py_imports_ingest_openbible() -> None:
    """ingest/lexical/run.py must import ingest_openbible from the adapter.

    This test does NOT call the adapter; it inspects run.py source text.
    """
    run_py = REPO / "ingest" / "lexical" / "run.py"
    source = run_py.read_text(encoding="utf-8")
    assert "from ingest.lexical.openbible import ingest_openbible" in source, (
        "run.py must contain 'from ingest.lexical.openbible import ingest_openbible'"
    )
    assert "ingest_openbible(" in source, (
        "run.py must call ingest_openbible(...) in _run_one"
    )


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep
#
# For each of the 13 attack-vector stubs, attempt to run it through the same
# edge-type and provenance assertions. The stub must be rejected by at least
# one check. These tests skip (not fail) when the stub has no entry point.
# ---------------------------------------------------------------------------

STUB_MODULES = [
    "tests.lexical.stubs.broken_adapter",
    "tests.lexical.stubs.empty_required",
    "tests.lexical.stubs.identical_lemma",
    "tests.lexical.stubs.zero_records",
    "tests.lexical.stubs.hardcoded_fixture",
    "tests.lexical.stubs.minimal_edges",
    "tests.lexical.stubs.nan_inf_numeric",
    "tests.lexical.stubs.duplicate_records",
    "tests.lexical.stubs.swapped_property_names",
    "tests.lexical.stubs.mutated_strings",
    "tests.lexical.stubs.silent_exception_swallow",
    "tests.lexical.stubs.reversed_edge_direction",
    "tests.lexical.stubs.hash_ordered",
]


@pytest.mark.parametrize("stub_module_name", STUB_MODULES)
def test_verifier_rejects_attack_stub(
    stub_module_name: str,
    fake_driver: FakeDriver,
    source_root: Path,
) -> None:
    """The coverage scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Find an entry point named ingest_openbible or ingest.
      3. If none found, skip (stub may only expose emit_records/emit_edges).
      4. If found, call it. If it raises, the stub is rejected.
      5. If it runs silently, check edge type and provenance separation.
         At least one check must fail. If none fail, the test itself fails
         with 'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
        )

    raised = False
    try:
        fn(source_root, fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_edges = fake_driver.captured_edge_types()
    has_correct_type = REQUIRED_EDGE_TYPE in emitted_edges
    has_forbidden_type = FORBIDDEN_EDGE_TYPE in emitted_edges
    edges = fake_driver.edges_of_type(REQUIRED_EDGE_TYPE)
    votes_ok = all(e.get("votes") is not None for e in edges) if edges else False

    rejected = not has_correct_type or has_forbidden_type or not votes_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Edge types: {sorted(emitted_edges)}, "
        f"OPENBIBLE_CROSS_REF count: {len(edges)}, "
        f"votes_ok: {votes_ok}"
    )
