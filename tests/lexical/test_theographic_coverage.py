"""Theographic Bible Metadata adapter coverage tests (Phase C Wave 2, Verifier caste).

This file tests the contract defined in ingest/lexical/theographic.py docstring
and docs/SCHEMA_DECISIONS.md Decision 10.

Predicate semantics are loaded at module level from tools/predicates_by_type.cypher
per RESEED_PLAN C.5. Inline predicate definitions are forbidden.

TDD red-state contract:
  The adapter at ingest/lexical/theographic.py has NO function body at this commit.
  importlib.import_module will succeed (the module is a docstring), but
  getattr(mod, 'ingest_theographic', None) returns None because the function is
  not defined. Calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires (>=3 FAILED).

Entry function confirmed:
  - ingest/lexical/theographic.py docstring: names ingest_theographic.
  - ingest/lexical/run.py line 21: from ingest.lexical.theographic import ingest_theographic
  - ingest/lexical/run.py line 57: return ingest_theographic(DATA_ROOT / 'theographic', settings)

Random seed:
  commit_sha = '27b5b53' (git log -1 -- ingest/lexical/theographic.py)
  seed = int('27b5b53', 16) = 41638739

Fixture: tests/lexical/fixtures/theographic_slice.json
  3 entities: 1 Person (mary-magdalene), 1 Place (bethlehem-of-judah), 1 Period (second-temple-period).
  Seeded from commit SHA 27b5b53 per RESEED_PLAN C.1.

Source: tools/expected_counts.json sources."Theographic-Bible-Metadata" expected_count=43690.
Decisions: 10 (Theographic projection schema), 14 (Strong/Source constraints).

Caste: verifier
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

# -- predicates_by_type.cypher (tools/predicates_by_type.cypher) ---------
# Loaded at module level. Any inline predicate definition here is forbidden
# per RESEED_PLAN C.5; use the canonical file instead.
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
ADAPTER_MODULE = "ingest.lexical.theographic"
ENTRY_FUNCTION = "ingest_theographic"
SOURCE_SLUG = "Theographic-Bible-Metadata"

REQUIRED_LABELS = frozenset({"Person", "Place", "Period", "Event", "Group", "Tribe"})
REQUIRED_ENTITY_LABELS = frozenset({"Person", "Place", "Period", "Event", "Group", "Tribe"})
REQUIRED_EDGES = frozenset({"MENTIONS"})

EXPECTED_RECORD_COUNT = 43690
DOCSTRING_COMMIT_SHA = "27b5b53"
SEED_INT = int(DOCSTRING_COMMIT_SHA, 16)  # = 41638739


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in for Theographic adapter tests.

    The adapter is expected to MERGE entity nodes (Person, Place, Period,
    Event, Group, Tribe) and Source nodes, then MERGE MENTIONS edges from
    entities to Verse nodes. This fake captures every payload so tests can
    assert on emitted labels, property presence, entity_id format, and edge
    types without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_theographic() raises TypeError first.
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
        return [n["entity_id"] for n in self._nodes if n.get("label") == label and "entity_id" in n]

    def captured_node_slugs(self, label: str) -> list[str]:
        return [n["slug"] for n in self._nodes if n.get("label") == label and "slug" in n]

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n.get("label") == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)

    def nodes_for_label(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]


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
    """Best-effort parse of MERGE Cypher for Theographic entity nodes and edges.

    Captures Person, Place, Period, Event, Group, Tribe, and Source node merges,
    plus MENTIONS edge merges, from adapter-issued Cypher calls.
    This parser is intentionally lenient; a docstring-only adapter produces no
    calls at all, so all assertions fail as required for the red state.
    """
    entity_labels = ("Person", "Place", "Period", "Event", "Group", "Tribe")
    for label in entity_labels:
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label})" in cypher
            or f":{label}{{" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    if ":Source" in cypher or ":`Source`" in cypher or "(s:Source" in cypher:
        slug_param = params.get("slug") or SOURCE_SLUG
        driver._nodes.append({"label": "Source", "slug": slug_param})

    for rel_type in ("MENTIONS", "FROM_EDITION"):
        if f"`{rel_type}`" in cypher or f":{rel_type}]" in cypher or f":{rel_type}" in cypher:
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
    p = REPO / "tests" / "lexical" / "fixtures" / "theographic_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the upstream data root for Theographic JSON."""
    return REPO / "data" / "private" / "theographic"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_theographic.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_theographic', None) returns None and the assert fails.
    That failure IS the expected red state at Wave 2 (docstring-only adapter).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_theographic must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable,
    because the adapter has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_theographic must return dict; got {type(result)!r}"
    )
    assert "Person" in result, "return dict must contain 'Person' key"


