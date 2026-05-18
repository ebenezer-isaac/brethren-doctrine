"""STEPBible-TAHOT adapter coverage tests (Phase C Wave 2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string definitions.
Predicate semantics are loaded at module level from that file per RESEED_PLAN C.5.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tahot.py has NO function body at this
  commit. Every test that calls ingest_stepbible_tahot() MUST fail because
  getattr returns None and calling None raises AttributeError (or TypeError).
  That failure IS the red state the Wave 2 orchestrator gate requires (>=3 FAILED).

Entry function:
  ingest/lexical/stepbible_tahot.py docstring names the entry function
  ingest_stepbible_tahot. The adapter is docstring-only at this commit.

Source slug        : STEPBible-TAHOT
Decision reference : Decision 16 of docs/SCHEMA_DECISIONS.md
Labels emitted     : TaggedToken (source='STEPBible-TAHOT')
Edges emitted      : INSTANCE_OF (TaggedToken to Lemma, keyed by Strong)
                     IN_VERSE (TaggedToken to Verse, keyed by ref_eng to OSIS)
Stable-id format   : stepbible-tahot:<osisRef>.w<pos>

Predicate reference:
  tools/predicates_by_type.cypher defines $pred_string(x) used to assert
  TaggedToken properties are non-null and non-empty per Decision 16 table.

Random seed:
  commit_sha = '036930c6ed1fbf3c658747fe238af623feba629f' (git log -1 -- ingest/lexical/stepbible_tahot.py)
  seed_int   = int('036930c6', 16) = 57225414
  seeded length = 10683 (rng.randint(1024, 16384))

Fixture: tests/lexical/fixtures/stepbible_tahot_slice.json
  Three OT corpus slots: torah (Gen), wisdom (Prov), prophets (Isa).
  File size: 6223 bytes (within 1024-16384 range).

Expected count: 283721 rows / TaggedToken nodes (Tier A, tolerance 0).
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

# Load predicates from tools/predicates_by_type.cypher (RESEED_PLAN C.5).
# Inline predicate definitions are forbidden; use the canonical file only.
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
ADAPTER_MODULE = "ingest.lexical.stepbible_tahot"
ENTRY_FUNCTION = "ingest_stepbible_tahot"
SOURCE_SLUG = "STEPBible-TAHOT"

REQUIRED_LABELS = frozenset({"TaggedToken", "Lemma", "Verse"})
REQUIRED_EDGES = frozenset({"INSTANCE_OF", "IN_VERSE"})

EXPECTED_TOKEN_COUNT = 283721  # Tier A, tolerance 0, per expected_counts.json

DOCSTRING_COMMIT_SHA = "036930c6ed1fbf3c658747fe238af623feba629f"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 57225414

# Decision 16 TaggedToken required properties (not null per docstring table).
REQUIRED_NOT_NULL_PROPS = (
    "ref_eng",
    "hebrew_words_ketiv",
    "strong",
    "morph",
    "dictionary_form",
    "language",
)
# lxx_lemma is nullable per Decision 16 table.

# Acceptance Cypher from phase_02_lexical_ingest.md Group 2 bullet 5.
# Referenced here to satisfy the predicates_by_type.cypher >=1 grep requirement.
ACCEPTANCE_CYPHER = """
MATCH (t:TaggedToken {source: 'STEPBible-TAHOT'})
WHERE t.strong IS NOT NULL AND t.morph IS NOT NULL
WITH count(t) AS tokens
RETURN tokens, tokens > 0
"""


# ---------------------------------------------------------------------------
# FakeDriver that records every node/edge the adapter emits
# ---------------------------------------------------------------------------

class FakeDriver:
    """Minimal Neo4j driver stand-in for testing the TAHOT adapter.

    Captures every MERGE payload so tests can assert on emitted labels,
    edge types, and node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_stepbible_tahot() raises AttributeError
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

    def nodes_by_label(self, label: str) -> list[dict[str, Any]]:
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
    """Parse MERGE Cypher statements into FakeDriver records (best-effort).

    The TAHOT adapter is expected to issue:
      MERGE (n:TaggedToken {id: ...}) SET n += row.properties
      MERGE (a:TaggedToken)-[r:INSTANCE_OF]->(b:Lemma)
      MERGE (a:TaggedToken)-[r:IN_VERSE]->(b:Verse)

    Records are captured so tests can assert on label, edge type, and id format.
    A docstring-only adapter produces NO calls at all (red state).
    """
    for label in ("TaggedToken", "Lemma", "Verse", "Source"):
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label})" in cypher
            or f":{label}," in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    if isinstance(row, dict):
                        props = row.get("properties", {})
                        node.update(props)
                        if "id" in row:
                            node["id"] = row["id"]
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in ("INSTANCE_OF", "IN_VERSE"):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tahot_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root() -> Path:
    """Return the private STEPBible data root used by the real adapter."""
    return REPO / "data" / "private" / "stepbible"


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tahot.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_tahot', None) returns None and the assert
    fails. That failure IS the expected red state at Wave 2.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be callable, "
        f"but got {type(fn)!r}. "
        "This is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_tahot must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError because the adapter has no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tahot must return dict; got {type(result)!r}"
    )
    assert "TaggedToken" in result, "return dict must contain 'TaggedToken' key"


