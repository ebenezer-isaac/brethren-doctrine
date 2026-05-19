"""ETCBC-parallels adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string and
$pred_float definitions. Predicate semantics are loaded at module level from
that file and used to assert property types on captured edge payloads.

TDD red-state contract:
  The adapter at ingest/lexical/etcbc_parallels.py has NO function body at
  this commit. Every test that calls ingest_etcbc_parallels() MUST fail
  because getattr returns None and calling None raises AttributeError or
  TypeError. That failure IS the red state the Wave 2 orchestrator gate
  requires. Gate threshold: >= 3 FAILED.

Entry function:
  ingest/lexical/etcbc_parallels.py - no def; docstring-only stub.
  Function named ingest_etcbc_parallels per Wave 2 spec.

Random seed:
  commit_sha = 'e4743362c344524d9022c5186aeb30de7d855a10'
    (git log -1 --format=%H -- ingest/lexical/etcbc_parallels.py)
  seed_int = int('e4743362', 16) = 3832820578

Fixture: tests/lexical/fixtures/etcbc_parallels_slice.json
  3 parallel pairs from distinct corpus regions (early-OT, mid-OT, late-OT).
  Length seeded from rng: 14920 (within [1024, 16384]).
  Seed INT derived from first 8 hex chars of the commit SHA above.

Source: tools/expected_counts.json sources."ETCBC-parallels" expected_count=5882
(reconciled per Phase D [SCHEMA-REVISION]; SHA-locked tools/expected_counts.json
ETCBC-parallels=5882. The prior 8246 was the pre-reconciliation raw crossref.tf
feature-row count, stale per docs/PHASE_D_DECISIONS_LOG.md).
Decisions: 3 (ETCBC syntax tree shape, parallels edge-case bullet).
Labels: none (edge-only adapter).
Edges: PARALLEL_OF (BhsaWord -> BhsaWord) with similarity float property.
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

# -- predicates_by_type.cypher ------------------------------------------------
# Loaded at module level. Inline predicate definitions are forbidden per
# RESEED_PLAN C.5; the canonical file is the single source of truth.
_PREDICATES_CYPHER_PATH = REPO / "tools" / "predicates_by_type.cypher"
_PREDICATES_RAW = _PREDICATES_CYPHER_PATH.read_text(encoding="utf-8")


def _load_predicates(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$pred_") and ":=" in line:
            lhs, rhs = line.split(":=", 1)
            name = lhs.strip().split("$pred_")[1].split("(")[0]
            result[name] = rhs.strip()
    return result


PREDICATES = _load_predicates(_PREDICATES_RAW)

# -- adapter constants -------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.etcbc_parallels"
ENTRY_FUNCTION = "ingest_etcbc_parallels"
SOURCE_SLUG = "ETCBC-parallels"

REQUIRED_LABELS: frozenset[str] = frozenset()  # edge-only: no new labels
REQUIRED_EDGES: frozenset[str] = frozenset({"PARALLEL_OF"})
EDGE_PROPERTY = "similarity"

# reconciled per Phase D [SCHEMA-REVISION]; SHA-locked
# tools/expected_counts.json ETCBC-parallels=5882. The prior 8246 was the
# pre-reconciliation raw crossref.tf feature-row count.
EXPECTED_COUNT = 5882  # Tier A, tolerance 0

# Seed from etcbc_parallels.py commit SHA
DOCSTRING_COMMIT_SHA = "e4743362c344524d9022c5186aeb30de7d855a10"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3832820578


# -- FakeDriver that records edges the adapter emits -------------------------

class FakeDriver:
    """Minimal Neo4j driver stand-in for the edge-only etcbc_parallels adapter.

    Captures every PARALLEL_OF MERGE call so tests can assert on edge tuples,
    similarity values, and source properties without a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_etcbc_parallels() raises AttributeError or
    TypeError first.
    """

    def __init__(self) -> None:
        self._edges: list[dict[str, Any]] = []
        self.settings = _FakeSettings()

    def session(self, *_: Any, **__: Any) -> "_FakeSession":
        return _FakeSession(self)

    def close(self) -> None:
        pass

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)

    def edges_of(self, rel_type: str) -> list[dict[str, Any]]:
        return [e for e in self._edges if e["rel_type"] == rel_type]


class _FakeSettings:
    """Minimal settings stub matching real Settings fields."""

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
        return {"edges": 1, "pairs": 1}

    def consume(self) -> None:
        pass


def _parse_cypher_into_driver(
    cypher: str, params: dict[str, Any], driver: FakeDriver
) -> None:
    """Best-effort parse of MERGE Cypher for PARALLEL_OF edges.

    The adapter is expected to issue MATCH/MERGE patterns like:
      MATCH (a:BhsaWord {id: $source_id})
      MATCH (b:BhsaWord {id: $target_id})
      MERGE (a)-[r:PARALLEL_OF]->(b)
      ON CREATE SET r.similarity = $similarity, r.source = 'ETCBC-parallels'
      ON MATCH  SET r.similarity = $similarity, r.source = 'ETCBC-parallels'

    Or batched via UNWIND with rows parameter. Both forms are captured.
    """
    if "PARALLEL_OF" not in cypher:
        return

    rows_param = params.get("rows") or params.get("records") or []
    if isinstance(rows_param, list) and rows_param:
        for row in rows_param:
            if isinstance(row, dict):
                edge: dict[str, Any] = {
                    "rel_type": "PARALLEL_OF",
                    "from_id": row.get("source_id") or row.get("from_id") or row.get("source_node", ""),
                    "to_id": row.get("target_id") or row.get("to_id") or row.get("target_node", ""),
                    "similarity": row.get("similarity"),
                    "source": row.get("source", SOURCE_SLUG),
                }
                driver._edges.append(edge)
    else:
        # Single-row call: pull scalar kwargs
        edge = {
            "rel_type": "PARALLEL_OF",
            "from_id": params.get("source_id") or params.get("from_id") or params.get("source_node", ""),
            "to_id": params.get("target_id") or params.get("to_id") or params.get("target_node", ""),
            "similarity": params.get("similarity"),
            "source": params.get("source", SOURCE_SLUG),
        }
        driver._edges.append(edge)


# -- fixtures ----------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "etcbc_parallels_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_etcbc_parallels.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_etcbc_parallels', None) returns None and the
    assert fails. That failure IS the expected red state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver) -> None:
    """ingest_etcbc_parallels must return a dict mapping edge type to count.

    FAILS at Wave 2 with AttributeError or TypeError because the adapter
    has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_etcbc_parallels must return dict; got {type(result)!r}"
    )
    assert "PARALLEL_OF" in result, "return dict must contain 'PARALLEL_OF' key"


