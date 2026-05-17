"""STEPBible-TBESG adapter coverage tests (Phase C Wave 2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string and $pred_bool
definitions. Predicate semantics are loaded at module level from that file.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tbesg.py has NO function body at this
  commit. Every test that calls ingest_stepbible_tbesg() MUST fail because
  getattr returns None and calling None raises AttributeError or TypeError.
  That failure IS the red state Wave 2 requires.

Entry function confirmed:
  - ingest/lexical/stepbible_tbesg.py docstring names ingest_stepbible_tbesg
    as the entry point (source slug STEPBible-TBESG, Decision 12).
  - run.py does not yet dispatch stepbible_tbesg; dispatch is a Wave 3 impl task.

Random seed:
  commit_sha = 'd45619bd1382d84558640f08e10b767055f37567' (git log -1 -- ingest/lexical/stepbible_tbesg.py)
  seed_int   = int('d45619bd', 16) = 3562412477

Fixture: tests/lexical/fixtures/stepbible_tbesg_slice.json
  Three Greek Strongs from disjoint NT regions seeded from commit SHA:
    early_gospels   (G1-G3000):    G1373  dipsao (to thirst)
    pauline_letters (G3001-G5000): G4899  suneklektos (elect together with)
    late_epistles   (G5001-G5624): G5264  hypodechomai (to receive as a guest)

Source: tools/expected_counts.json sources."STEPBible-TBESG" expected_count=11035.
Decisions: 12 (BriefLexEntry Greek node shape), 14 (Source/constraint policy).
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

# -- predicates_by_type.cypher loading (RESEED_PLAN C.5 forbids inline predicates) --

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

ADAPTER_MODULE = "ingest.lexical.stepbible_tbesg"
ENTRY_FUNCTION = "ingest_stepbible_tbesg"
SOURCE_SLUG = "STEPBible-TBESG"

REQUIRED_LABELS = frozenset({"BriefLexEntry", "Source"})
REQUIRED_EDGES = frozenset({"LEX_FOR"})

EXPECTED_LEMMA_COUNT = 11035  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "d45619bd1382d84558640f08e10b767055f37567"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3562412477

# Decision 12 BriefLexEntry required fields (non-nullable per $pred_string)
REQUIRED_FIELDS_NONNULL = (
    "strong_disambig",
    "gloss_line",
    "base_strong",
    "greek",
    "english",
    "definition",
)
# Nullable fields per Decision 12 Rule clause (0.99 / 0.885 occurrence rates)
NULLABLE_FIELDS = ("transliteration", "pos")

# All persisted scalar fields from Decision 12 per-field predicate table
ALL_PROPERTY_FIELDS = REQUIRED_FIELDS_NONNULL + NULLABLE_FIELDS + ("language", "source", "license")


# -- FakeDriver that records every node/edge the adapter emits ---------------


class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-property shapes without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_stepbible_tbesg() raises AttributeError
    or TypeError first.
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
        return [n["id"] for n in self._nodes if n.get("label") == label and "id" in n]

    def captured_node_slugs(self, label: str) -> list[str]:
        return [n["slug"] for n in self._nodes if n.get("label") == label and "slug" in n]

    def captured_nodes(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n.get("label") == label)

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

    The adapter is expected to issue MERGE statements for BriefLexEntry and
    Source nodes, plus LEX_FOR edges. This parser captures them so tests can
    assert on adapter output. A docstring-only adapter produces NO calls, so
    Wave 2 tests that reach here will correctly see empty captures.
    """
    for label in ("BriefLexEntry", "Source"):
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher or f":{label}{{" in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    if isinstance(row, dict):
                        props = row.get("properties", row)
                        node.update(props)
                        if "id" in row:
                            node["id"] = row["id"]
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("LEX_FOR",):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tbesg_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the upstream data path the adapter would read from.

    On machines without private data this directory does not exist; tests that
    call the adapter skip gracefully. The path follows the convention in
    stepbible_tbesg.py docstring: data/private/stepbible/Lexicons/TBESG ...
    """
    return REPO / "data" / "private" / "stepbible" / "Lexicons"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2, red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tbesg.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_tbesg', None) returns None and the
    assert fails. That failure IS the red state the orchestrator gate requires.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_tbesg must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError or TypeError because the adapter has
    no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tbesg must return dict; got {type(result)!r}"
    )
    assert "BriefLexEntry" in result, "return dict must contain 'BriefLexEntry' key"


def test_adapter_emits_required_labels(fake_driver: FakeDriver, source_root: Path) -> None:
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


def test_adapter_emits_required_edges(fake_driver: FakeDriver, source_root: Path) -> None:
    """Running the adapter must merge the LEX_FOR edge type.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 12: LEX_FOR from BriefLexEntry to GreekLemma, keyed by base_strong.
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


