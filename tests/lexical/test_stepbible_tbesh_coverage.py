"""STEPBible-TBESH adapter coverage tests (phase C.2 verifier: stepbible_tbesh).

References tools/predicates_by_type.cypher for pred_string and pred_bool
definitions. Predicate expressions are loaded at module level from that file;
inline predicates here are forbidden per RESEED_PLAN C.5.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tbesh.py has NO function body at
  this commit. importlib.import_module returns the module, getattr returns None
  because no def exists, and calling None raises TypeError. That is the red
  state the Wave 2 gate requires (at least 3 FAILED).

Entry function confirmed:
  - ingest/lexical/stepbible_tbesh.py docstring: contract names
    ingest_stepbible_tbesh but no def block present.
  - run.py does not yet wire stepbible_tbesh; the function is absent,
    so getattr(mod, ENTRY_FUNCTION, None) returns None.

Seed derivation:
  commit_sha = 'fdf5f40e258a01adff3b5f06b66d535f8a678111'
    (git log -1 -- ingest/lexical/stepbible_tbesh.py)
  seed_int = int('fdf5f40e', 16) = 4260754446
  length   = random.Random(seed_int).randint(1024, 16384) = 9005

Fixture: tests/lexical/fixtures/stepbible_tbesh_slice.json
  Three Hebrew Strongs from disjoint corpus regions:
    early   H0001   (Genesis context, creation vocabulary)
    mid     H4397   (Psalms/prophetic context, messenger domain)
    late    H8451   (Deuteronomy context, law/Torah vocabulary)
  Plus one Aramaic subscript entry H10001 per Decision 11 edge case 2.

Source: tools/expected_counts.json sources."STEPBible-TBESH"
  tier A, expected_count 11682, record_unit lemma.
Decisions: 11 (BriefLexEntry shape, LEX_FOR), 14 (Source/license).

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

# Predicates loaded from canonical file per RESEED_PLAN C.5.
_PREDICATES_CYPHER_PATH = REPO / "tools" / "predicates_by_type.cypher"
_PREDICATES_RAW = _PREDICATES_CYPHER_PATH.read_text(encoding="utf-8")


def _load_predicates(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("$pred_") and ":=" in stripped:
            lhs, rhs = stripped.split(":=", 1)
            name = lhs.strip().split("$pred_")[1].split("(")[0]
            result[name] = rhs.strip()
    return result


PREDICATES = _load_predicates(_PREDICATES_RAW)

# Adapter constants
ADAPTER_MODULE = "ingest.lexical.stepbible_tbesh"
ENTRY_FUNCTION = "ingest_stepbible_tbesh"
SOURCE_SLUG = "STEPBible-TBESH"
EXPECTED_COUNT = 11682

# Seed from docstring commit SHA
DOCSTRING_COMMIT_SHA = "fdf5f40e258a01adff3b5f06b66d535f8a678111"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 4260754446

# Required BriefLexEntry fields per Decision 11
REQUIRED_STRING_FIELDS = frozenset({
    "strong_disambig",
    "gloss_line",
    "base_strong",
    "hebrew",
    "transliteration",
    "pos",
    "english",
    "definition",
})
LANGUAGE_DISCRIMINATOR = "hebrew"


# FakeDriver records every node and edge emitted by the adapter.

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures MERGE payloads so tests can assert on emitted labels, edge
    types, and property shapes without a live graph connection.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_stepbible_tbesh() raises TypeError first.
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

    def captured_node_props(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]

    def captured_edge_types(self) -> set[str]:
        return {e["rel_type"] for e in self._edges}

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n.get("label") == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e.get("rel_type") == rel_type)


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
    """Best-effort MERGE parser; records BriefLexEntry nodes and LEX_FOR edges."""
    for label in ("BriefLexEntry", "Source", "Lemma"):
        # Phase D label-add reconciliation: only a node-MERGE statement
        # ("MERGE (n:") may contribute node records. Post-Phase-D edge-MERGE
        # Cypher carries endpoint labels in its MATCH clause; without this
        # guard its edge-batch rows (from_id/to_id, no node identity) would
        # be recorded as phantom nodes. Real node MERGEs always contain
        # "MERGE (n:" so genuine node capture is byte-identical; the edge
        # loop is untouched.
        if "MERGE (n:" not in cypher:
            continue
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    if isinstance(row, dict):
                        props = row.get("properties", row)
                        if isinstance(props, dict):
                            node.update(props)
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("LEX_FOR", "FROM_EDITION"):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# Fixtures

@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tbesh_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the parent directory the adapter expects for TBESH input."""
    return REPO / "data" / "private" / "stepbible"


