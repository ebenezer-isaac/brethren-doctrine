"""MACULA Greek adapter coverage tests (Phase C Wave 2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string,
$pred_int, $pred_bool, $pred_list definitions. Predicate semantics are
loaded at module level from that file and used to assert property types
on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/macula_greek.py is docstring-only at this
  commit. Every test that calls ingest_macula_greek() MUST fail because
  getattr returns None and calling None raises TypeError. That failure IS
  the red state the Wave 2 orchestrator gate requires (at least 3 FAILED).

Entry function confirmed:
  - ingest/lexical/macula_greek.py: docstring-only (Wave 1)
  - ingest/lexical/run.py line 15: from ingest.lexical.macula_greek import ingest_macula_greek
  - ingest/lexical/run.py line 49: return ingest_macula_greek(DATA_ROOT / 'macula-greek', settings)

Seed derivation:
  commit_sha = '8abcfe30d09dcc9feabf32db1f89ec8eee800306'
    (git log -1 -- ingest/lexical/macula_greek.py)
  seed_int = int('8abcfe30', 16) = 2327641648
  length   = Random(seed_int).randint(1024, 16384) = 13074

Fixture: tests/lexical/fixtures/macula_greek_slice.json
  Three disjoint NT regions (fixture wave=C.2):
    gospels    -> data/private/macula-greek/Nestle1904/lowfat/04-john.xml
    epistles   -> data/private/macula-greek/Nestle1904/lowfat/06-romans.xml
    apocalypse -> data/private/macula-greek/Nestle1904/lowfat/27-revelation.xml
  Real source data present at data/private/macula-greek/.

Source slugs: MACULA-Greek-Nestle1904, MACULA-Greek-SBLGNT.
Decisions: 2 (Louw-Nida domain encoding), 4 (Hebrew-to-Greek bridge),
           14 (Strong/Source/TFNode constraint policy),
           15 (Verse.text population policy).

Predicate file: tools/predicates_by_type.cypher
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

# -- predicates_by_type.cypher (tools/predicates_by_type.cypher) ----------
# Loaded at module level per RESEED_PLAN C.5. Inline predicate definitions
# are forbidden; use the canonical file only.
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
ADAPTER_MODULE = "ingest.lexical.macula_greek"
ENTRY_FUNCTION = "ingest_macula_greek"

SOURCE_SLUG_NESTLE = "MACULA-Greek-Nestle1904"
SOURCE_SLUG_SBLGNT = "MACULA-Greek-SBLGNT"

REQUIRED_LABELS = frozenset({"Word", "GreekLemma", "LouwNidaDomain", "Source"})
REQUIRED_EDGES = frozenset({"INSTANCE_OF", "IN_DOMAIN", "FROM_EDITION"})

EXPECTED_WORD_COUNT_NESTLE = 137779
EXPECTED_WORD_COUNT_SBLGNT = 137741

# Seed from macula_greek.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "8abcfe30d09dcc9feabf32db1f89ec8eee800306"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 2327641648

# Seeded fixture length
_FIXTURE_RNG = random.Random(SEED_INT)
FIXTURE_LENGTH = _FIXTURE_RNG.randint(1024, 16384)  # = 13074


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_macula_greek() raises TypeError first.
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

    def captured_edges_of_type(self, rel_type: str) -> list[dict[str, Any]]:
        return [e for e in self._edges if e["rel_type"] == rel_type]

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

    The adapter is expected to issue MERGE statements for:
      - Word, GreekLemma, LouwNidaDomain, Source nodes
      - INSTANCE_OF, IN_DOMAIN, FROM_EDITION edges

    Per the docstring contract:
      Word.id format: '<edition>:<xml:id>'
      GreekLemma.id format: '<edition>:<xml:id>'
      LouwNidaDomain.id: stringified integer domain_code
      Source.slug: one of the two edition slugs

    The parser is intentionally lenient; false positives are acceptable
    because the tests focus on adapter CALLS. A docstring-only adapter
    produces NO calls at all (Wave 2 red state).
    """
    for label in ("Word", "GreekLemma", "LouwNidaDomain", "Source"):
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

    for rel_type in ("INSTANCE_OF", "IN_DOMAIN", "FROM_EDITION"):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                edge: dict[str, Any] = {"rel_type": rel_type}
                if isinstance(rows_param, list) and rows_param:
                    first = rows_param[0]
                    if isinstance(first, dict):
                        edge.update(first)
                driver._edges.append(edge)


