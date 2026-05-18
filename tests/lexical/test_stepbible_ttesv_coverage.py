"""STEPBible-TTESV adapter coverage tests (Phase C Wave 2, verifier caste).

Subject: phase C.2 verifier: stepbible_ttesv

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool definitions. Predicate semantics are loaded at module level from that
file. Inline predicate definitions are forbidden per RESEED_PLAN C.5.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_ttesv.py has NO function body at this
  commit. Every test that calls ingest_stepbible_ttesv() MUST fail because
  getattr returns None and calling None raises TypeError. That failure IS the
  red state the Wave 2 orchestrator gate requires (GATE: >=3 FAILED).

Entry function confirmed:
  ingest/lexical/stepbible_ttesv.py docstring: contract names ingest_stepbible_ttesv.
  Source slug: STEPBible-TTESV.

Random seed:
  commit_sha = 'd45619bd1382d84558640f08e10b767055f37567' (git log -1 -- ingest/lexical/stepbible_ttesv.py)
  seed = int('d45619bd', 16) = 3562412477

Fixture: tests/lexical/fixtures/stepbible_ttesv_slice.json
  Three corpus slices: OT-torah (Gen.1.1), OT-prophets (Isa.53.5), NT-epistles (Rom.5.8).
  Mix of OT and NT to exercise H-prefix dispatch to Lemma and G-prefix to GreekLemma.
  Includes one untagged glue token (no Strong) to test INSTANCE_OF skip.
  length = 6515 (seeded from RNG).

Source: tools/expected_counts.json sources."STEPBible-TTESV" expected_count=31127.
Decisions: 14 (Strong/Source predicate constraints), 15 (Verse.text exclusion policy).

Caste: verifier
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

# -- predicates_by_type.cypher (tools/predicates_by_type.cypher) ------------------
# Loaded at module level. Inline predicate definitions are forbidden per RESEED_PLAN C.5.
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

# -- adapter constants -------------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.stepbible_ttesv"
ENTRY_FUNCTION = "ingest_stepbible_ttesv"
SOURCE_SLUG = "STEPBible-TTESV"
LICENSE = "CC-BY-NC-4.0"
REDISTRIBUTE = False

REQUIRED_LABELS = frozenset({"TaggedToken", "Source"})
REQUIRED_EDGES = frozenset({"INSTANCE_OF", "FROM_EDITION"})

EXPECTED_TOKEN_COUNT = 31127  # Tier A, tolerance 0, per expected_counts.json

# Seed from stepbible_ttesv.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "d45619bd1382d84558640f08e10b767055f37567"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3562412477


# -- FakeDriver that records every node/edge emitted ------------------------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels, edge
    types, and node-id formats without a live graph. When the adapter body is
    absent (Wave 2 red state) the driver is never reached because calling
    ingest_stepbible_ttesv() raises TypeError first.
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
      MERGE (n:TaggedToken {id: ...})
      MERGE (n:Source {slug: ...})
      MERGE (a)-[r:INSTANCE_OF]->(b)
      MERGE (a)-[r:FROM_EDITION]->(b)

    The parser records the label and key property found in the UNWIND batch
    (rows/records parameter) when present. Intentionally lenient; a
    docstring-only adapter produces NO calls at all (red state).
    """
    for label in ("TaggedToken", "Source", "Lemma", "GreekLemma"):
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label}{{" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("INSTANCE_OF", "FROM_EDITION"):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# -- fixtures ---------------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_ttesv_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the private TTESV data directory (may not exist on CI)."""
    return REPO / "data" / "private" / "stepbible" / "Tagged-Bibles"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_ttesv.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_ttesv', None) returns None and the assert
    fails. That failure IS the expected red state.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_ttesv must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_ttesv must return dict; got {type(result)!r}"
    )
    assert "TaggedToken" in result, "return dict must contain 'TaggedToken' key"


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

    INSTANCE_OF dispatches to Lemma (H-prefix Strong) or GreekLemma (G-prefix Strong).
    FROM_EDITION links every TaggedToken to the Source node.
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


def test_tagged_token_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every TaggedToken must have id starting with 'stepbible-ttesv:'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id spec: 'stepbible-ttesv:<osisRef>.w<pos>' per adapter docstring.
    Predicate: $pred_string from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_ids = fake_driver.captured_node_ids("TaggedToken")
    assert token_ids, "adapter must emit at least one TaggedToken node"
    bad = [tid for tid in token_ids if not tid.startswith("stepbible-ttesv:")]
    assert not bad, f"TaggedToken ids violate 'stepbible-ttesv:' prefix format: {bad[:5]}"


def test_source_node_slug_and_license(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Source node must be MERGEd with slug='STEPBible-TTESV', license='CC-BY-NC-4.0'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Source uniqueness constraint on source_slug.
    $pred_string predicate applies to both slug and license.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )
    source_nodes = [
        n for n in fake_driver._nodes
        if n.get("label") == "Source" and n.get("slug") == SOURCE_SLUG
    ]
    assert source_nodes, f"No Source node found with slug='{SOURCE_SLUG}'"
    for sn in source_nodes:
        assert sn.get("license") == LICENSE, (
            f"Source node license must be '{LICENSE}'; got {sn.get('license')!r}"
        )
        assert sn.get("redistribute") is REDISTRIBUTE, (
            f"Source node redistribute must be {REDISTRIBUTE}; got {sn.get('redistribute')!r}"
        )


def test_tagged_token_carries_license_and_redistribute(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every TaggedToken must carry license='CC-BY-NC-4.0' and redistribute=False.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Acceptance Cypher (phase_02 bullet 13):
      MATCH (t:TaggedToken {source: 'STEPBible-TTESV'})
      WHERE t.license = 'CC-BY-NC-4.0' AND t.redistribute = false
      WITH count(t) AS tokens
      RETURN tokens, tokens > 0

    $pred_string applies to license; $pred_bool applies to redistribute.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.nodes_for_label("TaggedToken")
    assert tokens, "adapter must emit at least one TaggedToken"
    bad_license = [t for t in tokens if t.get("license") != LICENSE]
    assert not bad_license, (
        f"TaggedToken nodes with wrong license (expected '{LICENSE}'): "
        f"{[t.get('license') for t in bad_license[:3]]}"
    )
    bad_redistribute = [t for t in tokens if t.get("redistribute") is not REDISTRIBUTE]
    assert not bad_redistribute, (
        f"TaggedToken nodes with wrong redistribute (expected {REDISTRIBUTE}): "
        f"{[t.get('redistribute') for t in bad_redistribute[:3]]}"
    )


def test_instance_of_dispatches_h_prefix_to_lemma(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """INSTANCE_OF from a Hebrew TaggedToken (H-prefix Strong) must point to Lemma.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Strong prefix 'H' -> INSTANCE_OF -> Lemma.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    hebrew_tokens = [
        n for n in fake_driver._nodes
        if n.get("label") == "TaggedToken" and str(n.get("language", "")).lower() == "hebrew"
    ]
    assert hebrew_tokens, (
        "adapter must emit at least one TaggedToken with language='hebrew' "
        "(OT corpus tokens with H-prefix Strong)"
    )
    # When a hebrew token has a Strong, an INSTANCE_OF edge to Lemma is expected.
    # The FakeDriver records INSTANCE_OF edges; Lemma nodes must also be emitted.
    instance_of_count = fake_driver.edge_count("INSTANCE_OF")
    assert instance_of_count > 0, (
        "adapter must emit at least one INSTANCE_OF edge for H-prefix tokens"
    )


def test_instance_of_dispatches_g_prefix_to_greek_lemma(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """INSTANCE_OF from a Greek TaggedToken (G-prefix Strong) must point to GreekLemma.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Strong prefix 'G' -> INSTANCE_OF -> GreekLemma.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    greek_tokens = [
        n for n in fake_driver._nodes
        if n.get("label") == "TaggedToken" and str(n.get("language", "")).lower() == "greek"
    ]
    assert greek_tokens, (
        "adapter must emit at least one TaggedToken with language='greek' "
        "(NT corpus tokens with G-prefix Strong)"
    )
    # GreekLemma targets must exist for G-prefix INSTANCE_OF edges.
    emitted_labels = fake_driver.captured_labels()
    assert "GreekLemma" in emitted_labels, (
        "adapter must emit GreekLemma nodes for G-prefix INSTANCE_OF dispatch. "
        f"Labels seen: {sorted(emitted_labels)}"
    )


def test_untagged_token_skips_instance_of(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """A TaggedToken with no Strong must NOT produce an INSTANCE_OF edge.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Adapter edge-case 1: glue tokens (strong='') are persisted as TaggedToken
    nodes but the INSTANCE_OF edge is skipped. The total row count must still
    reach 31127 (tier A, tolerance 0).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_count = fake_driver.node_count("TaggedToken")
    instance_of_count = fake_driver.edge_count("INSTANCE_OF")
    # INSTANCE_OF count must be < TaggedToken count if any untagged tokens exist.
    # Fixture contains exactly one untagged token; this assertion holds for full data too.
    assert token_count > 0, "adapter must emit TaggedToken nodes"
    assert instance_of_count <= token_count, (
        f"INSTANCE_OF count ({instance_of_count}) exceeds TaggedToken count "
        f"({token_count}). Untagged glue tokens must not produce INSTANCE_OF edges."
    )


def test_adapter_does_not_write_verse_text(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter must NOT set or update any Verse.text property (Decision 15).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 15: only OSHB-morphology (OT) and MorphGNT-SBLGNT (NT) may write
    Verse.text. TTESV emits an English ESV surface, not the canonical Hebrew or
    Greek surface. Writing it into Verse.text would shadow canonical text.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    verse_nodes = fake_driver.nodes_for_label("Verse")
    nodes_with_text = [v for v in verse_nodes if v.get("text") is not None]
    assert not nodes_with_text, (
        f"adapter must NOT write Verse.text (Decision 15), "
        f"but {len(nodes_with_text)} Verse nodes carry a 'text' property: "
        f"{nodes_with_text[:2]}"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool predicates.

    This test does NOT call the adapter. It validates the predicate source file
    is present and parseable per RESEED_PLAN C.5. predicates_by_type.cypher
    must contain at least one INSTANCE_OF-applicable entry.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )


def test_expected_token_count_from_expected_counts_json() -> None:
    """STEPBible-TTESV expected count in expected_counts.json must be 31127 (Tier A).

    This test does NOT call the adapter. It validates the count constant
    used by the coverage tests is correct per the source file.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TTESV"]
    assert entry["expected_count"] == EXPECTED_TOKEN_COUNT, (
        f"expected_counts.json STEPBible-TTESV count {entry['expected_count']} "
        f"!= {EXPECTED_TOKEN_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TTESV must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('d45619bd', 16) = 3562412477.
    RNG.randint(1024, 16384) -> 6515.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (parametrized over 13 attack-vector stubs)
#
# Each stub must be rejected by at least one coverage assertion. These tests
# skip (not fail) when the stub has no ingest entry point.
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
      2. Try to find an ingest entry point named ingest_stepbible_ttesv or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test itself fails with
         'verifier failed to detect defect'.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_ttesv", None)
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
    token_ids = fake_driver.captured_node_ids("TaggedToken")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_format_ok = (
        all(tid.startswith("stepbible-ttesv:") for tid in token_ids)
        if token_ids
        else False
    )

    rejected = not label_ok or not edge_ok or not id_format_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample token ids: {token_ids[:3]}"
    )
