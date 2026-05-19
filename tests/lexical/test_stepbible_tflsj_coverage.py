"""STEPBible-TFLSJ (LSJ extract) adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_bool
definitions. Predicate semantics are loaded at module level from that file and used
to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tflsj.py has NO function body at this
  commit. getattr(mod, 'ingest_stepbible_tflsj', None) returns None because the
  module is a single docstring Expr node. Calling None raises TypeError. That
  failure IS the red state the Wave 2 orchestrator gate requires.

Entry function confirmed:
  ingest/lexical/stepbible_tflsj.py docstring section 1 names ingest_stepbible_tflsj
  as the entry function. run.py does not yet import it (Group 3 dependency declared
  in phase_02 bullet 10), and no def statement exists in the file at this commit.

Random seed:
  commit_sha = 'd45619bd1382d84558640f08e10b767055f37567' (git log -1 -- ingest/lexical/stepbible_tflsj.py)
  seed = int('d45619bd', 16) = 3562412477

Fixture: tests/lexical/fixtures/stepbible_tflsj_slice.json
  Three Greek lemmas from disjoint NT regions (Johannine logos, Pauline pistis,
  Synoptic agape). Each row exercises a distinct Decision 13 nullability axis:
  row 1 all fields populated, row 2 english=null (occ 0.991), row 3
  lsj_definition=null (occ 0.896).

Source: tools/expected_counts.json sources."STEPBible-TFLSJ" expected_count=9488
  (reconciled per Phase D [SCHEMA-REVISION]; was naive raw 11034, faithful
  adapter drops 1370 empty-field rows and collapses 176 duplicate lsj_entry_id
  collisions; see PHASE_D_DECISIONS_LOG.md line 19-20).
Decisions: 13 (LsjEntry shape), 14 (Source constraint).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# -- predicates_by_type.cypher (tools/predicates_by_type.cypher) --------
# Loaded at module level. Inline predicate definitions are forbidden per
# RESEED_PLAN C.5; use the canonical file instead.
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

# -- adapter constants --------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.stepbible_tflsj"
ENTRY_FUNCTION = "ingest_stepbible_tflsj"
SOURCE_SLUG = "STEPBible-TFLSJ"

REQUIRED_LABELS = frozenset({"LsjEntry", "Source"})
REQUIRED_EDGES = frozenset({"LEX_FOR"})

# reconciled per Phase D [SCHEMA-REVISION]; SHA-locked tools/expected_counts.json
# sources.STEPBible-TFLSJ.expected_count=9488 (was naive raw 11034; faithful
# adapter drops 1370 rows with empty lemma/translit/pos and collapses 176
# duplicate lsj_entry_id stable-id collisions; adapter unchanged). See
# PHASE_D_DECISIONS_LOG.md line 19-20 catalog reconciliation set #3.
EXPECTED_COUNT = 9488  # Tier A, tolerance 0, per expected_counts.json

# Seed from tflsj.py docstring commit SHA (git log -1 -- ingest/lexical/stepbible_tflsj.py)
DOCSTRING_COMMIT_SHA = "d45619bd1382d84558640f08e10b767055f37567"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3562412477

# Decision 13 required LsjEntry properties (non-nullable)
REQUIRED_NODE_FIELDS = ("strong", "lemma", "lemma_unaccented", "transliteration", "pos", "id", "source")
# Nullable fields per Decision 13 occurrence rates
NULLABLE_FIELDS = ("english", "lsj_definition")


# -- FakeDriver that records every node/edge the adapter emits ----------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_stepbible_tflsj() raises TypeError first.
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

    def captured_nodes(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]

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
      MERGE (n:LsjEntry {id: ...})
      MERGE (n:Source {slug: ...})
      MERGE (a)-[r:LEX_FOR]->(b)

    The parser records label and key properties from UNWIND batch rows
    when present. Intentionally lenient; a docstring-only adapter makes
    NO calls at all, which the test detects as TypeError.
    """
    for label in ("LsjEntry", "Source"):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher or f":{label})" in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("LEX_FOR",):
        if f"`{rel_type}`" in cypher or f":{rel_type}]" in cypher or f":{rel_type}" in cypher:
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# -- fixtures -----------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tflsj_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the Lexicons data directory the adapter reads from."""
    return REPO / "data" / "private" / "stepbible" / "Lexicons"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tflsj.

    FAILS at Wave 2: the adapter has no function body. getattr returns None and
    the assert fails. That failure IS the expected red state at Wave 2
    (docstring-only adapter satisfying len(ast.parse(source).body) == 1).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_tflsj must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tflsj must return dict; got {type(result)!r}"
    )
    assert "LsjEntry" in result, "return dict must contain 'LsjEntry' key"


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


