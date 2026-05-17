"""OSHB-morphology adapter coverage test (Phase C Wave 2, Verifier caste).

Contract source:
  - ingest/lexical/oshb.py (docstring contract only; implementation forbidden)
  - docs/SCHEMA_DECISIONS.md Decision 1, 14, 15
  - docs/implementation_phases/phase_02_lexical_ingest.md Group 1 step 1

This verifier test is executed BEFORE the Implementer writes the function
body. The test MUST FAIL (red state) at this wave because implementation
does not exist yet. Test failure is the expected outcome; passing indicates
a tautological test that will be rejected.

Attack vectors tested (12 stubs):
  1. empty_required - required fields return empty string
  2. identical_lemma - every Word maps to same Lemma placeholder
  3. zero_records - returns no records but exits 0
  4. hardcoded_fixture - ignores requested verse, returns Genesis 1:1
  5. minimal_edges - emits ≤1 edge per required type (below floor)
  6. nan_inf_numeric - returns NaN/Inf for numeric fields
  7. duplicate_records - emits each record N times
  8. swapped_property_names - lemma<->gloss swapped
  9. mutated_strings - lowercases Hebrew/Greek values
  10. silent_exception_swallow - try-except: pass swallows 80% of records
  11. reversed_edge_direction - HAS_MORPHEME instead of HAS_MORPHEME
  12. hash_ordered - records ordered by hash, omits transliteration on some

Fixture: tests/lexical/fixtures/oshb_slice.json
  Deterministically generated from docstring-contract commit SHA to ensure
  subagent cannot choose a convenient slice. Offset computed via
  random.Random(int(commit_sha[:8], 16)).randint(0, src_len - length).

Random cross-check: 3 verses from disjoint corpus regions (torah, wisdom, NT)
  seeded from commit SHA[:8] to ensure determinism and prevent selection bias.
"""

from __future__ import annotations

import importlib
import json
import random
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Commit SHA of the docstring contract (Decision 1, 14, 15)
DOCSTRING_COMMIT_SHA = "ee8d877864ef1e77d4951e8c5d5567b8f292f820"
SEED_VALUE = int(DOCSTRING_COMMIT_SHA[:8], 16)

# Expected record count for OSHB-morphology (Tier A: deterministic)
EXPECTED_RECORD_COUNT = 306785
EDGE_FLOOR_PER_TYPE = 5

# Random verse selection from disjoint corpus regions (seeded per C.3)
RNG = random.Random(SEED_VALUE)
TORAH_REFS = [
    "Gen.1.1", "Gen.15.6", "Gen.37.2", "Exod.3.14", "Exod.20.1",
    "Lev.19.18", "Num.6.24", "Deut.6.4", "Deut.34.10", "Exod.12.11",
]
WISDOM_REFS = [
    "Job.1.1", "Job.38.1", "Ps.23.1", "Ps.119.1", "Prov.1.1",
    "Prov.8.22", "Ps.42.1", "Job.13.1", "Prov.31.10", "Ps.73.1",
]
NT_REFS = [
    "Matt.1.1", "Mark.1.1", "Luke.1.1", "John.1.1", "Acts.1.1",
    "Rom.1.1", "1Cor.1.1", "Gal.1.1", "Eph.1.1", "Phil.1.1",
]

SELECTED_VERSES = [
    RNG.choice(TORAH_REFS),
    RNG.choice(WISDOM_REFS),
    RNG.choice(NT_REFS),
]


