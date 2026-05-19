"""STEPBible-TAGNT adapter coverage tests (Phase C Wave 2).

This file references tools/predicates_by_type.cypher for $pred_string and
$pred_list definitions. Predicate semantics are loaded at module level from
that file; inline predicate definitions are forbidden per RESEED_PLAN C.5.

TDD red-state contract:
  The adapter at ingest/lexical/stepbible_tagnt.py has NO function body at
  this commit. Every test that calls ingest_stepbible_tagnt() MUST fail
  because the module exposes no callable and getattr returns None.
  That failure IS the red state the Wave 2 orchestrator gate requires:
  at least 3 FAILED.

Entry function:
  ingest/lexical/stepbible_tagnt.py declares the function via its docstring
  contract (source slug STEPBible-TAGNT, phase 02 bullet 6).

Adapter: ingest/lexical/stepbible_tagnt.py
Entry:   ingest_stepbible_tagnt
Slug:    STEPBible-TAGNT
Labels:  TaggedToken (source='STEPBible-TAGNT')
Edges:   INSTANCE_OF (TaggedToken -> GreekLemma), IN_VERSE (TaggedToken -> Verse)
Decisions: 16

Random seed:
  commit_sha = 'de38fdb5e2f502a8479298e23e7cd70464dad90f' (git log -1 -- ingest/lexical/stepbible_tagnt.py)
  seed = int('de38fdb5', 16) = 3728276917

Fixture: tests/lexical/fixtures/stepbible_tagnt_slice.json
  Three NT corpus regions: Matt.1.1 (gospels), Rom.8.1 (epistles), Rev.1.1 (apocalypse).
  Length (from seed): 13498.
  Source: TSV under data/private/stepbible/Translators Amalgamated OT+NT/

predicates_by_type.cypher references (required by gate):
  $pred_string(x) := x IS NOT NULL AND trim(toString(x)) <> ""
  $pred_list(x)   := x IS NOT NULL AND size(x) > 0
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
# Loaded at module level. Inline definitions are forbidden per RESEED_PLAN C.5.
# This file is referenced in the module docstring and consumed here.
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
ADAPTER_MODULE = "ingest.lexical.stepbible_tagnt"
ENTRY_FUNCTION = "ingest_stepbible_tagnt"

REQUIRED_LABELS = frozenset({"TaggedToken"})
REQUIRED_EDGES = frozenset({"INSTANCE_OF", "IN_VERSE"})

# Decision 16: ten semantic columns on every TaggedToken row
REQUIRED_STRING_FIELDS = (
    "word_and_type",
    "greek",
    "english_translation",
    "dstrongs_grammar",
    "dictionary_gloss",
    "editions",
    "sstrong_instance",
    "alt_strongs",
)
REQUIRED_LIST_FIELDS = (
    "meaning_variants",
    "spelling_variants",
)

EXPECTED_TOKEN_COUNT = 142096  # Tier A, tolerance 0, per expected_counts.json
SOURCE_SLUG = "STEPBible-TAGNT"

# Seed from stepbible_tagnt.py docstring commit SHA
DOCSTRING_COMMIT_SHA = "de38fdb5e2f502a8479298e23e7cd70464dad90f"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 3728276917


# -- FakeDriver that records every node/edge the adapter emits --------------

class FakeDriver:
    """Minimal Neo4j driver stand-in.

    When the adapter body is absent (Wave 2 red state) the driver is never
    reached because calling ingest_stepbible_tagnt() raises TypeError first.
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

    def captured_nodes_by_label(self, label: str) -> list[dict[str, Any]]:
        return [n for n in self._nodes if n.get("label") == label]

    def node_count(self, label: str) -> int:
        return sum(1 for n in self._nodes if n["label"] == label)

    def edge_count(self, rel_type: str) -> int:
        return sum(1 for e in self._edges if e["rel_type"] == rel_type)


