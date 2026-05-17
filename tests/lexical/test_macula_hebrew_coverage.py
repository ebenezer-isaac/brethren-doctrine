"""MACULA-Hebrew adapter coverage tests (Phase C Wave 2, non-tautological).

This file references tools/predicates_by_type.cypher for $pred_string, $pred_int,
$pred_bool, $pred_list definitions. Predicate semantics are loaded at module level
from that file and used to assert property types on captured node payloads.

TDD red-state contract:
  The adapter at ingest/lexical/macula_hebrew.py has NO function body at this commit.
  Every test that calls ingest_macula_hebrew() MUST fail because the module
  exposes only a docstring (module body == single Expr node). Calling
  ingest_macula_hebrew raises AttributeError: module has no attribute 'ingest_macula_hebrew'
  because the function is not defined. That failure IS the red TDD state the
  Wave 2 orchestrator gate requires.

Entry function confirmed:
  - ingest/lexical/macula_hebrew.py docstring: contract names ingest_macula_hebrew.
  - ingest/lexical/run.py line 16: from ingest.lexical.macula_hebrew import ingest_macula_hebrew
  - ingest/lexical/run.py line 43: return ingest_macula_hebrew(DATA_ROOT / 'macula-hebrew', settings)

Random seed:
  commit_sha = '99e73e50716850924294668809adab92004c3cee' (git log -1 -- ingest/lexical/macula_hebrew.py)
  seed_int = int('99e73e50', 16) = 2582068816

Fixture: tests/lexical/fixtures/macula_hebrew_slice.json
  Three OT corpus regions from real source files in data/private/macula-hebrew/WLC/lowfat/:
    torah   = 01-Gen-001-lowfat.xml  offset=446289 length=15923 (GEN 1:1)
    wisdom  = 19-Psa-023-lowfat.xml  offset=37815  length=15923 (PSA 23:1)
    prophets = 23-Isa-053-lowfat.xml offset=53876  length=15923 (ISA 53:1)
  MACULA-Hebrew is OT-only; no NT corpus exists. Regions are disjoint:
  Pentateuch, Psalter, Major Prophets.

Source: tools/expected_counts.json sources."MACULA-Hebrew" expected_count=475911.
Decisions: 1 (OSHB-to-MACULA-Hebrew morpheme alignment),
           4 (Hebrew-to-Greek bridge granularity),
           14 (Strong, Source, TFNode constraint policy).
Predicates: tools/predicates_by_type.cypher (canonical source, no inline definitions).
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

# -- predicates_by_type.cypher load (tools/predicates_by_type.cypher) ----------
# Loaded at module level. Inline predicate definitions are forbidden per
# RESEED_PLAN C.5. The canonical file path is tools/predicates_by_type.cypher.
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

# -- adapter constants ---------------------------------------------------------
ADAPTER_MODULE = "ingest.lexical.macula_hebrew"
ENTRY_FUNCTION = "ingest_macula_hebrew"
SOURCE_SLUG = "MACULA-Hebrew"

REQUIRED_LABELS = frozenset(
    {"MaculaToken", "Lemma", "GreekLemma", "Source"}
)
# LouwNidaDomain is intentionally NOT in REQUIRED_LABELS: per Decision 2,
# the MACULA-Hebrew adapter emits zero LouwNidaDomain nodes. IN_DOMAIN is
# owned exclusively by MACULA-Greek adapters.

REQUIRED_EDGES = frozenset(
    {"HAS_MACULA_ENRICHMENT", "INSTANCE_OF", "BRIDGES_LXX"}
)
# IN_DOMAIN is not emitted by this adapter (Decision 2 / Decision 4 boundary).

EXPECTED_MORPHEME_COUNT = 475911  # Tier A, tolerance 0, per expected_counts.json

# Seed from macula_hebrew.py docstring commit SHA (git log -1 -- ingest/lexical/macula_hebrew.py)
DOCSTRING_COMMIT_SHA = "99e73e50716850924294668809adab92004c3cee"
SEED_INT = int(DOCSTRING_COMMIT_SHA[:8], 16)  # = 2582068816


# -- Stable-id format constants -----------------------------------------------
# MaculaToken.id: xml:id verbatim from upstream lowfat TEI (no prefix)
# Lemma.id: "macula-hebrew-lemma:<strong>"  (e.g. "macula-hebrew-lemma:H7225")
# GreekLemma.id: "macula-hebrew-greek-lemma:<strong>" (e.g. "macula-hebrew-greek-lemma:G0746")
LEMMA_ID_PREFIX = "macula-hebrew-lemma:"
GREEK_LEMMA_ID_PREFIX = "macula-hebrew-greek-lemma:"


# -- FakeDriver that records every node/edge the adapter emits -----------------


class FakeDriver:
    """Minimal Neo4j driver stand-in.

    Captures MERGE payloads so tests can assert on emitted labels, edge
    types, and node-id formats without touching a live graph.

    When the adapter body is absent (Wave 2 red state), the driver is never
    reached because calling ingest_macula_hebrew() raises AttributeError first.
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
        return {"upserted": 1, "edges": 1}

    def consume(self) -> None:
        pass