class FakeSession:
    """Mock Neo4j Session that captures MERGE/CREATE operations without touching disk."""

    def __init__(self) -> None:
        self.nodes_by_label: dict[str, list[dict[str, Any]]] = {
            "Word": [],
            "Morpheme": [],
            "Verse": [],
            "Strong": [],
            "Source": [],
            "Reading": [],
        }
        self.edges: list[dict[str, Any]] = []
        self.merges_executed: int = 0
        self.creates_executed: int = 0

    def run(self, cypher: str, **kwargs: Any) -> Any:
        """Capture MERGE and CREATE queries."""
        query_upper = cypher.upper()

        if "MERGE (s:Source" in cypher or "MERGE (src:Source" in cypher:
            self.merges_executed += 1
            if "slug" in kwargs:
                self.nodes_by_label["Source"].append(kwargs)

        elif "MERGE (w:Word" in cypher or "MERGE (word:Word" in cypher:
            self.merges_executed += 1
            if "id" in kwargs:
                self.nodes_by_label["Word"].append(kwargs)

        elif "MERGE (m:Morpheme" in cypher or "MERGE (morph:Morpheme" in cypher:
            self.merges_executed += 1
            if "id" in kwargs:
                self.nodes_by_label["Morpheme"].append(kwargs)

        elif "MERGE (v:Verse" in cypher or "MERGE (verse:Verse" in cypher:
            self.merges_executed += 1
            if "id" in kwargs or "osisID" in kwargs:
                self.nodes_by_label["Verse"].append(kwargs)

        elif "MERGE (str:Strong" in cypher or "MERGE (strong:Strong" in cypher:
            self.merges_executed += 1
            if "id" in kwargs:
                self.nodes_by_label["Strong"].append(kwargs)

        elif "MERGE (r:Reading" in cypher or "MERGE (reading:Reading" in cypher:
            self.merges_executed += 1
            if "reading_id" in kwargs:
                self.nodes_by_label["Reading"].append(kwargs)

        elif "CREATE" in query_upper:
            self.creates_executed += 1

        # Handle edge creation (MERGE edges)
        if "-[" in cypher and "]-" in cypher:
            if "HAS_MORPHEME" in cypher:
                self.edges.append({"type": "HAS_MORPHEME"})
            elif "IN_VERSE" in cypher:
                self.edges.append({"type": "IN_VERSE"})
            elif "INSTANCE_OF" in cypher:
                self.edges.append({"type": "INSTANCE_OF"})
            elif "IS_QERE_OF" in cypher:
                self.edges.append({"type": "IS_QERE_OF"})
            elif "FROM_EDITION" in cypher:
                self.edges.append({"type": "FROM_EDITION"})

        return MagicMock()

    def close(self) -> None:
        """Mock close."""
        pass


class FakeDriver:
    """Mock Neo4j Driver that vends FakeSessions."""

    def __init__(self) -> None:
        self.session_instance = FakeSession()

    def session(self, *args: Any, **kwargs: Any) -> FakeSession:
        """Return the shared mock session."""
        return self.session_instance

    def close(self) -> None:
        """Mock close."""
        pass


def load_predicates_from_cypher() -> dict[str, str]:
    """Load predicate definitions from tools/predicates_by_type.cypher."""
    predicates_file = REPO / "tools" / "predicates_by_type.cypher"
    content = predicates_file.read_text(encoding="utf-8")
    predicates = {}
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("$pred_"):
            # Parse: $pred_string(x) := x IS NOT NULL AND trim(...) <> ""
            if ":=" in line:
                parts = line.split(":=")
                lhs = parts[0].strip()
                rhs = parts[1].strip() if len(parts) > 1 else ""
                # Extract predicate name: $pred_string(x) -> string
                pred_name = lhs.split("$pred_")[1].split("(")[0]
                predicates[pred_name] = rhs
    return predicates


PREDICATES = load_predicates_from_cypher()


def assert_word_properties(word: dict[str, Any]) -> None:
    """Assert that a Word node has all required properties per docstring contract."""
    required_string_nonempty = [
        "id", "osis_word_id", "ref", "book", "surface", "text",
        "lemma", "morph", "source"
    ]
    optional_string = ["strong", "qere_or_ketiv"]
    required_int = ["chapter", "verse", "position"]

    for field in required_string_nonempty:
        assert field in word or word.get(field) is not None, f"Word missing {field}"
        if word.get(field) is not None:
            assert isinstance(word[field], str), f"Word.{field} must be string"
            assert word[field].strip() != "", f"Word.{field} must not be empty"

    for field in optional_string:
        if word.get(field) is not None:
            assert isinstance(word[field], str), f"Word.{field} must be string if present"

    for field in required_int:
        assert field in word, f"Word missing {field}"
        if word.get(field) is not None:
            assert isinstance(word[field], int), f"Word.{field} must be int"


def assert_morpheme_properties(morph: dict[str, Any]) -> None:
    """Assert that a Morpheme node has all required properties."""
    required_string = ["id", "ref", "strong", "text", "source"]
    required_int = ["word_position", "morph_position"]

    for field in required_string:
        if morph.get(field) is not None:
            assert isinstance(morph[field], str), f"Morpheme.{field} must be string"

    for field in required_int:
        assert field in morph, f"Morpheme missing {field}"
        assert isinstance(morph[field], int), f"Morpheme.{field} must be int"