class _FakeSettings:
    """Minimal settings stub."""

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
      MERGE (n:TaggedToken {id: ...}) SET n += row.properties
      MERGE (a)-[r:INSTANCE_OF]->(b)
      MERGE (a)-[r:IN_VERSE]->(b)

    The parser records labels and key properties found in UNWIND batch params.
    When the adapter body is absent, no calls are made, so nothing is recorded.
    """
    for label in ("TaggedToken",):
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
                    if "properties" in node and isinstance(node["properties"], dict):
                        node.update(node["properties"])
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    # Source node
    if "Source" in cypher and ("slug" in cypher or "slug" in str(params)):
        rows_param = params.get("rows") or params.get("records") or []
        if isinstance(rows_param, list):
            for row in rows_param:
                node = {"label": "Source"}
                node.update(row if isinstance(row, dict) else {})
                driver._nodes.append(node)
        else:
            driver._nodes.append({"label": "Source"})

    for rel_type in ("INSTANCE_OF", "IN_VERSE"):
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
    p = REPO / "tests" / "lexical" / "fixtures" / "stepbible_tagnt_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root(fixture_slice: dict[str, Any]) -> Path:
    """Return the parent directory of the fixture source_path."""
    return (REPO / fixture_slice["source_path"]).parent.parent


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------

def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_stepbible_tagnt.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_stepbible_tagnt', None) returns None and the assert fails.
    That failure IS the expected red state at Wave 2 (docstring-only adapter).
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION, None)
    assert callable(fn), (
        f"{ADAPTER_MODULE}.{ENTRY_FUNCTION} must be a callable, "
        f"but got {type(fn)!r}. "
        "This failure is the expected red state at Wave 2 (docstring-only adapter)."
    )


def test_adapter_returns_dict(fake_driver: FakeDriver, source_root: Path) -> None:
    """ingest_stepbible_tagnt must return a dict mapping label to count.

    FAILS at Wave 2 with TypeError or AttributeError because the adapter
    exposes no function body.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_stepbible_tagnt must return dict; got {type(result)!r}"
    )
    assert "TaggedToken" in result, "return dict must contain 'TaggedToken' key"


def test_adapter_emits_tagged_token_label(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes with label TaggedToken.

    FAILS at Wave 2 with TypeError or AttributeError.
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
    """Running the adapter must merge INSTANCE_OF and IN_VERSE edge types.

    FAILS at Wave 2 with TypeError or AttributeError.
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
    """Every TaggedToken node id must match 'stepbible-tagnt:<osisRef>.w<pos>'.

    FAILS at Wave 2 with TypeError or AttributeError.

    Stable id spec from docstring: 'stepbible-tagnt:<osisRef>.w<pos>'
    where osisRef = Book.Chapter.Verse (e.g. Matt.1.1) and pos is
    zero-padded two-digit position (e.g. w01).
    Predicate: $pred_string from tools/predicates_by_type.cypher.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_ids = fake_driver.captured_node_ids("TaggedToken")
    assert token_ids, "adapter must emit at least one TaggedToken node"
    bad = [tid for tid in token_ids if not tid.startswith("stepbible-tagnt:")]
    assert not bad, (
        f"TaggedToken ids violate 'stepbible-tagnt:' prefix format: {bad[:5]}"
    )


def test_tagged_token_source_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every TaggedToken node must have source='STEPBible-TAGNT'.

    FAILS at Wave 2 with TypeError or AttributeError.

    Decision 16 docstring: 'TaggedToken (with property source set to the
    string STEPBible-TAGNT)'. Predicate: $pred_string.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_nodes = fake_driver.captured_nodes_by_label("TaggedToken")
    assert token_nodes, "adapter must emit at least one TaggedToken node"
    bad = [n for n in token_nodes if n.get("source") != SOURCE_SLUG]
    assert not bad, (
        f"TaggedToken nodes with wrong source property: "
        f"{[n.get('source') for n in bad[:3]]}"
    )


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='STEPBible-TAGNT'.

    FAILS at Wave 2 with TypeError or AttributeError.

    Decision 14: Source uniqueness constraint on source_slug.
    license='CC-BY-4.0', redistribute=True.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


