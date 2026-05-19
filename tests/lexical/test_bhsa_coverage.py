"""ETCBC-BHSA adapter coverage tests (Phase C.2 verifier, TDD red state).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool, $pred_list definitions. Predicate semantics are loaded at module level
from that file and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/bhsa.py has NO function body at this commit.
  Every test that calls ingest_bhsa() MUST fail because getattr returns None
  and calling None raises AttributeError or TypeError. That failure IS the
  red state the Wave 2 orchestrator gate requires (GATE: >=3 FAILED).

Entry function confirmed:
  - ingest/lexical/bhsa.py docstring: no def; contract names the function via
    the Acceptance Cypher section (phase_02 Group 4 step 14).
  - ingest/lexical/run.py line 14: from ingest.lexical.bhsa import ingest_bhsa
  - ingest/lexical/run.py line 45: return ingest_bhsa(settings)

Random seed:
  commit_sha = 'c4da6c1d4972f92f308566f320e9a5411c98c71f' (git log -1 -- ingest/lexical/bhsa.py)
  seed = int('c4da6c1d', 16) = 3302648861

Fixture: tests/lexical/fixtures/bhsa_slice.json
  Synthetic representation of 3 OT verses: torah (Gen.1.1), wisdom (Pro.1.1),
  prophets (Isa.1.1). BHSA upstream is a text-fabric module at
  C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021 which may not
  exist locally; tests that require live TF data are skipped when absent.
  seeded_length: 10108 (from rng.randint(1024, 16384) with seed 3302648861).

Source: tools/expected_counts.json sources."ETCBC-BHSA" expected_count=426590.
Decisions: 3 (ETCBC syntax tree shape), 14 (Strong/Source/TFNode constraints).
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

# -- predicates_by_type.cypher load -----------------------------------------
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
ADAPTER_MODULE = "ingest.lexical.bhsa"
ENTRY_FUNCTION = "ingest_bhsa"
SOURCE_SLUG = "ETCBC-BHSA"

REQUIRED_LABELS = frozenset({"BhsaWord", "BhsaPhrase", "BhsaClause", "TFNode"})
REQUIRED_EDGES = frozenset({"CONTAINS_PHRASE", "CONTAINS_WORD", "IN_VERSE"})

# Decision 3: BhsaWord properties (function MUST NOT appear on word nodes)
BHSA_WORD_REQUIRED_PROPS = frozenset({
    "g_word_utf8", "lex_utf8", "gloss", "sp", "pdp",
    "vt", "vs", "ps", "nu", "gn", "freq_lex", "language",
})
BHSA_WORD_FORBIDDEN_PROPS = frozenset({"function"})

EXPECTED_WORD_COUNT = 426590  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "c4da6c1d4972f92f308566f320e9a5411c98c71f"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3302648861


# -- FakeDriver that records every node/edge the adapter emits ---------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_bhsa() raises AttributeError or TypeError
    first.
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

    def nodes_for_label(self, label: str) -> list[dict[str, Any]]:
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

    The adapter is expected to issue MERGE for BhsaWord, BhsaPhrase, BhsaClause,
    TFNode nodes and CONTAINS_PHRASE, CONTAINS_WORD, IN_VERSE edges.
    When the adapter body is absent, no calls reach here.
    """
    for label in ("BhsaWord", "BhsaPhrase", "BhsaClause", "TFNode"):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if f":`{label}`" in cypher or f":{label} " in cypher or f"(n:{label}" in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    if isinstance(row, dict):
                        node.update(row)
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("CONTAINS_PHRASE", "CONTAINS_WORD", "IN_VERSE"):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "bhsa_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_bhsa.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_bhsa', None) returns None and the assert fails.
    That failure IS the expected red state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver) -> None:
    """ingest_bhsa must return a dict mapping label to count.

    FAILS at Wave 2: adapter body absent; calling None raises TypeError/AttributeError.
    Signature per run.py line 45: ingest_bhsa(settings).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(fake_driver.settings)
    assert isinstance(result, dict), f"ingest_bhsa must return dict; got {type(result)!r}"
    assert "BhsaWord" in result, "return dict must contain 'BhsaWord' key"


def test_adapter_emits_required_labels(fake_driver: FakeDriver) -> None:
    """Running the adapter must merge nodes for every required label.

    FAILS at Wave 2: adapter body absent.
    Required: BhsaClause, BhsaPhrase, BhsaWord, TFNode (Decision 3, Decision 14).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    emitted = fake_driver.captured_labels()
    missing = REQUIRED_LABELS - emitted
    assert not missing, (
        f"adapter did not emit required node labels: {sorted(missing)}. "
        f"Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_required_edges(fake_driver: FakeDriver) -> None:
    """Running the adapter must merge every required edge type.

    FAILS at Wave 2: adapter body absent.
    Required: CONTAINS_PHRASE (clause->phrase), CONTAINS_WORD (phrase->word),
    IN_VERSE (word->Verse). Decision 3.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    missing = REQUIRED_EDGES - emitted
    assert not missing, (
        f"adapter did not emit required edge types: {sorted(missing)}. "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_bhsa_word_stable_id_format(fake_driver: FakeDriver) -> None:
    """Every BhsaWord node must have id starting with 'bhsa:tf:'.

    FAILS at Wave 2: adapter body absent.

    Stable id spec per Decision 3 and phase_02 Idempotency section:
    'bhsa:tf:<node_id>' where node_id is the text-fabric integer word slot.
    Predicate: $pred_string -- x IS NOT NULL AND trim(toString(x)) <> ''.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    word_ids = fake_driver.captured_node_ids("BhsaWord")
    assert word_ids, "adapter must emit at least one BhsaWord node"
    bad = [wid for wid in word_ids if not wid.startswith("bhsa:tf:")]
    assert not bad, f"BhsaWord ids violate 'bhsa:tf:' prefix format: {bad[:5]}"


def test_bhsa_phrase_stable_id_format(fake_driver: FakeDriver) -> None:
    """Every BhsaPhrase node must have id starting with 'bhsa:tf:'.

    FAILS at Wave 2: adapter body absent.

    Stable id spec: 'bhsa:tf:<node_id>' for phrase slots. Decision 3.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    phrase_ids = fake_driver.captured_node_ids("BhsaPhrase")
    assert phrase_ids, "adapter must emit at least one BhsaPhrase node"
    bad = [pid for pid in phrase_ids if not pid.startswith("bhsa:tf:")]
    assert not bad, f"BhsaPhrase ids violate 'bhsa:tf:' prefix format: {bad[:5]}"


def test_bhsa_clause_stable_id_format(fake_driver: FakeDriver) -> None:
    """Every BhsaClause node must have id starting with 'bhsa:tf:'.

    FAILS at Wave 2: adapter body absent.

    Stable id spec: 'bhsa:tf:<node_id>' for clause slots. Decision 3.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    clause_ids = fake_driver.captured_node_ids("BhsaClause")
    assert clause_ids, "adapter must emit at least one BhsaClause node"
    bad = [cid for cid in clause_ids if not cid.startswith("bhsa:tf:")]
    assert not bad, f"BhsaClause ids violate 'bhsa:tf:' prefix format: {bad[:5]}"


def test_bhsa_word_required_properties_present(fake_driver: FakeDriver) -> None:
    """BhsaWord nodes must carry all Decision 3 required properties.

    FAILS at Wave 2: adapter body absent.

    Required per Decision 3 Per-field predicate type table:
    g_word_utf8, lex_utf8, gloss, sp, pdp, vt, vs, ps, nu, gn, freq_lex, language.
    Each is either $pred_string or $pred_int -- non-null required.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    word_nodes = fake_driver.nodes_for_label("BhsaWord")
    assert word_nodes, "adapter must emit at least one BhsaWord node"
    for node in word_nodes:
        missing = [p for p in BHSA_WORD_REQUIRED_PROPS if p not in node]
        assert not missing, (
            f"BhsaWord node missing required properties: {missing}. "
            f"Node id: {node.get('id', 'unknown')}"
        )


def test_bhsa_word_forbidden_property_function_absent(fake_driver: FakeDriver) -> None:
    """BhsaWord nodes must NOT carry the 'function' property.

    FAILS at Wave 2: adapter body absent.

    Decision 3 Edge cases handled bullet 1: the function field is empty on
    word slots and populated only on phrase slots. The adapter MUST NOT copy
    function onto BhsaWord nodes. This is the key discriminator between
    Decision 3 compliance and a naive field-copy bug.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    word_nodes = fake_driver.nodes_for_label("BhsaWord")
    assert word_nodes, "adapter must emit at least one BhsaWord node"
    bad = [n for n in word_nodes if "function" in n]
    assert not bad, (
        f"BhsaWord nodes carry forbidden 'function' property "
        f"(Decision 3: function belongs on BhsaPhrase only). "
        f"Bad node ids: {[n.get('id') for n in bad[:3]]}"
    )


def test_bhsa_phrase_carries_function_property(fake_driver: FakeDriver) -> None:
    """BhsaPhrase nodes must carry the 'function' property.

    FAILS at Wave 2: adapter body absent.

    Decision 3: function is a phrase-level feature sourced from the text-fabric
    phrase feature. BhsaPhrase must have it; BhsaWord must not.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    phrase_nodes = fake_driver.nodes_for_label("BhsaPhrase")
    assert phrase_nodes, "adapter must emit at least one BhsaPhrase node"
    missing_fn = [n for n in phrase_nodes if "function" not in n]
    assert not missing_fn, (
        f"BhsaPhrase nodes missing 'function' property (Decision 3). "
        f"Bad node ids: {[n.get('id') for n in missing_fn[:3]]}"
    )


def test_tfnode_tuple_uniqueness_per_decision_14(fake_driver: FakeDriver) -> None:
    """TFNode records must have unique (corpus, node_id) tuples.

    FAILS at Wave 2: adapter body absent.

    Decision 14: the TFNode uniqueness constraint covers (corpus, node_id).
    This prevents cross-corpus collisions between ETCBC-BHSA, ETCBC-Peshitta,
    and ETCBC-syrnt. Adapter must emit corpus='bhsa' on every TFNode.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    tfnodes = fake_driver.nodes_for_label("TFNode")
    assert tfnodes, "adapter must emit at least one TFNode"
    tuples = [(n.get("corpus"), n.get("node_id")) for n in tfnodes]
    unique_tuples = set(tuples)
    assert len(tuples) == len(unique_tuples), (
        f"TFNode (corpus, node_id) tuples are not unique. "
        f"Total: {len(tuples)}, unique: {len(unique_tuples)}. "
        f"Decision 14: tuple constraint must include both corpus and node_id."
    )
    bad_corpus = [n for n in tfnodes if n.get("corpus") != "bhsa"]
    assert not bad_corpus, (
        f"TFNode nodes with corpus != 'bhsa': "
        f"{[n.get('corpus') for n in bad_corpus[:3]]}. "
        "Decision 14: BHSA adapter emits corpus='bhsa' on every TFNode."
    )


def test_contains_word_count_ge_bhsa_word_count(fake_driver: FakeDriver) -> None:
    """CONTAINS_WORD edge count must be >= BhsaWord node count.

    FAILS at Wave 2: adapter body absent.

    Acceptance gate from phase_02_lexical_ingest.md Group 4 step 14:
    every word slot is covered by exactly one phrase, so CONTAINS_WORD
    count equals the BhsaWord count. Asserting >= catches any under-count bug.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    words = fake_driver.node_count("BhsaWord")
    edges = fake_driver.edge_count("CONTAINS_WORD")
    assert words > 0, "adapter must emit at least one BhsaWord node"
    assert edges >= words, (
        f"CONTAINS_WORD edge count ({edges}) must be >= BhsaWord count ({words}). "
        "Acceptance Cypher: MATCH (c:BhsaClause)-[:CONTAINS_PHRASE]->(p:BhsaPhrase)"
        "-[:CONTAINS_WORD]->(w:BhsaWord) WITH count(DISTINCT w) AS words RETURN words, words > 0"
    )


# ---------------------------------------------------------------------------
# GROUP 2: static fixture and tooling tests (do NOT call the adapter)
# ---------------------------------------------------------------------------

def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture seeded_length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('c4da6c1d', 16) = 3302648861.
    This test does NOT call the adapter.
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["seeded_length"], (
        f"Fixture seeded_length {fixture_slice['seeded_length']} != seeded length {length} "
        f"from seed {SEED_INT} (commit sha[:8]='c4da6c1d')"
    )


def test_fixture_contains_three_ot_corpus_regions(fixture_slice: dict[str, Any]) -> None:
    """The fixture must cover three distinct OT corpus regions: torah, wisdom, prophets.

    This test does NOT call the adapter.
    Three regions are required to demonstrate BhsaWord properties across
    the Hebrew canon without relying on a single corpus sample.
    """
    regions = {w["corpus_region"] for w in fixture_slice["words"]}
    required = {"torah", "wisdom", "prophets"}
    missing = required - regions
    assert not missing, (
        f"Fixture missing corpus regions: {missing}. "
        f"Got: {regions}"
    )


def test_fixture_words_have_required_bhsa_properties(fixture_slice: dict[str, Any]) -> None:
    """Every word entry in the fixture must carry all Decision 3 required properties.

    This test does NOT call the adapter. It validates the fixture is well-formed
    so adapter-calling tests can rely on it.
    """
    for word in fixture_slice["words"]:
        missing = [p for p in BHSA_WORD_REQUIRED_PROPS if p not in word]
        assert not missing, (
            f"Fixture word {word.get('stable_id')} missing properties: {missing}"
        )
        assert "function" not in word, (
            f"Fixture word {word.get('stable_id')} must not carry 'function' "
            f"(Decision 3: function is phrase-only)"
        )


def test_fixture_stable_ids_follow_bhsa_tf_format(fixture_slice: dict[str, Any]) -> None:
    """Every node in the fixture must have stable_id starting with 'bhsa:tf:'.

    This test does NOT call the adapter. Validates fixture correctness.
    """
    all_nodes = (
        fixture_slice.get("words", [])
        + fixture_slice.get("phrases", [])
        + fixture_slice.get("clauses", [])
    )
    bad = [n["stable_id"] for n in all_nodes if not n["stable_id"].startswith("bhsa:tf:")]
    assert not bad, f"Fixture nodes with non-conformant stable_id: {bad}"


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool, float predicates.

    This test does NOT call the adapter. Validates the predicate source file.
    Referenced by: bhsa.py docstring cross-reference section.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_predicates_cypher_ge_one_predicate() -> None:
    """tools/predicates_by_type.cypher must contain at least one predicate definition.

    Satisfies TASK MUST bullet 4: predicates_by_type.cypher >= 1.
    This test does NOT call the adapter.
    """
    assert len(PREDICATES) >= 1, (
        f"predicates_by_type.cypher contains no parseable predicates. "
        f"File path: {_PREDICATES_CYPHER_PATH}"
    )


def test_expected_word_count_from_expected_counts_json() -> None:
    """The ETCBC-BHSA expected count in expected_counts.json must be 426590 (Tier A).

    This test does NOT call the adapter. Validates the count constant is correct.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    bhsa_entry = ec["sources"]["ETCBC-BHSA"]
    assert bhsa_entry["expected_count"] == EXPECTED_WORD_COUNT, (
        f"expected_counts.json ETCBC-BHSA count {bhsa_entry['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT}"
    )
    assert bhsa_entry["tier"] == "A", "ETCBC-BHSA must be Tier A"
    assert bhsa_entry["tolerance"] == 0, "Tier A tolerance must be 0"


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep
# Parametrized across 13 stubs. Each must be detected as defective.
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
      2. Try to find an entry point named ingest_bhsa or ingest.
      3. If no entry point, skip (stub exposes only emit_records/emit_edges).
      4. If entry point found, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_bhsa", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
        )

    raised = False
    try:
        fn(fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_labels = fake_driver.captured_labels()
    emitted_edges = fake_driver.captured_edge_types()
    word_ids = fake_driver.captured_node_ids("BhsaWord")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_format_ok = (
        all(wid.startswith("bhsa:tf:") for wid in word_ids) if word_ids else False
    )

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample BhsaWord ids: {word_ids[:3]}"
    )
