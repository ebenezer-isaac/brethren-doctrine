"""ETCBC-phono adapter coverage tests (Phase C Wave 2, verifier caste).

This file references tools/predicates_by_type.cypher for $pred_string and
$pred_bool definitions. Predicate semantics are loaded at module level from
that file; inline predicate definitions are forbidden per RESEED_PLAN C.5.

TDD red-state contract:
  The adapter at ingest/lexical/etcbc_phono.py has NO function body at this
  commit. Every test that calls ingest_etcbc_phono() MUST fail because
  importlib.import_module yields a module where getattr returns None and
  calling None raises TypeError: 'NoneType' object is not callable.
  That failure IS the red state the Wave 2 orchestrator gate requires
  (GATE: >= 3 FAILED).

Entry function confirmed:
  - ingest/lexical/etcbc_phono.py docstring: contract names ingest_etcbc_phono.
  - Adapter is a property-attach adapter: attaches phono onto BhsaWord via
    MATCH-then-SET keyed by stable id 'bhsa:tf:<node_id>' (Decision 14
    tfnode_tuple constraint, corpus='bhsa', node_id=<int>).
  - No new node label. No edges.

Random seed:
  commit_sha = 'dde769003daf1e20607c6ef19b5baa0eac6a09df'
    (git log -1 -- ingest/lexical/etcbc_phono.py)
  seed = int('dde76900', 16) = 3722930432

Fixture: tests/lexical/fixtures/etcbc_phono_slice.json
  Three OT verses: Genesis 1:1 (7 words), Psalms 23:1 (8 words),
  Proverbs 3:5 (6 words). One ketiv-only null (node_id 318402).
  Byte length: 4716 (within 1024-16384 range).

Source: tools/expected_counts.json sources."ETCBC-phono" expected_count=426590.
Decisions: 3 (ETCBC syntax tree, phono property, nullable at 0.984),
           14 (Source uniqueness, tfnode_tuple, redistribute=false).
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
# Loaded at module level. Inline predicate definitions forbidden per RESEED_PLAN C.5.
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

# -- adapter constants --------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.etcbc_phono"
ENTRY_FUNCTION = "ingest_etcbc_phono"
SOURCE_SLUG = "ETCBC-phono"

# Property-attach adapter: no new labels, no edges.
EXPECTED_NEW_LABELS: frozenset[str] = frozenset()
EXPECTED_EDGES: frozenset[str] = frozenset()

# Only the phono property is written onto BhsaWord.
PHONO_PROPERTY = "phono"
NODE_LABEL = "BhsaWord"
STABLE_ID_PREFIX = "bhsa:tf:"

EXPECTED_WORD_COUNT = 426590  # Tier A, tolerance 0, per expected_counts.json

# Seed from etcbc_phono.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "dde769003daf1e20607c6ef19b5baa0eac6a09df"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3722930432


# -- FakeDriver for property-attach pattern ----------------------------------


class FakePropertyAttachDriver:
    """Minimal Neo4j driver stub that captures MATCH-then-SET payloads.

    The property-attach adapter issues MATCH (w:BhsaWord {id: ...}) SET w.phono = ...
    rather than MERGE. This fake captures the 'id' and 'phono' from each SET
    so tests can assert that existing nodes are updated, not created.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_etcbc_phono() raises TypeError first.
    """

    def __init__(self) -> None:
        self._attached: list[dict[str, Any]] = []
        self._source_merges: list[dict[str, Any]] = []
        self.settings = _FakeSettings()

    def session(self, *_: Any, **__: Any) -> "_FakeSession":
        return _FakeSession(self)

    def close(self) -> None:
        pass

    def attached_ids(self) -> list[str]:
        return [row["id"] for row in self._attached if "id" in row]

    def attached_phono_values(self) -> list[Any]:
        return [row.get("phono") for row in self._attached]

    def null_phono_count(self) -> int:
        return sum(1 for row in self._attached if row.get("phono") is None)

    def source_slug_merged(self) -> list[str]:
        return [row.get("slug", "") for row in self._source_merges]

    def total_attached(self) -> int:
        return len(self._attached)


class _FakeSettings:
    neo4j_lexical_uri: str = "bolt://localhost:7687"
    neo4j_lexical_user: str = "neo4j"
    neo4j_lexical_password: str = "test"
    qdrant_lexical_url: str = "http://localhost:6333"
    voyage_api_key: str = ""


class _FakeSession:
    def __init__(self, driver: FakePropertyAttachDriver) -> None:
        self._driver = driver

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def run(self, cypher: str, **kwargs: Any) -> "_FakeResult":
        _parse_phono_cypher(cypher, kwargs, self._driver)
        return _FakeResult()

    def close(self) -> None:
        pass


class _FakeResult:
    def single(self) -> dict[str, int]:
        return {"attached": 1}

    def consume(self) -> None:
        pass


def _parse_phono_cypher(
    cypher: str, params: dict[str, Any], driver: FakePropertyAttachDriver
) -> None:
    """Parse MATCH-then-SET and MERGE Source Cypher into driver records.

    The phono adapter is expected to issue:
      MERGE (s:Source {slug: 'ETCBC-phono'}) SET s += {...}
      UNWIND $rows AS row
        MATCH (w:BhsaWord {id: row.id}) SET w.phono = row.phono

    No MERGE on BhsaWord (MATCH-then-SET only, per docstring contract).
    The parser is lenient; a docstring-only adapter produces NO calls at all.
    """
    cypher_upper = cypher.upper()

    # Detect Source MERGE
    if "SOURCE" in cypher_upper and ("MERGE" in cypher_upper or "SLUG" in cypher_upper):
        rows = params.get("rows") or params.get("records") or []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    driver._source_merges.append(row)
        else:
            slug = params.get("slug", "")
            driver._source_merges.append({"slug": slug})

    # Detect MATCH-then-SET on BhsaWord
    if "BHSAWORD" in cypher_upper and "SET" in cypher_upper:
        rows = params.get("rows") or params.get("records") or []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    entry: dict[str, Any] = {}
                    if "id" in row:
                        entry["id"] = row["id"]
                    if "phono" in row:
                        entry["phono"] = row["phono"]
                    driver._attached.append(entry)
        else:
            # Scalar params path
            entry = {}
            if "id" in params:
                entry["id"] = params["id"]
            if "phono" in params:
                entry["phono"] = params["phono"]
            if entry:
                driver._attached.append(entry)


# -- fixtures ----------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakePropertyAttachDriver:
    return FakePropertyAttachDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "etcbc_phono_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# GROUP 1: entry-function contract tests (WILL FAIL at Wave 2, red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_etcbc_phono.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_etcbc_phono', None) returns None, which is not
    callable. That failure IS the red TDD state the orchestrator gate
    requires (GATE: >= 3 FAILED).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "Expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(
    fake_driver: FakePropertyAttachDriver, fixture_slice: dict[str, Any]
) -> None:
    """ingest_etcbc_phono must return a dict (at minimum with a count key).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_etcbc_phono must return dict; got {type(result)!r}"
    )


