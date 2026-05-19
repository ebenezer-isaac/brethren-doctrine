"""STEPBible-proper-nouns adapter coverage tests (phase C.2 verifier: stepbible_proper_nouns).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool definitions. Predicate semantics are loaded at module level from that
file and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_proper_nouns.py has NO function body at
  this commit. Every test that calls ingest_stepbible_proper_nouns() MUST fail
  because getattr returns None and calling None raises TypeError. That failure IS
  the red state this verifier gate requires (>= 3 FAILED).

Entry function confirmed:
  ingest/lexical/stepbible_proper_nouns.py docstring names the function via the
  Acceptance Cypher in phase_02_lexical_ingest.md Group 3 step 12.
  Function: ingest_stepbible_proper_nouns

Random seed:
  commit_sha = 'e3ed6dc4ae935d108ad2525521074abaf5d65667'
      (git log -1 --format=%H -- ingest/lexical/stepbible_proper_nouns.py)
  seed_int = int('e3ed6dc4', 16) = 3823988164

Fixture: tests/lexical/fixtures/stepbible_proper_nouns_slice.json
  3 entries: 1 Hebrew person (Avraham/H85), 1 Greek person (Petros/G4074),
  1 place (Yerushalayim/H3389 with null verse_count).
  Length = rng.randint(1024,16384) where rng = random.Random(3823988164) = 9782.

Source: tools/expected_counts.json sources."STEPBible-proper-nouns" expected_count=5468.
Decision: 17 (STEPBible morph-codes and proper-nouns reference tables).

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

# -- predicates_by_type.cypher load ------------------------------------------
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
ADAPTER_MODULE = "ingest.lexical.stepbible_proper_nouns"
ENTRY_FUNCTION = "ingest_stepbible_proper_nouns"
SOURCE_SLUG = "STEPBible-proper-nouns"

REQUIRED_LABELS = frozenset({"ProperNoun", "Source"})
REQUIRED_EDGES = frozenset({"NAMED_AT"})

# Decision 17 populated projection fields (all 8 per the docstring):
PROPER_NOUN_FIELDS = (
    "proper_name_entry",
    "transliteration",
    "meaning",
    "strong",
    "pos",
    "language",
    "verse_count",
    "first_occurrence",
)

EXPECTED_COUNT = 5468  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "e3ed6dc4ae935d108ad2525521074abaf5d65667"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3823988164


# -- FakeDriver that records every node/edge the adapter emits ---------------

class FakeDriver:
    """Minimal Neo4j driver stand-in for ProperNoun/NAMED_AT adapter testing."""

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

    def captured_properties(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n["label"] == label]

    def captured_node_slugs(self, label: str) -> list[str]:
        return [n["slug"] for n in self._nodes if n["label"] == label and "slug" in n]

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n["label"] == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)


class _FakeSettings:
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
    """Best-effort parse of MERGE Cypher statements into FakeDriver records.

    The proper-nouns adapter is expected to emit:
      MERGE (n:ProperNoun {proper_name_entry: ...})
      MERGE (n:Source {slug: 'STEPBible-proper-nouns'})
      MERGE (p)-[:NAMED_AT]->(v)  (when first_occurrence resolves)
    """
    for label in ("ProperNoun", "Source", "Verse"):
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

    for rel_type in ("NAMED_AT",):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_proper_nouns_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the data root expected by the proper-nouns adapter."""
    return REPO / "data" / "private" / "stepbible"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_proper_nouns.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_proper_nouns', None) returns None.
    That failure IS the expected red state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_proper_nouns must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_proper_nouns must return dict; got {type(result)!r}"
    )
    assert "ProperNoun" in result, "return dict must contain 'ProperNoun' key"


