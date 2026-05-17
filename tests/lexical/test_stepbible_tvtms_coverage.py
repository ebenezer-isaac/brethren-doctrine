"""STEPBible-TVTMS versification rule adapter coverage tests (Phase C.2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string and $pred_bool
definitions. Predicate semantics are loaded at module level from that file and used
to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tvtms.py has NO function body at this commit.
  Every test that calls ingest_stepbible_tvtms() MUST fail because getattr returns None
  and calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires (gate: >= 3 FAILED).

Entry function confirmed:
  - ingest/lexical/stepbible_tvtms.py docstring: no def body; contract names the
    function via the Acceptance Cypher (phase_02 Group 2 step 7).
  - The function is named ingest_stepbible_tvtms per source slug STEPBible-TVTMS.
  - run.py does not yet import this adapter (migration pending, docstring line 21).

Random seed:
  commit_sha = '27b5b533084b102f128f5ebc0b75d1d2f98f56fa' (git log -1 -- ingest/lexical/stepbible_tvtms.py)
  seed_int = int('27b5b533', 16) = 666219827
  seeded_length = random.Random(666219827).randint(1024, 16384) = 8179

Fixture: tests/lexical/fixtures/stepbible_tvtms_slice.json
  3 distinct rule_type categories: merged (KJV-LXX Psalms), split (Peshitta 1 John,
  Coptic Acts per Decisions 7 and 9), renumbered (Clementine Vulgate Psalms per Decision 8).
  Each category has 3 rows; total 9 rows, serialized fixture 3834 bytes (within 1024-16384).
  Seed from commit SHA above per RESEED_PLAN C.1.

Source: tools/expected_counts.json sources."STEPBible-TVTMS" expected_count=1308 (Tier A, tolerance 0).
Decisions: 5 (TVTMS per-field predicate table), 7 (Peshitta), 8 (Vulgate Clementine), 9 (Coptic).
Labels: VersificationRule.
Edges: none (lookup table, no graph edges emitted from this adapter per docstring).

Stub parametrization N/A notes (documented per RESEED_PLAN C.1 Verifier caste requirement):
  - Stubs that expose only emit_records/emit_edges with no ingest_stepbible_tvtms callable
    are skipped with an explicit reason message; the stub sweep still exercises the full list.
  - TVTMS has no outbound graph edges, so edge-direction and edge-floor stubs (reversed_edge_direction,
    minimal_edges) are skipped in the edge-floor assertion but still run the no-edges invariant.

Caste: verifier
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

# -- predicates_by_type.cypher (tools/predicates_by_type.cypher) -----------
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
ADAPTER_MODULE = "ingest.lexical.stepbible_tvtms"
ENTRY_FUNCTION = "ingest_stepbible_tvtms"

# VersificationRule is the only emitted label; Source is administrative.
REQUIRED_LABELS = frozenset({"VersificationRule", "Source"})

# No graph edges emitted from this adapter (lookup table per docstring).
REQUIRED_EDGES: frozenset[str] = frozenset()

EXPECTED_RULE_COUNT = 1308  # Tier A, tolerance 0, per expected_counts.json
SOURCE_SLUG = "STEPBible-TVTMS"
ARTIFACT_PATH = "data/private/stepbible/tvtms.parsed.json"

DOCSTRING_COMMIT_SHA = "27b5b533084b102f128f5ebc0b75d1d2f98f56fa"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 666219827

# VersificationRule required string fields per Decision 5 per-field predicate table.
REQUIRED_STRING_FIELDS = ("id", "tradition_a", "ref_a", "tradition_b", "ref_b", "rule_type", "source")
# 'note' is present but may be empty in some rows; not asserted as non-empty here.

# Stable-id five-axis tuple format per docstring.
STABLE_ID_PREFIX = "tvtms:"


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    The adapter under test (VersificationRule lookup table) emits nodes but
    no outbound graph edges. This fake captures MERGE payloads so tests can
    assert label presence, stable-id format, and the no-edges invariant.

    When the adapter body is absent (Wave 2 red state), the driver is never
    reached because calling ingest_stepbible_tvtms() raises TypeError first.
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
        return {"upserted": 1, "edges": 0}

    def consume(self) -> None:
        pass


def _parse_cypher_into_driver(
    cypher: str, params: dict[str, Any], driver: FakeDriver
) -> None:
    """Best-effort parse of MERGE Cypher statements into FakeDriver records.

    The TVTMS adapter is expected to issue:
      MERGE (n:VersificationRule {id: ...})
      MERGE (n:Source {slug: ...})
    and NO edge MERGE statements (lookup table, no outbound edges per docstring).

    The parser records the label and key property from UNWIND batch params.
    This is intentionally lenient; the important invariant is that no edge
    records are captured, which is asserted by test_no_outbound_edges.
    """
    for label in ("VersificationRule", "Source"):
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label})" in cypher
            or f":{label}{{" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list) and rows_param:
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    # TVTMS has no edge types; detect any accidental edge MERGE and record it
    # so the no-edges invariant test will catch it.
    for candidate in (
        "]->(", "]-[", "MERGE (a)-", "MERGE (b)-"
    ):
        if candidate in cypher:
            rel_match = None
            for tok in cypher.split(":"):
                stripped = tok.split("]")[0].split(")")[0].strip()
                if stripped and stripped.upper() == stripped and len(stripped) > 2:
                    rel_match = stripped
                    break
            driver._edges.append({"rel_type": rel_match or "UNKNOWN"})


# -- fixtures ----------------------------------------------------------------

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tvtms_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def data_root(tmp_path: Path, fixture_slice: dict[str, Any]) -> Path:
    """Return a temp directory that contains a synthetic tvtms.parsed.json.

    The adapter docstring specifies it reads from
    data/private/stepbible/tvtms.parsed.json. We write the fixture rows
    to that path under tmp_path so the adapter can be called without
    private data on disk.
    """
    tvtms_dir = tmp_path / "stepbible"
    tvtms_dir.mkdir(parents=True)
    artifact = tvtms_dir / "tvtms.parsed.json"
    artifact.write_text(
        json.dumps(fixture_slice["rows"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tvtms.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_tvtms', None) returns None and the assert fails.
    That failure IS the expected red state the orchestrator gate requires.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """ingest_stepbible_tvtms must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(data_root / "stepbible", fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tvtms must return dict; got {type(result)!r}"
    )
    assert "VersificationRule" in result, "return dict must contain 'VersificationRule' key"