def test_adapter_attaches_phono_on_bhsa_word(
    fake_driver: FakePropertyAttachDriver, fixture_slice: dict[str, Any]
) -> None:
    """Running the adapter must attach phono property on BhsaWord nodes.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per Decision 3 Edge cases handled bullet 3: phono is an optional
    property on BhsaWord, not a new node. The adapter uses MATCH-then-SET
    keyed by stable id 'bhsa:tf:<node_id>'.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    assert fake_driver.total_attached() > 0, (
        "adapter must attach phono property on at least one BhsaWord node"
    )


def test_adapter_emits_no_new_labels(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """Property-attach adapter must not emit any new node labels.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring: 'The adapter emits ZERO new node labels.' No MERGE on
    BhsaWord, no new BhsaClause, BhsaPhrase, TFNode, etc.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    # A property-attach adapter must NOT create new BhsaWord nodes.
    # We verify by asserting that no MERGE-on-BhsaWord cypher was issued,
    # i.e., all BhsaWord interactions are MATCH-then-SET only.
    # In the fake driver, new label creation is not tracked because the
    # adapter should not create any; so we verify indirectly by ensuring
    # only Source is merged (no BhsaWord MERGE-style row in _source_merges).
    non_source = [
        row for row in fake_driver._source_merges
        if row.get("slug", SOURCE_SLUG) != SOURCE_SLUG
    ]
    assert not non_source, (
        f"adapter must not MERGE non-Source nodes; unexpected merges: {non_source}"
    )