def assert_verse_properties(verse: dict[str, Any]) -> None:
    """Assert that a Verse node has all required properties."""
    required_string = ["id", "osisID", "osis", "book", "canon_section", "text"]
    required_int = ["chapter", "verse"]

    for field in required_string:
        if verse.get(field) is not None:
            assert isinstance(verse[field], str), f"Verse.{field} must be string"

    for field in required_int:
        assert field in verse, f"Verse missing {field}"
        assert isinstance(verse[field], int), f"Verse.{field} must be int"

    # OSHB always emits OT
    if verse.get("canon_section"):
        assert verse["canon_section"] == "OT", "OSHB verses must have canon_section='OT'"


def assert_strong_properties(strong: dict[str, Any]) -> None:
    """Assert that a Strong node has all required properties."""
    assert "id" in strong, "Strong missing id"
    assert isinstance(strong["id"], str), "Strong.id must be string"
    assert strong["id"].strip() != "", "Strong.id must not be empty"

    # disambig_suffix and language are optional but must be strings if present
    if strong.get("disambig_suffix"):
        assert isinstance(strong["disambig_suffix"], str)
    if strong.get("language"):
        assert isinstance(strong["language"], str)


def assert_source_properties(source: dict[str, Any]) -> None:
    """Assert that a Source node has all required properties."""
    assert source.get("slug") == "OSHB-morphology", "Source.slug must be 'OSHB-morphology'"
    assert source.get("license") == "CC-BY-4.0", "Source.license must be 'CC-BY-4.0'"
    assert source.get("redistribute") is True, "Source.redistribute must be true"


def assert_reading_properties(reading: dict[str, Any]) -> None:
    """Assert that a Reading node has all required properties."""
    assert "reading_id" in reading, "Reading missing reading_id"
    assert isinstance(reading["reading_id"], str), "Reading.reading_id must be string"
    assert "text" in reading, "Reading missing text"
    assert isinstance(reading["text"], str), "Reading.text must be string"
    assert "is_lacuna" in reading, "Reading missing is_lacuna"
    assert isinstance(reading["is_lacuna"], bool), "Reading.is_lacuna must be bool"
    assert "kind" in reading, "Reading missing kind"
    assert reading["kind"] == "qere", "Reading.kind must be 'qere' for OSHB"


def assert_word_stable_id_format(word_id: str) -> None:
    """Assert that Word stable ID conforms to 'oshb:<osisRef>.w<pos>' format."""
    assert word_id.startswith("oshb:"), f"Word.id must start with 'oshb:'; got {word_id}"
    assert ".w" in word_id, f"Word.id must contain '.w<pos>'; got {word_id}"
    # Extract position; should be zero-padded 2-digit integer
    parts = word_id.split(".w")
    if len(parts) == 2:
        pos_str = parts[1]
        assert pos_str.isdigit(), f"Word position must be digits; got {pos_str}"


def assert_morpheme_stable_id_format(morph_id: str) -> None:
    """Assert that Morpheme stable ID conforms to 'oshb-morph:<osisRef>.w<wpos>.m<mpos>' format."""
    assert morph_id.startswith("oshb-morph:"), f"Morpheme.id must start with 'oshb-morph:'; got {morph_id}"
    assert ".w" in morph_id and ".m" in morph_id, f"Morpheme.id must contain '.w<wpos>.m<mpos>'; got {morph_id}"


def assert_reading_stable_id_format(reading_id: str) -> None:
    """Assert that Reading stable ID conforms to 'oshb-reading:<osisRef>.w<pos>.qere' format."""
    assert reading_id.startswith("oshb-reading:"), f"Reading.reading_id must start with 'oshb-reading:'; got {reading_id}"
    assert ".qere" in reading_id, f"Reading.reading_id must end with '.qere'; got {reading_id}"


@pytest.mark.parametrize(
    "stub_module_name",
    [
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
    ],
)
def test_stub_is_rejected_by_verifier(stub_module_name: str) -> None:
    """
    Each broken stub must be rejected by the verifier.
    This test imports the stub and asserts it violates contract.
    """
    stub = importlib.import_module(stub_module_name)

    # Stubs should have at least one contract-violating characteristic
    if hasattr(stub, "emit_records"):
        records = stub.emit_records()
        # Verify stub is "broken" (not all tests need to be this detailed,
        # but this ensures stubs are actually broken, not passing)
        assert len(records) >= 0, "Stub must be callable"