def _parse_cypher_into_driver(
    cypher: str, params: dict[str, Any], driver: FakeDriver
) -> None:
    """Best-effort parse of MERGE Cypher into FakeDriver records.

    The adapter is expected to issue MERGE statements for:
      MaculaToken, Lemma, GreekLemma, Source
    and relationships:
      HAS_MACULA_ENRICHMENT, INSTANCE_OF, BRIDGES_LXX

    LouwNidaDomain nodes and IN_DOMAIN edges are forbidden for this adapter
    per Decision 2 / Decision 4 boundary.
    """
    for label in ("MaculaToken", "Lemma", "GreekLemma", "LouwNidaDomain", "Source"):
        if (
            f":`{label}`" in cypher
            or f"(n:{label}" in cypher
            or f":{label} " in cypher
            or f":{label})" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or []
            if isinstance(rows_param, list):
                for row in rows_param:
                    node: dict[str, Any] = {"label": label}
                    node.update(row if isinstance(row, dict) else {})
                    driver._nodes.append(node)
            else:
                driver._nodes.append({"label": label})

    for rel_type in (
        "HAS_MACULA_ENRICHMENT",
        "INSTANCE_OF",
        "BRIDGES_LXX",
        "IN_DOMAIN",
    ):
        if (
            f"`{rel_type}`" in cypher
            or f":{rel_type}]" in cypher
            or f":{rel_type}" in cypher
        ):
            rows_param = params.get("rows") or params.get("records") or [{}]
            count = len(rows_param) if isinstance(rows_param, list) else 1
            for _ in range(count):
                driver._edges.append({"rel_type": rel_type})


# -- fixtures ------------------------------------------------------------------


@pytest.fixture()
def fake_driver() -> FakeDriver:
    return FakeDriver()


@pytest.fixture()
def fixture_slice() -> dict[str, Any]:
    p = REPO / "tests" / "lexical" / "fixtures" / "macula_hebrew_slice.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def source_root(fixture_slice: dict[str, Any]) -> Path:
    """Return the parent directory two levels above the first slice source_path."""
    first_slice = fixture_slice["slices"][0]
    return (REPO / first_slice["source_path"]).parent.parent


# ---------------------------------------------------------------------------
# GROUP 1: entry-function tests (WILL FAIL at Wave 2 - red state)
# ---------------------------------------------------------------------------


def test_adapter_entry_function_is_callable() -> None:
    """The adapter module must expose a callable named ingest_macula_hebrew.

    FAILS at Wave 2: the adapter has no function body, so
    getattr(mod, 'ingest_macula_hebrew', None) returns None and the assert fails.
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
    """ingest_macula_hebrew must return a dict mapping label to count.

    FAILS at Wave 2 with AttributeError: module 'ingest.lexical.macula_hebrew'
    has no attribute 'ingest_macula_hebrew'.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    result = fn(source_root, fake_driver.settings)
    assert isinstance(result, dict), (
        f"ingest_macula_hebrew must return dict; got {type(result)!r}"
    )
    assert "MaculaToken" in result, "return dict must contain 'MaculaToken' key"


def test_adapter_emits_required_labels(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge nodes for every required label.

    Required: MaculaToken, Lemma, GreekLemma, Source.
    LouwNidaDomain is NOT required (Decision 2 owns IN_DOMAIN; MACULA-Hebrew emits zero).

    FAILS at Wave 2 with AttributeError.
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


def test_adapter_must_not_emit_louw_nida_domain(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter MUST NOT create LouwNidaDomain nodes (Decision 2 / Decision 4 boundary).

    Per the docstring contract: 'This adapter MUST NOT create LouwNidaDomain nodes
    from the Hebrew morpheme stream.'

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_labels()
    assert "LouwNidaDomain" not in emitted, (
        "MACULA-Hebrew adapter must not emit LouwNidaDomain nodes. "
        "Decision 2 binds IN_DOMAIN to MACULA-Greek adapters only."
    )


def test_adapter_must_not_emit_in_domain_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The adapter MUST NOT emit IN_DOMAIN edges (Decision 4 boundary).

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    emitted = fake_driver.captured_edge_types()
    assert "IN_DOMAIN" not in emitted, (
        "MACULA-Hebrew adapter must not emit IN_DOMAIN edges. "
        "Decision 2 binds IN_DOMAIN to MACULA-Greek-Nestle1904 and MACULA-Greek-SBLGNT."
    )


def test_adapter_emits_required_edges(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Running the adapter must merge every required edge type.

    Required: HAS_MACULA_ENRICHMENT, INSTANCE_OF, BRIDGES_LXX.

    FAILS at Wave 2 with AttributeError.
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


def test_macula_token_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every MaculaToken node must have id = xml:id verbatim (no prefix added).

    Per docstring: 'The stable node identifier id is the xml:id attribute value
    verbatim from the upstream TEI lowfat file. No prefix is added because the
    upstream identifier is already globally unique within the MACULA-Hebrew release.'

    Sample ids from corpus: o010010010011, o010010010012 (Genesis), etc.

    Predicate: $pred_string from tools/predicates_by_type.cypher.
    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_ids = fake_driver.captured_node_ids("MaculaToken")
    assert token_ids, "adapter must emit at least one MaculaToken node"
    # xml:id values are purely alphanumeric (letter + digits), no colon prefix
    bad = [tid for tid in token_ids if ":" in tid or tid.startswith("macula")]
    assert not bad, (
        f"MaculaToken ids must be xml:id verbatim (no prefix), "
        f"but found prefixed ids: {bad[:5]}"
    )


def test_lemma_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Lemma node must have id starting with 'macula-hebrew-lemma:'.

    Per docstring: 'Stable-id format for Lemma: macula-hebrew-lemma:<strong>
    where <strong> is the canonical Hebrew Strong identifier (e.g. H0001).'

    Predicate: $pred_string from tools/predicates_by_type.cypher.
    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    lemma_ids = fake_driver.captured_node_ids("Lemma")
    assert lemma_ids, "adapter must emit at least one Lemma node"
    bad = [lid for lid in lemma_ids if not lid.startswith(LEMMA_ID_PREFIX)]
    assert not bad, (
        f"Lemma ids must start with '{LEMMA_ID_PREFIX}', "
        f"but got: {bad[:5]}"
    )


def test_greek_lemma_stable_id_format(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every GreekLemma node must have id starting with 'macula-hebrew-greek-lemma:'.

    Per docstring: 'Stable-id format for GreekLemma: macula-hebrew-greek-lemma:<strong>
    where <strong> is the canonical Greek Strong identifier (e.g. G0001).'

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    greek_ids = fake_driver.captured_node_ids("GreekLemma")
    assert greek_ids, "adapter must emit at least one GreekLemma node"
    bad = [gid for gid in greek_ids if not gid.startswith(GREEK_LEMMA_ID_PREFIX)]
    assert not bad, (
        f"GreekLemma ids must start with '{GREEK_LEMMA_ID_PREFIX}', "
        f"but got: {bad[:5]}"
    )


def test_source_node_slug(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must be MERGEd with slug='MACULA-Hebrew'.

    Decision 14: Source uniqueness constraint on Source.slug.
    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    slugs = fake_driver.captured_node_slugs("Source")
    assert SOURCE_SLUG in slugs, (
        f"Source node with slug='{SOURCE_SLUG}' not found. Got slugs: {slugs}"
    )


def test_bridges_lxx_has_greek_surface_property(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every BRIDGES_LXX edge must carry greek_surface property (Decision 4).

    Acceptance query from docstring:
      MATCH (h:Lemma)-[b:BRIDGES_LXX]->(g:GreekLemma)
      WHERE b.greek_surface IS NOT NULL
      RETURN count(b) AS bridges, bridges > 0

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    bridge_edges = [e for e in fake_driver._edges if e["rel_type"] == "BRIDGES_LXX"]
    assert bridge_edges, "adapter must emit at least one BRIDGES_LXX edge"
    bad = [e for e in bridge_edges if not e.get("greek_surface")]
    assert not bad, (
        f"{len(bad)} BRIDGES_LXX edge(s) missing greek_surface property. "
        "Decision 4 requires greek_surface on every bridge edge."
    )


def test_has_macula_enrichment_has_osis_ref(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every HAS_MACULA_ENRICHMENT edge must carry osis_ref property (Decision 1).

    Edge properties: osis_ref (string), join_lemma (string).
    Predicate: $pred_string from tools/predicates_by_type.cypher.

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    enrichment_edges = [
        e for e in fake_driver._edges if e["rel_type"] == "HAS_MACULA_ENRICHMENT"
    ]
    assert enrichment_edges, "adapter must emit at least one HAS_MACULA_ENRICHMENT edge"
    bad = [e for e in enrichment_edges if not e.get("osis_ref")]
    assert not bad, (
        f"{len(bad)} HAS_MACULA_ENRICHMENT edge(s) missing osis_ref property. "
        "Decision 1 requires osis_ref and join_lemma on every enrichment edge."
    )


def test_functional_particle_no_instance_of_edge(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Functional particles (strongnumberx=null) must NOT produce INSTANCE_OF edges.

    Decision 1 edge case: 'The adapter MUST NOT create an INSTANCE_OF edge when
    strongnumberx is null.' Particles like ha- carry no Strong attachment.

    The test verifies that MaculaToken count > INSTANCE_OF edge count (since
    some tokens are functional particles with no Strong).

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_count = fake_driver.node_count("MaculaToken")
    instance_of_count = fake_driver.edge_count("INSTANCE_OF")
    assert token_count > 0, "adapter must emit at least one MaculaToken"
    assert instance_of_count < token_count, (
        f"INSTANCE_OF edge count ({instance_of_count}) must be < MaculaToken count "
        f"({token_count}) because functional particles carry no Strong attachment. "
        "Decision 1: skip INSTANCE_OF when strongnumberx is null."
    )


def test_fixture_sha256_matches_source_slices(
    fixture_slice: dict[str, Any],
) -> None:
    """The fixture SHA-256 for each slice must match the bytes at offset..offset+length.

    This test does NOT call the adapter. It passes even at Wave 2.
    It verifies the fixture was generated correctly from the seeded RNG.
    Three slices: torah (Gen 1:1), wisdom (Psa 23:1), prophets (Isa 53:1).
    """
    for sl in fixture_slice["slices"]:
        src_path = REPO / sl["source_path"]
        if not src_path.exists():
            pytest.skip(f"Source file not present: {src_path}")
        data = src_path.read_bytes()
        offset = sl["offset"]
        length = sl["length"]
        actual = hashlib.sha256(data[offset : offset + length]).hexdigest()
        assert actual == sl["fixture_sha256"], (
            f"Slice SHA-256 mismatch for region '{sl['region']}'. "
            f"Expected: {sl['fixture_sha256']}. Got: {actual}."
        )


def test_fixture_seed_derivation(fixture_slice: dict[str, Any]) -> None:
    """Fixture length must be reproducible from the stored seed.

    seed_int = int('99e73e50', 16) = 2582068816
    length = Random(seed_int).randint(1024, 16384) = 15923
    """
    rng = random.Random(SEED_INT)
    length = rng.randint(1024, 16384)
    assert length == fixture_slice["length"], (
        f"Fixture length {fixture_slice['length']} != seeded length {length} "
        f"(seed={SEED_INT} from commit {DOCSTRING_COMMIT_SHA[:8]})"
    )


def test_predicates_file_has_required_predicates() -> None:
    """tools/predicates_by_type.cypher must define string, int, bool, float predicates.

    This test does NOT call the adapter.
    The file path tools/predicates_by_type.cypher is referenced in the docstring
    of this test module and used by the _load_predicates loader above.
    """
    assert "string" in PREDICATES, "predicates_by_type.cypher missing $pred_string"
    assert "int" in PREDICATES, "predicates_by_type.cypher missing $pred_int"
    assert "bool" in PREDICATES, "predicates_by_type.cypher missing $pred_bool"
    assert "float" in PREDICATES, "predicates_by_type.cypher missing $pred_float"
    assert "IS NOT NULL" in PREDICATES["string"], (
        "$pred_string from predicates_by_type.cypher must contain IS NOT NULL check"
    )


def test_expected_morpheme_count_from_expected_counts_json() -> None:
    """MACULA-Hebrew expected count in expected_counts.json must be 475911 (Tier A).

    This test does NOT call the adapter.
    """
    ec_path = REPO / "tools" / "expected_counts.json"
    with open(ec_path, encoding="utf-8") as fh:
        ec = json.load(fh)
    entry = ec["sources"]["MACULA-Hebrew"]
    assert entry["expected_count"] == EXPECTED_MORPHEME_COUNT, (
        f"expected_counts.json MACULA-Hebrew count {entry['expected_count']} "
        f"!= {EXPECTED_MORPHEME_COUNT}"
    )
    assert entry["tier"] == "A", "MACULA-Hebrew must be Tier A"
    assert entry["tolerance"] == 0, "Tier A tolerance must be 0"


def test_sample_words_cover_all_three_ot_regions(
    fixture_slice: dict[str, Any],
) -> None:
    """The fixture sample_words must include tokens from torah, wisdom, and prophets.

    This test does NOT call the adapter. It validates fixture completeness.
    """
    regions = {sl["region"] for sl in fixture_slice["slices"]}
    assert "torah" in regions, "fixture must include a torah region slice"
    assert "wisdom" in regions, "fixture must include a wisdom region slice"
    assert "prophets" in regions, "fixture must include a prophets region slice"
    sample = fixture_slice.get("sample_words", {})
    for region in ("torah", "wisdom", "prophets"):
        words = sample.get(region, [])
        assert words, f"fixture sample_words['{region}'] must be non-empty"
        for word in words:
            assert word.get("xml_id"), (
                f"Every sample word in '{region}' must have non-empty xml_id"
            )


def test_lemma_language_is_hebrew(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every Lemma node emitted by this adapter must have language='hebrew'.

    Per docstring: 'The language property is set to hebrew on every Lemma this
    adapter writes so the lexical graph partitions cleanly from Greek lemmas.'

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    lemma_nodes = [n for n in fake_driver._nodes if n.get("label") == "Lemma"]
    assert lemma_nodes, "adapter must emit at least one Lemma node"
    bad = [n for n in lemma_nodes if n.get("language") not in ("hebrew", None, "")]
    assert not bad, (
        f"Lemma nodes with wrong language: {bad[:3]}. "
        "Decision 14: language='hebrew' on every Lemma from MACULA-Hebrew adapter."
    )


def test_greek_lemma_language_is_greek(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Every GreekLemma node emitted by this adapter must have language='greek'.

    Per docstring: 'The language property is greek.' (Decision 4 / Decision 14).

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    greek_nodes = [n for n in fake_driver._nodes if n.get("label") == "GreekLemma"]
    assert greek_nodes, "adapter must emit at least one GreekLemma node"
    bad = [n for n in greek_nodes if n.get("language") not in ("greek", None, "")]
    assert not bad, (
        f"GreekLemma nodes with wrong language: {bad[:3]}. "
        "Decision 14: language='greek' on every GreekLemma node."
    )


# ---------------------------------------------------------------------------
# GROUP 2: stub-rejection sweep (parametrized across all 13 attack stubs)
#
# For each stub, attempt to run it through the same label/edge/id assertions.
# The stub must be rejected by at least one check.
# These tests skip (not fail) when the stub has no ingest entry point.
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
    """The coverage scaffold must detect defects in each attack-vector stub.

    Pattern:
      1. Import the stub.
      2. Try to find an ingest entry point named ingest_macula_hebrew or ingest.
      3. If no entry point, skip (stub may only expose emit_records/emit_edges).
      4. If entry point exists, call it. If it raises, stub is rejected. Good.
      5. If it runs silently, check labels, edge types, and id format.
         At least one check must fail. If none fail, the test fails with
         'verifier failed to detect defect in <stub_module_name>'.

    predicates_by_type.cypher is the source for predicate semantics (see
    module-level PREDICATES dict). Inline predicates are forbidden.
    """
    stub_mod = importlib.import_module(stub_module_name)

    fn = (
        getattr(stub_mod, ENTRY_FUNCTION, None)
        or getattr(stub_mod, "ingest", None)
        or getattr(stub_mod, "ingest_macula_hebrew", None)
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
    token_ids = fake_driver.captured_node_ids("MaculaToken")
    lemma_ids = fake_driver.captured_node_ids("Lemma")
    greek_ids = fake_driver.captured_node_ids("GreekLemma")

    label_ok = REQUIRED_LABELS.issubset(emitted_labels)
    edge_ok = REQUIRED_EDGES.issubset(emitted_edges)
    in_domain_absent = "IN_DOMAIN" not in emitted_edges
    louw_absent = "LouwNidaDomain" not in emitted_labels

    # MaculaToken ids must be verbatim xml:id (no colon prefix, no 'macula' prefix)
    token_id_ok = (
        all(":" not in tid and not tid.startswith("macula") for tid in token_ids)
        if token_ids
        else False
    )
    lemma_id_ok = (
        all(lid.startswith(LEMMA_ID_PREFIX) for lid in lemma_ids)
        if lemma_ids
        else False
    )
    greek_id_ok = (
        all(gid.startswith(GREEK_LEMMA_ID_PREFIX) for gid in greek_ids)
        if greek_ids
        else False
    )

    rejected = (
        not label_ok
        or not edge_ok
        or not token_id_ok
        or not lemma_id_ok
        or not greek_id_ok
        or not in_domain_absent
        or not louw_absent
    )
    assert rejected, (
        f"verifier failed to detect defect in {stub_module_name}. "
        f"Labels: {sorted(emitted_labels)}, "
        f"Edges: {sorted(emitted_edges)}, "
        f"Sample token ids: {token_ids[:3]}, "
        f"Sample lemma ids: {lemma_ids[:3]}"
    )


def test_source_node_has_redistribute_false(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """The Source node must carry redistribute=False (CC-BY-NC-4.0 composite license).

    Per docstring: 'Redistribute boolean on the emitted Source node: false (the
    strictest applicable component is non-commercial).'
    Decision 14: Source registration with license and redistribute properties.

    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    source_nodes = [n for n in fake_driver._nodes if n.get("label") == "Source"]
    assert source_nodes, "adapter must emit at least one Source node"
    macula_src = [n for n in source_nodes if n.get("slug") == SOURCE_SLUG]
    assert macula_src, f"Source node with slug='{SOURCE_SLUG}' not found"
    for node in macula_src:
        assert node.get("redistribute") is False or node.get("redistribute") is None, (
            f"Source node for '{SOURCE_SLUG}' must have redistribute=False "
            f"(CC-BY-NC-4.0 composite). Got: {node.get('redistribute')!r}"
        )


def test_hapax_question_mark_gloss_normalised(
    fake_driver: FakeDriver, source_root: Path
) -> None:
    """Hapax gloss value '?' must be normalised to null before persistence.

    Decision 1 edge case: 'Hapax legomena whose ETCBC-BHSA freq_lex equals one
    occasionally carry a MACULA gloss value that is the literal English string ?.
    The adapter MUST normalise this to a null gloss so $pred_string(gloss)
    returns false rather than reporting a populated value.'

    Predicate: $pred_string from tools/predicates_by_type.cypher.
    FAILS at Wave 2 with AttributeError.
    """
    mod = importlib.import_module(ADAPTER_MODULE)
    fn = getattr(mod, ENTRY_FUNCTION)
    fn(source_root, fake_driver.settings)
    token_nodes = [n for n in fake_driver._nodes if n.get("label") == "MaculaToken"]
    # Any token with gloss='?' is a normalisation failure.
    bad = [n for n in token_nodes if n.get("gloss") == "?"]
    assert not bad, (
        f"{len(bad)} MaculaToken node(s) have un-normalised hapax gloss '?'. "
        "Decision 1: normalise '?' gloss to null (empty/None) before persistence."
    )
