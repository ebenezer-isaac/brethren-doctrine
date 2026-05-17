"""Tests for embeddings.embed_lexical.build_embed_text
(RESEED_PLAN Z.1 item 6, E.1).

Contract:

* deterministic per-row composition of the Voyage input string;
* yields >= 6 distinct whitespace-separated tokens when the row carries
  pos and domain in addition to lemma/translit/gloss;
* two distinct Strong's IDs produce embed texts with Jaccard token
  overlap < 0.5;
* every expected substring in a hand-picked 10-Strong's panel appears
  in the corresponding embed text;
* never returns the empty string for a row with non-empty
  lemma/translit/gloss;
* truncates at the documented cap.

The ``pos`` and ``domain`` row keys are populated by Phase E
enrichment; the panel rows supply them explicitly so the contract is
testable today.
"""

from __future__ import annotations

import pytest

from embeddings.embed_lexical import EMBED_TEXT_MAX_LEN, build_embed_text


PANEL: list[dict[str, object]] = [
    {
        "strong": "H430",
        "lemma": "אֱלֹהִים",
        "transliteration": "ʾĕlōhîm",
        "gloss": "God; gods; rulers",
        "pos": "noun-masc-plural",
        "domain": "deity",
        "_expected_substrings": ("אֱלֹהִים", "ʾĕlōhîm", "God", "deity"),
    },
    {
        "strong": "H3068",
        "lemma": "יְהוָה",
        "transliteration": "YHWH",
        "gloss": "the LORD; the proper name of God",
        "pos": "proper-name",
        "domain": "deity",
        "_expected_substrings": ("יְהוָה", "YHWH", "LORD", "proper-name"),
    },
    {
        "strong": "H7225",
        "lemma": "רֵאשִׁית",
        "transliteration": "rēšîṯ",
        "gloss": "beginning, first, chief",
        "pos": "noun-fem",
        "domain": "time",
        "_expected_substrings": ("רֵאשִׁית", "rēšîṯ", "beginning", "time"),
    },
    {
        "strong": "H1254",
        "lemma": "בָּרָא",
        "transliteration": "bārāʾ",
        "gloss": "to create, shape, form (divine activity)",
        "pos": "verb-qal",
        "domain": "action-creation",
        "_expected_substrings": ("בָּרָא", "bārāʾ", "create", "action-creation"),
    },
    {
        "strong": "H4428",
        "lemma": "מֶלֶךְ",
        "transliteration": "melek",
        "gloss": "king, ruler, sovereign",
        "pos": "noun-masc",
        "domain": "social-rule",
        "_expected_substrings": ("מֶלֶךְ", "melek", "king", "social-rule"),
    },
    {
        "strong": "G2316",
        "lemma": "θεός",
        "transliteration": "theos",
        "gloss": "God; deity",
        "pos": "noun-masc",
        "domain": "deity",
        "_expected_substrings": ("θεός", "theos", "God", "deity"),
    },
    {
        "strong": "G2962",
        "lemma": "κύριος",
        "transliteration": "kyrios",
        "gloss": "lord, master, owner",
        "pos": "noun-masc",
        "domain": "title-authority",
        "_expected_substrings": ("κύριος", "kyrios", "lord", "title-authority"),
    },
    {
        "strong": "G5547",
        "lemma": "χριστός",
        "transliteration": "christos",
        "gloss": "Christ, anointed one, Messiah",
        "pos": "noun-masc",
        "domain": "title-messianic",
        "_expected_substrings": ("χριστός", "christos", "Christ", "title-messianic"),
    },
    {
        "strong": "G3056",
        "lemma": "λόγος",
        "transliteration": "logos",
        "gloss": "word, speech, reason, account",
        "pos": "noun-masc",
        "domain": "speech",
        "_expected_substrings": ("λόγος", "logos", "word", "speech"),
    },
    {
        "strong": "G4151",
        "lemma": "πνεῦμα",
        "transliteration": "pneuma",
        "gloss": "spirit, breath, wind; Holy Spirit",
        "pos": "noun-neut",
        "domain": "spirit",
        "_expected_substrings": ("πνεῦμα", "pneuma", "spirit", "spirit"),
    },
]


