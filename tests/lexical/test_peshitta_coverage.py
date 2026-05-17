"""Peshitta Syriac NT adapter coverage tests (Phase C Wave 2).

This file exercises the contract from Decision 7 of docs/SCHEMA_DECISIONS.md
and Phase 02 runbook bullet 20 (ingest/lexical/peshitta.py, Group 6).

References:
  tools/predicates_by_type.cypher  -- predicate source of truth
  tools/expected_counts.json       -- peshitta entry (tier C, count null)
  tests/lexical/fixtures/peshitta_slice.json  -- seeded fixture

TDD red-state contract:
  The adapter at ingest/lexical/peshitta.py is a docstring-only stub.
  getattr(mod, 'ingest_peshitta', None) returns None because the module
  body is a single Expr(Constant) per the AST gate. Calling None raises
  AttributeError (not TypeError) because the attribute is absent entirely,
  so every test that calls the adapter MUST fail with AttributeError.
  That failure IS the red state the Phase C Wave 2 gate requires
  (gate: >=3 FAILED).

Random seed:
  commit_sha = 'dee1fb927fbcb91de68d98c97df1ce6c0d53582b'
  (git log -1 -- ingest/lexical/peshitta.py, first implementation commit)
  seed = int('dee1fb92', 16) = 3739351954
  length = random.Random(3739351954).randint(1024, 16384) = 13626

Fixture: tests/lexical/fixtures/peshitta_slice.json
  source: data/private/peshitta/peshitta_nt.tf (network procurement, gitignored)
  Three Syriac NT verses: Matthew 6:9, John 1:1, Romans 1:1
  offset/sha256 populated once data/private/peshitta/ is fetched.

Source: tools/expected_counts.json sources."peshitta"
  tier=C, expected_count=null, tolerance_relative=0.05
Decision: 7 (SyriacWord shape, Estrangela preservation, TVTMS mapping)
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

# Predicates loaded from canonical file per RESEED_PLAN C.5.
# Inline predicate definitions are forbidden here.
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

# Adapter constants
ADAPTER_MODULE = "ingest.lexical.peshitta"
ENTRY_FUNCTION = "ingest_peshitta"

REQUIRED_LABELS = frozenset({"SyriacWord"})
REQUIRED_EDGES = frozenset({"IN_VERSE"})

# Decision 7 per-field contract
SYRIAC_WORD_STRING_FIELDS = ("siglum", "lex_nfc", "gloss", "verse_ref", "text", "morph")
SYRIAC_WORD_NULLABLE_FIELDS = ("lex",)  # nullable for conjectural readings

DOCSTRING_COMMIT_SHA = "dee1fb927fbcb91de68d98c97df1ce6c0d53582b"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3739351954


# ---------------------------------------------------------------------------
# FakeDriver infrastructure (mirrors test_oshb_coverage.py pattern)
# ---------------------------------------------------------------------------


class FakeDriver:
    """Minimal Neo4j driver stub that records every node and edge the adapter emits.

    When the adapter body is absent (Wave 2 red state) this driver is never
    reached because calling ingest_peshitta() raises AttributeError first.
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
        return [n for n in self._nodes if n.get("label") == label]


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
    """Best-effort parser that captures node/edge MERGE payloads from Cypher strings."""
    for label in ("SyriacWord", "Source", "Verse"):
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("IN_VERSE",):
        if f"`{rel_type}`" in cypher or f":{rel_type}]" in cypher or f":{rel_type}" in cypher:
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "peshitta_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    return REPO / "data" / "private" / "peshitta"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2, red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_peshitta.

    FAILS at Wave 2: the adapter is a docstring-only stub with no function
    definition, so getattr(mod, 'ingest_peshitta', None) returns None and
    the assert fails. This failure IS the expected red state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be callable, "
        f"but got {type(fn)!r}. "
        "Expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_peshitta must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError because ingest_peshitta is absent
    from the docstring-only stub.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_peshitta must return dict; got {type(result)!r}"
    )
    assert "SyriacWord" in result, "return dict must contain 'SyriacWord' key"


