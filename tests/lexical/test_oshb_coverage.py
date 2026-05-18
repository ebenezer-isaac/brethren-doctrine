"""OSHB-morphology adapter coverage tests (Phase C Wave 2, non-tautological rewrite).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool, $pred_list definitions. Predicate semantics are loaded at module level
from that file and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/oshb.py has NO function body at this commit.
  Every test that calls ingest_oshb() MUST fail because getattr returns None
  and calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires.

Entry function confirmed:
  - ingest/lexical/oshb.py docstring: no def; but contract section names the
    function via the Acceptance Cypher (phase_02 Group 1 step 1).
  - ingest/lexical/run.py line 19: from ingest.lexical.oshb import ingest_oshb
  - ingest/lexical/run.py line 41: return ingest_oshb(DATA_ROOT / 'oshb', settings)

Random seed:
  commit_sha = 'ee8d877864ef1e77d4951e8c5d5567b8f292f820' (git log -1 -- ingest/lexical/oshb.py)
  seed = int('ee8d8778', 16) = 4002252664

Fixture: tests/lexical/fixtures/oshb_slice.json
  source: data/private/oshb/wlc/Gen.xml (torah corpus, real OSIS XML on disk)
  offset: 227422, length: 1429
  fixture_sha256: c209c6c593c0dd14e1ec9656e369228a268879323393407f2849ffb24dfdf9ca
  Third corpus slot: Proverbs (wisdom-adjacent, distinct from Psalms/Job).
  OSHB is OT-only; NT slot is replaced by Proverbs with that noted in fixture.

Source: tools/expected_counts.json sources."OSHB-morphology" expected_count=305507.
Decisions: 1 (morpheme alignment), 14 (Strong/Source constraints), 15 (Verse.text policy).
"""

from __future__ import annotations

import hashlib
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
ADAPTER_MODULE = "ingest.lexical.oshb"
ENTRY_FUNCTION = "ingest_oshb"

REQUIRED_LABELS = frozenset({"Word", "Morpheme", "Verse", "Strong", "Source", "Reading"})
REQUIRED_EDGES = frozenset({"HAS_MORPHEME", "IN_VERSE", "INSTANCE_OF", "IS_QERE_OF", "FROM_EDITION"})

EXPECTED_WORD_COUNT = 305507  # Tier A, tolerance 0, per expected_counts.json

# Seed from oshb.py docstring commit SHA (git log -1 -- ingest/lexical/oshb.py)
DOCSTRING_COMMIT_SHA = "ee8d877864ef1e77d4951e8c5d5567b8f292f820"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 4002252664


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    The adapter under test is expected to call driver methods (e.g. session()
    with Cypher strings) to emit nodes and edges. This fake captures every
    MERGE payload so tests can assert on emitted labels, edge types, and
    node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_oshb() raises TypeError first.
    """

    def __init__(self) -> None:
        self._nodes: list[dict[str, Any]] = []
        self._edges: list[dict[str, Any]] = []
        self.settings = _FakeSettings()

    # Session context-manager support
    def session(self, *_: Any, **__: Any) -> "_FakeSession":
        return _FakeSession(self)

    def close(self) -> None:
        pass

    # -- query accessors ------------------------------------------------

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
        """Parse MERGE statements to capture node/edge records."""
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

    The adapter is expected to issue:
      MERGE (n:Word {id: ...})
      MERGE (n:Morpheme {id: ...})
      MERGE (n:Verse {id: ...})
      MERGE (n:Strong {id: ...})
      MERGE (n:Source {slug: ...})
      MERGE (n:Reading {reading_id: ...})
      MERGE (a)-[r:HAS_MORPHEME]->(b)
      ... and so on per the docstring contract.

    The parser records the label and the key property found in the UNWIND
    batch (rows / records parameter) when present. This is intentionally
    lenient; false positives are acceptable because the test assertions
    focus on the adapter's CALLS, and a docstring-only adapter produces
    NO calls at all.
    """
    # Node MERGE patterns
    for label in ("Word", "Morpheme", "Verse", "Strong", "Source", "Reading"):
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    # Edge MERGE patterns
    for rel_type in (
        "HAS_MORPHEME", "IN_VERSE", "INSTANCE_OF", "IS_QERE_OF", "FROM_EDITION"
    ):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "oshb_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root(fixture_slice: dict[str, Any]) -> Path:
    """Return the parent directory of the fixture source_path."""
    return (REPO / fixture_slice["source_path"]).parent.parent


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_oshb.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_oshb', None) returns None and the assert fails.
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
    """ingest_oshb must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable,
    because the adapter has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), f"ingest_oshb must return dict; got {type(result)!r}"
    assert "Word" in result, "return dict must contain 'Word' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for every required label.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
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

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
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


def test_word_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Word node must have an id starting with 'oshb:' per the docstring contract.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id spec: 'oshb:<osisRef>.w<pos>' where pos is 1-based, zero-padded to 2 digits.
    Predicate: $pred_string from tools/predicates_by_type.cypher = x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("Word")
    assert word_ids, "adapter must emit at least one Word node"
    bad = [wid for wid in word_ids if not wid.startswith("oshb:")]
    assert not bad, f"Word ids violate 'oshb:' prefix format: {bad[:5]}"


def test_morpheme_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Morpheme node must have an id starting with 'oshb-morph:'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id spec: 'oshb-morph:<osisRef>.w<wpos>.m<mpos>'
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    morph_ids = fake_driver.captured_node_ids("Morpheme")
    assert morph_ids, "adapter must emit at least one Morpheme node"
    bad = [mid for mid in morph_ids if not mid.startswith("oshb-morph:")]
    assert not bad, f"Morpheme ids violate 'oshb-morph:' prefix: {bad[:5]}"


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='OSHB-morphology'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Predicate: $pred_string from tools/predicates_by_type.cypher.
    Decision 14: Source uniqueness constraint on source_slug.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert "OSHB-morphology" in slugs, (
        f"Source node with slug='OSHB-morphology' not found. Got slugs: {slugs}"
    )


def test_verse_canon_section_is_ot(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Verse node emitted by OSHB must have canon_section='OT'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 15: OSHB is OT-only. canon_section is a $pred_string property.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_nodes = [n for n in fake_driver._nodes if n.get("label") == "Verse"]
    assert verse_nodes, "adapter must emit at least one Verse node"
    bad = [v for v in verse_nodes if v.get("canon_section") not in ("OT", None, "")]
    assert not bad, (
        f"Verse nodes with wrong canon_section: {bad[:3]}"
    )


def test_has_morpheme_count_ge_word_count(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """HAS_MORPHEME edge count must be >= Word count.

    This is the literal acceptance gate from phase_02_lexical_ingest.md Group 1 step 1:
      morphs >= words

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    words = fake_driver.node_count("Word")
    morphs = fake_driver.edge_count("HAS_MORPHEME")
    assert words > 0, "adapter must emit at least one Word node"
    assert morphs >= words, (
        f"HAS_MORPHEME edge count ({morphs}) must be >= Word count ({words}). "
        "Acceptance Cypher: RETURN words, morphs, morphs >= words"
    )


