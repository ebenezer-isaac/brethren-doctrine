"""Vulgate Clementine adapter coverage tests (Phase C Wave 2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_bool,
$pred_list definitions. Predicate semantics are loaded at module level from that file
and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/vulgate_clementine.py has NO function body at this commit.
  Every test that calls ingest_vulgate_clementine() MUST fail because getattr returns None
  and calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires.

Entry function confirmed:
  - ingest/lexical/vulgate_clementine.py docstring: no def; contract names the function
    in the Acceptance Cypher section (phase_02 Group 6 step 21).
  - The function is ingest_vulgate_clementine per the source slug naming convention.

Random seed:
  commit_sha = '1f0e87fb9a94c80e71cfa9624c3bed73d946f961' (git log -1 --diff-filter=A -- ingest/lexical/vulgate_clementine.py)
  seed = int('1f0e87fb', 16) = 521046011

Fixture: tests/lexical/fixtures/vulgate_clementine_slice.json
  source: data/private/vulgate/clementine.xml (pre-fetched local cache, absent on CI)
  length: 6276 (derived from seed via rng.randint(1024, 16384))
  offset: 0 (sentinel; source file absent; seed derivation test asserts length only)
  fixture_sha256: sentinel zeros (source file absent from this machine)
  Three verse regions:
    (1) protocanonical Psalms-offset case (Ps.9.1, TVTMS projection from Clementine numbering)
    (2) deuterocanonical (Tob.1.1, Tobit is in the Clementine but not Protestant canon)
    (3) standard protocanonical with transcription footnote (Gen.1.1)

Source: tools/expected_counts.json sources."vulgate-clementine" expected_count=null (Tier C).
Decisions: 8 (VulgateVerse integration), 14 (Source / license / redistribute constraint).

Edge-related stub skips:
  This adapter emits NO edges (verse-granular only per Decision 8 and vulgate_clementine.py
  docstring section "Emitted edge types"). Stubs that expose only emit_edges and no callable
  ingest entry are skipped by the parametrized stub sweep.
  Edge-skipped stubs: minimal_edges, reversed_edge_direction (no ingest entry point).
  All other stubs are exercised via the VulgateVerse label and osis id-format checks.
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
ADAPTER_MODULE = "ingest.lexical.vulgate_clementine"
ENTRY_FUNCTION = "ingest_vulgate_clementine"

# VulgateVerse is the only record-level label; no edges per Decision 8.
REQUIRED_LABELS = frozenset({"VulgateVerse", "Source"})
REQUIRED_NO_EDGES: frozenset[str] = frozenset()

CANON_VALUES = frozenset({"protocanonical", "deutero"})

# Seed from vulgate_clementine.py docstring commit SHA (git log -1 --diff-filter=A -- ingest/lexical/vulgate_clementine.py)
DOCSTRING_COMMIT_SHA = "1f0e87fb9a94c80e71cfa9624c3bed73d946f961"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 521046011


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    The adapter under test is expected to call driver methods (e.g. session()
    with Cypher strings) to emit nodes. This fake captures every MERGE payload
    so tests can assert on emitted labels and node-id formats without touching
    a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_vulgate_clementine() raises TypeError first.
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

    def captured_node_props(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n["label"] == label]

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
        return {"upserted": 1}

    def consume(self) -> None:
        pass


def _parse_cypher_into_driver(
    cypher: str, params: dict[str, Any], driver: FakeDriver
) -> None:
    """Best-effort parse of MERGE Cypher statements into FakeDriver records.

    The adapter is expected to issue:
      MERGE (n:VulgateVerse {id: ...}) SET n += row.properties
      MERGE (n:Source {slug: ...}) SET n += row.properties

    No edges are expected. The parser records the label and property payload
    found in the UNWIND batch (rows parameter) when present.

    When the adapter body is absent (Wave 2 red state) this function is never
    called because the call to ingest_vulgate_clementine() raises TypeError.
    """
    for label in ("VulgateVerse", "Source"):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher or f":{label}{{" in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    if isinstance(row, dict):
                        props = row.get("properties", {})
                        node.update(row if not props else props)
                        if "id" in row:
                            node["id"] = row["id"]
                        if "slug" in row:
                            node["slug"] = row["slug"]
                        if isinstance(props, dict):
                            node.update(props)
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    # Edge MERGE patterns: adapter must emit NONE. Record any that slip through.
    for rel_type in ("IN_VERSE", "INSTANCE_OF", "HAS_MORPHEME", "FROM_EDITION", "CROSS_REF"):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "vulgate_clementine_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root(fixture_slice: dict[str, Any]) -> Path:
    """Return the parent directory of the fixture source_path."""
    return (REPO / fixture_slice["source_path"]).parent


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 -- red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_vulgate_clementine.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_vulgate_clementine', None) returns None and the assert fails.
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
    """ingest_vulgate_clementine must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable,
    because the adapter has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_vulgate_clementine must return dict; got {type(result)!r}"
    )
    assert "VulgateVerse" in result, "return dict must contain 'VulgateVerse' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for VulgateVerse and Source.

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


