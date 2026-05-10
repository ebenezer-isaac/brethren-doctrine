"""Locks the STEPBible TAHOT/TAGNT parser against fixture samples.

Fixtures in tests/fixtures/ are small byte-range pulls from the actual
STEPBible-Data repo (CC BY 4.0). They contain the column-header preamble
plus the first few real data rows. If STEPBible changes its column layout
the fixtures will need refreshing — and these tests will surface the change
before the orchestrator runs.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from ingest.adapters.concordance_loader import (
    _iter_tagnt_tsv,
    _iter_tahot_tsv,
    _iter_tsk,
    _normalize_strongs_atom,
    _parse_stepbible_ref,
    _parse_tsk_ref_token,
    _expand_osis_range,
)

FIX = Path(__file__).parent / "fixtures"


def nfc(s: str | None) -> str | None:
    """NFC-normalize for comparing precomposed vs decomposed Unicode (Hebrew
    cantillation order, Greek polytonic variants)."""
    return unicodedata.normalize("NFC", s) if s else s


def test_tahot_parses_real_rows():
    rows = list(_iter_tahot_tsv(FIX / "TAHOT_sample.txt"))
    assert len(rows) >= 30, f"expected >=30 rows, got {len(rows)}"

    # Spot-check Gen.1.1#01: 'in/beginning' -> root H7225G
    first = next(r for r in rows if r.verse_osis == "Gen.1.1" and r.position == 1)
    assert first.strongs == "H7225G"
    assert nfc(first.lemma_form) == nfc("רֵאשִׁית")
    assert first.gloss == "beginning"
    assert first.transliteration == "be./re.Shit"
    assert first.language == "he"
    assert first.morph == "HR/Ncfsa"

    # Gen.1.1#02: 'created' -> H1254A
    second = next(r for r in rows if r.verse_osis == "Gen.1.1" and r.position == 2)
    assert second.strongs == "H1254A"
    assert nfc(second.lemma_form) == nfc("בָּרָא")

    # Gen.1.1#03: 'God' -> H430G
    third = next(r for r in rows if r.verse_osis == "Gen.1.1" and r.position == 3)
    assert third.strongs == "H430G"
    assert nfc(third.lemma_form) == nfc("אֱלֹהִים")

    # Token IDs are unique
    assert len({r.token_id for r in rows}) == len(rows)


def test_tagnt_parses_real_rows():
    rows = list(_iter_tagnt_tsv(FIX / "TAGNT_sample.txt"))
    assert len(rows) >= 30, f"expected >=30 rows, got {len(rows)}"

    # Spot-check Mat.1.1#01: G976, lemma βίβλος, gloss 'book'
    first = next(r for r in rows if r.verse_osis == "Matt.1.1" and r.position == 1)
    assert first.strongs == "G976"
    assert nfc(first.surface_form) == nfc("Βίβλος")
    assert nfc(first.lemma_form) == nfc("βίβλος")
    assert first.gloss == "book"
    assert first.transliteration == "Biblos"
    assert first.language == "gr"
    assert first.morph == "N-NSF"

    # Mat.1.1#03: G2424G
    third = next(r for r in rows if r.verse_osis == "Matt.1.1" and r.position == 3)
    assert third.strongs == "G2424G"
    assert nfc(third.lemma_form) == nfc("Ἰησοῦς")

    # Mat.1.1#04: G5547
    fourth = next(r for r in rows if r.verse_osis == "Matt.1.1" and r.position == 4)
    assert fourth.strongs == "G5547"


@pytest.mark.parametrize("raw,expected", [
    ("H07706", "H7706"),
    ("H7706", "H7706"),
    ("H7706a", "H7706a"),
    ("H7225G", "H7225G"),
    ("G3056", "G3056"),
    ("G0026", "G26"),
    ("G26", "G26"),
    ("", None),
    ("H9003/", None),
    ("garbage", None),
])
def test_normalize_strongs_atom(raw, expected):
    assert _normalize_strongs_atom(raw) == expected


@pytest.mark.parametrize("raw,lang,expected", [
    ("Gen.1.1#01=L", "he", ("Gen.1.1", 1)),
    ("Gen.1.1#07=L", "he", ("Gen.1.1", 7)),
    ("Mat.1.1#01=NKO", "gr", ("Matt.1.1", 1)),
    ("Rom.6.3#04=NKO", "gr", ("Rom.6.3", 4)),
    ("Exo.20.1#01=L", "he", ("Exod.20.1", 1)),
    ("", "he", None),
    ("nonsense", "he", None),
])
def test_parse_stepbible_ref(raw, lang, expected):
    assert _parse_stepbible_ref(raw, lang) == expected


def test_tagnt_uses_osis_book_codes():
    """Regression guard: STEPBible's actual TAGNT codes (Jhn, Mrk, Php, 1Jn,
    2Jn, 3Jn) must be mapped to OSIS standard (John, Mark, Phil, 1John, etc.).
    Without this mapping, OpenBible cross-references (which use OSIS standard)
    won't reconcile with token verse_osis values, breaking spider-map."""
    rows = list(_iter_tagnt_tsv(FIX / "TAGNT_sample.txt"))
    osis_books = {r.verse_osis.split(".")[0] for r in rows}
    forbidden_stepbible_codes = {"Jhn", "Mrk", "Php", "1Jn", "2Jn", "3Jn"}
    leak = osis_books & forbidden_stepbible_codes
    assert not leak, f"raw STEPBible codes leaked into OSIS verse_osis: {leak}"