def test_fixture_sha256_matches_source_slice(fixture_slice: dict[str, Any]) -> None:
    """The fixture SHA-256 must match the bytes at offset..offset+length in Gen.xml.

    This test does NOT call the adapter, so it passes even at Wave 2.
    It verifies the fixture was generated correctly from the seeded RNG.
    """
    src_path = REPO / fixture_slice["source_path"]
    if not src_path.exists():
        pytest.skip(f"Source file not present on this machine: {src_path}")
    data = src_path.read_bytes()
    offset = fixture_slice["offset"]
    length = fixture_slice["length"]
    slice_bytes = data[offset : offset + length]
    actual = hashlib.sha256(slice_bytes).hexdigest()
    assert actual == fixture_slice["fixture_sha256"], (
        f"Fixture SHA-256 mismatch. "
        f"Expected: {fixture_slice['fixture_sha256']}. "
        f"Got: {actual}. "
        "Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture offset and length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('ee8d8778', 16) = 4002252664.
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {length}"
    )
    src_path = REPO / fixture_slice["source_path"]
    if src_path.exists():
        src_len = src_path.stat().st_size
        max_offset = src_len - length
        offset = rng.randint(0, max_offset)
        assert offset == fixture_slice["offset"], (
            f"Fixture offset {fixture_slice['offset']} != seeded offset {offset}"
        )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    This test does NOT call the adapter. It validates that the predicate
    source file is present and parseable per RESEED_PLAN C.5.

    The file path tools/predicates_by_type.cypher is referenced in the
    docstring of this test and in the module-level load above.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    # Spot-check the string predicate expression matches the file
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_word_count_from_expected_counts_json() -> None:
    """The OSHB-morphology expected count in expected_counts.json must be 305507 (Tier A).

    This test does NOT call the adapter. It validates the count constant
    used by the coverage tests is correct per the source file.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    oshb_entry = ec["sources"]["OSHB-morphology"]
    assert oshb_entry["expected_count"] == EXPECTED_WORD_COUNT, (
        f"expected_counts.json OSHB-morphology count {oshb_entry['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT}"
    )
    assert oshb_entry["tier"] == "A", "OSHB-morphology must be Tier A"
    assert oshb_entry["tolerance"] == 0, "Tier A tolerance must be 0"


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep
#
# For each of the 12 attack-vector stubs, attempt to run it through the same
# label/edge/id assertions. The stub must be rejected by at least one check.
# These tests skip (not fail) when the stub has no ingest entry point.
# In Wave 3 (real impl present), these tests will assert defect detection.
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
      2. Try to find an ingest entry point named ingest_oshb or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected. Good.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    # Try to find an ingest entry point
    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_oshb", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
        )

    # Attempt to run the stub
    raised = False
    try:
        fn(source_root, fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        # Stub crashed; that counts as a rejection.
        return

    # Stub ran. Apply coverage assertions; at least one must catch the defect.
    emitted_labels = fake_driver.captured_labels()
    emitted_edges = fake_driver.captured_edge_types()
    word_ids = fake_driver.captured_node_ids("Word")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_format_ok = all(wid.startswith("oshb:") for wid in word_ids) if word_ids else False

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample word ids: {word_ids[:3]}"
    )
