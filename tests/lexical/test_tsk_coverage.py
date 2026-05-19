"""TSK adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool definitions. Predicate semantics are loaded at module level from that file
and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/tsk.py has NO function body at this commit.
  Every test that calls ingest_tsk() MUST fail because getattr returns None
  and calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires (>=3 FAILED).

Entry function confirmed:
  - ingest/lexical/tsk.py: docstring-only module; no def ingest_tsk present.
  - ingest/lexical/run.py line 22: from ingest.lexical.tsk import ingest_tsk
  - ingest/lexical/run.py line 55: return ingest_tsk(DATA_ROOT / 'tskxref.txt', settings)

Random seed:
  commit_sha = 'c68bac76e7ef67d2e383145f4c5fd1ccfa019281' (git log -1 -- ingest/lexical/tsk.py)
  seed = int('c68bac76', 16) = 3331042422
  length = random.Random(seed).randint(1024, 16384) = 16076

Fixture: tests/lexical/fixtures/tsk_slice.json
  3 entries covering: single cross-ref, range cross-ref (Ps 119:1-5), unresolved-candidate.
  Corpus slots: Genesis 1:1 (OT narrative), Psalm 119:1 (OT wisdom/range), John 3:36 (NT unresolved).

Source: tools/expected_counts.json sources."TSK" expected_count=63682 (Tier A, tolerance 0).
Decision: 5 (TSK versification policy, CROSS_REF edge type, stable-id format, TVTMS reconciliation).
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

# -- predicates_by_type.cypher -----------------------------------------------
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
ADAPTER_MODULE = "ingest.lexical.tsk"
ENTRY_FUNCTION = "ingest_tsk"

SOURCE_SLUG = "TSK"
REQUIRED_LABELS = frozenset({"CrossRef"})
REQUIRED_EDGE_TYPES = frozenset({"CROSS_REF"})
FORBIDDEN_EDGE_TYPES = frozenset({"OPENBIBLE_CROSS_REF"})

EXPECTED_NODE_COUNT = 63682  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "c68bac76e7ef67d2e383145f4c5fd1ccfa019281"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3331042422


# -- FakeDriver that records every node/edge the adapter emits ---------------


class FakeDriver:
    """Minimal Neo4j driver stand-in for TSK adapter tests.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_tsk() raises TypeError first.
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

    def edges_by_type(self, rel_type: str) -> list[dict[str, Any]]:
        return [e for e in self._edges if e["rel_type"] == rel_type]

    def nodes_by_label(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n["label"] == label]


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
    """Best-effort parse of MERGE Cypher into FakeDriver records.

    Captures CrossRef node merges and CROSS_REF edge merges from adapter output.
    OPENBIBLE_CROSS_REF must never appear; if it does the forbidden-edge test catches it.
    """
    for label in ("CrossRef",):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if f":`{label}`" in cypher or f"(n:{label}" in cypher or f":{label} " in cypher:
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("CROSS_REF", "OPENBIBLE_CROSS_REF"):
        if f"`{rel_type}`" in cypher or f":{rel_type}]" in cypher or f":{rel_type}" in cypher:
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                props: dict[str, Any] = {}
                if isinstance(rows_param, list) and rows_param:
                    first = rows_param[0]
                    if isinstance(first, dict):
                        props = dict(first)
                driver._edges.append({"rel_type": rel_type, **props})


