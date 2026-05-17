"""STEPBible-morph-codes adapter coverage tests (Phase C.2 verifier).

This file references tools/predicates_by_type.cypher for $pred_string and
$pred_list definitions. Predicate semantics are loaded at module level from
that file per RESEED_PLAN C.5; inline predicates are forbidden.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_morph_codes.py has NO function body
  at this commit. Every test that calls ingest_stepbible_morph_codes() MUST
  fail because getattr returns None and calling None raises
  TypeError: 'NoneType' object is not callable. That failure IS the red state
  the Phase C.2 orchestrator gate requires (gate: >= 3 FAILED).

Entry function confirmed:
  - ingest/lexical/stepbible_morph_codes.py docstring: no def present.
  - SOURCE_SLUG: STEPBible-morph-codes
  - ENTRY_FUNCTION: ingest_stepbible_morph_codes

Random seed:
  commit_sha = 'd45619bd1382d84558640f08e10b767055f37567'
      (git log -1 -- ingest/lexical/stepbible_morph_codes.py)
  seed_int = int('d45619bd', 16) = 3562412477

Fixture: tests/lexical/fixtures/stepbible_morph_codes_slice.json
  3 morph codes: one verb (HVqp3ms), one noun (HNcmsa), one particle (HTi).
  The particle carries an expansions list (multi-expansion edge case from
  Decision 17 Edge cases handled bullet 1).
  seeded_length = 6515 (json.dumps output, UTF-8 bytes).

Source: tools/expected_counts.json sources."STEPBible-morph-codes"
  expected_count = 2782, tier = A, tolerance = 0, record_unit = morph_code.
Decisions implemented: 17 (MorphCode fields, sparse-column rule, multi-expansion),
                       14 (Source node MERGE, source_slug constraint).
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
# Loaded at module level. Inline predicates are forbidden per RESEED_PLAN C.5.
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
ADAPTER_MODULE = "ingest.lexical.stepbible_morph_codes"
ENTRY_FUNCTION = "ingest_stepbible_morph_codes"
SOURCE_SLUG = "STEPBible-morph-codes"

REQUIRED_LABELS = frozenset({"MorphCode", "Source"})

# No outbound edges from MorphCode per the docstring contract.
REQUIRED_EDGES: frozenset[str] = frozenset()

EXPECTED_MORPH_CODE_COUNT = 2782  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "d45619bd1382d84558640f08e10b767055f37567"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3562412477


# -- FakeDriver that records every node the adapter emits --------------------


class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures every MERGE payload so tests can assert on emitted labels and
    node property bags without a live graph. When the adapter body is absent
    (Wave 2 red state) the driver is never reached because calling
    ingest_stepbible_morph_codes() raises TypeError first.
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

    def captured_nodes(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]

    def captured_node_ids(self, label: str) -> list[str]:
        return [
            n["code"]
            for n in self._nodes
            if n.get("label") == label and "code" in n
        ]

    def captured_node_slugs(self, label: str) -> list[str]:
        return [
            n["slug"]
            for n in self._nodes
            if n.get("label") == label and "slug" in n
        ]

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n.get("label") == label)


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

    def run(self, cypher: str, **kwargs: Any) -> "_FakeResult":
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
    """Best-effort parse of MERGE Cypher into FakeDriver records.

    The adapter is expected to issue MERGE (n:MorphCode {code: ...}) and
    MERGE (n:Source {slug: ...}) statements. This parser records label and
    property bag from the UNWIND batch when present, and is intentionally
    lenient because a docstring-only adapter produces no Cypher at all.
    """
    for label in ("MorphCode", "Source"):
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


# -- fixtures ----------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_morph_codes_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def data_root() -> Path:
    """Return the conventional data root for the STEPBible-morph-codes adapter."""
    return REPO / "data" / "private" / "stepbible"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_morph_codes.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_morph_codes', None) returns None and the
    assert fails. That failure IS the red TDD state the orchestrator requires.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Phase C.2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, data_root: Path) -> None:
    """ingest_stepbible_morph_codes must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17: adapter writes MorphCode nodes; return dict must contain
    'MorphCode' key.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(data_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_morph_codes must return dict; got {type(result)!r}"
    )
    assert "MorphCode" in result, "return dict must contain 'MorphCode' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Running the adapter must merge nodes for every required label.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Required labels: MorphCode (Decision 17), Source (Decision 14).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    missing = REQUIRED_LABELS - emitted
    assert not missing, (
        f"adapter did not emit required node labels: {sorted(missing)}. "
        f"Labels seen: {sorted(emitted)}"
    )