def _without_marker(row: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def test_panel_has_ten_strongs() -> None:
    assert len(PANEL) == 10
    strongs = {row["strong"] for row in PANEL}
    assert len(strongs) == 10


@pytest.mark.parametrize("row", PANEL, ids=[r["strong"] for r in PANEL])  # type: ignore[arg-type]
def test_panel_expected_substrings_present(row: dict[str, object]) -> None:
    text = build_embed_text(_without_marker(row))
    expected = row["_expected_substrings"]
    assert isinstance(expected, tuple) and len(expected) == 4
    missing = [s for s in expected if s not in text]
    assert not missing, (
        f"strong={row['strong']!r}: missing {missing!r} in {text!r}"
    )


@pytest.mark.parametrize("row", PANEL, ids=[r["strong"] for r in PANEL])  # type: ignore[arg-type]
def test_distinct_token_floor(row: dict[str, object]) -> None:
    text = build_embed_text(_without_marker(row))
    distinct = len(set(text.split()))
    assert distinct >= 6, (
        f"strong={row['strong']!r}: distinct tokens={distinct} < 6 "
        f"for text {text!r}"
    )


def test_contrastive_jaccard_h7225_vs_h430() -> None:
    a = build_embed_text(_without_marker(PANEL[2]))  # H7225 beginning
    b = build_embed_text(_without_marker(PANEL[0]))  # H430 elohim
    tok_a = set(a.split())
    tok_b = set(b.split())
    inter = tok_a & tok_b
    union = tok_a | tok_b
    jaccard = len(inter) / len(union) if union else 0.0
    assert jaccard < 0.5, (
        f"H7225 vs H430 too similar: jaccard={jaccard:.3f} "
        f"common={sorted(inter)}"
    )


def test_contrastive_jaccard_g2316_vs_g4151() -> None:
    a = build_embed_text(_without_marker(PANEL[5]))   # G2316 theos
    b = build_embed_text(_without_marker(PANEL[9]))   # G4151 pneuma
    tok_a = set(a.split())
    tok_b = set(b.split())
    union = tok_a | tok_b
    jaccard = len(tok_a & tok_b) / len(union) if union else 0.0
    assert jaccard < 0.5


def test_deterministic() -> None:
    row = _without_marker(PANEL[0])
    a = build_embed_text(row)
    b = build_embed_text(dict(row))
    assert a == b


def test_non_empty_for_minimal_valid_row() -> None:
    minimal = {"lemma": "α", "transliteration": "alpha", "gloss": "first"}
    text = build_embed_text(minimal)
    assert text != ""
    assert "α" in text and "alpha" in text and "first" in text


def test_empty_row_yields_empty_string() -> None:
    assert build_embed_text({}) == ""


def test_truncates_at_cap() -> None:
    row = {
        "lemma": "X",
        "transliteration": "Y",
        "gloss": "z " * 10_000,
        "pos": "noun",
        "domain": "test",
    }
    text = build_embed_text(row)
    assert len(text) <= EMBED_TEXT_MAX_LEN


def test_skips_redundant_transliteration_equal_to_lemma() -> None:
    row = {"lemma": "alpha", "transliteration": "alpha", "gloss": "first"}
    text = build_embed_text(row)
    assert text.count("alpha") == 1


def test_handles_missing_optional_fields() -> None:
    row = {"lemma": "X", "transliteration": "Y", "gloss": "Z"}
    text = build_embed_text(row)
    assert "X" in text and "Y" in text and "Z" in text
    assert "pos" not in text and "domain" not in text


@pytest.mark.parametrize("row", PANEL, ids=[r["strong"] for r in PANEL])  # type: ignore[arg-type]
def test_no_panel_text_is_empty(row: dict[str, object]) -> None:
    assert build_embed_text(_without_marker(row)).strip() != ""


def test_pairwise_jaccard_within_panel_mostly_below_threshold() -> None:
    texts = [build_embed_text(_without_marker(r)).split() for r in PANEL]
    bad = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            tok_i = set(texts[i])
            tok_j = set(texts[j])
            union = tok_i | tok_j
            j_score = len(tok_i & tok_j) / len(union) if union else 0.0
            if j_score >= 0.5:
                bad += 1
    pairs = len(PANEL) * (len(PANEL) - 1) // 2
    assert bad / pairs < 0.1, (
        f"too many panel pairs above jaccard 0.5: {bad}/{pairs}"
    )