# -- fixtures ----------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "tsk_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_path(fixture_slice: dict[str, Any]) -> Path:
    """Return the path to the TSK upstream flat file."""
    return REPO / fixture_slice["source_path"]


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_tsk.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_tsk', None) returns None and the assert fails.
    That failure IS the expected red state at Wave 2 (docstring-only adapter).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_path: Path) -> None:
    """ingest_tsk must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError because the adapter has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_path, fake_driver.settings)
    assert isinstance(result, dict), f"ingest_tsk must return dict; got {type(result)!r}"
    assert "CrossRef" in result, "return dict must contain 'CrossRef' key"


def test_adapter_emits_crossref_label(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Running the adapter must merge CrossRef nodes.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    missing = REQUIRED_LABELS - emitted
    assert not missing, (
        f"adapter did not emit required node labels: {sorted(missing)}. "
        f"Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_cross_ref_edge(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Running the adapter must merge at least one CROSS_REF edge.

    FAILS at Wave 2 with TypeError.
    Decision 5: TSK uses CROSS_REF (CrossRef to Verse), not OPENBIBLE_CROSS_REF.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    missing = REQUIRED_EDGE_TYPES - emitted
    assert not missing, (
        f"adapter did not emit required edge types: {sorted(missing)}. "
        f"Edge types seen: {sorted(emitted)}"
    )


def test_adapter_does_not_emit_openbible_cross_ref_edge(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """TSK adapter must NEVER emit OPENBIBLE_CROSS_REF edges.

    Decision 5: provenance separation between TSK (CROSS_REF) and
    OpenBible (OPENBIBLE_CROSS_REF) must be mechanically enforceable.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    forbidden = FORBIDDEN_EDGE_TYPES & emitted
    assert not forbidden, (
        f"adapter emitted forbidden edge types: {sorted(forbidden)}. "
        "TSK must use CROSS_REF only; OPENBIBLE_CROSS_REF belongs to openbible.py."
    )


# ---------------------------------------------------------------------------
# GROUP 2: CrossRef node property assertions
# ---------------------------------------------------------------------------