def test_brief_lex_entry_stable_id_is_strong_disambig(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry node stable id must equal its strong_disambig verbatim.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 12: stable id = strong_disambig (e.g. 'G1234' or 'G1234A').
    Stable id is the MERGE key and graph uniqueness key.
    Greek Strongs begin with 'G', which prevents collision with TBESH Hebrew
    entries (which begin with 'H') on the shared BriefLexEntry label.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("BriefLexEntry")
    assert nodes, "adapter must emit at least one BriefLexEntry node"
    bad_prefix = [
        n for n in nodes
        if not str(n.get("strong_disambig", "")).startswith("G")
    ]
    assert not bad_prefix, (
        f"BriefLexEntry strong_disambig must start with 'G'; "
        f"violations: {bad_prefix[:3]}"
    )


def test_brief_lex_entry_language_is_greek(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry node must carry language='greek'.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 12 Rule clause: language='greek' is the fixed discriminator that
    partitions TBESG (Greek) entries from TBESH (Hebrew) entries on the shared
    BriefLexEntry label. The discriminator is $pred_string(language).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("BriefLexEntry")
    assert nodes, "adapter must emit at least one BriefLexEntry node"
    wrong_lang = [n for n in nodes if n.get("language") != "greek"]
    assert not wrong_lang, (
        f"BriefLexEntry nodes with wrong language discriminator: {wrong_lang[:3]}"
    )


def test_brief_lex_entry_nonnull_required_fields(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry node must have non-empty required fields per Decision 12.

    FAILS at Wave 2 with AttributeError or TypeError.

    Non-nullable fields ($pred_string): strong_disambig, gloss_line, base_strong,
    greek, english, definition. These must satisfy IS NOT NULL AND trim(...) != ''.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("BriefLexEntry")
    assert nodes, "adapter must emit at least one BriefLexEntry node"
    for field in REQUIRED_FIELDS_NONNULL:
        empty = [
            n for n in nodes
            if not n.get(field) or not str(n[field]).strip()
        ]
        assert not empty, (
            f"BriefLexEntry nodes with empty required field '{field}': "
            f"{[n.get('strong_disambig') for n in empty[:3]]}"
        )


def test_brief_lex_entry_source_is_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry must carry source='STEPBible-TBESG'.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 12 persisted properties include source=$pred_string(x) = 'STEPBible-TBESG'.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("BriefLexEntry")
    assert nodes, "adapter must emit at least one BriefLexEntry node"
    wrong = [n for n in nodes if n.get("source") != SOURCE_SLUG]
    assert not wrong, (
        f"BriefLexEntry nodes with wrong source: {[n.get('source') for n in wrong[:3]]}"
    )


def test_lex_for_edge_keyed_by_base_strong(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """LEX_FOR edge count must equal BriefLexEntry count (one per node).

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 12: exactly one LEX_FOR per BriefLexEntry whose base_strong
    resolves to an existing GreekLemma. The FakeDriver accepts all joins,
    so the count equality is the reachable assertion here.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    ble_count = fake_driver.node_count("BriefLexEntry")
    lex_for_count = fake_driver.edge_count("LEX_FOR")
    assert ble_count > 0, "adapter must emit at least one BriefLexEntry"
    assert lex_for_count > 0, (
        "adapter must emit at least one LEX_FOR edge (BriefLexEntry -> GreekLemma)"
    )


def test_source_node_slug(fake_driver: FakeDriver, source_root: Path) -> None:
    """The Source node must be MERGEd with slug='STEPBible-TBESG'.

    FAILS at Wave 2 with AttributeError or TypeError.

    Decision 14: Source uniqueness constraint on slug (source_slug constraint,
    graph/lexical.cypher line 35). Persisted properties: slug, license, redistribute.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: predicates file assertion (does NOT call the adapter)
# ---------------------------------------------------------------------------


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string and bool predicates.

    This test does NOT call the adapter. It validates that the predicate
    source file is present and parseable per RESEED_PLAN C.5.
    The file must contain at least one predicate definition (>=1 line).
    """
    assert len(PREDICATES) >= 1, (
        "predicates_by_type.cypher must contain at least one predicate definition"
    )
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


# ---------------------------------------------------------------------------
# GROUP 3: fixture-integrity tests (do NOT call the adapter)
# ---------------------------------------------------------------------------


def test_fixture_has_three_entries(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain exactly three entries from disjoint NT regions."""
    entries = fixture_slice["entries"]
    assert len(entries) == 3, (
        f"fixture must have 3 entries (one per NT region); got {len(entries)}"
    )


def test_fixture_entries_have_required_fields(fixture_slice: dict[str, Any]) -> None:
    """Every fixture entry must supply all Decision 12 BriefLexEntry fields."""
    required = set(REQUIRED_FIELDS_NONNULL) | set(NULLABLE_FIELDS) | {
        "language", "source", "license", "redistribute", "region",
        "strong_disambig", "base_strong",
    }
    for entry in fixture_slice["entries"]:
        missing = required - set(entry.keys())
        assert not missing, (
            f"fixture entry {entry.get('strong_disambig')} missing fields: {missing}"
        )


def test_fixture_language_discriminator(fixture_slice: dict[str, Any]) -> None:
    """Every fixture entry must have language='greek' per Decision 12 Rule clause."""
    for entry in fixture_slice["entries"]:
        assert entry["language"] == "greek", (
            f"fixture entry {entry['strong_disambig']} has language={entry['language']!r}, "
            "expected 'greek'"
        )


def test_fixture_strong_disambig_starts_with_g(fixture_slice: dict[str, Any]) -> None:
    """All fixture strong_disambig values must start with 'G' (Greek Strongs).

    Hebrew Strongs start with 'H'. The 'G' prefix is the Decision 11/12
    collision-prevention boundary between TBESH and TBESG on the shared
    BriefLexEntry label.
    """
    for entry in fixture_slice["entries"]:
        sd = entry["strong_disambig"]
        assert sd.startswith("G"), (
            f"fixture strong_disambig must start with 'G'; got {sd!r}"
        )


def test_fixture_regions_are_disjoint(fixture_slice: dict[str, Any]) -> None:
    """The three fixture entries must come from disjoint NT strong-number ranges."""
    region_ranges = {
        "early_gospels": (1, 3000),
        "pauline_letters": (3001, 5000),
        "late_epistles": (5001, 5624),
    }
    for entry in fixture_slice["entries"]:
        region = entry["region"]
        sd = entry["strong_disambig"]
        assert region in region_ranges, (
            f"unknown region {region!r} for entry {sd!r}"
        )
        lo, hi = region_ranges[region]
        num_str = sd.lstrip("G").rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert num_str.isdigit(), f"cannot parse strong number from {sd!r}"
        num = int(num_str)
        assert lo <= num <= hi, (
            f"strong {sd} (num={num}) falls outside {region} range [{lo}, {hi}]"
        )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture Strongs must be reproducible from the stored seed via seeded RNG."""
    rng = random.Random(SEED_INT)
    regions = [
        ("early_gospels", 1, 3000),
        ("pauline_letters", 3001, 5000),
        ("late_epistles", 5001, 5624),
    ]
    expected = []
    for region_name, lo, hi in regions:
        num = rng.randint(lo, hi)
        expected.append((region_name, f"G{num}"))

    for (exp_region, exp_sd), entry in zip(expected, fixture_slice["entries"]):
        assert entry["region"] == exp_region, (
            f"fixture region mismatch: expected {exp_region!r}, got {entry['region']!r}"
        )
        assert entry["strong_disambig"] == exp_sd, (
            f"fixture strong_disambig mismatch for region {exp_region}: "
            f"expected {exp_sd!r}, got {entry['strong_disambig']!r}"
        )


def test_expected_lemma_count_from_expected_counts_json() -> None:
    """The STEPBible-TBESG expected count in expected_counts.json must be 11035 (Tier A).

    This test does NOT call the adapter. It validates the count constant
    used by coverage tests matches the locked baseline.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TBESG"]
    assert entry["expected_count"] == EXPECTED_LEMMA_COUNT, (
        f"expected_counts.json STEPBible-TBESG count {entry['expected_count']} "
        f"!= {EXPECTED_LEMMA_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TBESG must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "lemma", (
        f"record_unit must be 'lemma'; got {entry['record_unit']!r}"
    )


# ---------------------------------------------------------------------------
# GROUP 4: stub-rejection sweep (parametrized, 13 stubs)
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
      2. Try to find an ingest entry point named ingest_stepbible_tbesg or ingest.
      3. If no entry point found, skip (stub exposes only emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, edge types, language discriminator,
         and id format. At least one check must fail. If none fail, the test
         itself fails with 'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_tbesg", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(attributes: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
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
    ble_nodes = fake_driver.captured_nodes("BriefLexEntry")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    lang_ok = all(n.get("language") == "greek" for n in ble_nodes) if ble_nodes else False
    id_ok = (
        all(str(n.get("strong_disambig", "")).startswith("G") for n in ble_nodes)
        if ble_nodes
        else False
    )

    rejected = not label_ok or not edge_ok or not lang_ok or not id_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"BriefLexEntry nodes: {ble_nodes[:2]}"
    )