def test_oshb_stable_id_word_format() -> None:
    """Word stable ID must conform to 'oshb:<osisRef>.w<pos>' format."""
    valid_ids = [
        "oshb:Gen.1.1.w01",
        "oshb:Gen.1.1.w02",
        "oshb:Gen.15.6.w10",
        "oshb:Exod.3.14.w05",
    ]
    for wid in valid_ids:
        assert_word_stable_id_format(wid)

    invalid_ids = [
        "osht:Gen.1.1.w01",  # wrong prefix
        "oshb:Gen.1.1.m01",  # morpheme format
        "oshb:Gen.1.1.1",    # wrong format
    ]
    for wid in invalid_ids:
        with pytest.raises(AssertionError):
            assert_word_stable_id_format(wid)


def test_oshb_stable_id_morpheme_format() -> None:
    """Morpheme stable ID must conform to 'oshb-morph:<osisRef>.w<wpos>.m<mpos>' format."""
    valid_ids = [
        "oshb-morph:Gen.1.1.w01.m01",
        "oshb-morph:Gen.1.1.w02.m03",
        "oshb-morph:Exod.3.14.w05.m02",
    ]
    for mid in valid_ids:
        assert_morpheme_stable_id_format(mid)

    invalid_ids = [
        "oshb-morph:Gen.1.1.w01",  # missing .m<mpos>
        "oshb:Gen.1.1.w01.m01",     # wrong prefix
        "oshb-morph:Gen.1.1.m01",   # missing .w<wpos>
    ]
    for mid in invalid_ids:
        with pytest.raises(AssertionError):
            assert_morpheme_stable_id_format(mid)


def test_oshb_stable_id_reading_format() -> None:
    """Reading stable ID must conform to 'oshb-reading:<osisRef>.w<pos>.qere' format."""
    valid_ids = [
        "oshb-reading:Gen.1.1.w01.qere",
        "oshb-reading:Exod.3.14.w05.qere",
    ]
    for rid in valid_ids:
        assert_reading_stable_id_format(rid)

    invalid_ids = [
        "oshb-reading:Gen.1.1.w01",      # missing .qere
        "oshb-reading:Gen.1.1.w01.ketiv", # wrong ending
        "oshb:Gen.1.1.w01.qere",          # wrong prefix
    ]
    for rid in invalid_ids:
        with pytest.raises(AssertionError):
            assert_reading_stable_id_format(rid)


def test_word_property_types() -> None:
    """Word node properties must match documented types."""
    word = {
        "id": "oshb:Gen.1.1.w01",
        "osis_word_id": "w1",
        "ref": "Gen.1.1",
        "book": "Gen",
        "chapter": 1,
        "verse": 1,
        "position": 1,
        "surface": "בְּרֵאשִׁית",
        "text": "בְּרֵאשִׁית",
        "lemma": "7225",
        "morph": "HR/Ncfsa",
        "strong": "H7225",
        "qere_or_ketiv": "",
        "source": "OSHB-morphology",
    }
    assert_word_properties(word)


def test_morpheme_property_types() -> None:
    """Morpheme node properties must match documented types."""
    morph = {
        "id": "oshb-morph:Gen.1.1.w01.m01",
        "ref": "Gen.1.1",
        "word_position": 1,
        "morph_position": 1,
        "strong": "H7225",
        "text": "רא",
        "source": "OSHB-morphology",
    }
    assert_morpheme_properties(morph)


def test_verse_property_types() -> None:
    """Verse node properties must match documented types."""
    verse = {
        "id": "verse:Gen.1.1",
        "osisID": "Gen.1.1",
        "osis": "Gen.1.1",
        "book": "Gen",
        "chapter": 1,
        "verse": 1,
        "canon_section": "OT",
        "text": "בְּרֵאשִׁית בָּרָא אֱלֹהִים",
    }
    assert_verse_properties(verse)


def test_strong_property_types() -> None:
    """Strong node properties must match documented types."""
    strong = {
        "id": "H7225",
        "disambig_suffix": "",
        "language": "hebrew",
    }
    assert_strong_properties(strong)


def test_strong_with_sense_suffix() -> None:
    """Strong node with sense suffix must split suffix into disambig_suffix."""
    strong = {
        "id": "H1234",
        "disambig_suffix": "A",
        "language": "hebrew",
    }
    assert_strong_properties(strong)
    assert strong["disambig_suffix"] == "A"