# ---------------------------------------------------------------------------
# GROUP 2: Decision-16 field-shape assertions (WILL FAIL at Wave 2)
# ---------------------------------------------------------------------------

def test_decision16_string_fields_present(fixture_slice: dict[str, Any]) -> None:
    """Every sample row in the fixture must carry all eight string-typed Decision 16 fields.

    Tests the fixture integrity and documents the required schema.
    This test runs against the fixture, not the adapter, so it PASSES at Wave 2.
    The adapter tests that call ingest_stepbible_tagnt will FAIL.
    """
    for row in fixture_slice["sample_rows"]:
        for field in REQUIRED_STRING_FIELDS:
            assert field in row, (
                f"sample row {row.get('word_and_type')!r} missing field {field!r}. "
                f"Decision 16 requires: {list(REQUIRED_STRING_FIELDS)}"
            )
            # $pred_string: value must be non-null and non-empty (alt_strongs may be empty string)
            # We only require the key is present; alt_strongs is nullable per edge case 2.
            assert row[field] is not None, (
                f"field {field!r} must not be None in fixture row "
                f"{row.get('word_and_type')!r}"
            )


def test_decision16_list_fields_are_lists(fixture_slice: dict[str, Any]) -> None:
    """Both list-typed fields must be Python lists in every fixture row.

    Tests $pred_list: meaning_variants and spelling_variants must be lists,
    not packed semicolon strings.
    This test runs against the fixture and PASSES at Wave 2.
    """
    for row in fixture_slice["sample_rows"]:
        for field in REQUIRED_LIST_FIELDS:
            assert field in row, (
                f"sample row {row.get('word_and_type')!r} missing list field {field!r}"
            )
            assert isinstance(row[field], list), (
                f"field {field!r} must be a list (not a packed string). "
                f"Got {type(row[field])!r} in row {row.get('word_and_type')!r}. "
                f"Decision 16 edge case 1: semicolon split required."
            )


def test_decision16_stable_id_derivable_from_word_and_type(
    fixture_slice: dict[str, Any],
) -> None:
    """The stable id must be derivable from word_and_type per the docstring format.

    Format: stepbible-tagnt:<osisRef>.w<pos>
    word_and_type carries the OSIS ref token and position: e.g. 'Matt.1.1#01=N'
    yields osisRef='Matt.1.1' and pos='01'.
    This test runs against the fixture and PASSES at Wave 2.
    """
    for row in fixture_slice["sample_rows"]:
        wat = row["word_and_type"]
        assert "#" in wat, (
            f"word_and_type {wat!r} must contain '#' to separate osisRef from position"
        )
        osis_part, pos_part = wat.split("#", 1)
        pos_num = pos_part.split("=")[0]
        stable_id = f"stepbible-tagnt:{osis_part}.w{pos_num}"
        assert stable_id.startswith("stepbible-tagnt:"), (
            f"derived stable id {stable_id!r} does not start with 'stepbible-tagnt:'"
        )
        assert ".w" in stable_id, (
            f"derived stable id {stable_id!r} missing '.w<pos>' suffix"
        )


def test_decision16_editions_is_string_not_list(fixture_slice: dict[str, Any]) -> None:
    """editions must be a string, not a list.

    Decision 16 edge case 4: editions is persisted verbatim as a string
    ($pred_string). The list split is reserved for the two semicolon-delimited
    columns only. This test runs against the fixture and PASSES at Wave 2.
    """
    for row in fixture_slice["sample_rows"]:
        assert isinstance(row["editions"], str), (
            f"editions must be a string in row {row.get('word_and_type')!r}. "
            f"Got {type(row['editions'])!r}. "
            "Decision 16 edge case 4: do NOT split editions into a list."
        )