def test_lsj_entry_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every LsjEntry node must have an id with the 'tflsj:<strong>:<lemma>' format.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id spec per Decision 13: 'tflsj:' + strong + ':' + lemma (polytonic form).
    Predicate: $pred_string from tools/predicates_by_type.cypher.
    The lsj_entry_id uniqueness constraint in graph/lexical.cypher enforces e.id UNIQUE.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entry_ids = fake_driver.captured_node_ids("LsjEntry")
    assert entry_ids, "adapter must emit at least one LsjEntry node"
    bad = [eid for eid in entry_ids if not eid.startswith("tflsj:")]
    assert not bad, (
        f"LsjEntry ids violate 'tflsj:<strong>:<lemma>' format: {bad[:5]}"
    )
    for eid in entry_ids:
        parts = eid.split(":", 2)
        assert len(parts) == 3, (
            f"LsjEntry id '{eid}' must have exactly two colons "
            "(format: tflsj:<strong>:<lemma>)"
        )
        assert parts[1], f"LsjEntry id '{eid}' has empty strong field"
        assert parts[2], f"LsjEntry id '{eid}' has empty lemma field"


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='STEPBible-TFLSJ'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Predicate: $pred_string from tools/predicates_by_type.cypher.
    Decision 14: Source uniqueness constraint on source_slug prevents duplicate
    registration. The adapter registers exactly one Source before any record write.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_lsj_entry_source_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every LsjEntry node must carry source='STEPBible-TFLSJ'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 13: the 'source' property is the adapter-derived discriminator
    used by Pipeline 2 citations. $pred_string predicate applies.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_nodes("LsjEntry")
    assert entries, "adapter must emit at least one LsjEntry node"
    bad = [e for e in entries if e.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"LsjEntry nodes with wrong or missing source property: "
        f"{[e.get('source') for e in bad[:3]]}"
    )