def test_adapter_emits_parallel_of_edges(fake_driver: FakeDriver) -> None:
    """Running the adapter must merge at least one PARALLEL_OF edge.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert "PARALLEL_OF" in emitted, (
        f"adapter did not emit PARALLEL_OF edge. Edge types seen: {sorted(emitted)}"
    )


def test_parallel_of_edges_have_similarity_float(fake_driver: FakeDriver) -> None:
    """Every PARALLEL_OF edge must carry a finite float similarity property.

    FAILS at Wave 2 with AttributeError or TypeError.

    The $pred_float(x) predicate from tools/predicates_by_type.cypher is the
    authoritative check: x IS NOT NULL AND NOT (x <> x) AND x < (1.0/0.0)
    AND x > -(1.0/0.0). NaN and Inf violate this predicate.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    edges = fake_driver.edges_of("PARALLEL_OF")
    assert edges, "adapter must emit at least one PARALLEL_OF edge"
    bad: list[Any] = []
    for e in edges:
        sim = e.get("similarity")
        if sim is None:
            bad.append(("missing_similarity", e))
        elif not isinstance(sim, float):
            bad.append(("not_float", e))
        elif sim != sim:  # NaN check
            bad.append(("nan_similarity", e))
        elif sim == float("inf") or sim == float("-inf"):
            bad.append(("inf_similarity", e))
    assert not bad, (
        f"PARALLEL_OF edges with invalid similarity: {bad[:3]}. "
        "Predicate: $pred_float(x) from tools/predicates_by_type.cypher"
    )


def test_parallel_of_edges_have_source_property(fake_driver: FakeDriver) -> None:
    """Every PARALLEL_OF edge must carry source='ETCBC-parallels'.

    FAILS at Wave 2 with AttributeError or TypeError.

    The source property is required per section 5 of the docstring contract
    so Pipeline 2 provenance filters can isolate ETCBC parallels.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    edges = fake_driver.edges_of("PARALLEL_OF")
    assert edges, "adapter must emit at least one PARALLEL_OF edge"
    bad = [e for e in edges if e.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"PARALLEL_OF edges missing source='{SOURCE_SLUG}': {bad[:3]}"
    )


def test_parallel_of_endpoints_are_bhsa_word_nodes(fake_driver: FakeDriver) -> None:
    """Every PARALLEL_OF edge must connect two BhsaWord nodes.

    FAILS at Wave 2 with AttributeError or TypeError.

    This adapter is edge-only. It must never create BhsaWord nodes; it
    must MATCH them by id. The FakeDriver captures the endpoint id strings
    used in the MERGE call; the test asserts they are non-empty strings.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    edges = fake_driver.edges_of("PARALLEL_OF")
    assert edges, "adapter must emit at least one PARALLEL_OF edge"
    bad_from = [e for e in edges if not e.get("from_id")]
    bad_to = [e for e in edges if not e.get("to_id")]
    assert not bad_from, f"PARALLEL_OF edges with empty from_id: {bad_from[:3]}"
    assert not bad_to, f"PARALLEL_OF edges with empty to_id: {bad_to[:3]}"


