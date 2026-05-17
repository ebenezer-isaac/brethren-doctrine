"""MorphGNT-SBLGNT adapter coverage tests (Phase C Wave 2, non-tautological scaffold).

This file references tools/predicates_by_type.cypher for $pred_string definitions.
Predicate semantics are loaded at module level from that file and used to assert
property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/morphgnt.py has NO function body at this commit.
  Every test that calls ingest_morphgnt() MUST fail because getattr returns None
  and calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires.

Entry function confirmed:
  - ingest/lexical/morphgnt.py docstring: no def; contract names the function.
  - ingest/lexical/run.py line 17: from ingest.lexical.morphgnt import ingest_morphgnt
  - ingest/lexical/run.py line 47: return ingest_morphgnt(DATA_ROOT / 'morphgnt', settings)

Random seed:
  commit_sha = 'e08001ccfdaf28d3496632e5d0aaa722b28cb9c6' (git log -1 -- ingest/lexical/morphgnt.py)
  seed = int('e0800100', 16) = int(commit_sha[:8], 16) = 3766485452

Fixture: tests/lexical/fixtures/morphgnt_slice.json
  source: data/private/morphgnt/ (gospels, epistles, apocalypse regions)
  verses: Matt.16.7 (gospels), Rom.8.30 (epistles), Rev.12.9 (apocalypse)
  byte_length: 14968

Decision 15: Verse.text population policy (NT verses).
  MorphGNT-SBLGNT is the canonical NT populator of Verse.text.
  Concatenates per-word text field in document order, single-space joined,
  byte-identical to upstream, no diacritic normalization.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# -- predicates_by_type.cypher -------------------------------------------------
# Loaded at module level per RESEED_PLAN C.5; inline predicates forbidden.
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

# -- adapter constants ---------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.morphgnt"
ENTRY_FUNCTION = "ingest_morphgnt"

REQUIRED_LABELS = frozenset({"Word", "Verse"})
REQUIRED_EDGES = frozenset({"PARSE_OF", "IN_VERSE"})

EXPECTED_WORD_COUNT = 137554  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "e08001ccfdaf28d3496632e5d0aaa722b28cb9c6"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3766485452

STABLE_ID_RE = re.compile(r"^morphgnt-sblgnt:[A-Za-z0-9]+\.\d+\.\d+\.w\d{2}$")


# -- FakeDriver that records every node/edge the adapter emits -----------------


class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on labels, edge types,
    and node-id formats without touching a live graph.

    At Wave 2 (docstring-only adapter) the driver is never reached because
    calling ingest_morphgnt() raises TypeError first.
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

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n["label"] == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)

    def nodes_by_label(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n["label"] == label]


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

    The MorphGNT adapter is expected to issue:
      MERGE (n:Word {id: ...}) with source='MorphGNT-SBLGNT'
      MERGE (n:Verse {id: ...}) with osis, text, canon_section
      MERGE (a)-[r:IN_VERSE]->(b)
      MERGE (a)-[r:PARSE_OF]->(b)

    The $pred_string predicate (tools/predicates_by_type.cypher) is the
    type-check used for all string properties on Word and Verse nodes.
    """
    for label in ("Word", "Verse"):
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("PARSE_OF", "IN_VERSE"):
        if f"`{rel_type}`" in cypher or f":{rel_type}]" in cypher or f":{rel_type}" in cypher:
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# -- fixtures ------------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "morphgnt_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    return REPO / "data" / "private" / "morphgnt"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_morphgnt.

    FAILS at Wave 2: adapter has no function body, so
    getattr(mod, 'ingest_morphgnt', None) returns None and the assert fails.
    That failure IS the expected red TDD state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_morphgnt must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError or TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), f"ingest_morphgnt must return dict; got {type(result)!r}"
    assert "Word" in result, "return dict must contain 'Word' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for Word and Verse labels.

    FAILS at Wave 2 with AttributeError or TypeError.

    Labels per docstring: Word {source: 'MorphGNT-SBLGNT'}, Verse.
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
    """Running the adapter must merge PARSE_OF and IN_VERSE edges.

    FAILS at Wave 2 with AttributeError or TypeError.

    Edges per docstring: PARSE_OF (Word to MACULA Word), IN_VERSE (Word to Verse).
    The $pred_string predicate from predicates_by_type.cypher applies to all
    string properties on both endpoints of these edges.
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
    """Every Word node must have a stable_id matching 'morphgnt-sblgnt:<osisRef>.w<NN>'.

    FAILS at Wave 2 with AttributeError or TypeError.

    Per docstring: 'morphgnt-sblgnt:<osisRef>.w<pos>' where pos is 1-based,
    two-digit zero-padded (w01, w02 ... w27).
    Predicate: $pred_string(x) from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("Word")
    assert word_ids, "adapter must emit at least one Word node"
    bad = [wid for wid in word_ids if not wid.startswith("morphgnt-sblgnt:")]
    assert not bad, f"Word ids violate 'morphgnt-sblgnt:' prefix format: {bad[:5]}"
    bad_re = [wid for wid in word_ids if not STABLE_ID_RE.match(wid)]
    assert not bad_re, f"Word ids violate stable_id regex: {bad_re[:5]}"


def test_word_source_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Word node must carry source='MorphGNT-SBLGNT'.

    FAILS at Wave 2 with AttributeError or TypeError.

    The source property is a $pred_string field per Decision 15 field table.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_nodes = fake_driver.nodes_by_label("Word")
    assert word_nodes, "adapter must emit at least one Word node"
    bad = [n for n in word_nodes if n.get("source") != "MorphGNT-SBLGNT"]
    assert not bad, (
        f"Word nodes with wrong or missing source property: {bad[:3]}"
    )