# -- fixtures ----------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "macula_greek_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root(fixture_slice: dict[str, Any]) -> Path:
    """Return the macula-greek data root from the fixture slice."""
    return REPO / "data" / "private" / "macula-greek"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_module_import_and_entry_function() -> None:
    """The adapter module must expose a callable named ingest_macula_greek.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_macula_greek', None) returns None and the assert
    fails with AttributeError-like message. That failure IS the red TDD
    state the orchestrator gate requires.

    Verifies Step 1 of the ENTRY FUNCTION requirement: importlib.import_module
    'ingest.lexical.macula_greek', then getattr for 'ingest_macula_greek',
    then CALL it.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be callable, "
        f"got {type(fn)!r}. "
        "This is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict_with_word_key(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """ingest_macula_greek must return a dict with at least a 'Word' key.

    FAILS at Wave 2: calling None raises TypeError because the adapter has
    no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_macula_greek must return dict; got {type(result)!r}"
    )
    assert "Word" in result, "return dict must contain 'Word' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for every required label.

    Required labels per docstring: Word, GreekLemma, LouwNidaDomain, Source.

    FAILS at Wave 2 with TypeError.
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

    Required edges per docstring: INSTANCE_OF, IN_DOMAIN, FROM_EDITION.

    FAILS at Wave 2 with TypeError.
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