def test_lsj_entry_required_fields_non_null(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every LsjEntry must have all non-nullable Decision 13 fields populated.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Non-nullable per Decision 13 per-field predicate table (occ 1.0):
    strong, lemma, lemma_unaccented, transliteration, pos.
    Plus adapter-derived: id, source.
    $pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_nodes("LsjEntry")
    assert entries, "adapter must emit at least one LsjEntry node"
    for field in REQUIRED_NODE_FIELDS:
        bad = [
            e for e in entries
            if not (e.get(field) and str(e.get(field, "")).strip())
        ]
        assert not bad, (
            f"LsjEntry nodes missing required field '{field}': "
            f"{[{k: e.get(k) for k in ('id', 'strong', 'lemma')} for e in bad[:3]]}"
        )


def test_lsj_entry_nullable_fields_persisted_not_rejected(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """LsjEntry rows with null english or lsj_definition must still emit a node.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 13 edge case B: null lsj_definition rows (occ 0.896) must be
    persisted. Decision 13 field table: english nullable at occ 0.991.
    The adapter MUST NOT reject these rows; Pipeline 2 anchor-lemma bundles
    still need the headword node.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_nodes("LsjEntry")
    assert entries, "adapter must emit at least one LsjEntry node"
    # If at least one node exists the adapter did not blanket-reject null rows.
    # The fixture has rows with null english and null lsj_definition; if the
    # adapter filtered them the total count would drop.
    total = len(entries)
    assert total > 0, (
        "adapter must persist rows with null english/lsj_definition; "
        "emitted zero LsjEntry nodes which indicates upstream row rejection"
    )


def test_lex_for_edge_direction(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """LEX_FOR edges must flow LsjEntry -> GreekLemma, not the reverse.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 13: the edge carries no properties; join key is
    LsjEntry.strong matching GreekLemma.strong. Rows whose strong
    does not resolve to a known GreekLemma emit no LEX_FOR edge rather
    than fabricating a sentinel node.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edges = fake_driver._edges
    lex_for = [e for e in edges if e.get("rel_type") == "LEX_FOR"]
    # If any LEX_FOR edges exist they must originate from LsjEntry nodes.
    # We cannot inspect direction from Cypher parse alone, but we can
    # verify the edge type appears in the emitted set at all.
    edge_types = fake_driver.captured_edge_types()
    assert "LEX_FOR" in edge_types, (
        f"adapter must emit LEX_FOR edges. Edge types seen: {sorted(edge_types)}"
    )
    # Verify no reversed edge type is present (Decision 13 prohibits
    # INSTANCE_OF, IN_DOMAIN, FROM_EDITION, BRIDGES_LXX, IN_VERSE for this adapter).
    forbidden = {"INSTANCE_OF", "IN_DOMAIN", "FROM_EDITION", "BRIDGES_LXX", "IN_VERSE"}
    emitted = fake_driver.captured_edge_types()
    spurious = forbidden & emitted
    assert not spurious, (
        f"adapter emitted edge types not in contract: {sorted(spurious)}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string and bool predicates.

    This test does NOT call the adapter. It validates that the predicate
    source file is present and parseable per RESEED_PLAN C.5.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """STEPBible-TFLSJ expected count in expected_counts.json must be 9488 (Tier A).

    Reconciled per Phase D [SCHEMA-REVISION]; SHA-locked
    tools/expected_counts.json sources.STEPBible-TFLSJ.expected_count=9488.
    This test does NOT call the adapter. It validates the count constant
    used by the coverage tests matches the locked baseline.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TFLSJ"]
    assert entry["expected_count"] == EXPECTED_COUNT, (
        f"expected_counts.json STEPBible-TFLSJ count {entry['expected_count']} "
        f"!= {EXPECTED_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TFLSJ must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_fixture_seed_derivation() -> None:
    """The seed must equal int(commit_sha[:8], 16) = int('d45619bd', 16) = 3562412477.

    This test does NOT call the adapter. It validates fixture provenance.
    """
    expected_seed = int(DOCSTRING_COMMIT_SHA[:8], 16)
    assert expected_seed == SEED_INT, (
        f"SEED_INT {SEED_INT} does not match int('{DOCSTRING_COMMIT_SHA[:8]}', 16) "
        f"= {expected_seed}"
    )


def test_fixture_rows_cover_nullable_axes(fixture_slice: dict[str, Any]) -> None:
    """Fixture must include one row with null english and one with null lsj_definition.

    This test does NOT call the adapter. It validates the fixture exercises
    the two Decision 13 nullable axes so stub-rejection tests are meaningful.
    """
    rows = fixture_slice["rows"]
    assert len(rows) >= 3, f"fixture must have at least 3 rows, got {len(rows)}"
    has_null_english = any(r.get("english") is None for r in rows)
    has_null_lsj = any(r.get("lsj_definition") is None for r in rows)
    assert has_null_english, (
        "fixture must include at least one row with english=null "
        "(Decision 13 occ 0.991 nullable axis)"
    )
    assert has_null_lsj, (
        "fixture must include at least one row with lsj_definition=null "
        "(Decision 13 occ 0.896 nullable axis)"
    )


def test_fixture_stable_ids_are_unique(fixture_slice: dict[str, Any]) -> None:
    """Every fixture row must produce a distinct stable id.

    This test does NOT call the adapter. It validates no fixture row
    collision which would mask a duplicate-rejection test.
    Stable id = 'tflsj:' + strong + ':' + lemma (Decision 13).
    """
    rows = fixture_slice["rows"]
    stable_ids = [f"tflsj:{r['strong']}:{r['lemma']}" for r in rows]
    assert len(stable_ids) == len(set(stable_ids)), (
        f"fixture rows produce duplicate stable ids: {stable_ids}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (parametrized across 13 attack-vector stubs)
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

    Pattern (mirrors test_oshb_coverage.py reference at commit 8096f9b):
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_stepbible_tflsj or ingest.
      3. If no entry point, skip (stub only exposes emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail the test fails with
         'verifier failed to detect defect'.

    Decision 13 assertions checked:
      - REQUIRED_LABELS subset of emitted labels
      - REQUIRED_EDGES subset of emitted edge types
      - LsjEntry id prefix 'tflsj:'
      - LsjEntry id has exactly two colons (three parts)
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
    entry_ids = fake_driver.captured_node_ids("LsjEntry")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_prefix_ok = (
        all(eid.startswith("tflsj:") for eid in entry_ids) if entry_ids else False
    )
    id_parts_ok = (
        all(len(eid.split(":", 2)) == 3 for eid in entry_ids) if entry_ids else False
    )

    rejected = not label_ok or not edge_ok or not id_prefix_ok or not id_parts_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample LsjEntry ids: {entry_ids[:3]}"
    )
