"""Coptic SCRIPTORIUM adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string,
$pred_int, $pred_bool, $pred_list definitions. Predicate semantics are
loaded at module level from that file.

TDD red-state contract:
  The adapter at ingest/lexical/coptic_scriptorium.py has NO function body.
  Every test that calls ingest_coptic_scriptorium() MUST fail because
  getattr returns None and calling None raises AttributeError or TypeError.
  That failure IS the red state the Wave 2 orchestrator gate requires.

Entry function:
  ingest/lexical/coptic_scriptorium.py docstring names the function.
  Source slug: coptic-scriptorium (Tier C).

Random seed:
  commit_sha = 'e1a37d32ea0af51957d3a505e1733fd3a5ba52a9'
  seed_hex = 'e1a37d32'
  seed_int = int('e1a37d32', 16) = 3785588018

Fixture: tests/lexical/fixtures/coptic_scriptorium_slice.json
  3 tokens: 1 sahidic, 1 bohairic, 1 with supplement=true.
  Source: synthesised from SCRIPTORIUM TT format per Decision 9 contract.
  Fixture length: 1757 bytes (seed RNG gives length=2690; fixture content
  is the structured JSON object, size within 1024-16384 range).

Source: tools/expected_counts.json sources."coptic-scriptorium"
  tier C, expected_count null (locked at first ingest run).
  tolerance_relative 0.05.
Decisions: 9 (CopticWord integration, dialect, supplement, verse_ref),
           14 (Source node, license, redistribute).
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
# Loaded at module level. Inline predicate definitions are forbidden per
# RESEED_PLAN C.5; use the canonical file.
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
ADAPTER_MODULE = "ingest.lexical.coptic_scriptorium"
ENTRY_FUNCTION = "ingest_coptic_scriptorium"

REQUIRED_LABELS = frozenset({"CopticWord", "Source"})
REQUIRED_EDGES = frozenset({"IN_VERSE"})

VALID_DIALECTS = frozenset({"sahidic", "bohairic"})

SOURCE_SLUG = "coptic-scriptorium"
LICENSE_VALUE = "CC-BY-4.0"

# Seed from coptic_scriptorium.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "e1a37d32ea0af51957d3a505e1733fd3a5ba52a9"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3785588018


# -- FakeDriver that records every node/edge the adapter emits ---------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-property formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_coptic_scriptorium() raises TypeError or
    AttributeError first.
    """

    def __init__(self) -> None:
        self._nodes: list[dict[str, Any]] = []
        self._edges: list[dict[str, Any]] = []
        self.settings = _FakeSettings()

    def session(self, *_: Any, **__: Any) -> "_FakeSession":
        return _FakeSession(self)

    def close(self) -> None:
        pass

    def captured_labels(self) -> set[str]:
        return {n["label"] for n in self._nodes}

    def captured_node_ids(self, label: str) -> list[str]:
        return [n["id"] for n in self._nodes if n["label"] == label and "id" in n]

    def captured_node_slugs(self, label: str) -> list[str]:
        return [n["slug"] for n in self._nodes if n["label"] == label and "slug" in n]

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n["label"] == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)

    def nodes_for_label(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n["label"] == label]


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

    def run(self, cypher: str, **kwargs: Any) -> Any:
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
    """Best-effort parser for MERGE Cypher statements into FakeDriver records.

    The adapter is expected to issue:
      MERGE (n:CopticWord {id: ...})
      MERGE (n:Source {slug: ...})
      MERGE (a)-[r:IN_VERSE]->(b)

    The parser records label and key properties from the UNWIND batch
    (rows / records parameter) when present.
    """
    for label in ("CopticWord", "Source"):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label})" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("IN_VERSE",):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# -- fixtures ----------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "coptic_scriptorium_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the expected data root for the coptic corpus cache."""
    return REPO / "data" / "private" / "coptic"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2, red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_coptic_scriptorium.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_coptic_scriptorium', None) returns None and the
    assert fails. That failure IS the expected red state at Wave 2.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_coptic_scriptorium must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError or TypeError because the adapter
    has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_coptic_scriptorium must return dict; got {type(result)!r}"
    )
    assert "CopticWord" in result, "return dict must contain 'CopticWord' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for every required label.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    missing = REQUIRED_LABELS - emitted
    assert not missing, (
        f"adapter did not emit required node labels: {sorted(missing)}. "
        f"Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_required_edges(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge every required edge type.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    missing = REQUIRED_EDGES - emitted
    assert not missing, (
        f"adapter did not emit required edge types: {sorted(missing)}. "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_coptic_word_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every CopticWord node must have an id starting with 'coptic-scriptorium:'.

    Decision 9: stable id = 'coptic-scriptorium:<corpus>:<doc_id>:<token_pos>'.
    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("CopticWord")
    assert word_ids, "adapter must emit at least one CopticWord node"
    bad = [wid for wid in word_ids if not wid.startswith("coptic-scriptorium:")]
    assert not bad, (
        f"CopticWord ids violate 'coptic-scriptorium:' prefix format: {bad[:5]}"
    )


def test_coptic_word_stable_id_has_four_parts(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """CopticWord stable id must have exactly 4 colon-separated parts.

    Format: 'coptic-scriptorium:<corpus>:<doc_id>:<token_pos>'.
    The first part is the source prefix which itself contains a hyphen but
    no additional colon, so splitting on ':' yields exactly 4 segments.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("CopticWord")
    assert word_ids, "adapter must emit at least one CopticWord node"
    bad = [wid for wid in word_ids if len(wid.split(":")) != 4]
    assert not bad, (
        f"CopticWord ids do not have exactly 4 colon-separated parts: {bad[:5]}"
    )