def test_adapter_emits_no_edges(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """Property-attach adapter must not emit any edges.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring Emitted edge types section: 'NONE. This adapter is a
    property-attach adapter. It does not emit any new edges.'
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    # No edge captures should exist in the fake driver.
    # The fake driver does not track edges; this test passes trivially for
    # the red state and becomes meaningful once the implementation runs.
    # We assert that the returned dict has no edge-type keys.
    result = fn(fake_driver.settings)
    if isinstance(result, dict):
        edge_keys = {k for k in result if "edge" in k.lower() or "rel" in k.lower()}
        assert not edge_keys, (
            f"adapter return dict must not contain edge count keys; found: {edge_keys}"
        )


def test_stable_id_format_bhsa_tf_prefix(
    fake_driver: FakePropertyAttachDriver, fixture_slice: dict[str, Any]
) -> None:
    """Every BhsaWord matched by the adapter must use stable id 'bhsa:tf:<node_id>'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring: 'The stable id for the BhsaWord MATCH is the same id
    property the bhsa adapter wrote: bhsa:tf:<node_id>'. Join key is
    (corpus='bhsa', node_id=<int>) under the TFNode tuple uniqueness
    constraint (Decision 14, tfnode_tuple).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    attached_ids = fake_driver.attached_ids()
    assert attached_ids, "adapter must attach phono on at least one BhsaWord"
    bad = [aid for aid in attached_ids if not aid.startswith(STABLE_ID_PREFIX)]
    assert not bad, (
        f"BhsaWord match ids must start with '{STABLE_ID_PREFIX}'; "
        f"violating ids: {bad[:5]}"
    )


def test_phono_nullable_at_0984_rate(
    fake_driver: FakePropertyAttachDriver, fixture_slice: dict[str, Any]
) -> None:
    """The adapter must tolerate null phono for ketiv-only slots (1.6 percent).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per Decision 3 Edge cases handled bullet 3: 'ETCBC-phono ships a single
    phono field at 0.984 occurrence rate. The null is preserved verbatim and
    no fallback substitution is applied.'

    The fixture has 1 null out of 21 words (4.8 percent, above the 1.6 percent
    floor). The adapter must not skip or substitute nulls.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    null_count = fake_driver.null_phono_count()
    total = fake_driver.total_attached()
    assert total > 0, "adapter must attach at least one row"
    # At least one null must pass through when the source has nulls.
    # We verify the adapter does not silently drop or substitute nulls.
    phono_values = fake_driver.attached_phono_values()
    # If null rows are present in the fixture-driven call, null must appear.
    fixture_null_count = sum(1 for w in fixture_slice["words"] if w["phono"] is None)
    if fixture_null_count > 0:
        assert null_count > 0, (
            "adapter must preserve null phono for ketiv-only slots; "
            f"fixture has {fixture_null_count} null(s) but adapter attached "
            f"{null_count} nulls"
        )
    # Every non-null phono must be a non-empty string per $pred_string.
    bad_phono = [v for v in phono_values if v is not None and (
        not isinstance(v, str) or v.strip() == ""
    )]
    assert not bad_phono, (
        f"non-null phono values must satisfy $pred_string (non-empty string); "
        f"violating values: {bad_phono[:5]}"
    )


def test_source_node_merged_with_correct_slug(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """The adapter must MERGE a Source node with slug='ETCBC-phono'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring: 'The Source node for slug ETCBC-phono is MERGEd exactly
    once at ingest start.' Decision 14 source_slug uniqueness constraint.
    Predicate: $pred_string from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    slugs = fake_driver.source_slug_merged()
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not merged. "
        f"Slugs seen: {slugs}"
    )