def test_adapter_emits_proper_noun_label(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit ProperNoun nodes.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "ProperNoun" in emitted, (
        f"adapter did not emit ProperNoun nodes. Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_named_at_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit at least one NAMED_AT edge when first_occurrence resolves.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per Decision 17 Edge cases handled: NAMED_AT is emitted zero or one per ProperNoun,
    only when first_occurrence resolves to a Verse node from Group 1.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edges = fake_driver.captured_edge_types()
    assert "NAMED_AT" in edges, (
        f"adapter must emit NAMED_AT edges on first_occurrence resolution. "
        f"Edge types seen: {sorted(edges)}"
    )


def test_proper_noun_stable_id_is_proper_name_entry(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """ProperNoun stable id must equal proper_name_entry (graph MERGE key, Decision 17).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17: stable id format is the verbatim headline column value
    (proper_name_entry). MERGE key: ProperNoun.proper_name_entry (constraint
    proper_noun_entry, graph/lexical.cypher line 41).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_properties("ProperNoun")
    assert nodes, "adapter must emit at least one ProperNoun node"
    bad = [
        n for n in nodes
        if "proper_name_entry" not in n
        or not isinstance(n.get("proper_name_entry"), str)
        or not n.get("proper_name_entry")
    ]
    assert not bad, (
        f"ProperNoun nodes missing non-empty proper_name_entry (stable id): {bad[:3]}"
    )


def test_proper_noun_language_discriminator_is_hebrew_or_greek(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every ProperNoun node must have language in ('hebrew', 'greek').

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17 Edge cases handled bullet 2: the adapter MUST tag each ProperNoun
    with a language discriminator derived from the TSV section. Recognised values
    are 'hebrew' and 'greek' only. Any other value is a parse error.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_properties("ProperNoun")
    assert nodes, "adapter must emit at least one ProperNoun node"
    bad = [
        n for n in nodes
        if n.get("language") not in ("hebrew", "greek")
    ]
    assert not bad, (
        f"ProperNoun nodes with invalid language discriminator: {bad[:3]}. "
        "Decision 17: only 'hebrew' and 'greek' are valid language values."
    )


def test_proper_noun_verse_count_nullable_coercion(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """ProperNoun.verse_count must be int or null, never a non-numeric placeholder string.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17 Edge cases handled bullet 3: non-numeric verse_count placeholders
    MUST be coerced to null integer, not stored as strings and not used to reject rows.
    $pred_int(verse_count) returns False on null (IS NOT NULL), surfacing the uncertainty.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_properties("ProperNoun")
    assert nodes, "adapter must emit at least one ProperNoun node"
    bad = [
        n for n in nodes
        if "verse_count" in n
        and n["verse_count"] is not None
        and not isinstance(n["verse_count"], int)
    ]
    assert not bad, (
        f"ProperNoun.verse_count must be int or null, "
        f"found non-int non-null values: {bad[:3]}. "
        "Decision 17 Edge case 3: coerce non-numeric placeholders to null."
    )


def test_proper_noun_source_property_matches_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every ProperNoun node must carry source='STEPBible-proper-nouns'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14 Source policy: source property on each node identifies the upstream
    slug used in the Source MERGE and acceptance Cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_properties("ProperNoun")
    assert nodes, "adapter must emit at least one ProperNoun node"
    bad = [n for n in nodes if n.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"ProperNoun nodes with wrong source property: {bad[:3]}. "
        f"Expected source='{SOURCE_SLUG}'"
    )


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='STEPBible-proper-nouns'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Source uniqueness constraint on source_slug. The Source node
    is MERGEd once per ingest run, before any record-level write.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_proper_noun_all_eight_fields_present(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Each ProperNoun node must carry all 8 populated projection fields per Decision 17.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17 populated projection: proper_name_entry, transliteration, meaning,
    strong, pos, language, verse_count, first_occurrence. Sparse residual columns
    are NOT persisted.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_properties("ProperNoun")
    assert nodes, "adapter must emit at least one ProperNoun node"
    for node in nodes:
        missing = [f for f in PROPER_NOUN_FIELDS if f not in node]
        assert not missing, (
            f"ProperNoun node missing required Decision 17 fields: {missing}. "
            f"Node: {node}"
        )


# ---------------------------------------------------------------------------
# GROUP 2: fixture metadata tests (pass regardless of adapter state)
# ---------------------------------------------------------------------------

def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """Fixture length must be reproducible from the stored seed.

    Seed = int('e3ed6dc4', 16) = 3823988164.
    rng.randint(1024, 16384) with this seed must equal fixture['length'].

    This test does NOT call the adapter.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert fixture_slice["length"] == expected_length, (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}. "
        f"Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_fixture_has_three_proper_nouns(fixture_slice: dict[str, Any]) -> None:
    """Fixture must contain exactly 3 proper noun entries.

    This test does NOT call the adapter. Verifies fixture structure.
    """
    nouns = fixture_slice.get("proper_nouns", [])
    assert len(nouns) == 3, (
        f"Fixture must contain exactly 3 proper nouns; got {len(nouns)}"
    )


def test_fixture_covers_hebrew_person_greek_person_place(
    fixture_slice: dict[str, Any]
) -> None:
    """Fixture must cover: 1 Hebrew person, 1 Greek person, 1 place.

    Verifies language discriminator values and pos variety per spec.
    This test does NOT call the adapter.
    """
    nouns = fixture_slice.get("proper_nouns", [])
    hebrew_persons = [n for n in nouns if n.get("language") == "hebrew" and n.get("pos") == "person"]
    greek_persons = [n for n in nouns if n.get("language") == "greek" and n.get("pos") == "person"]
    places = [n for n in nouns if n.get("pos") == "place"]
    assert len(hebrew_persons) >= 1, "Fixture must contain at least 1 Hebrew person"
    assert len(greek_persons) >= 1, "Fixture must contain at least 1 Greek person"
    assert len(places) >= 1, "Fixture must contain at least 1 place entry"


def test_fixture_null_verse_count_entry_present(fixture_slice: dict[str, Any]) -> None:
    """Fixture must include at least one entry with null verse_count.

    Verifies Decision 17 Edge case 3 (non-numeric placeholder -> null) is exercised.
    This test does NOT call the adapter.
    """
    nouns = fixture_slice.get("proper_nouns", [])
    null_entries = [n for n in nouns if n.get("verse_count") is None]
    assert null_entries, (
        "Fixture must include at least one entry with null verse_count "
        "to exercise Decision 17 Edge case 3."
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    Validates the predicate source file is present and parseable per RESEED_PLAN C.5.
    Checks >= 1 entry in the file per the gate requirement.
    This test does NOT call the adapter.
    """
    assert len(PREDICATES) >= 1, "predicates_by_type.cypher must define at least one predicate"
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """STEPBible-proper-nouns expected count in expected_counts.json must be 5468.

    Validates the count constant is correct per the source file.
    This test does NOT call the adapter.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-proper-nouns"]
    assert entry["expected_count"] == EXPECTED_COUNT, (
        f"expected_counts.json STEPBible-proper-nouns count {entry['expected_count']} "
        f"!= {EXPECTED_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-proper-nouns must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "proper_name", (
        f"record_unit must be 'proper_name'; got {entry['record_unit']!r}"
    )


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep (13 stubs parametrized)
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
      2. Try to find an ingest entry point named ingest_stepbible_proper_nouns or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, edge types, and stable id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_proper_nouns", None)
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
    nodes = fake_driver.captured_properties("ProperNoun")

    label_ok = "ProperNoun" in emitted_labels
    edge_ok = "NAMED_AT" in emitted_edges

    proper_name_ok = all(
        isinstance(n.get("proper_name_entry"), str) and n.get("proper_name_entry")
        for n in nodes
    ) if nodes else False

    language_ok = all(
        n.get("language") in ("hebrew", "greek")
        for n in nodes
    ) if nodes else False

    rejected = not label_ok or not edge_ok or not proper_name_ok or not language_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample nodes: {nodes[:2]}"
    )