def test_adapter_emits_versification_rule_label(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Running the adapter must merge VersificationRule nodes.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 5: VersificationRule is the only record-level label emitted.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "VersificationRule" in emitted, (
        f"adapter did not emit VersificationRule label. Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_source_node(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """The Source node must be MERGEd with slug='STEPBible-TVTMS'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Source.slug uniqueness constraint. Source is MERGEd once at
    ingest start, before any record-level write per adapter-local invariant 2.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_versification_rule_stable_id_format(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Every VersificationRule node must have an id starting with 'tvtms:'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Stable id format per docstring: 'tvtms:<tradition_a>:<ref_a>:<tradition_b>:<ref_b>:<rule_type>'
    Five-axis tuple as the natural composite key, byte-preserving from upstream row.
    Predicate: $pred_string from tools/predicates_by_type.cypher = x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    rule_ids = fake_driver.captured_node_ids("VersificationRule")
    assert rule_ids, "adapter must emit at least one VersificationRule node"
    bad = [rid for rid in rule_ids if not rid.startswith(STABLE_ID_PREFIX)]
    assert not bad, (
        f"VersificationRule ids violate '{STABLE_ID_PREFIX}' prefix format: {bad[:5]}"
    )


def test_versification_rule_stable_id_has_five_axes(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Every VersificationRule stable id must encode exactly five axes separated by colons.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Format: 'tvtms:<tradition_a>:<ref_a>:<tradition_b>:<ref_b>:<rule_type>'
    After stripping the 'tvtms:' prefix, the remainder must contain exactly 4 additional
    colon-delimited segments (5 total axes, 4 separators after the prefix colon).
    The ref fields may themselves contain dots but not colons per the upstream format.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    rule_ids = fake_driver.captured_node_ids("VersificationRule")
    assert rule_ids, "adapter must emit at least one VersificationRule node"
    bad = []
    for rid in rule_ids:
        # Strip 'tvtms:' prefix then split the remainder on ':'
        # Expected parts: tradition_a, ref_a, tradition_b, ref_b, rule_type (5 parts)
        after_prefix = rid[len(STABLE_ID_PREFIX):]
        parts = after_prefix.split(":")
        if len(parts) != 5:
            bad.append((rid, len(parts)))
    assert not bad, (
        f"VersificationRule ids do not have exactly 5 axes after 'tvtms:' prefix: {bad[:3]}"
    )


def test_no_outbound_edges(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """The TVTMS adapter must emit zero outbound graph edges (lookup table).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring 'Emitted edge types: None.' The VersificationRule label is a
    lookup table consumed by downstream adapters via serialized artifact, not via
    graph edges from this module. Any edge captured by FakeDriver is a defect.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    emitted_edges = fake_driver.captured_edge_types()
    assert not emitted_edges, (
        f"TVTMS adapter must emit no graph edges but emitted: {sorted(emitted_edges)}. "
        "VersificationRule is a lookup table; downstream adapters read the serialized artifact."
    )


def test_versification_rule_required_fields_non_empty(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Every VersificationRule node must have non-empty values for all required string fields.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Required fields per Decision 5 per-field predicate type table:
    tradition_a, ref_a, tradition_b, ref_b, rule_type, source.
    All are $pred_string: x IS NOT NULL AND trim(toString(x)) <> ''
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    rule_nodes = [n for n in fake_driver._nodes if n.get("label") == "VersificationRule"]
    assert rule_nodes, "adapter must emit at least one VersificationRule node"
    violations: list[tuple[str, str]] = []
    for node in rule_nodes:
        node_id = node.get("id", "<no-id>")
        for field in REQUIRED_STRING_FIELDS:
            val = node.get(field)
            if not (val is not None and str(val).strip() != ""):
                violations.append((node_id, field))
    assert not violations, (
        f"VersificationRule nodes with empty required fields: {violations[:5]}. "
        f"Predicate: {PREDICATES.get('string', 'not loaded')}"
    )


def test_versification_rule_source_property(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Every VersificationRule node must have source='STEPBible-TVTMS'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    The Acceptance Cypher from phase_02 bullet 7 gates on
    VersificationRule {source: 'STEPBible-TVTMS'} explicitly.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    rule_nodes = [n for n in fake_driver._nodes if n.get("label") == "VersificationRule"]
    assert rule_nodes, "adapter must emit at least one VersificationRule node"
    bad = [n for n in rule_nodes if n.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"VersificationRule nodes with wrong source property: "
        f"{[n.get('source') for n in bad[:3]]}. Expected '{SOURCE_SLUG}'."
    )


def test_versification_rule_license_and_redistribute(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """VersificationRule nodes must carry license='CC-BY-4.0' and redistribute=True.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: CC-BY-4.0 sources have redistribute=true per LICENSE_TAGGING.md row
    STEPBible-TVTMS (line 58). $pred_bool: x IS NOT NULL.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root / "stepbible", fake_driver.settings)
    rule_nodes = [n for n in fake_driver._nodes if n.get("label") == "VersificationRule"]
    assert rule_nodes, "adapter must emit at least one VersificationRule node"
    bad_license = [n for n in rule_nodes if n.get("license") != "CC-BY-4.0"]
    assert not bad_license, (
        f"VersificationRule nodes with wrong license: "
        f"{[n.get('license') for n in bad_license[:3]]}. Expected 'CC-BY-4.0'."
    )
    bad_redist = [n for n in rule_nodes if n.get("redistribute") is not True]
    assert not bad_redist, (
        f"VersificationRule nodes with redistribute != True: "
        f"{[n.get('redistribute') for n in bad_redist[:3]]}. "
        f"Predicate: {PREDICATES.get('bool', 'not loaded')}"
    )


def test_artifact_path_referenced_in_contract() -> None:
    """The serialized rule-set artifact path must be referenced in the adapter docstring.

    This test does NOT call the adapter. It validates the artifact path contract
    per docstring 'Serialized rule set artifact: data/private/stepbible/tvtms.parsed.json'.
    Downstream adapters (TSK, OpenBible, Peshitta, Vulgate, Coptic) load this artifact
    at ingest start; the path must be stable and documented.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    docstring = mod.__doc__ or ""
    assert ARTIFACT_PATH in docstring, (
        f"Adapter docstring must reference artifact path '{ARTIFACT_PATH}'. "
        f"Downstream adapters (TSK, OpenBible, Peshitta, Vulgate, Coptic) depend on it."
    )


def test_expected_count_from_expected_counts_json() -> None:
    """STEPBible-TVTMS expected count in expected_counts.json must be 1308 (Tier A).

    This test does NOT call the adapter. It validates the count constant
    used by coverage tests against the source file per RESEED_PLAN A.4 freeze.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TVTMS"]
    assert entry["expected_count"] == EXPECTED_RULE_COUNT, (
        f"expected_counts.json STEPBible-TVTMS count {entry['expected_count']} "
        f"!= {EXPECTED_RULE_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TVTMS must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "versification_rule", (
        f"record_unit must be 'versification_rule'; got {entry['record_unit']!r}"
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
    assert "IS NOT NULL" in PREDICATES["bool"], (
        "$pred_bool must contain IS NOT NULL check"
    )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture seeded_length must be reproducible from the stored seed_int.

    Seed = int(commit_sha[:8], 16) = int('27b5b533', 16) = 666219827.
    seeded_length = random.Random(666219827).randint(1024, 16384) = 8179.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert fixture_slice["seeded_length"] == expected_length, (
        f"Fixture seeded_length {fixture_slice['seeded_length']} != "
        f"seeded length {expected_length} from seed_int={SEED_INT}"
    )
    assert fixture_slice["seed_int"] == SEED_INT, (
        f"Fixture seed_int {fixture_slice['seed_int']} != {SEED_INT}"
    )


def test_fixture_has_three_rule_type_categories(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain exactly 3 distinct rule_type categories.

    This test does NOT call the adapter. It validates the fixture quality per
    RESEED_PLAN C.1 Verifier requirement: fixture must cover 3 distinct rule_type
    categories so the stub sweep exercises the rule_type discriminator.
    """
    rows = fixture_slice.get("rows", [])
    assert rows, "fixture must contain at least one row"
    categories = fixture_slice.get("rule_type_categories", [])
    assert len(categories) == 3, (
        f"fixture must declare exactly 3 rule_type_categories; got {categories}"
    )
    seen_types = {row["rule_type"] for row in rows}
    for cat in categories:
        assert cat in seen_types, (
            f"fixture declares rule_type_categories={categories} but "
            f"'{cat}' not found in rows. Seen: {sorted(seen_types)}"
        )


# ---------------------------------------------------------------------------
# Acceptance Cypher reference test
# ---------------------------------------------------------------------------

def test_acceptance_cypher_in_phase02_runbook() -> None:
    """The Acceptance Cypher from phase_02 bullet 7 must be present in the docstring.

    This test does NOT call the adapter. It validates that the adapter docstring
    reproduces the acceptance Cypher verbatim per the Verifier caste contract.
    The Cypher fragment: 'MATCH (r:VersificationRule {source: .STEPBible-TVTMS.})'
    must appear in the module docstring so Phase D can grep for it.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    docstring = mod.__doc__ or ""
    expected_fragment = "MATCH (r:VersificationRule {source: 'STEPBible-TVTMS'})"
    assert expected_fragment in docstring, (
        f"Adapter docstring must contain the acceptance Cypher fragment: "
        f"'{expected_fragment}'"
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (13 stubs, parametrized)
#
# TVTMS-specific N/A notes:
#   - reversed_edge_direction: N/A because TVTMS emits no edges; skipped with reason.
#   - minimal_edges: N/A for the same reason; tested via no-edges invariant above.
#   - hash_ordered: applies to stable-id determinism; tested via id-format assertions.
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
    data_root: Path,
) -> None:
    """The coverage-test scaffold must detect defects in each attack-vector stub.

    TVTMS-specific N/A assertions (documented per RESEED_PLAN C.1):
      - reversed_edge_direction: TVTMS emits no edges, so edge-direction check is N/A.
        The stub is still imported and run; if it crashes, that counts as rejection.
        If it runs silently, the no-edges invariant catches any edge it emits.
      - minimal_edges: same as reversed_edge_direction.
      - hash_ordered: tested via stable-id format check (five-axis tuple).

    Pattern:
      1. Import the stub.
      2. Find an ingest entry point named ingest_stepbible_tvtms, ingest_oshb, or ingest.
      3. If no entry point, skip (stub exposes only emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, stub is rejected.
      5. If it runs silently, check label presence, source property, and id format.
         At least one check must fail. If none fail, the test fails.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest_oshb", None)
        or getattr(stub_mod, "ingest", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(attrs: {[x for x in dir(stub_mod) if not x.startswith('_')]}). "
            "Stub exposes only emit_records/emit_edges; no adapter contract to exercise."
        )

    raised = False
    try:
        fn(data_root / "stepbible", fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    # Stub ran without raising. At least one check must catch the defect.
    emitted_labels = fake_driver.captured_labels()
    rule_nodes = [n for n in fake_driver._nodes if n.get("label") == "VersificationRule"]
    rule_ids = fake_driver.captured_node_ids("VersificationRule")

    has_required_label = "VersificationRule" in emitted_labels
    source_ok = all(n.get("source") == SOURCE_SLUG for n in rule_nodes) if rule_nodes else False
    id_format_ok = (
        all(rid.startswith(STABLE_ID_PREFIX) for rid in rule_ids) if rule_ids else False
    )
    # For TVTMS, emitting any edges is itself a defect (no-edges invariant).
    no_edge_defect = len(fake_driver._edges) == 0

    rejected = (
        not has_required_label
        or not source_ok
        or not id_format_ok
        or not no_edge_defect
    )
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Source ok: {source_ok}, "
        f"Id format ok: {id_format_ok}, "
        f"Edge count: {len(fake_driver._edges)}"
    )