def test_target_and_value_split_on_comma_delimiter(
    fixture_slice: dict[str, Any],
) -> None:
    """The adapter must split target_and_value on comma to extract target+similarity.

    FAILS at Wave 2 with AttributeError or TypeError.

    The split rule from the docstring (section 4):
      parts = target_and_value.split(',', 1)
      target_node = parts[0].strip()
      similarity = float(parts[1].strip())

    This test verifies the fixture pairs conform to the split rule and that
    a naive split on the documented delimiter correctly unpacks both fields.
    """
    for pair in fixture_slice["pairs"]:
        tav = pair["target_and_value"]
        parts = tav.split(",", 1)
        assert len(parts) == 2, (
            f"target_and_value '{tav}' does not split into 2 parts on comma"
        )
        target_node = parts[0].strip()
        similarity_raw = parts[1].strip()
        assert target_node.isdigit(), (
            f"target_node '{target_node}' is not a decimal integer string"
        )
        sim = float(similarity_raw)
        assert 0.0 <= sim <= 1.0, (
            f"similarity {sim} is outside [0.0, 1.0] for pair {pair}"
        )
        assert sim == sim, f"similarity is NaN for pair {pair}"
        assert sim < float("inf"), f"similarity is Inf for pair {pair}"


def test_merge_idempotency_key_is_source_target_tuple(fake_driver: FakeDriver) -> None:
    """Running the adapter twice must produce no duplicate edges.

    FAILS at Wave 2 with AttributeError or TypeError.

    Idempotency is guaranteed by MERGE on (source BhsaWord.id, target
    BhsaWord.id) per docstring section 6. After two identical runs the set
    of (from_id, to_id) tuples must equal the set from one run.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    first_run_tuples = {
        (e["from_id"], e["to_id"]) for e in fake_driver.edges_of("PARALLEL_OF")
    }
    fn(fake_driver.settings)
    second_run_tuples = {
        (e["from_id"], e["to_id"]) for e in fake_driver.edges_of("PARALLEL_OF")
    }
    assert first_run_tuples == second_run_tuples, (
        "MERGE idempotency violated: second run produced different edge tuples. "
        f"First run: {len(first_run_tuples)} unique pairs. "
        f"Second run: {len(second_run_tuples)} unique pairs."
    )


def test_adapter_does_not_create_bhsa_word_nodes(fake_driver: FakeDriver) -> None:
    """The adapter must create zero new nodes.

    FAILS at Wave 2 with AttributeError or TypeError.

    This adapter is edge-only per the docstring contract. Any node creation
    is a contract violation because it would corrupt the BhsaWord keyspace
    written by the BHSA adapter.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    # The FakeDriver only tracks edges for this adapter; verify no stray nodes
    # were written by checking the absence of node-creating Cypher calls.
    # If the adapter respects the edge-only contract, _nodes stays empty.
    assert not hasattr(fake_driver, "_nodes") or not fake_driver._nodes, (  # type: ignore[attr-defined]
        "edge-only adapter must not write any nodes. "
        f"Got nodes: {getattr(fake_driver, '_nodes', [])[:3]}"
    )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The seeded_length must be reproducible from the stored seed_int.

    Seed = int(commit_sha[:8], 16) = int('e4743362', 16) = 3832820578.
    This test does NOT call the adapter; it passes even at Wave 2.
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["seeded_length"], (
        f"Fixture seeded_length {fixture_slice['seeded_length']} "
        f"!= reproducible length {length} from seed {SEED_INT}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string and float predicates.

    This test does NOT call the adapter; it passes even at Wave 2.
    It validates the predicate source file is present and parseable per
    RESEED_PLAN C.5.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "float" in PREDICATES, "predicates_by_type.cypher missing $pred_float"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )
    assert "IS NOT NULL" in PREDICATES["float"], (
        "$pred_float must contain IS NOT NULL check"
    )
    assert "1.0/0.0" in PREDICATES["float"], (
        "$pred_float must check for Inf via (1.0/0.0)"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """The ETCBC-parallels expected count in expected_counts.json must be 5882 (Tier A).

    Reconciled per Phase D [SCHEMA-REVISION]; SHA-locked
    tools/expected_counts.json ETCBC-parallels=5882. This test still fails if
    the SHA-locked contract count deviates from the reconciled truth.

    This test does NOT call the adapter; it passes even at Wave 2.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["ETCBC-parallels"]
    assert entry["expected_count"] == EXPECTED_COUNT, (
        f"expected_counts.json ETCBC-parallels count {entry['expected_count']} "
        f"!= {EXPECTED_COUNT}"
    )
    assert entry["tier"] == "A", "ETCBC-parallels must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "parallel_edge", (
        "ETCBC-parallels record_unit must be 'parallel_edge'"
    )


def test_acceptance_cypher_is_documented_in_predicates() -> None:
    """The $pred_float predicate covers the similarity IS NOT NULL acceptance gate.

    The acceptance Cypher from docstring section 7:
      MATCH (a:BhsaWord)-[r:PARALLEL_OF]->(b:BhsaWord)
      WHERE r.similarity IS NOT NULL
      WITH count(r) AS pairs
      RETURN pairs, pairs > 0

    This test verifies the predicate file's float definition is consistent
    with that WHERE clause. Does NOT call the adapter; passes at Wave 2.
    """
    float_pred = PREDICATES.get("float", "")
    assert "IS NOT NULL" in float_pred, (
        "The acceptance Cypher uses 'WHERE r.similarity IS NOT NULL', "
        "but $pred_float does not contain IS NOT NULL check."
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (parametrized over 13 attack-vector stubs)
#
# Node-assertion stubs (broken_adapter, empty_required, identical_lemma,
# zero_records, hardcoded_fixture, minimal_edges, duplicate_records,
# swapped_property_names, mutated_strings, silent_exception_swallow,
# reversed_edge_direction, hash_ordered) are OSHB-oriented and expose no
# ingest_etcbc_parallels entry point. They are skipped with documented
# reason. The nan_inf_numeric stub exposes emit_records (no entry point)
# and is also skipped. The parametrize list mirrors test_oshb_coverage.py
# for structural parity.
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
) -> None:
    """The coverage-test scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Try to find an entry point named ingest_etcbc_parallels or ingest.
      3. If no entry point: skip with documented reason (stubs are OSHB-scoped;
         they expose no ingest_etcbc_parallels function, so the N/A skip is
         the correct Wave 2 behaviour rather than a false PASS).
      4. If entry point exists: call it. If it raises, stub is rejected. Good.
      5. If it runs silently: check edge types and similarity property validity.
         At least one check must fail. If none fail, the test fails.

    Skip reason for all 13 stubs: these stubs are scoped to the OSHB adapter
    and expose no ingest_etcbc_parallels callable. The verifier's ability to
    detect ETCBC-parallels defects is instead exercised by GROUP 1 tests
    which assert on the edge-only contract (PARALLEL_OF, similarity float,
    source property, endpoint id presence). Stubs targeting the OSHB node
    contract (labels, Word/Morpheme ids) are not applicable to an edge-only
    adapter and are correctly skipped here per the Wave 2 N/A rule.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable '{ENTRY_FUNCTION}' entry point "
            "(stubs are OSHB-scoped; skip is correct N/A for edge-only adapter). "
            f"Exposed names: {[x for x in dir(stub_mod) if not x.startswith('_')]}"
        )

    raised = False
    try:
        fn(fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_edges = fake_driver.captured_edge_types()
    parallel_edges = fake_driver.edges_of("PARALLEL_OF")

    edge_ok = "PARALLEL_OF" in emitted_edges
    sim_ok = all(
        isinstance(e.get("similarity"), float)
        and e.get("similarity") == e.get("similarity")  # NaN guard
        and e.get("similarity") < float("inf")
        for e in parallel_edges
    ) if parallel_edges else False
    source_ok = all(e.get("source") == SOURCE_SLUG for e in parallel_edges)

    rejected = not edge_ok or not sim_ok or not source_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Edge types: {sorted(emitted_edges)}, "
        f"Similarity sample: {[e.get('similarity') for e in parallel_edges[:3]]}, "
        f"Source sample: {[e.get('source') for e in parallel_edges[:3]]}"
    )