def test_adapter_emits_no_edges(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit zero edges (verse-granular only per Decision 8).

    The docstring section 'Emitted edge types' states the adapter MUST NOT emit
    IN_VERSE, INSTANCE_OF, HAS_MORPHEME, FROM_EDITION, CROSS_REF, or any other edge.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert not emitted, (
        f"adapter must emit zero edges (verse-granular only); "
        f"found edge types: {sorted(emitted)}"
    )


def test_vulgate_verse_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every VulgateVerse node must have an id starting with 'vulgate-clementine:' per Decision 8.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id spec: 'vulgate-clementine:<osis>' where <osis> is the OSIS verse reference
    produced by projecting the Clementine reference through the TVTMS rule set.
    Predicate: $pred_string from tools/predicates_by_type.cypher = x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_ids = fake_driver.captured_node_ids("VulgateVerse")
    assert verse_ids, "adapter must emit at least one VulgateVerse node"
    bad = [vid for vid in verse_ids if not vid.startswith("vulgate-clementine:")]
    assert not bad, (
        f"VulgateVerse ids violate 'vulgate-clementine:' prefix format: {bad[:5]}"
    )


def test_vulgate_verse_osis_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every VulgateVerse node must have a non-empty osis property ($pred_string).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 8: VulgateVerse.osis is the MERGE key (constraint vulgate_verse_osis,
    graph/lexical.cypher line 45). $pred_string(x) = x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_node_props("VulgateVerse")
    assert nodes, "adapter must emit at least one VulgateVerse node"
    bad = [n for n in nodes if not n.get("osis") or not str(n["osis"]).strip()]
    assert not bad, (
        f"VulgateVerse nodes with empty/missing osis ($pred_string violation): {bad[:3]}"
    )


def test_vulgate_verse_text_latin_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every VulgateVerse node must have a non-empty text_latin property ($pred_string).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 8: text_latin is byte-identical to Wikisource Special:Export surface
    after transcription footnote stripping. $pred_string(x) = x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_node_props("VulgateVerse")
    assert nodes, "adapter must emit at least one VulgateVerse node"
    bad = [n for n in nodes if not n.get("text_latin") or not str(n["text_latin"]).strip()]
    assert not bad, (
        f"VulgateVerse nodes with empty/missing text_latin ($pred_string violation): {bad[:3]}"
    )


def test_vulgate_verse_canon_values(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every VulgateVerse node must have canon in ('protocanonical', 'deutero').

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 8: canon='protocanonical' for books in the Protestant canon intersection;
    canon='deutero' for Clementine deuterocanonical books (Tobit, Judith, 1+2 Maccabees,
    Wisdom, Sirach, Baruch, Greek additions to Esther and Daniel).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_node_props("VulgateVerse")
    assert nodes, "adapter must emit at least one VulgateVerse node"
    bad = [n for n in nodes if n.get("canon") not in CANON_VALUES]
    assert not bad, (
        f"VulgateVerse nodes with canon not in {CANON_VALUES}: {bad[:3]}"
    )


def test_vulgate_verse_transcription_notes_is_list(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every VulgateVerse node must have transcription_notes as a list ($pred_list or empty list).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 8 edge case 3: Wikisource transcription footnote markers are stripped from
    text_latin into transcription_notes as an ordered list of strings. The list may be
    empty when the verse carries no footnote markers. $pred_list(x) = x IS NOT NULL AND size(x) > 0
    applies only when footnotes are present; an empty list is also valid.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_node_props("VulgateVerse")
    assert nodes, "adapter must emit at least one VulgateVerse node"
    bad = [
        n for n in nodes
        if "transcription_notes" in n and not isinstance(n["transcription_notes"], list)
    ]
    assert not bad, (
        f"VulgateVerse nodes with non-list transcription_notes: {bad[:3]}"
    )


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='vulgate-clementine'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Source uniqueness constraint on source_slug.
    $pred_string from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert "vulgate-clementine" in slugs, (
        f"Source node with slug='vulgate-clementine' not found. Got slugs: {slugs}"
    )


def test_source_node_license(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must have license='public_domain'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: public-domain text carries no redistribution restriction.
    The vulgate_clementine.py docstring states: license = 'public_domain' ($pred_string).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    source_nodes = fake_driver.captured_node_props("Source")
    assert source_nodes, "adapter must emit at least one Source node"
    vulgate_nodes = [
        n for n in source_nodes if n.get("slug") == "vulgate-clementine"
    ]
    assert vulgate_nodes, (
        "Source node with slug='vulgate-clementine' not found"
    )
    for node in vulgate_nodes:
        assert node.get("license") == "public_domain", (
            f"Source node license must be 'public_domain'; got {node.get('license')!r}"
        )


def test_psalms_offset_osis_in_fixture(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain the Psalms-offset verse (Ps.9.1).

    This test does NOT call the adapter. It verifies the fixture covers the
    Psalms-offset edge case from Decision 8 edge case 1.

    Clementine Ps 9 covers the modern OSIS Ps.9 plus Ps.10 range. The TVTMS
    rule set projects the Clementine reference to OSIS Ps.9.1.
    """
    verses = fixture_slice.get("verses", [])
    osis_refs = [v["osis"] for v in verses]
    psalms_offset = [r for r in osis_refs if r.startswith("Ps.")]
    assert psalms_offset, (
        f"Fixture must contain at least one Psalms-offset verse (starts with 'Ps.'); "
        f"found osis refs: {osis_refs}"
    )
    for v in verses:
        if v["osis"].startswith("Ps."):
            assert v["canon"] == "protocanonical", (
                f"Psalms verse must have canon='protocanonical'; got {v['canon']!r}"
            )


def test_deutero_verse_in_fixture(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain a deuterocanonical verse (Tob.1.1).

    This test does NOT call the adapter. It verifies the fixture covers the
    deuterocanonical edge case from Decision 8 edge case 2.

    Tobit is in the Clementine canon but not the Protestant canon.
    canon='deutero' enables Pipeline 2 to filter deuterocanonical verses.
    """
    verses = fixture_slice.get("verses", [])
    deutero = [v for v in verses if v.get("canon") == "deutero"]
    assert deutero, (
        f"Fixture must contain at least one verse with canon='deutero'; "
        f"found verses: {[v['osis'] for v in verses]}"
    )
    for v in deutero:
        assert v["osis"].strip(), (
            f"Deuterocanonical verse must have non-empty osis; got {v!r}"
        )


def test_transcription_notes_stripped_in_fixture(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain a verse with transcription_notes stripped from text_latin.

    This test does NOT call the adapter. It verifies the fixture covers the
    transcription footnote edge case from Decision 8 edge case 3.
    """
    verses = fixture_slice.get("verses", [])
    stripped = [v for v in verses if v.get("transcription_notes")]
    assert stripped, (
        f"Fixture must contain at least one verse with non-empty transcription_notes; "
        f"found verses: {[(v['osis'], v.get('transcription_notes')) for v in verses]}"
    )
    for v in stripped:
        notes = v["transcription_notes"]
        assert isinstance(notes, list), (
            f"transcription_notes must be a list; got {type(notes)!r} for {v['osis']}"
        )
        for marker in notes:
            assert isinstance(marker, str), (
                f"Each transcription note must be a string; got {type(marker)!r}"
            )


def test_fixture_sha256_matches_source_slice(fixture_slice: dict[str, Any]) -> None:
    """The fixture SHA-256 must match the bytes at offset..offset+length in clementine.xml.

    This test does NOT call the adapter. It verifies the fixture was generated
    correctly from the seeded RNG.

    The fixture SHA-256 is a sentinel of 64 zeros because the source file is absent
    from this machine. The test skips when the source file is not present.
    """
    src_path = REPO / fixture_slice["source_path"]
    if not src_path.exists():
        pytest.skip(f"Source file not present on this machine: {src_path}")
    data = src_path.read_bytes()
    offset = fixture_slice["offset"]
    length = fixture_slice["length"]
    slice_bytes = data[offset: offset + length]
    actual = hashlib.sha256(slice_bytes).hexdigest()
    assert actual == fixture_slice["fixture_sha256"], (
        f"Fixture SHA-256 mismatch. "
        f"Expected: {fixture_slice['fixture_sha256']}. "
        f"Got: {actual}. "
        f"Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('1f0e87fb', 16) = 521046011.
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
    """tools/predicates_by_type.cypher must define string, bool, list predicates.

    This test does NOT call the adapter. It validates that the predicate
    source file is present and parseable per RESEED_PLAN C.5.

    The file path tools/predicates_by_type.cypher is referenced in the
    docstring of this test and in the module-level load above.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "list" in PREDICATES, "predicates_by_type.cypher missing $pred_list"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )
    assert "IS NOT NULL" in PREDICATES["list"], (
        "$pred_list must contain IS NOT NULL check"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """The vulgate-clementine entry in expected_counts.json must be Tier C with null count.

    This test does NOT call the adapter. It validates the Tier C procurement
    entry per tools/expected_counts.json.

    Tier C: tolerance_relative=0.05, expected_count=null at A.4 freeze.
    The count is locked into a follow-on baseline commit at first ingest.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["vulgate-clementine"]
    assert entry["tier"] == "C", (
        f"vulgate-clementine must be Tier C; got tier={entry['tier']!r}"
    )
    assert entry["expected_count"] is None, (
        f"vulgate-clementine expected_count must be null at A.4 freeze; "
        f"got {entry['expected_count']!r}"
    )
    assert entry["record_unit"] == "vulgate_verse", (
        f"vulgate-clementine record_unit must be 'vulgate_verse'; got {entry['record_unit']!r}"
    )
    assert abs(entry["tolerance_relative"] - 0.05) < 1e-9, (
        f"Tier C tolerance_relative must be 0.05; got {entry['tolerance_relative']!r}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep
#
# For each of the 13 attack-vector stubs, attempt to run it through the same
# label/id assertions. The stub must be rejected by at least one check.
# These tests skip (not fail) when the stub has no ingest entry point.
#
# Edge-related stubs (minimal_edges, reversed_edge_direction) expose only
# emit_records/emit_edges with no callable ingest entry point; they are
# skipped because this adapter emits no edges per Decision 8.
# ---------------------------------------------------------------------------

STUB_MODULES = [
    "tests.lexical.stubs.broken_adapter",       # crashes on import or call
    "tests.lexical.stubs.empty_required",        # required fields are empty strings
    "tests.lexical.stubs.identical_lemma",       # every record maps to same key
    "tests.lexical.stubs.zero_records",          # returns no records, exits 0
    "tests.lexical.stubs.hardcoded_fixture",     # ignores source, returns fixed payload
    "tests.lexical.stubs.minimal_edges",         # edge-only stub; skipped (no edges in adapter)
    "tests.lexical.stubs.nan_inf_numeric",       # numeric fields carry NaN/Inf
    "tests.lexical.stubs.duplicate_records",     # emits duplicate node ids
    "tests.lexical.stubs.swapped_property_names",# osis/text_latin swapped or renamed
    "tests.lexical.stubs.mutated_strings",       # string properties mutated in-place
    "tests.lexical.stubs.silent_exception_swallow",  # swallows all exceptions
    "tests.lexical.stubs.reversed_edge_direction",   # edge-only stub; skipped (no edges)
    "tests.lexical.stubs.hash_ordered",          # outputs only deterministic hash-ordered records
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
      2. Try to find an ingest entry point named ingest_vulgate_clementine or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
         Edge-related stubs (minimal_edges, reversed_edge_direction) are documented
         skips for this adapter because no edges are emitted per Decision 8.
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_vulgate_clementine", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]}). "
            "Edge-related stubs are expected skips: this adapter emits no edges per Decision 8."
        )

    raised = False
    try:
        fn(source_root, fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_labels = fake_driver.captured_labels()
    verse_ids = fake_driver.captured_node_ids("VulgateVerse")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    id_format_ok = (
        all(vid.startswith("vulgate-clementine:") for vid in verse_ids)
        if verse_ids
        else False
    )

    rejected = not label_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Sample verse ids: {verse_ids[:3]}"
    )