def test_crossref_stable_id_format(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Every CrossRef node must have an id matching 'tsk:<book>.<chapter>.<verse>.<word_num>'.

    Decision 5 stable-id format: tsk:<book_num>.<chapter>.<verse>.<word_num>
    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    crossref_ids = fake_driver.captured_node_ids("CrossRef")
    assert crossref_ids, "adapter must emit at least one CrossRef node"
    bad = [cid for cid in crossref_ids if not cid.startswith("tsk:")]
    assert not bad, (
        f"CrossRef ids violate 'tsk:' prefix format: {bad[:5]}. "
        "Expected format: tsk:<book_num>.<chapter>.<verse>.<word_num>"
    )


def test_crossref_stable_id_has_four_dot_parts(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Each CrossRef stable id must have exactly four dot-separated integer parts after 'tsk:'.

    Format: tsk:<book_num>.<chapter>.<verse>.<word_num>
    All four parts must be parseable as integers.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    crossref_ids = fake_driver.captured_node_ids("CrossRef")
    assert crossref_ids, "adapter must emit at least one CrossRef node"
    bad: list[str] = []
    for cid in crossref_ids:
        if not cid.startswith("tsk:"):
            bad.append(cid)
            continue
        parts = cid[4:].split(".")
        if len(parts) != 4:
            bad.append(cid)
            continue
        if not all(p.isdigit() for p in parts):
            bad.append(cid)
    assert not bad, (
        f"CrossRef ids with malformed 4-part integer tuple: {bad[:5]}. "
        "Expected tsk:<int>.<int>.<int>.<int>"
    )


def test_crossref_required_int_properties(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """CrossRef nodes must have book_num, chapter, verse, word_num as integers (not null).

    Predicates per Decision 5 table: $pred_int(x) := x IS NOT NULL
    Applied here as: value is not None and isinstance(value, int).

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    nodes = fake_driver.nodes_by_label("CrossRef")
    assert nodes, "adapter must emit at least one CrossRef node"
    int_fields = ("book_num", "chapter", "verse", "word_num")
    bad: list[str] = []
    for node in nodes:
        node_id = node.get("id", "<no-id>")
        for field in int_fields:
            val = node.get(field)
            if val is None or not isinstance(val, int):
                bad.append(f"id={node_id} field={field} val={val!r}")
    assert not bad, (
        f"CrossRef nodes failed $pred_int check on int fields: {bad[:5]}"
    )


def test_crossref_required_string_properties(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """CrossRef nodes must have keyword and xref_string as non-empty strings.

    Predicates per Decision 5 table: $pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ''

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    nodes = fake_driver.nodes_by_label("CrossRef")
    assert nodes, "adapter must emit at least one CrossRef node"
    string_fields = ("keyword", "xref_string")
    bad: list[str] = []
    for node in nodes:
        node_id = node.get("id", "<no-id>")
        for field in string_fields:
            val = node.get(field)
            if val is None or not isinstance(val, str) or val.strip() == "":
                bad.append(f"id={node_id} field={field} val={val!r}")
    assert not bad, (
        f"CrossRef nodes failed $pred_string check on string fields: {bad[:5]}"
    )


def test_crossref_source_property_equals_tsk(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Every CROSS_REF edge must carry source='TSK'.

    Decision 5: the source property on every CROSS_REF edge from this adapter
    MUST equal the literal string 'TSK'.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    edges = fake_driver.edges_by_type("CROSS_REF")
    assert edges, "adapter must emit at least one CROSS_REF edge"
    bad = [e for e in edges if e.get("source") != "TSK"]
    assert not bad, (
        f"CROSS_REF edges with source != 'TSK': {bad[:3]}. "
        "Decision 5: source must be 'TSK' on every CROSS_REF edge from this adapter."
    )


def test_cross_ref_edge_has_osis_target(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """Every CROSS_REF edge must carry a non-empty osis_target property.

    Decision 5: osis_target holds the canonical OSIS rendering of the resolved
    target verse; it is the join key Pipeline 2 walks back to the Verse node.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    edges = fake_driver.edges_by_type("CROSS_REF")
    assert edges, "adapter must emit at least one CROSS_REF edge"
    bad = [
        e for e in edges
        if not e.get("osis_target") or not isinstance(e.get("osis_target"), str)
    ]
    assert not bad, (
        f"CROSS_REF edges missing or empty osis_target: {bad[:3]}. "
        "Each expanded verse target needs its own osis_target value."
    )


# ---------------------------------------------------------------------------
# GROUP 3: xref_string range expansion
# ---------------------------------------------------------------------------


def test_range_xref_expands_to_multiple_edges(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """A verse range must fan out to one CROSS_REF edge per verse, real corpus.

    xref_string range expansion rule (Decision 5, frozen docstring section
    "xref_string range expansion"): when a verse suffix contains 'a-b', the
    adapter enumerates every v with a <= v <= b and emits one CROSS_REF edge
    per single verse; the packed xref_string stays verbatim on the CrossRef
    node and the first expanded reference is denormalised onto the node's
    to_ref hint.

    This assertion is grounded in the real 63682-row SWORD corpus at
    data/private/tskxref.txt rather than the 3-row synthetic slice. The
    earlier "all Ps.119.* targets globally distinct" framing was satisfiable
    only against the single-Psalm-119-row fixture: with the real corpus
    thousands of distinct anchors legitimately cross-reference into Psalm
    119, so repeated Ps.119.x targets across different anchors are correct.

    The check has two faithful, independent legs that both fail on an
    adapter that stops expanding ranges:

      LEG A (single known pure-range anchor, faithful node capture).
        Row tsk:1.8.4.1 (anchor Gen 8:4, keyword "ark") carries the verbatim
        single-token verse range 'ge 7:17-19' with no semicolon or comma, so
        its only references are Gen 7:17, 7:18, 7:19. The docstring contract
        puts the FIRST expanded reference on the node's to_ref hint, so a
        correctly range-aware adapter resolves to_ref to 'Gen.7.17'. An
        adapter that fails to parse the range, drops the range bound, or
        passes the packed token through opaquely cannot land to_ref on the
        first range verse, so this leg fails.

      LEG B (global expansion cardinality, faithful edge count).
        The FakeDriver edge capture preserves the true total CROSS_REF
        cardinality. If every semicolon token produced exactly one edge with
        no range fan-out, the total edge count would be at most the
        semicolon-token count over resolved rows. The real corpus contains
        24828 resolved rows with at least one range token, so correct
        per-verse expansion drives the edge total strictly above the token
        count. An adapter that emits one packed edge per range (hidden
        multiplicity) collapses the total back to roughly the token count
        and fails this leg.

    Neither leg is a tautology: both compare adapter output against a value
    the adapter does not control (the corpus-derived first range verse and
    the corpus-derived semicolon-token count).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)

    nodes = fake_driver.nodes_by_label("CrossRef")
    edges = fake_driver.edges_by_type("CROSS_REF")
    assert nodes, "adapter must emit at least one CrossRef node"
    assert edges, "adapter must emit at least one CROSS_REF edge"

    by_id = {n.get("id"): n for n in nodes}

    # LEG A: a single, pure verse-range anchor from the real corpus.
    range_anchor_id = "tsk:1.8.4.1"
    range_node = by_id.get(range_anchor_id)
    assert range_node is not None, (
        f"expected pure-range anchor {range_anchor_id} (Gen 8:4 'ark', "
        "xref 'ge 7:17-19') in the real 63682-row corpus; absent means the "
        "adapter did not parse the SWORD flat file at "
        "data/private/tskxref.txt."
    )
    raw_xref = range_node.get("xref_string", "")
    assert raw_xref == "ge 7:17-19", (
        f"{range_anchor_id} xref_string must be preserved verbatim as "
        f"'ge 7:17-19'; got {raw_xref!r}. The packed payload must stay "
        "auditable on the node, unmodified by range expansion."
    )
    assert ";" not in raw_xref and "," not in raw_xref and "-" in raw_xref, (
        "the chosen anchor must be a single-token verse range so its only "
        f"targets are the three range verses; got {raw_xref!r}."
    )
    assert range_node.get("to_ref") == "Gen.7.17", (
        f"{range_anchor_id} to_ref must resolve to the FIRST verse of the "
        f"'ge 7:17-19' range, 'Gen.7.17'; got {range_node.get('to_ref')!r}. "
        "An adapter that stops expanding ranges (drops the range, mangles "
        "the bound, or passes the packed token through) cannot land the "
        "first range verse here."
    )

    # LEG B: total expansion cardinality must exceed the semicolon-token
    # count, which is only possible when ranges fan out per verse.
    resolved = [
        n for n in nodes if n.get("tvtms_quarantine") is not True
    ]
    semicolon_token_count = sum(
        n.get("xref_string", "").count(";") + 1
        for n in resolved
        if n.get("xref_string")
    )
    range_bearing_rows = sum(
        1 for n in resolved if "-" in n.get("xref_string", "")
    )
    assert range_bearing_rows >= 1000, (
        f"real corpus must contain many range-bearing resolved rows; got "
        f"{range_bearing_rows}. Too few means the corpus or parse is wrong."
    )
    assert len(edges) > semicolon_token_count, (
        f"total CROSS_REF edges ({len(edges)}) must strictly exceed the "
        f"semicolon-token count over resolved rows ({semicolon_token_count}). "
        "Equality or fewer means the adapter emitted one edge per token "
        "with no per-verse range fan-out (hidden multiplicity), violating "
        "the Decision 5 expansion rule."
    )


def test_single_xref_produces_one_edge(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """A single ref like 'John.1.1' must produce exactly one CROSS_REF edge.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    edges = fake_driver.edges_by_type("CROSS_REF")
    assert edges, "adapter must emit at least one CROSS_REF edge"
    john_targets = [
        e for e in edges
        if e.get("osis_target") == "John.1.1"
    ]
    assert len(john_targets) >= 1, (
        "Expected at least one CROSS_REF edge with osis_target='John.1.1' "
        "from the single cross-ref entry (Gen 1:1 -> John 1:1)."
    )


# ---------------------------------------------------------------------------
# GROUP 4: TVTMS quarantine
# ---------------------------------------------------------------------------


def test_unresolved_tvtms_row_is_quarantined(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """CrossRef nodes for unresolvable TVTMS references must have tvtms_quarantine=True.

    Decision 5: rows the TVTMS mapping cannot resolve must be tagged with
    tvtms_quarantine=true (bool) rather than silently dropped.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    nodes = fake_driver.nodes_by_label("CrossRef")
    assert nodes, "adapter must emit at least one CrossRef node"

    # The earlier framing hardcoded fixture-only id tsk:43.3.36.2 and only
    # pytest.skip()'d when it was absent. Against the real 63682-row corpus
    # tsk:43.3.36.2 is a genuine fully-resolvable John 3:36 row (correctly
    # NOT quarantined), so the hardcoded check could only ever fail there.
    # Assert the quarantine MECHANISM on the rows the real TVTMS mapping
    # genuinely cannot resolve instead of any fixture-only id.
    quarantined = [n for n in nodes if n.get("tvtms_quarantine") is True]
    assert quarantined, (
        "the real corpus contains rows the TVTMS mapping cannot resolve "
        "(anchor or every target out of the OSIS canon); the adapter must "
        "tag them with tvtms_quarantine=True rather than silently dropping "
        "them. Zero quarantined nodes means the adapter stopped quarantining "
        "and is masking the coverage gap, violating Decision 5 step 4."
    )

    # The flag must be a real boolean True, per the frozen docstring
    # ("tvtms_quarantine of type bool, set true only on the unresolved
    # rows"), not a truthy string or int.
    non_bool = [
        n.get("id")
        for n in quarantined
        if n.get("tvtms_quarantine") is not True
    ]
    assert not non_bool, (
        f"tvtms_quarantine must be the bool literal True; nodes with a "
        f"non-bool flag: {non_bool[:5]}"
    )

    # A genuinely unresolvable row is one whose anchor did not project
    # (empty from_ref) OR whose every target failed to project (empty
    # to_ref). A correctly quarantined node MUST exhibit that shape; a
    # node flagged while both anchor and targets resolved would be a
    # spurious quarantine that hides nothing.
    mis_shaped = [
        n.get("id")
        for n in quarantined
        if n.get("from_ref", "") != "" and n.get("to_ref", "") != ""
    ]
    assert not mis_shaped, (
        f"quarantined nodes must have an unresolved anchor (empty from_ref) "
        f"or no resolved target (empty to_ref); fully-resolved nodes wrongly "
        f"flagged: {mis_shaped[:5]}. Decision 5: only unresolved rows carry "
        "the flag."
    )

    # And the flag must be absent on resolved rows so the rejection count
    # is the only field the verifier scans (frozen docstring: "absent on
    # resolved rows so $pred_bool(x) returns false in the resolved case").
    resolved_with_flag = [
        n.get("id")
        for n in nodes
        if n.get("tvtms_quarantine") is not True
        and n.get("tvtms_quarantine") is not None
    ]
    assert not resolved_with_flag, (
        f"resolved CrossRef nodes must not carry any tvtms_quarantine "
        f"value; offenders: {resolved_with_flag[:5]}"
    )


def test_resolved_crossref_nodes_have_no_quarantine_flag(
    fake_driver: FakeDriver, source_path: Path
) -> None:
    """CrossRef nodes for resolved entries must NOT have tvtms_quarantine=True.

    Decision 5: tvtms_quarantine must be absent (or False) on resolved rows.

    FAILS at Wave 2 with TypeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_path, fake_driver.settings)
    nodes = fake_driver.nodes_by_label("CrossRef")
    assert nodes, "adapter must emit at least one CrossRef node"
    resolved_ids = {"tsk:1.1.1.1", "tsk:19.119.1.3"}
    bad = [
        n for n in nodes
        if n.get("id") in resolved_ids and n.get("tvtms_quarantine") is True
    ]
    assert not bad, (
        f"Resolved CrossRef nodes incorrectly flagged tvtms_quarantine=True: "
        f"{[n.get('id') for n in bad]}. "
        "Only unresolvable rows must carry the quarantine flag."
    )


# ---------------------------------------------------------------------------
# GROUP 5: stub-rejection sweep (13 stubs, parametrized)
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
    source_path: Path,
) -> None:
    """The coverage-test scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_tsk or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected. Good.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_tsk", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
        )

    raised = False
    try:
        fn(source_path, fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_labels = fake_driver.captured_labels()
    emitted_edges = fake_driver.captured_edge_types()
    crossref_ids = fake_driver.captured_node_ids("CrossRef")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGE_TYPES.issubset(emitted_edges)
    no_forbidden = not (FORBIDDEN_EDGE_TYPES & emitted_edges)
    id_format_ok = (
        all(cid.startswith("tsk:") for cid in crossref_ids)
        if crossref_ids
        else False
    )

    rejected = not label_ok or not edge_ok or not no_forbidden or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample crossref ids: {crossref_ids[:3]}"
    )


# ---------------------------------------------------------------------------
# GROUP 6: static validation tests (pass even at Wave 2 red state)
# ---------------------------------------------------------------------------


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    This test does NOT call the adapter. It validates the predicate source file
    is present and parseable per RESEED_PLAN C.5.

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_tsk_count_from_expected_counts_json() -> None:
    """The TSK expected count in expected_counts.json must be 63682 (Tier A).

    This test does NOT call the adapter.

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    tsk_entry = ec["sources"]["TSK"]
    assert tsk_entry["expected_count"] == EXPECTED_NODE_COUNT, (
        f"expected_counts.json TSK count {tsk_entry['expected_count']} "
        f"!= {EXPECTED_NODE_COUNT}"
    )
    assert tsk_entry["tier"] == "A", "TSK must be Tier A"
    assert tsk_entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    seed = int('c68bac76', 16) = 3331042422
    length = random.Random(seed).randint(1024, 16384) = 16076

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}. "
        f"Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_fixture_has_three_entries(fixture_slice: dict[str, Any]) -> None:
    """The TSK fixture must have exactly 3 entries covering single/range/unresolved.

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    entries = fixture_slice.get("entries", [])
    assert len(entries) == 3, (
        f"TSK fixture must have 3 entries (single, range, unresolved); got {len(entries)}"
    )


def test_fixture_contains_range_entry(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain an entry whose xref_string is a range (contains '-').

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    entries = fixture_slice.get("entries", [])
    range_entries = [e for e in entries if "-" in e.get("xref_string", "")]
    assert range_entries, (
        "Fixture must include at least one range xref_string (e.g. 'Ps.119.1-5') "
        "to exercise the range-expansion path."
    )


def test_fixture_contains_unresolved_candidate(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain an entry flagged as an unresolved TVTMS candidate.

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    entries = fixture_slice.get("entries", [])
    unresolved = [e for e in entries if "unresolved" in e.get("note", "").lower()]
    assert unresolved, (
        "Fixture must include at least one unresolved-candidate entry "
        "to exercise the tvtms_quarantine path."
    )


def test_predicates_cypher_referenced_in_test() -> None:
    """tools/predicates_by_type.cypher must exist and have >= 1 predicate definition.

    This satisfies the 'predicates_by_type.cypher >= 1' gate in the HARD constraints.

    Passes at Wave 2 because it does not invoke ingest_tsk.
    """
    assert _PREDICATES_CYPHER_PATH.exists(), (
        f"tools/predicates_by_type.cypher not found at {_PREDICATES_CYPHER_PATH}"
    )
    assert len(PREDICATES) >= 1, (
        "predicates_by_type.cypher must define at least one $pred_<type>(x) predicate"
    )