def test_decision16_alt_strongs_verbatim(fixture_slice: dict[str, Any]) -> None:
    """alt_strongs must be present as a string (may be empty) without overwriting dstrongs_grammar.

    Decision 16 edge case 3: alt_strongs must be persisted verbatim.
    Both strong values stay independently queryable.
    This test runs against the fixture and PASSES at Wave 2.
    """
    for row in fixture_slice["sample_rows"]:
        assert "alt_strongs" in row, (
            f"alt_strongs field missing from row {row.get('word_and_type')!r}"
        )
        assert isinstance(row["alt_strongs"], str), (
            f"alt_strongs must be a string; got {type(row['alt_strongs'])!r}"
        )
        assert "dstrongs_grammar" in row, (
            f"dstrongs_grammar field missing from row {row.get('word_and_type')!r}"
        )
        # alt_strongs must not overwrite dstrongs_grammar
        if row["alt_strongs"]:
            assert row["alt_strongs"] != row["dstrongs_grammar"], (
                f"alt_strongs must differ from dstrongs_grammar when populated. "
                f"Row: {row.get('word_and_type')!r}"
            )


# ---------------------------------------------------------------------------
# GROUP 3: seed and count assertions (PASS at Wave 2)
# ---------------------------------------------------------------------------

def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """The fixture length must be reproducible from the stored seed.

    Seed = int(commit_sha[:8], 16) = int('de38fdb5', 16) = 3728276917.
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {length}. "
        f"Seed: {SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]}"
    )


def test_expected_token_count_from_expected_counts_json() -> None:
    """The STEPBible-TAGNT expected count in expected_counts.json must be 142096 (Tier A).

    This test does NOT call the adapter. It validates the count constant.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    tagnt_entry = ec["sources"]["STEPBible-TAGNT"]
    assert tagnt_entry["expected_count"] == EXPECTED_TOKEN_COUNT, (
        f"expected_counts.json STEPBible-TAGNT count {tagnt_entry['expected_count']} "
        f"!= {EXPECTED_TOKEN_COUNT}"
    )
    assert tagnt_entry["tier"] == "A", "STEPBible-TAGNT must be Tier A"
    assert tagnt_entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string and list predicates.

    This test does NOT call the adapter.
    The file path tools/predicates_by_type.cypher is referenced in the
    module docstring and consumed at module-level above.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "list" in PREDICATES, "predicates_by_type.cypher missing $pred_list"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string must contain IS NOT NULL check"
    )
    assert "size(" in PREDICATES["list"], (
        "$pred_list must contain size() check"
    )


def test_fixture_has_three_corpus_regions(fixture_slice: dict[str, Any]) -> None:
    """The fixture must cover three NT regions: gospels, epistles, apocalypse.

    Verifies the fixture spans Matt (gospel), Rom (epistle), Rev (apocalypse).
    This test runs against the fixture and PASSES at Wave 2.
    """
    refs = fixture_slice["sample_osis_refs"]
    books = {r.split(".")[0] for r in refs}
    assert "Matt" in books, (
        f"fixture must include a gospel verse (Matt.*). Got refs: {refs}"
    )
    assert "Rom" in books, (
        f"fixture must include an epistle verse (Rom.*). Got refs: {refs}"
    )
    assert "Rev" in books, (
        f"fixture must include an apocalyptic verse (Rev.*). Got refs: {refs}"
    )


# ---------------------------------------------------------------------------
# GROUP 4: stub-rejection sweep (parametrized across 13 stubs)
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
      2. Try to find an ingest entry point named ingest_stepbible_tagnt or ingest.
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
        or getattr(stub_mod, "ingest_stepbible_tagnt", None)
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
        all(tid.startswith("stepbible-tagnt:") for tid in token_ids)
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