def test_tahot_uses_osis_book_codes():
    """Same regression guard for OT: Ezk, Jol, Nam must be mapped to Ezek, Joel, Nah."""
    rows = list(_iter_tahot_tsv(FIX / "TAHOT_sample.txt"))
    osis_books = {r.verse_osis.split(".")[0] for r in rows}
    forbidden = {"Ezk", "Jol", "Nam"}
    leak = osis_books & forbidden
    assert not leak, f"raw STEPBible codes leaked into OSIS verse_osis: {leak}"


def test_skips_prefix_only_tokens():
    """TAHOT pure prefix/suffix entries (no {} root) must be skipped — they're
    syntactic particles, not lexical lemmas."""
    rows = list(_iter_tahot_tsv(FIX / "TAHOT_sample.txt"))
    # Every yielded row must have a root Strong's
    for r in rows:
        assert r.strongs.startswith("H")
        # H9000-range tags are syntactic prefix codes — should not appear as
        # the root lemma of any yielded row.
        n = int("".join(c for c in r.strongs if c.isdigit()))
        assert n < 9000, f"row {r.token_id} yielded prefix-tag root {r.strongs}"


# ----------------------------------------------------------------------------
# TSK parser tests
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("token,expected", [
    ("pr 8:22-24", ["Prov.8.22", "Prov.8.23", "Prov.8.24"]),
    ("ps 33:6,9", ["Ps.33.6", "Ps.33.9"]),
    ("ge 1:10,12,18,25,31", ["Gen.1.10", "Gen.1.12", "Gen.1.18", "Gen.1.25", "Gen.1.31"]),
    ("joh 1:1-3", ["John.1.1", "John.1.2", "John.1.3"]),
    ("re 21:6", ["Rev.21.6"]),
    ("1jo 1:1", ["1John.1.1"]),
    ("heb 1:10", ["Heb.1.10"]),
    ("mr 13:19", ["Mark.13.19"]),
    ("", []),
    ("xyz 1:1", []),  # unknown abbrev
])
def test_parse_tsk_ref_token(token, expected):
    assert list(_parse_tsk_ref_token(token)) == expected


def test_iter_tsk_real_sample():
    """The canonical TSK file has 6 columns: book_key, ch, v, sort, word, refs.
    Gen.1.1 row #2 anchors on 'beginning' and references Pr 8:22-24, Pr 16:4,
    Mr 13:19, Joh 1:1-3, Heb 1:10, 1Jo 1:1."""
    rows = list(_iter_tsk(FIX / "TSK_sample.txt"))
    assert len(rows) > 20  # sample has 25 lines, each yielding multiple refs

    # Every src must be Gen.* (sample is from Genesis)
    for r in rows:
        assert r.src_osis.startswith("Gen.")
        assert r.weight == 1.0
        assert r.polarity == "parallel"

    # Spot-check: 'beginning' anchor on Gen.1.1 should produce Prov.8.22-24 + John.1.1-3 etc.
    beginning_targets = {r.dst_osis for r in rows
                         if r.src_osis == "Gen.1.1" and r.category == "beginning"}
    assert "Prov.8.22" in beginning_targets
    assert "Prov.8.23" in beginning_targets
    assert "Prov.8.24" in beginning_targets
    assert "John.1.1" in beginning_targets
    assert "John.1.2" in beginning_targets
    assert "John.1.3" in beginning_targets
    assert "Heb.1.10" in beginning_targets
    assert "1John.1.1" in beginning_targets


def test_expand_osis_range():
    """OpenBible verse-range expansion."""
    assert _expand_osis_range("Gen.1.1") == ["Gen.1.1"]
    assert _expand_osis_range("Prov.8.22-Prov.8.30") == [
        f"Prov.8.{v}" for v in range(22, 31)
    ]
    # Cross-chapter: endpoints only
    assert _expand_osis_range("Gen.1.1-Gen.2.4") == ["Gen.1.1", "Gen.2.4"]