# GROUP 1: entry-function tests (red state at Wave 2)

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tbesh.

    FAILS at Wave 2: no function body means getattr returns None and
    callable(None) is False.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be callable "
        f"but got {type(fn)!r}. "
        "Red state: docstring-only adapter at Wave 2."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_tbesh must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tbesh must return dict; got {type(result)!r}"
    )
    assert "BriefLexEntry" in result, "return dict must contain 'BriefLexEntry' key"


def test_adapter_emits_brief_lex_entry_label(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge BriefLexEntry nodes.

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "BriefLexEntry" in emitted, (
        f"adapter must emit BriefLexEntry nodes; saw labels: {sorted(emitted)}"
    )


def test_adapter_emits_lex_for_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit at least one LEX_FOR edge.

    Decision 11: LEX_FOR links BriefLexEntry to Lemma keyed by base_strong.
    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    edge_types = fake_driver.captured_edge_types()
    assert "LEX_FOR" in edge_types, (
        f"adapter must emit LEX_FOR edges; saw: {sorted(edge_types)}"
    )


def test_brief_lex_entry_has_language_discriminator(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry must carry language='hebrew' per Decision 11.

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_node_props("BriefLexEntry")
    assert entries, "adapter must emit at least one BriefLexEntry node"
    bad = [e for e in entries if e.get("language") != LANGUAGE_DISCRIMINATOR]
    assert not bad, (
        f"BriefLexEntry nodes missing language='hebrew': {bad[:3]}"
    )


def test_brief_lex_entry_required_string_fields(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BriefLexEntry must carry all 8 required string fields (Decision 11).

    Fields: strong_disambig, gloss_line, base_strong, hebrew, transliteration,
    pos, english, definition. Each satisfies pred_string: IS NOT NULL and
    trim(toString(x)) <> ''.

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_node_props("BriefLexEntry")
    assert entries, "adapter must emit at least one BriefLexEntry"
    for entry in entries:
        for field in REQUIRED_STRING_FIELDS:
            val = entry.get(field)
            assert val is not None and str(val).strip() != "", (
                f"BriefLexEntry field '{field}' violates pred_string on entry "
                f"strong_disambig={entry.get('strong_disambig')!r}: got {val!r}"
            )


def test_strong_disambig_is_stable_id(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """strong_disambig is the MERGE key (UNIQUE constraint brief_lex_entry_id).

    Two sense-split entries such as H1234A and H1234B must both appear as
    distinct BriefLexEntry nodes. The set of strong_disambig values must
    equal the total node count (no duplicates).

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_node_props("BriefLexEntry")
    assert entries, "adapter must emit BriefLexEntry nodes"
    ids = [e.get("strong_disambig") for e in entries]
    assert all(v is not None and str(v).strip() != "" for v in ids), (
        "Every BriefLexEntry must carry a non-empty strong_disambig"
    )
    assert len(ids) == len(set(ids)), (
        f"strong_disambig values are not unique; found duplicates in: {ids}"
    )


def test_base_strong_suffix_stripped(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """base_strong must be the suffix-stripped form of strong_disambig.

    For H1234A the base_strong must be H1234, not H1234A. The LEX_FOR
    join targets Lemma.strong which holds the base form per Decision 11.

    FAILS at Wave 2 with TypeError: NoneType is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    entries = fake_driver.captured_node_props("BriefLexEntry")
    for entry in entries:
        disambig = entry.get("strong_disambig", "")
        base = entry.get("base_strong", "")
        if disambig and disambig[-1].isalpha() and len(disambig) > 2:
            # Sense suffix present: last char is alphabetic after leading H+digits
            numeric_part = disambig.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
            if numeric_part != disambig:
                assert base == numeric_part, (
                    f"base_strong {base!r} must be the suffix-stripped form "
                    f"of strong_disambig {disambig!r} (expected {numeric_part!r})"
                )


def test_expected_count_from_expected_counts_json() -> None:
    """The STEPBible-TBESH expected count in expected_counts.json must be 11682.

    Does not call the adapter. Validates the count constant used by coverage
    tests is correct per the source file.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TBESH"]
    assert entry["expected_count"] == EXPECTED_COUNT, (
        f"expected_counts.json STEPBible-TBESH count {entry['expected_count']} "
        f"!= {EXPECTED_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TBESH must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """Fixture length must be reproducible from the stored seed.

    seed_int = int('fdf5f40e', 16) = 4260754446
    length   = random.Random(seed_int).randint(1024, 16384) = 9005
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {length}"
    )


def test_fixture_has_three_disjoint_corpus_regions(
    fixture_slice: dict[str, Any]
) -> None:
    """Fixture must contain entries from three disjoint corpus regions.

    Early range: H0001-H1999 (creation/patriarchal vocabulary).
    Mid range:   H4000-H5999 (Psalms/prophetic vocabulary).
    Late range:  H7000-H8999 (Deuteronomy/wisdom vocabulary).
    """
    entries = fixture_slice["entries"]
    strong_nums = []
    for e in entries:
        disambig = e["strong_disambig"]
        numeric = "".join(c for c in disambig[1:] if c.isdigit())
        if numeric:
            strong_nums.append(int(numeric))
    early = any(n <= 1999 for n in strong_nums)
    mid = any(4000 <= n <= 5999 for n in strong_nums)
    late = any(n >= 7000 for n in strong_nums)
    assert early, f"Fixture missing early corpus region (H0001-H1999); nums: {strong_nums}"
    assert mid, f"Fixture missing mid corpus region (H4000-H5999); nums: {strong_nums}"
    assert late, f"Fixture missing late corpus region (H7000-H8999); nums: {strong_nums}"


def test_fixture_entries_have_required_fields(
    fixture_slice: dict[str, Any]
) -> None:
    """Every fixture entry must carry all required BriefLexEntry fields.

    Does not call the adapter. Validates fixture integrity.
    """
    entries = fixture_slice["entries"]
    assert len(entries) >= 3, "Fixture must have at least 3 entries"
    for entry in entries:
        for field in REQUIRED_STRING_FIELDS:
            val = entry.get(field)
            assert val is not None and str(val).strip() != "", (
                f"Fixture entry {entry.get('strong_disambig')!r} "
                f"missing or empty field {field!r}"
            )
        assert entry.get("language") == "hebrew", (
            f"Fixture entry {entry.get('strong_disambig')!r} "
            f"must have language='hebrew'"
        )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define at least string and bool predicates.

    Does not call the adapter. Validates the predicate source file per
    RESEED_PLAN C.5.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing pred_string"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing pred_bool"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "pred_string must contain IS NOT NULL check"
    )
    assert "IS NOT NULL" in PREDICATES["bool"], (
        "pred_bool must contain IS NOT NULL check"
    )


# GROUP 2: stub-rejection sweep (13 stubs parametrized)

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
    """The coverage scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Look for an ingest entry point named ingest_stepbible_tbesh or ingest.
      3. If none found, skip (stub only exposes emit_records/emit_edges).
      4. If entry point exists and raises, stub is rejected.
      5. If it runs silently, check labels, edge types, and required fields.
         At least one assertion must fail. If none fail, the test fails.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_tbesh", None)
    )
    if fn is None or not callable(fn):
        pytest.skip(
            f"{stub_module_name} has no callable ingest entry point "
            f"(attrs: {[x for x in dir(stub_mod) if not x.startswith('_')]})"
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
    entries = fake_driver.captured_node_props("BriefLexEntry")

    label_ok = "BriefLexEntry" in emitted_labels
    edge_ok = "LEX_FOR" in emitted_edges

    field_ok = True
    if entries:
        for entry in entries:
            for field in REQUIRED_STRING_FIELDS:
                val = entry.get(field)
                if val is None or str(val).strip() == "":
                    field_ok = False
                    break
            lang = entry.get("language")
            if lang != LANGUAGE_DISCRIMINATOR:
                field_ok = False
                break
    else:
        field_ok = False

    rejected = not label_ok or not edge_ok or not field_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Entries: {entries[:2]}"
    )