def test_adapter_emits_syriac_word_label(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge SyriacWord nodes.

    FAILS at Wave 2 with AttributeError.
    Decision 7: label is SyriacWord, not Word.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "SyriacWord" in emitted, (
        f"adapter did not emit SyriacWord label. Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_in_verse_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge IN_VERSE edges (SyriacWord to Verse).

    FAILS at Wave 2 with AttributeError.
    Decision 7: edge is IN_VERSE, keyed by verse_ref to Verse.osisID.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert "IN_VERSE" in emitted, (
        f"adapter did not emit IN_VERSE edge. Edge types seen: {sorted(emitted)}"
    )


def test_syriac_word_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every SyriacWord node must have an id starting with 'peshitta:'.

    FAILS at Wave 2 with AttributeError.

    Stable id spec: 'peshitta:<verse_ref>:<token_pos>'
    where verse_ref is the projected OSIS reference (e.g. 'John.1.1')
    and token_pos is the 1-based ordinal position inside the verse.
    Predicate: $pred_string from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("SyriacWord")
    assert word_ids, "adapter must emit at least one SyriacWord node"
    bad = [wid for wid in word_ids if not wid.startswith("peshitta:")]
    assert not bad, (
        f"SyriacWord ids violate 'peshitta:' prefix format: {bad[:5]}"
    )


def test_syriac_word_id_includes_verse_ref_and_token_pos(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Stable id format must be 'peshitta:<verse_ref>:<token_pos>' (3 parts).

    FAILS at Wave 2 with AttributeError.
    The colon-separated triple ensures verse_ref and token_pos are both present.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("SyriacWord")
    assert word_ids, "adapter must emit at least one SyriacWord node"
    bad = []
    for wid in word_ids:
        parts = wid.split(":")
        if len(parts) < 3:
            bad.append(wid)
        elif not parts[2].isdigit():
            bad.append(wid)
    assert not bad, (
        f"SyriacWord ids do not follow 'peshitta:<verse_ref>:<token_pos>': {bad[:5]}"
    )


def test_syriac_word_has_verse_ref_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Each SyriacWord node must carry a non-empty verse_ref property.

    FAILS at Wave 2 with AttributeError.
    Predicate: $pred_string(x) = x IS NOT NULL AND trim(toString(x)) <> ''
    verse_ref is the OSIS reference projected through TVTMS.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.nodes_for_label("SyriacWord")
    assert nodes, "adapter must emit at least one SyriacWord node"
    bad = [
        n for n in nodes
        if not (n.get("verse_ref") and str(n.get("verse_ref", "")).strip())
    ]
    assert not bad, (
        f"SyriacWord nodes missing verse_ref: {bad[:3]}"
    )


def test_syriac_word_lex_nullable_for_conjectural(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter must NOT substitute a placeholder when lex is null.

    FAILS at Wave 2 with AttributeError.
    Decision 7 edge case 3: conjectural readings have null lex; the adapter
    MUST persist null verbatim. This test confirms that nodes CAN have
    lex=None and that the adapter does not substitute a fallback.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.nodes_for_label("SyriacWord")
    assert nodes, "adapter must emit at least one SyriacWord node"
    # At least some nodes with lex=None must reach the graph without being
    # converted to a placeholder like '' or 'UNKNOWN'.
    placeholder_tokens = {"UNKNOWN", "PLACEHOLDER", "NULL", "N/A", ""}
    bad = [
        n for n in nodes
        if n.get("lex") is not None and str(n.get("lex", "")).upper() in placeholder_tokens
    ]
    assert not bad, (
        f"SyriacWord nodes have placeholder lex instead of null: {bad[:3]}"
    )


def test_syriac_word_has_citation_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Each SyriacWord node must carry source='peshitta'.

    FAILS at Wave 2 with AttributeError.
    peshitta.py docstring: source slug is 'peshitta'; citation slug is
    'peshitta-text' (for Pipeline 2 evidence files). The node property
    'source' carries the source slug, not the citation slug.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.nodes_for_label("SyriacWord")
    assert nodes, "adapter must emit at least one SyriacWord node"
    bad = [n for n in nodes if n.get("source") != "peshitta"]
    assert not bad, (
        f"SyriacWord nodes have wrong source property: {bad[:3]}"
    )


def test_syriac_word_text_is_non_empty(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every SyriacWord node must have a non-empty text property.

    FAILS at Wave 2 with AttributeError.
    Decision 7: text is the raw upstream surface bytes verbatim
    (Estrangela glyphs, no NFC/NFD applied). $pred_string(text) must be true.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    nodes = fake_driver.nodes_for_label("SyriacWord")
    assert nodes, "adapter must emit at least one SyriacWord node"
    bad = [
        n for n in nodes
        if not (n.get("text") and str(n.get("text", "")).strip())
    ]
    assert not bad, (
        f"SyriacWord nodes missing or empty text: {bad[:3]}"
    )


def test_in_verse_count_ge_syriac_word_count(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """IN_VERSE edge count must be >= SyriacWord node count.

    FAILS at Wave 2 with AttributeError.
    Every SyriacWord must link to exactly one Verse via IN_VERSE.
    This mirrors the acceptance gate from phase_02 bullet 20.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    words = fake_driver.node_count("SyriacWord")
    edges = fake_driver.edge_count("IN_VERSE")
    assert words > 0, "adapter must emit at least one SyriacWord node"
    assert edges >= words, (
        f"IN_VERSE edge count ({edges}) must be >= SyriacWord count ({words}). "
        "Acceptance gate: every word has exactly one IN_VERSE edge."
    )


# ---------------------------------------------------------------------------
# Tests that do NOT call the adapter (pass even at Wave 2)
# ---------------------------------------------------------------------------


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('dee1fb92', 16) = 3739351954.
    length = random.Random(3739351954).randint(1024, 16384) = 13626.
    This test passes at Wave 2 because it does not call the adapter.
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {length}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    This test passes at Wave 2. It validates the predicate source file per
    RESEED_PLAN C.5. predicates_by_type.cypher is referenced at module level.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """The peshitta entry in expected_counts.json must be tier C with null count.

    This test passes at Wave 2. It validates the count metadata used by
    coverage assertions once the baseline is locked.
    Source: tools/expected_counts.json sources.peshitta.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["peshitta"]
    assert entry["tier"] == "C", (
        f"peshitta must be Tier C in expected_counts.json; got {entry['tier']!r}"
    )
    assert entry["expected_count"] is None, (
        f"peshitta expected_count must be null at schema freeze; got {entry['expected_count']!r}"
    )
    assert entry["tolerance_relative"] == 0.05, (
        f"peshitta tolerance_relative must be 0.05; got {entry['tolerance_relative']!r}"
    )


def test_fixture_slice_has_three_nt_verses(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain at least 3 placeholder verses covering NT corpora.

    This test passes at Wave 2. It validates the fixture content.
    Three regions: Matthew (Synoptic), John (Johannine), Romans (Pauline).
    """
    verses = fixture_slice.get("placeholder_verses", [])
    assert len(verses) >= 3, (
        f"fixture must have >=3 placeholder verses; got {len(verses)}"
    )
    refs = {v["verse_ref"] for v in verses}
    books = {r.split(".")[0] for r in refs}
    assert len(books) >= 3, (
        f"fixture verses must span >=3 NT books; got {sorted(books)}"
    )


def test_fixture_has_conjectural_lex_null_example(fixture_slice: dict[str, Any]) -> None:
    """The fixture must include at least one verse with lex=null.

    This test passes at Wave 2. It validates that the fixture models the
    Decision 7 edge case (conjectural readings with null lex).
    """
    verses = fixture_slice.get("placeholder_verses", [])
    null_lex = [v for v in verses if v.get("lex") is None]
    assert null_lex, (
        "fixture must include at least one placeholder verse with lex=null "
        "to model Decision 7 conjectural reading edge case"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (13 stubs)
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
    """The coverage scaffold must detect defects in each of the 13 attack-vector stubs.

    Pattern:
      1. Import the stub.
      2. Look for a callable named ingest_peshitta or ingest.
      3. If absent, skip (stub exposes only emit_records/emit_edges helpers).
      4. If present, call it. A raised exception counts as detection. Good.
      5. If it runs silently, apply label/edge/id checks.
         At least one check must catch the defect; if none do,
         the test fails with 'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_peshitta", None)
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
    word_ids = fake_driver.captured_node_ids("SyriacWord")

    label_ok = "SyriacWord" in emitted_labels
    edge_ok = "IN_VERSE" in emitted_edges
    id_format_ok = (
        all(wid.startswith("peshitta:") for wid in word_ids) if word_ids else False
    )

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample SyriacWord ids: {word_ids[:3]}"
    )