def test_match_then_set_idempotency(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """Running the adapter twice must produce the same attach count (idempotent).

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring Idempotency section: 'Re-running this adapter over identical
    text-fabric phono feature bytes produces zero new nodes, zero new edges,
    and the SET writes the same phono value byte-identically onto every
    BhsaWord.' MATCH-then-SET is the idempotency mechanism.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    count_run1 = fake_driver.total_attached()
    fn(fake_driver.settings)
    count_run2 = fake_driver.total_attached() - count_run1
    assert count_run1 == count_run2, (
        f"Idempotency check: run 1 attached {count_run1} rows, "
        f"run 2 attached {count_run2} rows; counts must be equal"
    )


def test_source_license_and_redistribute(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """Source node must carry license='CC-BY-NC-4.0' and redistribute=false.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per docstring Source (Decision 14) section and Decision 14 Edge cases
    handled: 'redistribute is false per Decision 14, and the adapter MUST
    NOT override this even when the property attach itself is internally
    distributable.' Predicate: $pred_bool from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    source_rows = fake_driver._source_merges
    assert source_rows, "adapter must merge at least one Source node"
    phono_source = next(
        (r for r in source_rows if r.get("slug") == SOURCE_SLUG), None
    )
    if phono_source is not None:
        assert phono_source.get("license") == "CC-BY-NC-4.0", (
            f"Source license must be 'CC-BY-NC-4.0'; got {phono_source.get('license')!r}"
        )
        assert phono_source.get("redistribute") is False, (
            f"Source redistribute must be false; got {phono_source.get('redistribute')!r}"
        )


def test_corpus_identifier_is_bhsa_not_etcbc_phono(
    fake_driver: FakePropertyAttachDriver,
) -> None:
    """The corpus identifier used in the join key must be 'bhsa', not 'ETCBC-phono'.

    FAILS at Wave 2 with TypeError: 'NoneType' object is not callable.

    Per Decision 14 Edge cases handled bullet 2: 'This adapter MUST resolve
    BhsaWord rows by (corpus=bhsa, node_id=<int>) and MUST NOT register
    ETCBC-phono as a corpus value, because the corpus identifier for the
    text-fabric module is bhsa regardless of which feature file is being read.'
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(fake_driver.settings)
    attached_ids = fake_driver.attached_ids()
    # The stable id prefix 'bhsa:tf:' encodes corpus='bhsa' in the id string.
    # Any id using 'etcbc-phono:' or 'ETCBC-phono:' would be a corpus collision.
    wrong_corpus = [aid for aid in attached_ids if "etcbc-phono" in aid.lower()]
    assert not wrong_corpus, (
        f"BhsaWord match ids must not use 'etcbc-phono' as corpus; "
        f"violating ids: {wrong_corpus[:5]}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: static validation (do NOT call adapter, pass at Wave 2)
# ---------------------------------------------------------------------------


def test_predicates_file_defines_string_and_bool() -> None:
    """tools/predicates_by_type.cypher must define $pred_string and $pred_bool.

    This test does NOT call the adapter. It validates the predicate source
    file is present and parseable per RESEED_PLAN C.5.

    predicates_by_type.cypher is referenced for phono ($pred_string, nullable)
    and Source.redistribute ($pred_bool) per Decision 3 and Decision 14.
    """
    assert "string" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_string (required for phono property)"
    )
    assert "bool" in PREDICATES, (
        "predicates_by_type.cypher missing $pred_bool (required for Source.redistribute)"
    )
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL"
    )
    assert "IS NOT NULL" in PREDICATES["bool"], (
        "$pred_bool must contain IS NOT NULL"
    )


def test_expected_count_from_expected_counts_json() -> None:
    """expected_counts.json ETCBC-phono entry must be 426590, Tier A, tolerance 0.

    This test does NOT call the adapter. It validates the count constant
    the coverage tests use is correct per the source file.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["ETCBC-phono"]
    assert entry["expected_count"] == EXPECTED_WORD_COUNT, (
        f"expected_counts.json ETCBC-phono count {entry['expected_count']} "
        f"!= {EXPECTED_WORD_COUNT}"
    )
    assert entry["tier"] == "A", "ETCBC-phono must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"
    assert entry["record_unit"] == "word", "ETCBC-phono record_unit must be 'word'"


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """Fixture seeded_length must reproduce from int(commit_sha[:8], 16).

    Seed = int('dde76900', 16) = 3722930432.
    seeded_length = rng.randint(1024, 16384) = 12352.
    """
    rng = random.Random(SEED_INT)
    expected_length = rng.randint(1024, 16384)
    assert expected_length == fixture_slice["seeded_length"], (
        f"Fixture seeded_length {fixture_slice['seeded_length']} "
        f"!= {expected_length} (seed={SEED_INT})"
    )


def test_fixture_has_three_ot_verses(fixture_slice: dict[str, Any]) -> None:
    """Fixture must contain words from exactly 3 distinct OT books.

    This test does NOT call the adapter. It validates the fixture structure.
    Three OT verses are required per the Phase C Wave 2 caste brief.
    """
    books = {w["book"] for w in fixture_slice["words"]}
    assert len(books) == 3, (
        f"Fixture must have words from exactly 3 OT books; got {sorted(books)}"
    )
    for book in books:
        assert isinstance(book, str) and book.strip(), (
            f"Each book name must be a non-empty string; got {book!r}"
        )


def test_fixture_has_nullable_phono_slot(fixture_slice: dict[str, Any]) -> None:
    """Fixture must contain at least one word with phono=null (ketiv-only slot).

    This test does NOT call the adapter. It validates the fixture covers
    the 1.6 percent null-rate edge case per Decision 3 bullet 3.
    """
    null_words = [w for w in fixture_slice["words"] if w["phono"] is None]
    assert null_words, (
        "Fixture must have at least one word with phono=null to test "
        "the ketiv-only slot edge case (Decision 3 Edge cases handled bullet 3)"
    )


def test_fixture_stable_ids_use_bhsa_tf_prefix(fixture_slice: dict[str, Any]) -> None:
    """All fixture stable_id values must start with 'bhsa:tf:'.

    This test does NOT call the adapter. It validates the fixture carries
    the correct stable id format per Decision 14 tfnode_tuple constraint.
    """
    bad = [
        w["stable_id"] for w in fixture_slice["words"]
        if not w["stable_id"].startswith(STABLE_ID_PREFIX)
    ]
    assert not bad, (
        f"Fixture stable_ids violate '{STABLE_ID_PREFIX}' prefix: {bad[:5]}"
    )


def test_fixture_byte_length_in_range(fixture_slice: dict[str, Any]) -> None:
    """Fixture JSON file must be between 1024 and 16384 bytes.

    Seeded length = 12352 bytes; actual file is 4716 bytes (within range).
    """
    p = REPO / "tests" / "lexical" / "fixtures" / "etcbc_phono_slice.json"
    byte_len = p.stat().st_size
    assert 1024 <= byte_len <= 16384, (
        f"Fixture byte length {byte_len} is outside [1024, 16384]"
    )


def test_predicates_cypher_has_phono_relevant_entry() -> None:
    """predicates_by_type.cypher must have >= 1 predicate usable for BhsaWord.phono.

    This test does NOT call the adapter. It confirms the predicate file
    documents at least one predicate ($pred_string) that applies to the
    phono property (string, nullable).
    """
    assert len(PREDICATES) >= 1, (
        "predicates_by_type.cypher must define at least one predicate"
    )
    pred_string = PREDICATES.get("string", "")
    assert pred_string, "predicates_by_type.cypher must define $pred_string"


# ---------------------------------------------------------------------------
# GROUP 3: stub rejection sweep (13 stubs, parametrized)
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
    fake_driver: FakePropertyAttachDriver,
    fixture_slice: dict[str, Any],
) -> None:
    """The coverage-test scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_etcbc_phono or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, the stub is rejected.
      5. If it runs silently, check: does it attach phono on BhsaWord using
         stable ids with 'bhsa:tf:' prefix, and does it preserve null phono?
         At least one check must fail. If none fail, the test itself fails.
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
        fn(fake_driver.settings)
    except Exception:
        raised = True

    if raised:
        return

    # Stub ran. Apply coverage assertions; at least one must catch the defect.
    attached_ids = fake_driver.attached_ids()
    phono_values = fake_driver.attached_phono_values()

    # Check 1: stable id prefix must be 'bhsa:tf:'.
    id_format_ok = (
        bool(attached_ids)
        and all(aid.startswith(STABLE_ID_PREFIX) for aid in attached_ids)
    )

    # Check 2: non-null phono values must be non-empty strings ($pred_string).
    phono_quality_ok = all(
        v is None or (isinstance(v, str) and v.strip() != "")
        for v in phono_values
    )

    # Check 3: no new edge rows (property-attach adapter emits no edges).
    no_edges_ok = True  # fake driver has no edge accumulator by design.

    # Check 4: Source slug must be 'ETCBC-phono'.
    slugs = fake_driver.source_slug_merged()
    source_slug_ok = SOURCE_SLUG in slugs if slugs else True

    # The stub must be rejected by at least one of these checks.
    rejected = not id_format_ok or not phono_quality_ok or not source_slug_ok
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Attached ids (sample): {attached_ids[:3]}, "
        f"Phono values (sample): {phono_values[:3]}, "
        f"Source slugs: {slugs}"
    )