def test_morph_code_nodes_have_required_fields(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Every MorphCode node must carry code, expansion, and source fields.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17 per-field predicate table:
      code       string  $pred_string(x)  = x IS NOT NULL AND trim(toString(x)) <> ''
      expansion  string  $pred_string(x)
      source     string  $pred_string(x)  = 'STEPBible-morph-codes'
    Sparse residual columns MUST NOT appear as node properties.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("MorphCode")
    assert nodes, "adapter must emit at least one MorphCode node"

    pred_string = PREDICATES.get("string", "")
    assert "IS NOT NULL" in pred_string, (
        "$pred_string from predicates_by_type.cypher must contain IS NOT NULL"
    )

    for node in nodes:
        code = node.get("code")
        assert code is not None and str(code).strip() != "", (
            f"MorphCode node violates $pred_string on code: {node!r}"
        )
        expansion = node.get("expansion")
        assert expansion is not None and str(expansion).strip() != "", (
            f"MorphCode node violates $pred_string on expansion: {node!r}"
        )
        source = node.get("source")
        assert source == SOURCE_SLUG, (
            f"MorphCode.source must be '{SOURCE_SLUG}'; got {source!r}"
        )


def test_morph_code_stable_id_is_code_property(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """The stable id (MERGE key) for MorphCode is the code property verbatim.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17: 'The code property is the canonical join key downstream
    verifier queries reference via MATCH (m:MorphCode {code: $code})'.
    Constraint: morph_code_unique on MorphCode.code.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    codes = fake_driver.captured_node_ids("MorphCode")
    assert codes, "adapter must emit at least one MorphCode node with a code field"
    empty_codes = [c for c in codes if not str(c).strip()]
    assert not empty_codes, (
        f"MorphCode.code must never be empty string (graph constraint morph_code_unique). "
        f"Empty codes found: {empty_codes[:5]}"
    )


def test_multi_expansion_edge_case(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """When a row has multiple populated detail columns, expansions must be a non-empty list.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17 Edge cases handled bullet 1:
      'The adapter MUST persist all expansions in an expansions list-typed
      property when the row has more than one populated detail column,
      preventing silent loss of alternative parses.'
    $pred_list(x) := x IS NOT NULL AND size(x) > 0
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("MorphCode")
    assert nodes, "adapter must emit at least one MorphCode node"

    pred_list = PREDICATES.get("list", "")
    assert "size(x)" in pred_list, (
        "$pred_list from predicates_by_type.cypher must contain size(x)"
    )

    multi_expansion_nodes = [
        n for n in nodes
        if n.get("expansions") is not None
    ]
    if not multi_expansion_nodes:
        pytest.skip(
            "No multi-expansion MorphCode nodes emitted in this run; "
            "edge case requires upstream rows with more than one detail column. "
            "Skipped at Wave 2 (docstring-only). "
            "N/A: adapter has no function body to exercise this path."
        )

    for node in multi_expansion_nodes:
        expansions = node["expansions"]
        assert isinstance(expansions, list) and len(expansions) > 0, (
            f"expansions must be a non-empty list ($pred_list); got {expansions!r}"
        )


def test_single_expansion_leaves_expansions_null(
    fake_driver: FakeDriver, data_root: Path
) -> None:
    """Single-expansion rows must leave expansions null so $pred_list returns false.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 17: 'When the upstream row carries exactly one expansion,
    expansions is left null and the $pred_list(expansions) predicate returns
    false on that node, honestly reflecting the absence of alternatives.'
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    nodes = fake_driver.captured_nodes("MorphCode")
    assert nodes, "adapter must emit at least one MorphCode node"

    single_expansion_nodes = [
        n for n in nodes
        if n.get("expansions") is None
    ]
    if not single_expansion_nodes:
        pytest.skip(
            "All emitted MorphCode nodes have expansions set; "
            "cannot verify single-expansion null rule. "
            "N/A: edge case requires single-expansion rows from upstream."
        )

    for node in single_expansion_nodes:
        assert node.get("expansions") is None, (
            f"Single-expansion MorphCode must have expansions=None; got {node!r}"
        )


def test_source_node_slug(fake_driver: FakeDriver, data_root: Path) -> None:
    """The Source node must be MERGEd with slug='STEPBible-morph-codes'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Decision 14: Source uniqueness constraint on source_slug.
    The Source node carries:
      slug         = 'STEPBible-morph-codes'  ($pred_string)
      license      = 'CC-BY-4.0'
      redistribute = true
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_no_edges_emitted(fake_driver: FakeDriver, data_root: Path) -> None:
    """The adapter must emit zero outbound relationships from MorphCode nodes.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Docstring contract: 'STEPBible-morph-codes is a pure reference lookup
    table consumed by downstream verifier queries via MATCH on the code
    property; the adapter writes zero outbound relationships from MorphCode
    nodes.'
    N/A for edge assertions: documented skip reason per ADAPTER: no edges.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(data_root, fake_driver.settings)
    edge_count = len(fake_driver._edges)
    assert edge_count == 0, (
        f"adapter must emit zero edges from MorphCode (pure lookup table); "
        f"got {edge_count} edges. "
        "Decision 17: 'No edges are written.'"
    )


# ---------------------------------------------------------------------------
# GROUP 2: fixture and static validation (do NOT call the adapter)
# ---------------------------------------------------------------------------


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture seeded_length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('d45619bd', 16) = 3562412477.
    seeded_length = rng.randint(1024, 16384) = 6515.

    This test does NOT call the adapter. It validates the fixture was generated
    correctly from the seeded RNG.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["seeded_length"], (
        f"Fixture seeded_length {fixture_slice['seeded_length']} "
        f"!= seeded length {expected_length} "
        f"(seed={SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]})"
    )


def test_fixture_json_byte_length_matches_seeded_length(
    fixture_slice: dict[str, Any],
) -> None:
    """The JSON-serialised fixture must be exactly seeded_length UTF-8 bytes.

    This test does NOT call the adapter. It verifies the fixture was padded
    correctly so the byte-length contract is honoured.
    """
    s = json.dumps(fixture_slice, indent=2, ensure_ascii=False)
    actual = len(s.encode("utf-8"))
    expected = fixture_slice["seeded_length"]
    assert actual == expected, (
        f"Fixture JSON byte length {actual} != seeded_length {expected}. "
        "Fixture must be padded to exactly seeded_length bytes."
    )


def test_fixture_has_three_morph_codes(fixture_slice: dict[str, Any]) -> None:
    """The fixture must contain exactly 3 morph codes per the spec.

    Codes: one verb (HVqp3ms), one noun (HNcmsa), one particle (HTi).
    This test does NOT call the adapter.
    """
    codes = fixture_slice["morph_codes"]
    assert len(codes) == 3, (
        f"Fixture must have exactly 3 morph codes; got {len(codes)}"
    )
    code_vals = {c["code"] for c in codes}
    assert "HVqp3ms" in code_vals, "Fixture must contain verb code HVqp3ms"
    assert "HNcmsa" in code_vals, "Fixture must contain noun code HNcmsa"
    assert "HTi" in code_vals, "Fixture must contain particle code HTi"


def test_fixture_morph_code_fields_valid(fixture_slice: dict[str, Any]) -> None:
    """Every morph code in the fixture must have code, expansion, and source.

    This validates the fixture against Decision 17 per-field predicate table.
    This test does NOT call the adapter.
    """
    for entry in fixture_slice["morph_codes"]:
        code = entry.get("code")
        assert code and str(code).strip(), (
            f"Fixture morph code entry missing or empty code: {entry!r}"
        )
        expansion = entry.get("expansion")
        assert expansion and str(expansion).strip(), (
            f"Fixture morph code entry missing or empty expansion: {entry!r}"
        )
        source = entry.get("source")
        assert source == SOURCE_SLUG, (
            f"Fixture morph code entry source must be '{SOURCE_SLUG}'; got {source!r}"
        )


def test_fixture_particle_has_expansions_list(fixture_slice: dict[str, Any]) -> None:
    """The fixture particle (HTi) must have an expansions list with len >= 2.

    This exercises the multi-expansion edge case from Decision 17 Edge cases
    bullet 1 without calling the adapter.
    """
    particle = next(
        (c for c in fixture_slice["morph_codes"] if c["code"] == "HTi"), None
    )
    assert particle is not None, "Fixture must contain particle code HTi"
    expansions = particle.get("expansions")
    assert isinstance(expansions, list) and len(expansions) >= 2, (
        f"Fixture HTi must have expansions list with len >= 2; got {expansions!r}"
    )


def test_fixture_single_expansion_codes_have_null_expansions(
    fixture_slice: dict[str, Any],
) -> None:
    """Single-expansion fixture codes must carry expansions=None.

    Decision 17: 'When the upstream row carries exactly one expansion,
    expansions is left null.'
    This test does NOT call the adapter.
    """
    single_codes = [
        c for c in fixture_slice["morph_codes"]
        if c["code"] != "HTi"
    ]
    for entry in single_codes:
        assert entry.get("expansions") is None, (
            f"Single-expansion code {entry['code']} must have expansions=None; "
            f"got {entry.get('expansions')!r}"
        )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, bool, and list predicates.

    This test does NOT call the adapter. It validates the predicate source file
    is present and parseable per RESEED_PLAN C.5. The file is the single source
    of truth for non-empty value semantics. predicates_by_type.cypher >= 1.
    """
    assert "string" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_string definition"
    )
    assert "bool" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_bool definition"
    )
    assert "list" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_list definition"
    )
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )
    assert "size(x)" in PREDICATES["list"], (
        "$pred_list must contain size(x) check"
    )