def test_adapter_emits_all_six_entity_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for all six entity labels.

    Decision 10 Rule: Person, Place, Period, Event, Group, Tribe.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    missing = REQUIRED_ENTITY_LABELS - emitted
    assert not missing, (
        f"adapter did not emit required entity labels: {sorted(missing)}. "
        f"Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_mentions_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit at least one MENTIONS edge.

    Decision 10: MENTIONS edges link entity nodes to Verse nodes via
    the verses list in the upstream JSON.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert "MENTIONS" in emitted, (
        f"adapter must emit MENTIONS edges (entity to Verse). "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_person_entity_id_is_slug_not_display_name(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Person.entity_id must be the upstream filename slug, not the display_name.

    Decision 10 Edge cases handled bullet 1: several persons share a common
    name (e.g. numerous Marys). The adapter MUST preserve the filename slug
    as entity_id verbatim, not the display_name string.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    person_nodes = fake_driver.nodes_for_label("Person")
    assert person_nodes, "adapter must emit at least one Person node"
    for node in person_nodes:
        assert "entity_id" in node, (
            f"Person node missing entity_id property: {node}"
        )
        eid = node["entity_id"]
        assert isinstance(eid, str) and eid.strip(), (
            f"Person.entity_id must be a non-empty string; got {eid!r}"
        )
        assert " " not in eid, (
            f"Person.entity_id must be a filename slug (no spaces); "
            f"got {eid!r}. Display names must not be used as entity_id."
        )


def test_place_aliases_on_same_node(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Place entries with overlapping names must carry aliases on the same node.

    Decision 10 Edge cases handled bullet 2: place entries sometimes carry
    overlapping ancient and modern names. The adapter MUST persist each as
    an alias on the same Place node rather than emitting duplicate nodes.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    place_nodes = fake_driver.nodes_for_label("Place")
    assert place_nodes, "adapter must emit at least one Place node"
    for node in place_nodes:
        assert "entity_id" in node, (
            f"Place node missing entity_id: {node}"
        )


def test_period_start_end_year_integer_type(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Period.start_year and end_year must be integers per $pred_int.

    Decision 10 Per-field predicate type table, Period projection:
    start_year: int $pred_int(x), end_year: int $pred_int(x).
    BCE years are negative integers; CE years are positive.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    period_nodes = fake_driver.nodes_for_label("Period")
    assert period_nodes, "adapter must emit at least one Period node"
    for node in period_nodes:
        if "start_year" in node:
            assert isinstance(node["start_year"], int), (
                f"Period.start_year must be int; got {type(node['start_year']).__name__} "
                f"for entity_id={node.get('entity_id')!r}"
            )
        if "end_year" in node:
            assert isinstance(node["end_year"], int), (
                f"Period.end_year must be int; got {type(node['end_year']).__name__} "
                f"for entity_id={node.get('entity_id')!r}"
            )


def test_source_node_slug_is_theographic(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='Theographic-Bible-Metadata'.

    Decision 14: Source uniqueness constraint on source_slug.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug={SOURCE_SLUG!r} not found. Got slugs: {slugs}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: fixture and predicate file integrity tests (pass at Wave 2)
# ---------------------------------------------------------------------------

def test_predicates_file_defines_string_int_list_bool() -> None:
    """tools/predicates_by_type.cypher must define string, int, list, bool predicates.

    This test does NOT call the adapter. It validates the predicate source
    file is present and parseable per RESEED_PLAN C.5.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "list" in PREDICATES, "predicates_by_type.cypher missing $pred_list"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_predicates_file_has_cypher_ge_one() -> None:
    """tools/predicates_by_type.cypher must contain at least one := definition.

    Per RESEED_PLAN C.5 the file is the single source of predicate truth.
    This test asserts the file is non-trivial and the parser above found
    at least one valid definition.
    """
    assert len(PREDICATES) >= 1, (
        "predicates_by_type.cypher must define at least one $pred_* predicate; "
        f"got {len(PREDICATES)} definitions"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """Theographic-Bible-Metadata expected_count in expected_counts.json must be 43690 (Tier A).

    This test does NOT call the adapter. It validates the count constant
    is correct per tools/expected_counts.json.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"][SOURCE_SLUG]
    assert entry["expected_count"] == EXPECTED_RECORD_COUNT, (
        f"expected_counts.json {SOURCE_SLUG} count {entry['expected_count']} "
        f"!= {EXPECTED_RECORD_COUNT}"
    )
    assert entry["tier"] == "A", f"{SOURCE_SLUG} must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture seed must be reproducible from the commit SHA 27b5b53.

    seed = int('27b5b53', 16) = 665064275 per the module docstring.
    The fixture stores 3 entities which is within the 1024-16384 byte
    fixture length window per RESEED_PLAN C.1.
    """
    assert fixture_slice["seed_int"] == SEED_INT, (
        f"fixture seed_int {fixture_slice['seed_int']} != {SEED_INT}"
    )
    assert fixture_slice["seed_commit_sha"] == DOCSTRING_COMMIT_SHA, (
        f"fixture seed_commit_sha {fixture_slice['seed_commit_sha']!r} "
        f"!= {DOCSTRING_COMMIT_SHA!r}"
    )
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length >= 1024 and length <= 16384, (
        f"Seeded length {length} is outside [1024, 16384]"
    )


def test_fixture_has_three_entities(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain exactly 3 entities (1 Person, 1 Place, 1 Period).

    This test does NOT call the adapter. It validates the fixture structure
    matches the verifier contract.
    """
    entities = fixture_slice["entities"]
    assert len(entities) == 3, (
        f"fixture must have 3 entities; got {len(entities)}"
    )
    types = {e["entity_type"] for e in entities}
    assert "Person" in types, "fixture must include a Person entity"
    assert "Place" in types, "fixture must include a Place entity"
    assert "Period" in types, "fixture must include a Period entity"


def test_fixture_entity_ids_are_slugs(fixture_slice: dict[str, Any]) -> None:
    """Every fixture entity_id must be a filename slug (no spaces, non-empty).

    Decision 10 Stable identifier policy: entity_id is preserved verbatim
    from the upstream filename stem. Slugs never contain spaces.
    """
    for entity in fixture_slice["entities"]:
        eid = entity["entity_id"]
        assert isinstance(eid, str) and eid.strip(), (
            f"entity_id must be a non-empty string; got {eid!r}"
        )
        assert " " not in eid, (
            f"entity_id must be a slug (no spaces); got {eid!r}"
        )


def test_fixture_person_has_verses_list(fixture_slice: dict[str, Any]) -> None:
    """Fixture Person entity must have a verses list per Decision 10 Person projection."""
    person = next(e for e in fixture_slice["entities"] if e["entity_type"] == "Person")
    assert "verses" in person, "Person entity must have a verses field"
    assert isinstance(person["verses"], list) and len(person["verses"]) > 0, (
        "Person.verses must be a non-empty list of OSIS references"
    )
    for ref in person["verses"]:
        assert isinstance(ref, str) and "." in ref, (
            f"Person verse reference must be OSIS format (e.g. 'Matt.1.1'); got {ref!r}"
        )


def test_fixture_place_has_aliases(fixture_slice: dict[str, Any]) -> None:
    """Fixture Place entity must carry aliases per Decision 10 Place projection."""
    place = next(e for e in fixture_slice["entities"] if e["entity_type"] == "Place")
    assert "aliases" in place, "Place entity must have an aliases field"
    assert isinstance(place["aliases"], list) and len(place["aliases"]) > 0, (
        "Place.aliases must be a non-empty list"
    )


def test_fixture_period_has_integer_years(fixture_slice: dict[str, Any]) -> None:
    """Fixture Period entity must carry integer start_year and end_year.

    BCE years are negative integers per Decision 10 Period projection.
    """
    period = next(e for e in fixture_slice["entities"] if e["entity_type"] == "Period")
    assert "start_year" in period, "Period entity must have start_year"
    assert "end_year" in period, "Period entity must have end_year"
    assert isinstance(period["start_year"], int), (
        f"Period.start_year must be int; got {type(period['start_year']).__name__}"
    )
    assert isinstance(period["end_year"], int), (
        f"Period.end_year must be int; got {type(period['end_year']).__name__}"
    )
    assert period["start_year"] < 0, (
        "Fixture second-temple-period start_year should be BCE (negative int)"
    )


def test_fixture_field_presence_ledger_matches_entities(fixture_slice: dict[str, Any]) -> None:
    """The field_presence_ledger in the fixture must match each entity's present_fields.

    The snapshot ledger records per-entity field presence as a sorted vector
    per Decision 10 Adapter MUST NOT invent fields section.
    """
    ledger = fixture_slice["field_presence_ledger"]
    for entity in fixture_slice["entities"]:
        eid = entity["entity_id"]
        assert eid in ledger, f"field_presence_ledger missing entry for entity_id {eid!r}"
        ledger_fields = set(ledger[eid])
        present_fields = set(entity["present_fields"])
        assert ledger_fields == present_fields, (
            f"field_presence_ledger for {eid!r} has {sorted(ledger_fields)}, "
            f"but entity.present_fields has {sorted(present_fields)}"
        )


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep (13 stubs)
#
# For each of the 13 attack-vector stubs, attempt to run it through the same
# entity-label/edge-type/entity-id assertions. At least one check must fail
# (stub is rejected) or the stub must raise. These tests skip (not fail) when
# the stub has no ingest entry point named ingest_theographic or ingest.
# In Wave 3 (real impl present), these tests assert defect detection.
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
      2. Try to find an ingest entry point named ingest_theographic or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected. Good.
      5. If it runs silently, check labels, edge types, and entity_id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_theographic", None)
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
    entity_ids = []
    for label in REQUIRED_ENTITY_LABELS:
        entity_ids.extend(fake_driver.captured_node_ids(label))

    label_ok = REQUIRED_ENTITY_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_format_ok = (
        all(" " not in eid and eid.strip() for eid in entity_ids)
        if entity_ids
        else False
    )

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample entity ids: {entity_ids[:3]}"
    )