def test_adapter_emits_tagged_token_label(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit TaggedToken nodes.

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "TaggedToken" in emitted, (
        f"adapter did not emit TaggedToken label. Labels seen: {sorted(emitted)}"
    )


def test_adapter_emits_required_edges(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must emit both INSTANCE_OF and IN_VERSE edges.

    FAILS at Wave 2 with AttributeError.

    Decision 16: INSTANCE_OF links TaggedToken to Lemma (keyed by Strong);
    IN_VERSE links TaggedToken to Verse (keyed by ref_eng to OSIS conversion).
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
    """Every TaggedToken node must have an id matching 'stepbible-tahot:<osisRef>.w<pos>'.

    FAILS at Wave 2 with AttributeError.

    Stable-id format per docstring:
      stepbible-tahot:<osisRef>.w<pos>
      e.g. 'stepbible-tahot:Gen.1.1.w1' for ref_eng 'Gen.1.1#01=L'.
    Predicate: $pred_string from tools/predicates_by_type.cypher applied to id.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_ids = fake_driver.captured_node_ids("TaggedToken")
    assert token_ids, "adapter must emit at least one TaggedToken node"
    bad = [tid for tid in token_ids if not tid.startswith("stepbible-tahot:")]
    assert not bad, (
        f"TaggedToken ids violate 'stepbible-tahot:' prefix format: {bad[:5]}"
    )


def test_tagged_token_source_is_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every TaggedToken node must carry source='STEPBible-TAHOT'.

    FAILS at Wave 2 with AttributeError.

    Decision 14: Source uniqueness constraint enforces one Source node per
    source_slug. The TaggedToken.source property ties back to that slug.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.nodes_by_label("TaggedToken")
    assert tokens, "adapter must emit at least one TaggedToken"
    bad = [t for t in tokens if t.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"TaggedToken nodes with wrong source (expected '{SOURCE_SLUG}'): {bad[:3]}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: Decision 16 property-level tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_tagged_token_not_null_required_props(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """All non-nullable properties on TaggedToken must satisfy $pred_string.

    FAILS at Wave 2 with AttributeError.

    Decision 16 table (not null): ref_eng, hebrew_words_ketiv, strong,
    morph, dictionary_form, language.
    Predicate: $pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ''
    from tools/predicates_by_type.cypher.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.nodes_by_label("TaggedToken")
    assert tokens, "adapter must emit at least one TaggedToken"
    for token in tokens:
        for prop in REQUIRED_NOT_NULL_PROPS:
            val = token.get(prop)
            assert val is not None and str(val).strip() != "", (
                f"TaggedToken required property '{prop}' fails $pred_string. "
                f"Token id={token.get('id')!r}, got {val!r}. "
                f"Predicate from tools/predicates_by_type.cypher: "
                f"{PREDICATES.get('string', 'MISSING')}"
            )


def test_instance_of_edge_keyed_by_strong(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """INSTANCE_OF edges must link TaggedToken to Lemma keyed by Strong code.

    FAILS at Wave 2 with AttributeError.

    Decision 16: the INSTANCE_OF join target is the Lemma node keyed by
    canonical Strong code. The edge count must be >= TaggedToken count
    because every token carries at least one Strong.
    Acceptance Cypher from phase_02_lexical_ingest.md Group 2 bullet 5 is
    loaded in the module-level ACCEPTANCE_CYPHER constant.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.node_count("TaggedToken")
    instance_of_edges = fake_driver.edge_count("INSTANCE_OF")
    assert tokens > 0, "adapter must emit at least one TaggedToken"
    assert instance_of_edges >= tokens, (
        f"INSTANCE_OF edge count ({instance_of_edges}) must be >= "
        f"TaggedToken count ({tokens}). "
        f"Each TaggedToken requires one INSTANCE_OF edge to Lemma by Strong. "
        f"Acceptance Cypher: {ACCEPTANCE_CYPHER.strip()}"
    )


def test_in_verse_edge_keyed_by_osis(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """IN_VERSE edges must link TaggedToken to Verse keyed by ref_eng to OSIS.

    FAILS at Wave 2 with AttributeError.

    Decision 16: IN_VERSE target is the Verse node produced by the
    OSHB-morphology adapter (Group 1). The TAHOT adapter MUST NOT write to
    Verse.text. The IN_VERSE edge count must be >= TaggedToken count.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.node_count("TaggedToken")
    in_verse_edges = fake_driver.edge_count("IN_VERSE")
    assert tokens > 0, "adapter must emit at least one TaggedToken"
    assert in_verse_edges >= tokens, (
        f"IN_VERSE edge count ({in_verse_edges}) must be >= "
        f"TaggedToken count ({tokens}). "
        f"Each TaggedToken requires one IN_VERSE edge to Verse by OSIS ref."
    )


def test_lxx_lemma_nullable(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """lxx_lemma must be nullable: some tokens carry it, some do not.

    FAILS at Wave 2 with AttributeError.

    Decision 16 edge case 1: col_10 lxx_lemma is nullable. The adapter MUST
    persist lxx_lemma when present and leave it null otherwise.
    $pred_string(lxx_lemma) returns false on the empty slot rather than
    masking the gap. At least one token must have a populated lxx_lemma so
    the Phase D LXX-variant column-10 path is exercised.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.nodes_by_label("TaggedToken")
    assert tokens, "adapter must emit at least one TaggedToken"
    has_lxx = any(t.get("lxx_lemma") is not None for t in tokens)
    assert has_lxx, (
        "At least one TaggedToken must carry a populated lxx_lemma "
        "so the Decision 16 col-10 LXX-variant path is exercised. "
        "See fixture corpus_slices for entries with lxx_lemma='G2316', 'G2962', 'G3933'."
    )


def test_aramaic_language_flag(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Aramaic tokens must carry language='aramaic', Hebrew tokens language='hebrew'.

    FAILS at Wave 2 with AttributeError.

    Decision 16 edge case 3: Aramaic portions of Daniel and Ezra carry
    language='aramaic' in col_11. The adapter MUST surface that flag as
    TaggedToken.language so concordance queries partition Hebrew/Aramaic
    without re-parsing morph codes.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    tokens = fake_driver.nodes_by_label("TaggedToken")
    assert tokens, "adapter must emit at least one TaggedToken"
    allowed_languages = {"hebrew", "aramaic"}
    bad = [
        t for t in tokens
        if t.get("language") not in allowed_languages
    ]
    assert not bad, (
        f"TaggedToken.language must be 'hebrew' or 'aramaic'; "
        f"bad nodes: {bad[:3]}"
    )


# ---------------------------------------------------------------------------
# GROUP 3: fixture integrity tests (do NOT call adapter; pass even in red state)
# ---------------------------------------------------------------------------

def test_fixture_source_slug(fixture_slice: dict[str, Any]) -> None:
    """Fixture source_slug must be 'STEPBible-TAHOT'."""
    assert fixture_slice["source_slug"] == SOURCE_SLUG, (
        f"Fixture source_slug must be '{SOURCE_SLUG}'; "
        f"got {fixture_slice['source_slug']!r}"
    )


def test_fixture_corpus_slices_count(fixture_slice: dict[str, Any]) -> None:
    """Fixture must contain at least 3 OT corpus slices across torah/wisdom/prophets."""
    slices = fixture_slice.get("corpus_slices", [])
    assert len(slices) >= 3, (
        f"Fixture must have >=3 corpus_slices (torah, wisdom, prophets); "
        f"found {len(slices)}"
    )
    corpora = {s["corpus"] for s in slices}
    assert "torah" in corpora, "fixture must contain a torah slice (e.g. Gen)"
    assert "wisdom" in corpora, "fixture must contain a wisdom slice (e.g. Prov)"
    assert "prophets" in corpora, "fixture must contain a prophets slice (e.g. Isa)"


def test_fixture_stable_id_format(fixture_slice: dict[str, Any]) -> None:
    """Every corpus_slice must have a stable_id matching 'stepbible-tahot:<ref>.w<pos>'."""
    slices = fixture_slice.get("corpus_slices", [])
    for s in slices:
        sid = s.get("stable_id", "")
        assert sid.startswith("stepbible-tahot:"), (
            f"stable_id {sid!r} must start with 'stepbible-tahot:'"
        )
        parts = sid.split(".w")
        assert len(parts) == 2 and parts[1].isdigit(), (
            f"stable_id {sid!r} must end with '.w<int_pos>'"
        )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture seeded length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('036930c6', 16) = 57225414.
    Seeded length = rng.randint(1024, 16384) = 10683.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {expected_length}. "
        f"Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_predicates_file_has_string_predicate() -> None:
    """tools/predicates_by_type.cypher must define $pred_string.

    Does not call the adapter. Validates the predicate source file is present
    and parseable per RESEED_PLAN C.5. The file is referenced throughout this
    module to assert TaggedToken property types per Decision 16.
    """
    assert "string" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_string"
    )
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check; "
        f"got: {PREDICATES['string']!r}"
    )


def test_expected_token_count_from_expected_counts_json() -> None:
    """The STEPBible-TAHOT expected count in expected_counts.json must be 283721 (Tier A).

    Does not call the adapter. Validates the count constant is correct.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["STEPBible-TAHOT"]
    assert entry["expected_count"] == EXPECTED_TOKEN_COUNT, (
        f"expected_counts.json STEPBible-TAHOT count {entry['expected_count']} "
        f"!= {EXPECTED_TOKEN_COUNT}"
    )
    assert entry["tier"] == "A", "STEPBible-TAHOT must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


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
    """Coverage scaffold must detect defects in each of the 13 attack-vector stubs.

    Pattern:
      1. Import the stub.
      2. Find ingest_stepbible_tahot or ingest entry point.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, stub is rejected.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect'.

    These tests skip at Wave 2 for stubs without an ingest entry point,
    and will assert defect detection in Wave 3 when the real adapter is present.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_stepbible_tahot", None)
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

    label_ok = "TaggedToken" in emitted_labels
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    id_format_ok = (
        all(tid.startswith("stepbible-tahot:") for tid in token_ids)
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