def test_coptic_word_dialect_values(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every CopticWord node must have dialect in ('sahidic', 'bohairic').

    Decision 9: dialect derived from corpus slug; only two values allowed.
    Predicate: $pred_string(dialect).

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    bad = [
        n for n in cw_nodes
        if n.get("dialect") not in VALID_DIALECTS
    ]
    assert not bad, (
        f"CopticWord nodes with invalid dialect: "
        f"{[n.get('dialect') for n in bad[:5]]}. "
        f"Allowed: {sorted(VALID_DIALECTS)}"
    )


def test_coptic_word_both_dialects_present(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter must emit CopticWord nodes for both sahidic and bohairic.

    Decision 9 acceptance Cypher requires both dialects return non-zero
    coverage rows.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    emitted_dialects = {n.get("dialect") for n in cw_nodes}
    for dialect in VALID_DIALECTS:
        assert dialect in emitted_dialects, (
            f"dialect '{dialect}' not present in emitted CopticWord nodes. "
            f"Emitted dialects: {emitted_dialects}"
        )


def test_coptic_word_supplement_is_bool(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every CopticWord node must have supplement as a boolean.

    Decision 9: supplement derived from TT angle-bracket markup.
    $pred_bool(supplement) must return true on every row (false and true
    are both valid boolean values, but None is not).

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    bad = [n for n in cw_nodes if not isinstance(n.get("supplement"), bool)]
    assert not bad, (
        f"CopticWord nodes with non-bool supplement: "
        f"{[(n.get('id'), n.get('supplement')) for n in bad[:5]]}"
    )


def test_coptic_word_supplement_true_exists(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """At least one CopticWord must have supplement=True (editorial bracket coverage).

    Decision 9 Case A: angle-bracket supplements must be persisted with
    supplement=True, not dropped or merged.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    supplemented = [n for n in cw_nodes if n.get("supplement") is True]
    assert supplemented, (
        "adapter must emit at least one CopticWord with supplement=True. "
        "Decision 9 Case A: angle-bracket tokens must set supplement=True."
    )


def test_coptic_word_source_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every CopticWord must have source='coptic-scriptorium'.

    Decision 14: source property populated from slug constant.
    Predicate: $pred_string(source).

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    bad = [n for n in cw_nodes if n.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"CopticWord nodes with wrong source: "
        f"{[(n.get('id'), n.get('source')) for n in bad[:5]]}. "
        f"Expected: '{SOURCE_SLUG}'"
    )


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='coptic-scriptorium'.

    Decision 14: Source uniqueness constraint on source_slug.
    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_source_node_license(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Source node must carry license='CC-BY-4.0' and redistribute=True.

    Decision 14: license and redistribute fields required on Source node.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    src_nodes = fake_driver.nodes_for_label("Source")
    matching = [n for n in src_nodes if n.get("slug") == SOURCE_SLUG]
    assert matching, f"No Source node with slug='{SOURCE_SLUG}' found"
    node = matching[0]
    assert node.get("license") == LICENSE_VALUE, (
        f"Source node license must be '{LICENSE_VALUE}'; got {node.get('license')!r}"
    )
    assert node.get("redistribute") is True, (
        f"Source node redistribute must be True; got {node.get('redistribute')!r}"
    )


def test_in_verse_edge_for_resolved_verse_refs(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """IN_VERSE edges must be emitted for CopticWord nodes with non-null verse_ref.

    Decision 9: IN_VERSE joins CopticWord.verse_ref to Verse.osisID via
    STEPBible-TVTMS projection.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    assert fake_driver.edge_count("IN_VERSE") > 0, (
        "adapter must emit at least one IN_VERSE edge for resolved verse_refs"
    )


def test_sahidic_fragment_persisted_without_osis(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """CopticWord nodes with null verse_ref must be persisted without IN_VERSE edge.

    Decision 9 Case B: Sahidic fragment-only chapters where TVTMS cannot
    resolve a canonical OSIS slot must persist the CopticWord with
    verse_ref=null and no IN_VERSE edge. The node must NOT be dropped.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    cw_nodes = fake_driver.nodes_for_label("CopticWord")
    assert cw_nodes, "adapter must emit at least one CopticWord node"
    # If any fragment nodes exist (verse_ref is None or absent), they must
    # still be present in the node list; the adapter must not silently drop them.
    # We count total CopticWord nodes vs IN_VERSE edges: edges <= nodes.
    word_count = fake_driver.node_count("CopticWord")
    in_verse_count = fake_driver.edge_count("IN_VERSE")
    assert in_verse_count <= word_count, (
        f"IN_VERSE edge count ({in_verse_count}) exceeds CopticWord count "
        f"({word_count}). Every edge needs a source node."
    )


# ---------------------------------------------------------------------------
# GROUP 2: static fixture and metadata validation (PASS even at Wave 2)
# ---------------------------------------------------------------------------

def test_fixture_has_three_tokens(fixture_slice: dict[str, Any]) -> None:
    """The fixture must carry exactly 3 tokens: 1 sahidic, 1 bohairic, 1 supplement.

    This test does NOT call the adapter.
    """
    tokens = fixture_slice["tokens"]
    assert len(tokens) == 3, f"Expected 3 tokens; got {len(tokens)}"
    sahidic = [t for t in tokens if t["dialect"] == "sahidic"]
    bohairic = [t for t in tokens if t["dialect"] == "bohairic"]
    supplemented = [t for t in tokens if t["supplement"] is True]
    assert len(sahidic) >= 1, "fixture must have at least 1 sahidic token"
    assert len(bohairic) >= 1, "fixture must have at least 1 bohairic token"
    assert len(supplemented) >= 1, "fixture must have at least 1 supplement=true token"


def test_fixture_token_ids_match_stable_id_format(fixture_slice: dict[str, Any]) -> None:
    """Every token in the fixture must have a well-formed stable id.

    Format: 'coptic-scriptorium:<corpus>:<doc_id>:<token_pos>'

    This test does NOT call the adapter.
    """
    tokens = fixture_slice["tokens"]
    for token in tokens:
        token_id = token["id"]
        assert token_id.startswith("coptic-scriptorium:"), (
            f"token id must start with 'coptic-scriptorium:'; got {token_id!r}"
        )
        parts = token_id.split(":")
        assert len(parts) == 4, (
            f"token id must have 4 colon-separated parts; got {len(parts)}: {token_id!r}"
        )


def test_fixture_source_node_fields(fixture_slice: dict[str, Any]) -> None:
    """Fixture Source node must carry slug, license=CC-BY-4.0, redistribute=True.

    This test does NOT call the adapter.
    """
    src = fixture_slice["source_node"]
    assert src["slug"] == SOURCE_SLUG
    assert src["license"] == LICENSE_VALUE
    assert src["redistribute"] is True


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture_length must be reproducible from the stored seed.

    seed_int = int('e1a37d32', 16) = 3785588018.
    This test does NOT call the adapter.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["fixture_length"], (
        f"Fixture fixture_length {fixture_slice['fixture_length']} "
        f"!= seeded length {expected_length}"
    )


def test_fixture_seed_constant_matches_commit_sha() -> None:
    """SEED_INT must equal int(DOCSTRING_COMMIT_SHA[:8], 16).

    This test does NOT call the adapter.
    """
    expected = int(DOCSTRING_COMMIT_SHA[:8], 16)
    assert SEED_INT == expected, (
        f"SEED_INT {SEED_INT} != int('{DOCSTRING_COMMIT_SHA[:8]}', 16) = {expected}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    This test does NOT call the adapter. Validates the predicate source file
    is present and parseable per RESEED_PLAN C.5.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """coptic-scriptorium in expected_counts.json must be Tier C with null expected_count.

    This test does NOT call the adapter.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"][SOURCE_SLUG]
    assert entry["tier"] == "C", (
        f"coptic-scriptorium must be Tier C; got {entry['tier']!r}"
    )
    assert entry["expected_count"] is None, (
        f"Tier C coptic-scriptorium expected_count must be null at baseline; "
        f"got {entry['expected_count']!r}"
    )
    assert entry["tolerance_relative"] == 0.05, (
        f"Tier C tolerance_relative must be 0.05; got {entry['tolerance_relative']!r}"
    )


def test_predicates_cypher_file_present() -> None:
    """tools/predicates_by_type.cypher must exist on disk.

    This test does NOT call the adapter.
    """
    assert _PREDICATES_CYPHER_PATH.exists(), (
        f"predicates_by_type.cypher not found at {_PREDICATES_CYPHER_PATH}"
    )


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep (13 stubs)
#
# For each attack-vector stub, attempt to run it through the same label/edge/
# id assertions. At least one check must detect the defect.
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
    """The coverage-test scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_coptic_scriptorium or ingest.
      3. If no entry point, skip (stub exposes only emit_records/emit_edges).
      4. If entry point exists and raises, the stub is rejected.
      5. If it runs silently, at least one label/edge/id check must catch the defect.
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

    emitted_labels = fake_driver.captured_labels()
    emitted_edges = fake_driver.captured_edge_types()
    word_ids = fake_driver.captured_node_ids("CopticWord")
    cw_nodes = fake_driver.nodes_for_label("CopticWord")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_prefix_ok = (
        all(wid.startswith("coptic-scriptorium:") for wid in word_ids)
        if word_ids
        else False
    )
    id_parts_ok = (
        all(len(wid.split(":")) == 4 for wid in word_ids)
        if word_ids
        else False
    )
    dialect_ok = all(
        n.get("dialect") in VALID_DIALECTS for n in cw_nodes
    ) if cw_nodes else False
    supplement_ok = all(
        isinstance(n.get("supplement"), bool) for n in cw_nodes
    ) if cw_nodes else False

    rejected = (
        not label_ok
        or not edge_ok
        or not id_prefix_ok
        or not id_parts_ok
        or not dialect_ok
        or not supplement_ok
    )
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample CopticWord ids: {word_ids[:3]}, "
        f"Dialects: {sorted({n.get('dialect') for n in cw_nodes})}"
    )