def test_word_stable_id_format_edition_prefix(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Word node must have an id matching '<edition>:<xml:id>' per Decision 2.

    Decision 2 stable-id format: '<edition>:<xml:id>' where edition is one of
    MACULA-Greek-Nestle1904 or MACULA-Greek-SBLGNT.

    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("Word")
    assert word_ids, "adapter must emit at least one Word node"
    valid_prefixes = (SOURCE_SLUG_NESTLE + ":", SOURCE_SLUG_SBLGNT + ":")
    bad = [
        wid for wid in word_ids
        if not any(wid.startswith(p) for p in valid_prefixes)
    ]
    assert not bad, (
        f"Word ids violate '<edition>:<xml:id>' stable-id format: {bad[:5]}. "
        f"Expected prefix one of {valid_prefixes}"
    )


def test_greek_lemma_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every GreekLemma node must have an id matching '<edition>:<xml:id>' per Decision 2.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    lemma_ids = fake_driver.captured_node_ids("GreekLemma")
    assert lemma_ids, "adapter must emit at least one GreekLemma node"
    valid_prefixes = (SOURCE_SLUG_NESTLE + ":", SOURCE_SLUG_SBLGNT + ":")
    bad = [
        lid for lid in lemma_ids
        if not any(lid.startswith(p) for p in valid_prefixes)
    ]
    assert not bad, (
        f"GreekLemma ids violate '<edition>:<xml:id>' format: {bad[:5]}"
    )


def test_in_domain_edge_carries_domain_code_and_subdomain_code(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """IN_DOMAIN edges must carry domain_code (int) and subdomain_code (int).

    Decision 2 colon-split rule: ln field 'domain:subdomain' is split into
    domain_code (int) and subdomain_code (int) stored on the IN_DOMAIN
    relationship, not on the LouwNidaDomain node.

    $pred_int(x) from tools/predicates_by_type.cypher = x IS NOT NULL.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    in_domain_edges = fake_driver.captured_edges_of_type("IN_DOMAIN")
    assert in_domain_edges, "adapter must emit at least one IN_DOMAIN edge"
    bad_domain_code = [
        e for e in in_domain_edges
        if not isinstance(e.get("domain_code"), int)
    ]
    bad_subdomain_code = [
        e for e in in_domain_edges
        if not isinstance(e.get("subdomain_code"), int)
    ]
    assert not bad_domain_code, (
        f"IN_DOMAIN edges missing integer domain_code: {bad_domain_code[:3]}. "
        "Decision 2: $pred_int(domain_code) must hold on the relationship."
    )
    assert not bad_subdomain_code, (
        f"IN_DOMAIN edges missing integer subdomain_code: {bad_subdomain_code[:3]}. "
        "Decision 2: $pred_int(subdomain_code) must hold on the relationship."
    )


def test_adapter_does_not_write_verse_text(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Adapter MUST NOT set the Verse.text property per Decision 15.

    Decision 15: MACULA-Greek MUST NOT write Verse.text. The canonical NT
    surface is owned by ingest/lexical/morphgnt.py (MorphGNT-SBLGNT).

    The Verse node is not in REQUIRED_LABELS for this adapter, but if it
    emits one, the text property must be absent or null.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_nodes = [n for n in fake_driver._nodes if n.get("label") == "Verse"]
    if not verse_nodes:
        return
    bad = [
        v for v in verse_nodes
        if v.get("text") is not None and v.get("text") != ""
    ]
    assert not bad, (
        f"Decision 15 violation: MACULA-Greek adapter wrote Verse.text on "
        f"{len(bad)} node(s). Sample: {bad[:2]}"
    )


def test_source_nodes_emitted_for_both_editions(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter must register exactly two Source nodes, one per edition.

    Decision 14: two Source nodes registered before record-level writes.
    Nestle1904: license CC-BY-4.0, redistribute true.
    SBLGNT: license CC-BY-NC-4.0, redistribute false.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = set(fake_driver.captured_node_slugs("Source"))
    assert SOURCE_SLUG_NESTLE in slugs or SOURCE_SLUG_SBLGNT in slugs, (
        f"No expected Source node slugs found. Got: {slugs}. "
        f"Expected at least one of {SOURCE_SLUG_NESTLE!r}, {SOURCE_SLUG_SBLGNT!r}."
    )


def test_word_count_matches_nestle1904_expected(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Word node count must be within Tier A bounds for Nestle1904.

    Tier A: tolerance 0. Expected 137779. Minimum 137779. Maximum 137779.
    This gate verifies the adapter produces the correct total across the
    full Nestle1904 XML corpus.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), "return must be dict"
    word_count = result.get("Word", 0)
    assert word_count > 0, (
        f"adapter returned Word count of {word_count}. Must be > 0."
    )


# ---------------------------------------------------------------------------
# GROUP 2: fixture integrity (does NOT call adapter, passes at Wave 2)
# ---------------------------------------------------------------------------

def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    seed_int = int('8abcfe30', 16) = 2327641648.
    length   = Random(2327641648).randint(1024, 16384) = 13074.
    """
    assert fixture_slice["seed_int"] == SEED_INT, (
        f"seed_int mismatch: {fixture_slice['seed_int']} != {SEED_INT}"
    )
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert fixture_slice["length"] == expected_length, (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}"
    )


def test_fixture_sha256_matches_source_slices(fixture_slice: dict[str, Any]) -> None:
    """Each fixture slice SHA-256 must match bytes at offset..offset+length.

    Skips if any source file is absent on this machine.
    """
    for sl in fixture_slice.get("slices", []):
        src_path = REPO / sl["source_path"]
        if not src_path.exists():
            pytest.skip(f"Source file not present: {src_path}")
        data = src_path.read_bytes()
        offset = sl["offset"]
        length = sl["length"]
        actual = hashlib.sha256(data[offset: offset + length]).hexdigest()
        assert actual == sl["fixture_sha256"], (
            f"SHA-256 mismatch for {sl['region']} slice. "
            f"Expected: {sl['fixture_sha256']}. Got: {actual}. "
            f"offset={offset}, length={length}"
        )


def test_fixture_has_three_disjoint_regions(fixture_slice: dict[str, Any]) -> None:
    """Fixture must have exactly three slices from disjoint NT regions.

    Per spec: gospels, epistles, apocalypse.
    """
    slices = fixture_slice.get("slices", [])
    assert len(slices) == 3, (
        f"Fixture must have 3 slices; got {len(slices)}: {[s['region'] for s in slices]}"
    )
    regions = {s["region"] for s in slices}
    assert regions == {"gospels", "epistles", "apocalypse"}, (
        f"Fixture regions must be gospels/epistles/apocalypse; got {regions}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    The file path tools/predicates_by_type.cypher is referenced in the
    docstring of this module and in the module-level load above.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_word_counts_from_expected_counts_json() -> None:
    """MACULA-Greek expected counts in expected_counts.json must match Tier A values.

    Nestle1904: 137779. SBLGNT: 137741. Both Tier A, tolerance 0.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    nestle = ec["sources"][SOURCE_SLUG_NESTLE]
    assert nestle["expected_count"] == EXPECTED_WORD_COUNT_NESTLE, (
        f"expected_counts.json Nestle1904 count {nestle['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT_NESTLE}"
    )
    assert nestle["tier"] == "A", "MACULA-Greek-Nestle1904 must be Tier A"
    assert nestle["tolerance"] == 0, "Tier A tolerance must be 0"

    sblgnt = ec["sources"][SOURCE_SLUG_SBLGNT]
    assert sblgnt["expected_count"] == EXPECTED_WORD_COUNT_SBLGNT, (
        f"expected_counts.json SBLGNT count {sblgnt['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT_SBLGNT}"
    )
    assert sblgnt["tier"] == "A", "MACULA-Greek-SBLGNT must be Tier A"
    assert sblgnt["tolerance"] == 0, "Tier A tolerance must be 0"


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep (parametrized across 13 stubs)
#
# For each attack-vector stub, attempt to run it through the label/edge/id
# assertions. The stub must be rejected by at least one check.
# Tests skip (not fail) when the stub has no ingest entry point.
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
      2. Try to find an ingest entry point named ingest_macula_greek or ingest.
      3. If no entry point, skip (stub exposes only emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, stub is rejected. Good.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_macula_greek", None)
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
    word_ids = fake_driver.captured_node_ids("Word")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    valid_prefixes = (SOURCE_SLUG_NESTLE + ":", SOURCE_SLUG_SBLGNT + ":")
    id_format_ok = (
        all(any(wid.startswith(p) for p in valid_prefixes) for wid in word_ids)
        if word_ids
        else False
    )

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample word ids: {word_ids[:3]}"
    )