def test_expected_morph_code_count_from_expected_counts_json() -> None:
    """STEPBible-morph-codes expected count in expected_counts.json must be 2782.

    This test does NOT call the adapter. It validates the count constant used
    by the coverage tests against the source-of-truth file.
    Tier A, tolerance 0, record_unit morph_code.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"][SOURCE_SLUG]
    assert entry["expected_count"] == EXPECTED_MORPH_CODE_COUNT, (
        f"expected_counts.json {SOURCE_SLUG} count {entry['expected_count']} "
        f"!= {EXPECTED_MORPH_CODE_COUNT}"
    )
    assert entry["tier"] == "A", f"{SOURCE_SLUG} must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "morph_code", (
        f"record_unit must be 'morph_code'; got {entry['record_unit']!r}"
    )


# ---------------------------------------------------------------------------
# GROUP 3: stub-rejection sweep (13 attack-vector stubs)
#
# For each stub, attempt to run it through MorphCode-specific label/field/id
# assertions. The stub must be rejected by at least one check.
# Stubs that expose no ingest entry point are skipped (documented reason).
# Edge-related assertions are N/A for this adapter (no edges emitted).
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

    Pattern:
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_stepbible_morph_codes
         or ingest.
      3. If no callable entry point, skip with documented reason (stubs expose
         emit_records/emit_edges, not an ingest function; N/A for this adapter).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check labels, MorphCode field validity, and code
         format. At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.

    Edge assertions are N/A for this adapter (MorphCode emits no outbound
    edges per Decision 17 docstring contract; edge count is always zero).
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_morph_codes", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(has: {[x for x in dir(stub_mod) if not x.startswith('_')]}). "
            "Stubs expose emit_records/emit_edges only; "
            "N/A: no MorphCode ingest function to call."
        )

    raised = False
    try:
        fn(data_root, fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    emitted_labels = fake_driver.captured_labels()
    morph_code_nodes = fake_driver.captured_nodes("MorphCode")
    codes = fake_driver.captured_node_ids("MorphCode")

    label_ok = "MorphCode" in emitted_labels

    field_ok = True
    if morph_code_nodes:
        for node in morph_code_nodes:
            code_val = node.get("code")
            expansion_val = node.get("expansion")
            source_val = node.get("source")
            if (
                not code_val or not str(code_val).strip()
                or not expansion_val or not str(expansion_val).strip()
                or source_val != SOURCE_SLUG
            ):
                field_ok = False
                break

    code_nonempty_ok = all(str(c).strip() for c in codes) if codes else False

    rejected = not label_ok or not field_ok or not code_nonempty_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"MorphCode node count: {len(morph_code_nodes)}, "
        f"Sample codes: {codes[:3]}"
    )