def test_verse_canon_section_is_nt(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Verse node emitted by MorphGNT must have canon_section='NT'.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 15: MorphGNT only covers the Greek NT; canon_section='NT' on
    every Verse node. The $pred_string predicate applies to canon_section.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_nodes = fake_driver.nodes_by_label("Verse")
    assert verse_nodes, "adapter must emit at least one Verse node"
    bad = [v for v in verse_nodes if v.get("canon_section") not in ("NT", None, "")]
    assert not bad, f"Verse nodes with wrong canon_section: {bad[:3]}"


def test_verse_text_single_space_join(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Verse.text must be single-space joined per-word text, no leading/trailing spaces.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 15: byte-identical to upstream surface tokens joined by single
    ASCII space (U+0020); no diacritic normalization; no leading or trailing
    whitespace. $pred_string(text) must be true for every populated Verse.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_nodes = fake_driver.nodes_by_label("Verse")
    assert verse_nodes, "adapter must emit at least one Verse node"
    for v in verse_nodes:
        text = v.get("text")
        if text is None:
            continue
        assert isinstance(text, str), f"Verse.text must be str, got {type(text)!r}"
        assert text == text.strip(), (
            f"Verse.text must not have leading/trailing whitespace: {text!r}"
        )
        assert "  " not in text, (
            f"Verse.text must use single-space joins, found double-space: {text!r}"
        )


def test_expected_word_count_from_expected_counts_json() -> None:
    """The MorphGNT-SBLGNT expected count in expected_counts.json must be 137554 (Tier A).

    Does NOT call the adapter. Validates the count constant matches the source file.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["MorphGNT-SBLGNT"]
    assert entry["expected_count"] == EXPECTED_WORD_COUNT, (
        f"expected_counts.json MorphGNT-SBLGNT count {entry['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT}"
    )
    assert entry["tier"] == "A", "MorphGNT-SBLGNT must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool, list predicates.

    Does NOT call the adapter. Validates the predicate file referenced in the
    module docstring (tools/predicates_by_type.cypher) is present and parseable.

    The $pred_string predicate is applied to all string fields in Decision 15
    (bcv, pos, parsing_code, text, word, normalized, lemma, osis, canon_section).
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture must reproduce from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('e0800100', 16) = 3766485452.
    Verified: seed_int in morphgnt_slice.json matches the seeded derivation.
    """
    import random

    rng = random.Random(SEED_INT)
    target_length = rng.randint(1024, 16384)
    assert target_length == fixture_slice["target_length"], (
        f"Fixture target_length {fixture_slice['target_length']} "
        f"!= seeded target_length {target_length}"
    )
    assert fixture_slice["seed_int"] == SEED_INT, (
        f"Fixture seed_int {fixture_slice['seed_int']} != expected {SEED_INT}"
    )


def test_fixture_has_three_disjoint_regions(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain exactly 3 verses from gospels, epistles, apocalypse.

    Does NOT call the adapter.
    """
    verses = fixture_slice["verses"]
    assert len(verses) == 3, f"Expected 3 verses, got {len(verses)}"
    regions = {v["region"] for v in verses}
    assert regions == {"gospels", "epistles", "apocalypse"}, (
        f"Expected regions gospels/epistles/apocalypse, got {regions}"
    )


def test_fixture_stable_ids_match_format(fixture_slice: dict[str, Any]) -> None:
    """All stable_ids in the fixture must match 'morphgnt-sblgnt:<osisRef>.w<NN>'.

    Does NOT call the adapter. Validates the fixture itself is correct.
    """
    for verse in fixture_slice["verses"]:
        for word in verse["words"]:
            sid = word["stable_id"]
            assert STABLE_ID_RE.match(sid), (
                f"stable_id {sid!r} does not match expected format"
            )
            assert sid.startswith("morphgnt-sblgnt:"), f"Bad prefix: {sid}"
            pos = int(sid.split(".w")[1])
            assert 1 <= pos <= 99, f"pos out of range: {pos}"


def test_fixture_verse_text_single_space_join_policy(
    fixture_slice: dict[str, Any],
) -> None:
    """Fixture verse_text must equal single-space join of word text fields (Decision 15).

    NT verses; byte-identical to upstream; single-space joined; no diacritic normalization.
    This test validates the fixture itself encodes Decision 15 correctly.
    """
    for verse in fixture_slice["verses"]:
        expected = " ".join(w["text"] for w in verse["words"])
        actual = verse["verse_text"]
        assert actual == expected, (
            f"Verse {verse['osis_ref']} verse_text is not single-space join of word text: "
            f"expected {expected[:60]!r} ... got {actual[:60]!r}"
        )
        assert actual == actual.strip(), (
            f"Verse {verse['osis_ref']} verse_text has leading/trailing whitespace"
        )


def test_fixture_byte_length_in_range(fixture_slice: dict[str, Any]) -> None:
    """The fixture file must be between 1024 and 16384 bytes when encoded UTF-8.

    This constraint ensures the fixture stays reviewable and matches the
    seeded target_length band used by the oshb and morphgnt Wave 2 verifiers.
    """
    p = REPO / "tests" / "lexical" / "fixtures" / "morphgnt_slice.json"
    byte_length = len(p.read_bytes())
    assert 1024 <= byte_length <= 16384, (
        f"morphgnt_slice.json byte length {byte_length} is outside [1024, 16384]"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep
#
# For each of the 13 attack-vector stubs, attempt to run it through the same
# label/edge/id assertions. The stub must be rejected by at least one check.
# These tests skip (not fail) when the stub has no ingest entry point.
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
      2. Try to find an ingest entry point named ingest_morphgnt or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, stub is rejected.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_morphgnt", None)
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
    id_format_ok = (
        all(wid.startswith("morphgnt-sblgnt:") for wid in word_ids)
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
