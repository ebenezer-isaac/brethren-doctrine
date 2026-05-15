"""Tests for ingest.versification_mapper."""

from pathlib import Path

import pytest

from ingest.versification_mapper import VersificationMapper

FIXTURE = Path(__file__).parent / "fixtures" / "tvtms_sample.txt"


def test_stub_mode_when_file_missing(tmp_path: Path) -> None:
    mapper = VersificationMapper(tmp_path / "does-not-exist.txt")
    assert mapper.is_stub is True
    res = mapper.resolve("Psa.51.1", "english", "hebrew")
    assert res["to_ref"] == "Psa.51.1"
    assert res["rule_type"] == "identity"
    assert res["block_scope"] == "stub-mode"


def test_stub_mode_when_no_path() -> None:
    mapper = VersificationMapper(None)
    assert mapper.is_stub is True
    res = mapper.resolve("Psa.51.1", "english", "hebrew")
    assert res["to_ref"] == "Psa.51.1"


def test_loads_fixture() -> None:
    mapper = VersificationMapper(FIXTURE)
    assert mapper.is_stub is False


def test_canonical_psa_51_1_english_to_hebrew() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Psa.51.1", "english", "hebrew")
    assert res["to_ref"] == "Psa.51.3"
    assert res["rule_type"] == "OneToOne"
    assert res["block_scope"] == "Psa.51.title"


def test_canonical_psa_3_1_english_to_hebrew() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Psa.3.1", "english", "hebrew")
    assert res["to_ref"] == "Psa.3.2"


def test_joel_chapter_shift() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Joel.2.28", "english", "hebrew")
    assert res["to_ref"] == "Joel.3.1"


def test_malachi_chapter_shift() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Mal.4.1", "english", "hebrew")
    assert res["to_ref"] == "Mal.3.19"


def test_romans_doxology_floats() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Rom.16.25", "english", "greek")
    assert res["to_ref"] == "Rom.14.24"


def test_identity_english_to_english() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Gen.1.1", "english", "english")
    assert res["to_ref"] == "Gen.1.1"
    assert res["rule_type"] == "identity"


def test_no_rule_falls_back_to_identity() -> None:
    mapper = VersificationMapper(FIXTURE)
    res = mapper.resolve("Gen.1.1", "english", "hebrew")
    assert res["to_ref"] == "Gen.1.1"
    assert res["rule_type"] == "identity"
    assert res["block_scope"] == "no-rule"


def test_raises_on_unknown_scheme() -> None:
    mapper = VersificationMapper(FIXTURE)
    with pytest.raises(ValueError, match="unknown scheme"):
        mapper.resolve("Psa.51.1", "english", "klingon")


def test_raises_on_empty_scheme() -> None:
    mapper = VersificationMapper(FIXTURE)
    with pytest.raises(ValueError):
        mapper.resolve("Psa.51.1", "", "hebrew")


def test_raises_on_malformed_ref() -> None:
    mapper = VersificationMapper(FIXTURE)
    with pytest.raises(ValueError, match="malformed ref"):
        mapper.resolve("Psalm 51:1", "english", "hebrew")


def test_raises_on_blank_ref() -> None:
    mapper = VersificationMapper(FIXTURE)
    with pytest.raises(ValueError):
        mapper.resolve("", "english", "hebrew")


def test_bridge_set_resolves_each() -> None:
    mapper = VersificationMapper(FIXTURE)
    results = mapper.bridge_set(["Psa.51.1", "Psa.51.2", "Psa.51.3"], "english", "hebrew")
    assert [r["to_ref"] for r in results] == ["Psa.51.3", "Psa.51.4", "Psa.51.5"]


def test_bridge_set_empty_list_returns_empty() -> None:
    mapper = VersificationMapper(FIXTURE)
    assert mapper.bridge_set([], "english", "hebrew") == []