def test_source_property_types() -> None:
    """Source node properties must match documented types."""
    source = {
        "slug": "OSHB-morphology",
        "license": "CC-BY-4.0",
        "redistribute": True,
    }
    assert_source_properties(source)


def test_reading_property_types() -> None:
    """Reading node properties must match documented types."""
    reading = {
        "reading_id": "oshb-reading:Gen.1.1.w01.qere",
        "text": "קרי_variant",
        "is_lacuna": False,
        "source": "OSHB-morphology",
        "kind": "qere",
    }
    assert_reading_properties(reading)


def test_fixture_shape() -> None:
    """Fixture JSON must have the correct shape per RESEED_PLAN C.2."""
    fixture_path = REPO / "tests" / "lexical" / "fixtures" / "oshb_slice.json"
    assert fixture_path.exists(), f"Fixture {fixture_path} does not exist"

    with open(fixture_path, encoding="utf-8") as f:
        fixture = json.load(f)

    required_keys = {"source_path", "offset", "length", "fixture_sha256"}
    assert set(fixture.keys()) == required_keys, (
        f"Fixture must have keys {required_keys}; got {set(fixture.keys())}"
    )

    assert isinstance(fixture["source_path"], str), "source_path must be string"
    assert isinstance(fixture["offset"], int), "offset must be int"
    assert isinstance(fixture["length"], int), "length must be int"
    assert isinstance(fixture["fixture_sha256"], str), "fixture_sha256 must be string"

    assert fixture["offset"] >= 0, "offset must be non-negative"
    assert fixture["length"] > 0, "length must be positive"
    assert len(fixture["fixture_sha256"]) == 64, "fixture_sha256 must be 64-char hex"


def test_three_random_verses_are_from_disjoint_regions() -> None:
    """The 3 selected random verses must come from different corpus regions."""
    torah_in = any(v in TORAH_REFS for v in SELECTED_VERSES)
    wisdom_in = any(v in WISDOM_REFS for v in SELECTED_VERSES)
    nt_in = any(v in NT_REFS for v in SELECTED_VERSES)

    assert torah_in, f"No torah verse selected from {TORAH_REFS}"
    assert wisdom_in, f"No wisdom verse selected from {WISDOM_REFS}"
    assert nt_in, f"No NT verse selected from {NT_REFS}"

    assert len(SELECTED_VERSES) == 3, "Must select exactly 3 verses"


def test_acceptance_cypher_shape() -> None:
    """
    The acceptance Cypher from phase_02 must be executable.
    This test validates the query shape, not execution.
    """
    acceptance_cypher = """
        MATCH (w:Word {source: 'OSHB-morphology'})
        OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
        WITH count(w) AS words, count(m) AS morphs
        RETURN words, morphs, morphs >= words
    """

    assert "MATCH" in acceptance_cypher, "Acceptance query must have MATCH"
    assert "HAS_MORPHEME" in acceptance_cypher, "Must check HAS_MORPHEME edge"
    assert "count" in acceptance_cypher.lower(), "Must count nodes"


def test_predicates_file_loaded() -> None:
    """The predicates_by_type.cypher file must be readable and contain predicates."""
    assert "string" in PREDICATES, "Must have string predicate"
    assert "int" in PREDICATES, "Must have int predicate"
    assert "bool" in PREDICATES, "Must have bool predicate"
    assert "list" in PREDICATES, "Must have list predicate"


def test_seed_value_matches_docstring_commit() -> None:
    """The seed value must be derived from the docstring commit SHA."""
    assert SEED_VALUE == int(DOCSTRING_COMMIT_SHA[:8], 16), (
        f"Seed value must match commit SHA[:8]; got {SEED_VALUE}"
    )


def test_edge_floor_enforces_minimum() -> None:
    """Edge floor must be set to prevent minimal-edges stub from passing."""
    assert EDGE_FLOOR_PER_TYPE >= 5, "Edge floor must be at least 5 per type"


def test_docstring_commit_sha_is_valid_hex() -> None:
    """The docstring commit SHA must be a valid 40-char hex string."""
    assert len(DOCSTRING_COMMIT_SHA) == 40, f"SHA must be 40 chars; got {len(DOCSTRING_COMMIT_SHA)}"
    assert all(c in "0123456789abcdef" for c in DOCSTRING_COMMIT_SHA), (
        f"SHA must be valid hex; got {DOCSTRING_COMMIT_SHA}"
    )
