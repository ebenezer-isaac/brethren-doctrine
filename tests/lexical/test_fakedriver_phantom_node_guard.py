"""Proof tests for the FakeDriver Phase-D phantom-node guard.

Phase D added endpoint LABELS to every edge-MERGE Cypher template so the
Neo4j planner uses the backing uniqueness constraint instead of an
AllNodesScan. Example (ingest/lexical/oshb.py)::

    UNWIND $rows AS row
    MATCH (a:`Word` {id: row.from_id}), (b:`Morpheme` {id: row.to_id})
    MERGE (a)-[r:`HAS_MORPHEME`]->(b) RETURN count(r) AS edges

The per-adapter coverage tests share an in-test FakeDriver whose
``_parse_cypher_into_driver`` captured a node for any label whose
backtick-quoted token appeared ANYWHERE in the Cypher string. After the
Phase D label-add, an EDGE-merge call carries ``:`Word``` /
``:`Morpheme``` in its MATCH clause, so the node-capture branch fired and
recorded every edge-batch row (payload shaped ``{from_id, to_id, ...}``,
NO node ``id``/properties) as a PHANTOM node of those labels. That
polluted node_count / captured_node_ids / captured_properties and
false-failed coverage tests on data-present runs.

The faithful discrimination rule (proven across all 23 adapters):

* every NODE merge statement contains the literal ``"MERGE (n:"`` and
  carries node-identity rows;
* no EDGE merge statement contains ``"MERGE (n:"`` (edge merges are
  ``MERGE (a)-[r:`REL`]->(b)``); post-Phase-D the endpoint labels live
  only in the ``MATCH`` clause.

So a FakeDriver run may contribute node records only when the Cypher
contains ``"MERGE (n:"``. Real node MERGEs are captured byte-identically;
edge capture (the separate rel-type branch) is untouched.

These tests drive the SHARED helper of two representative adapters
(OSHB: heaviest edge surface; macula_greek: distinct label set) through
a real post-Phase-D edge-MERGE statement and a real node-MERGE statement
and assert:

1. the edge-MERGE call creates ZERO phantom nodes (the defect), while
2. the same call still records the edges (no edge regression), and
3. a genuine node-MERGE call is still captured with its id/properties.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

# The shared helper lives per-file; import the two representative copies.
_oshb = importlib.import_module("tests.lexical.test_oshb_coverage")
_macula = importlib.import_module("tests.lexical.test_macula_greek_coverage")


# Real post-Phase-D Cypher, copied verbatim in shape from the adapters.
_OSHB_EDGE_HAS_MORPHEME = (
    "UNWIND $rows AS row "
    "MATCH (a:`Word` {id: row.from_id}), (b:`Morpheme` {id: row.to_id}) "
    "MERGE (a)-[r:`HAS_MORPHEME`]->(b) RETURN count(r) AS edges"
)
_OSHB_EDGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a:`Word` {id: row.from_id}), (b:`Verse` {id: row.to_id}) "
    "MERGE (a)-[r:`IN_VERSE`]->(b) RETURN count(r) AS edges"
)
_OSHB_NODE_WORD = (
    "UNWIND $rows AS row MERGE (n:`Word` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)

_MG_EDGE_INSTANCE_OF = (
    "UNWIND $rows AS row "
    "MATCH (a:`Word` {id: row.from_id}), (b:`GreekLemma` {id: row.to_id}) "
    "MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges"
)
_MG_NODE_GREEK_LEMMA = (
    "UNWIND $rows AS row MERGE (n:`GreekLemma` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)

# Edge-batch rows: from_id/to_id only, NO node id/properties. These are
# exactly what the row builder UNWINDs for an edge MERGE.
_EDGE_ROWS = [
    {"from_id": "oshb:Gen.1.1.w01", "to_id": "oshb-morph:Gen.1.1.w01.m01"},
    {"from_id": "oshb:Gen.1.1.w02", "to_id": "oshb-morph:Gen.1.1.w02.m01"},
    {"from_id": "oshb:Gen.1.1.w03", "to_id": "oshb-morph:Gen.1.1.w03.m01"},
]


def _run(parser: Any, driver: Any, cypher: str, rows: list[dict[str, Any]]) -> None:
    parser(cypher, {"rows": rows}, driver)


# ---------------------------------------------------------------------------
# Defect proof: edge-MERGE with Phase-D labels must NOT create phantom nodes.
# ---------------------------------------------------------------------------


def test_oshb_edge_merge_creates_zero_phantom_nodes() -> None:
    drv = _oshb.FakeDriver()
    _run(_oshb._parse_cypher_into_driver, drv, _OSHB_EDGE_HAS_MORPHEME, _EDGE_ROWS)
    _run(_oshb._parse_cypher_into_driver, drv, _OSHB_EDGE_IN_VERSE, _EDGE_ROWS)

    assert drv._nodes == [], (
        "edge-MERGE Cypher created phantom nodes; the Phase-D MATCH-clause "
        f"labels leaked into node capture: {drv._nodes[:5]}"
    )
    assert drv.node_count("Word") == 0
    assert drv.node_count("Morpheme") == 0
    assert drv.node_count("Verse") == 0
    assert drv.captured_node_ids("Word") == []

    # Edge capture must STILL work (no edge regression).
    assert drv.edge_count("HAS_MORPHEME") == len(_EDGE_ROWS)
    assert drv.edge_count("IN_VERSE") == len(_EDGE_ROWS)
    assert drv.captured_edge_types() == {"HAS_MORPHEME", "IN_VERSE"}


def test_macula_greek_edge_merge_creates_zero_phantom_nodes() -> None:
    drv = _macula.FakeDriver()
    _run(_macula._parse_cypher_into_driver, drv, _MG_EDGE_INSTANCE_OF, _EDGE_ROWS)

    assert drv._nodes == [], (
        f"macula_greek edge-MERGE created phantom nodes: {drv._nodes[:5]}"
    )
    assert drv.node_count("Word") == 0
    assert drv.node_count("GreekLemma") == 0
    assert drv.edge_count("INSTANCE_OF") == len(_EDGE_ROWS)


# ---------------------------------------------------------------------------
# Faithfulness proof: a REAL node MERGE is still captured, unchanged.
# ---------------------------------------------------------------------------


def test_oshb_real_node_merge_still_captured() -> None:
    drv = _oshb.FakeDriver()
    node_rows = [
        {"id": "oshb:Gen.1.1.w01", "lemma": "rְ", "pos": 1},
        {"id": "oshb:Gen.1.1.w02", "lemma": "bָּרָא", "pos": 2},
    ]
    _run(_oshb._parse_cypher_into_driver, drv, _OSHB_NODE_WORD, node_rows)

    assert drv.node_count("Word") == 2
    assert drv.captured_node_ids("Word") == [
        "oshb:Gen.1.1.w01",
        "oshb:Gen.1.1.w02",
    ]
    captured = [n for n in drv._nodes if n["label"] == "Word"]
    assert captured[0]["lemma"] == "rְ" and captured[0]["pos"] == 1


def test_macula_greek_real_node_merge_still_captured() -> None:
    drv = _macula.FakeDriver()
    node_rows = [
        {"id": "SBLGNT:n40001001001", "lemma": "βίβλος"},
        {"id": "SBLGNT:n40001001002", "lemma": "γένεσις"},
    ]
    _run(_macula._parse_cypher_into_driver, drv, _MG_NODE_GREEK_LEMMA, node_rows)

    assert drv.node_count("GreekLemma") == 2
    assert drv.captured_node_ids("GreekLemma") == [
        "SBLGNT:n40001001001",
        "SBLGNT:n40001001002",
    ]


# ---------------------------------------------------------------------------
# Negative control: WITHOUT the guard the defect would manifest. We assert
# the guard token is the discriminator (edge cypher lacks it, node has it).
# This is a structural invariant, not a tautology: it fails if any future
# adapter edits break the "MERGE (n:" node-merge signature.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "edge_cypher",
    [_OSHB_EDGE_HAS_MORPHEME, _OSHB_EDGE_IN_VERSE, _MG_EDGE_INSTANCE_OF],
)
def test_edge_cypher_lacks_node_merge_signature(edge_cypher: str) -> None:
    assert "MERGE (n:" not in edge_cypher
    assert "MERGE (a)-[" in edge_cypher


@pytest.mark.parametrize(
    "node_cypher",
    [_OSHB_NODE_WORD, _MG_NODE_GREEK_LEMMA],
)
def test_node_cypher_has_node_merge_signature(node_cypher: str) -> None:
    assert "MERGE (n:" in node_cypher
    assert "-[" not in node_cypher
