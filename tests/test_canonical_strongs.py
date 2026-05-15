"""Tests for ingest.canonical_strongs."""

import json
from pathlib import Path

import pytest

from ingest.canonical_strongs import canonical_strongs

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canonical_strongs_cross_source.json"


def test_macula_hebrew_zero_padded_0001() -> None:
    assert canonical_strongs("0001", lang="hb") == ("H0001", None)


def test_macula_hebrew_zero_padded_0430() -> None:
    assert canonical_strongs("0430", lang="hb") == ("H0430", None)


def test_macula_hebrew_zero_padded_7225() -> None:
    assert canonical_strongs("7225", lang="hb") == ("H7225", None)


def test_oshb_slash_b_prefix_0430() -> None:
    assert canonical_strongs("b/0430", lang="hb") == ("H0430", None)


def test_oshb_slash_b_prefix_7225() -> None:
    assert canonical_strongs("b/7225", lang="hb") == ("H7225", None)


def test_oshb_slash_letter_prefix_arbitrary() -> None:
    assert canonical_strongs("c/3068", lang="hb") == ("H3068", None)


def test_oshb_suffix_letter_with_space() -> None:
    assert canonical_strongs("1254 a", lang="hb") == ("H1254A", "A")


def test_oshb_suffix_letter_with_space_b() -> None:
    assert canonical_strongs("0247 b", lang="hb") == ("H0247B", "B")


def test_oshb_suffix_letter_uppercase_input() -> None:
    assert canonical_strongs("1254 A", lang="hb") == ("H1254A", "A")


def test_oshb_suffix_letter_no_space() -> None:
    assert canonical_strongs("1254a", lang="hb") == ("H1254A", "A")


def test_oshb_suffix_letter_no_space_b() -> None:
    assert canonical_strongs("0247b", lang="hb") == ("H0247B", "B")


def test_stepbible_curly_brace_plain() -> None:
    assert canonical_strongs("{H0430}") == ("H0430", None)


def test_stepbible_curly_brace_with_suffix() -> None:
    canon, suffix = canonical_strongs("{H0430G}")
    assert canon == "H0430G"
    assert suffix == "G"


def test_stepbible_curly_brace_greek() -> None:
    assert canonical_strongs("{G2316}") == ("G2316", None)


def test_macula_greek_plain_2316() -> None:
    assert canonical_strongs("2316", lang="gk") == ("G2316", None)


def test_macula_greek_plain_3056() -> None:
    assert canonical_strongs("3056", lang="gk") == ("G3056", None)


def test_macula_greek_plain_0026_pads() -> None:
    assert canonical_strongs("26", lang="gk") == ("G0026", None)


def test_tagnt_prefixed_g2316() -> None:
    assert canonical_strongs("G2316") == ("G2316", None)


def test_tagnt_prefixed_h0430() -> None:
    assert canonical_strongs("H0430") == ("H0430", None)


def test_tagnt_lowercase_prefix() -> None:
    assert canonical_strongs("g2316") == ("G2316", None)


def test_raises_on_plain_digits_without_lang_hebrew_range() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        canonical_strongs("0430")


def test_raises_on_plain_digits_without_lang_greek_range() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        canonical_strongs("2316")


def test_lang_hb_on_plain_digits_returns_h_prefix_1() -> None:
    assert canonical_strongs("0430", lang="hb") == ("H0430", None)


def test_lang_hb_on_plain_digits_returns_h_prefix_2() -> None:
    assert canonical_strongs("7225", lang="hb") == ("H7225", None)


def test_lang_gk_on_plain_digits_returns_g_prefix_1() -> None:
    assert canonical_strongs("2316", lang="gk") == ("G2316", None)


def test_lang_gk_on_plain_digits_returns_g_prefix_2() -> None:
    assert canonical_strongs("3056", lang="gk") == ("G3056", None)


def test_round_trip_h0430() -> None:
    canon, suffix = canonical_strongs("0430", lang="hb")
    assert canonical_strongs(canon) == (canon, suffix)


def test_round_trip_g2316() -> None:
    canon, suffix = canonical_strongs("2316", lang="gk")
    assert canonical_strongs(canon) == (canon, suffix)


def test_round_trip_h1254a() -> None:
    canon, suffix = canonical_strongs("1254 a", lang="hb")
    assert canonical_strongs(canon) == (canon, suffix)


def test_round_trip_curly_brace_with_suffix() -> None:
    canon, suffix = canonical_strongs("{H0430G}")
    assert canonical_strongs(canon) == (canon, suffix)


def test_round_trip_oshb_slash() -> None:
    canon, suffix = canonical_strongs("b/7225", lang="hb")
    assert canonical_strongs(canon) == (canon, suffix)


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        canonical_strongs("")


def test_whitespace_raises() -> None:
    with pytest.raises(ValueError):
        canonical_strongs("   ")


def test_garbage_raises() -> None:
    with pytest.raises(ValueError):
        canonical_strongs("not-a-strong")


def test_non_string_raises() -> None:
    with pytest.raises(ValueError):
        canonical_strongs(123)  # type: ignore[arg-type]


def test_curly_brace_empty_raises() -> None:
    with pytest.raises(ValueError):
        canonical_strongs("{}")


def test_raises_on_num_space_letter_without_lang() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        canonical_strongs("1254 a")


def test_raises_on_num_letter_without_lang() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        canonical_strongs("1254a")


def test_cross_source_fixture_loads() -> None:
    assert FIXTURE_PATH.exists()
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(data) >= 50


def test_cross_source_canonicalization_consistent() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for entry in data:
        expected_canon = entry["canonical"]
        expected_suffix = entry["suffix"]
        lang = entry["lang"]
        for source, raw in entry["encodings"].items():
            canon, suffix = canonical_strongs(raw, lang=lang)
            assert (
                canon == expected_canon
            ), f"{source}={raw!r} canonicalized to {canon!r}, expected {expected_canon!r}"
            assert (
                suffix == expected_suffix
            ), f"{source}={raw!r} suffix {suffix!r}, expected {expected_suffix!r}"
