"""Unit tests for Pipeline 1 adapter parsing logic.

QUARANTINE NOTICE (verifier caste, [SCHEMA-REVISION] reconciliation):
  18 of the 20 cases below are dead scaffolding and are skipped with a
  reason. They were written against private record-iterator APIs that the
  per-source adapter refactor removed or renamed, and against the
  ingest.lexical.stepbible module that was deliberately quarantined for the
  int(pos) -> f'{pos:02d}' canonical-overwrite defect.

  - 16 cases reference private functions/constants that no longer exist on
    the current adapter modules (e.g. oshb._iter_records,
    tsk._TSK_BOOKS now _OSIS_BOOKS, openbible._expand_to_verses,
    macula_hebrew._word_records, macula_greek._iter_records,
    morphgnt._iter_records, theographic._explode_verses /
    theographic._iter_records). They raise AttributeError, are
    pre-existing (not a [SCHEMA-REVISION] regression; 76ad53f touched only
    stepbible.py), and every adapter they targeted now has a dedicated
    live tests/lexical/test_<adapter>_coverage.py suite that exercises the
    real entry function through the FakeDriver harness. They provide NO
    live coverage that the 23 coverage suites do not already provide.
    Evidence: docs/AUDIT_phase_d_preflight_verification.md (lines 244-250),
    docs/PHASE_D_CATALOG_RECONCILIATION.md.
  - 2 cases (test_stepbible_parses_tahot_line,
    test_stepbible_parses_tvtms_psa_51) hit the intended
    ingest.lexical.stepbible quarantine guard and raise RuntimeError by
    design. Reviving that module is forbidden; the faithful per-source
    adapters (stepbible_tahot / _tagnt / _ttesv / _tvtms / ...) replace it.
    Evidence: docs/AUDIT_phase_d_preflight_verification.md (lines 224-243).

  The 2 remaining cases (test_assert_counts_match_passes /
  test_assert_counts_match_raises) exercise the LIVE public API
  ingest.lexical._common.assert_counts_match and are kept running. The
  file is therefore retained, not deleted, so that live coverage is
  preserved.

Tests exercise the private record-iterators against small hand-crafted fixtures
to verify license tagging, ID namespacing, and structural correctness without
touching live Neo4j.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest.lexical import (
    macula_greek,
    macula_hebrew,
    morphgnt,
    openbible,
    oshb,
    stepbible,
    theographic,
    tsk,
)

FIXTURES = Path(__file__).parent / "fixtures"

# Dead-scaffolding skip: 16 cases call private record-iterator APIs that the
# per-source adapter refactor removed or renamed. Pre-existing, not a
# [SCHEMA-REVISION] regression. The dedicated test_<adapter>_coverage.py
# suites provide the live coverage. See module docstring + audit docs.
_REMOVED_API_SKIP = pytest.mark.skip(
    reason=(
        "dead scaffolding: targets a private adapter API removed or renamed "
        "by the per-source adapter refactor (pre-existing AttributeError, not "
        "a [SCHEMA-REVISION] regression). Live coverage is in the dedicated "
        "tests/lexical/test_<adapter>_coverage.py suite. See "
        "docs/AUDIT_phase_d_preflight_verification.md lines 244-250."
    )
)

# Intended-quarantine skip: 2 cases hit the deliberate ingest.lexical.stepbible
# quarantine guard (the int(pos) -> {pos:02d} canonical-overwrite defect
# module). Reviving it is forbidden; faithful per-source adapters replace it.
_QUARANTINE_SKIP = pytest.mark.skip(
    reason=(
        "intended quarantine: ingest.lexical.stepbible is dead code that "
        "carried the int(pos) -> f'{pos:02d}' canonical-overwrite defect and "
        "raises RuntimeError by design. Use the faithful per-source adapters "
        "(stepbible_tahot / _tagnt / _ttesv / _tvtms). See "
        "docs/AUDIT_phase_d_preflight_verification.md lines 224-243."
    )
)


@_REMOVED_API_SKIP
def test_macula_hebrew_parses_gen_1_1(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "WLC" / "lowfat").mkdir(parents=True)
    target = src / "WLC" / "lowfat" / "01-Gen-001-lowfat.xml"
    target.write_text(
        (FIXTURES / "macula_hebrew_gen_1.xml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    records = list(macula_hebrew._word_records(src))
    words = [r for r in records if r.record_type == "Word"]
    assert len(words) == 4
    assert all(r.license == "CC-BY-NC-4.0" for r in words)
    assert all(r.redistribute is False for r in words)
    assert all(r.id.startswith("macula-h:") for r in words)
    strongs = [w.properties["strong"] for w in words]
    assert "H7225" in strongs
    assert "H1254" in strongs
    assert "H0430" in strongs


@_REMOVED_API_SKIP
def test_macula_hebrew_hebrew_greek_bridge_edges_emitted(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "WLC" / "lowfat").mkdir(parents=True)
    (src / "WLC" / "lowfat" / "01-Gen-001-lowfat.xml").write_text(
        (FIXTURES / "macula_hebrew_gen_1.xml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    records = list(macula_hebrew._word_records(src))
    bridge_edges = [e for r in records for e in r.edges if e.rel_type == "GLOSSES_GREEK_LEMMA"]
    assert len(bridge_edges) >= 1


@_REMOVED_API_SKIP
def test_openbible_expands_range() -> None:
    refs = openbible._expand_to_verses("Rom.1.18-Rom.1.20")
    assert refs == ["Rom.1.18", "Rom.1.19", "Rom.1.20"]


@_REMOVED_API_SKIP
def test_openbible_single_ref() -> None:
    refs = openbible._expand_to_verses("Gen.1.1")
    assert refs == ["Gen.1.1"]


@_REMOVED_API_SKIP
def test_openbible_invalid_ref_returns_empty() -> None:
    assert openbible._expand_to_verses("not a ref") == []


@_REMOVED_API_SKIP
def test_openbible_emits_crossref_records(tmp_path: Path) -> None:
    src = tmp_path / "openbible"
    src.mkdir()
    crf = src / "cross_references.txt"
    crf.write_text(
        "From Verse\tTo Verse\tVotes\n"
        "Gen.1.1\tRev.21.6\t56\n"
        "Rom.1.18\tRom.1.19-Rom.1.20\t10\n",
        encoding="utf-8",
    )
    records = list(openbible._iter_records(crf))
    crossrefs = [r for r in records if r.record_type == "CrossRef"]
    assert len(crossrefs) == 3
    assert all(r.license == "CC-BY" for r in crossrefs)
    assert all(r.redistribute is True for r in crossrefs)


@_REMOVED_API_SKIP
def test_tsk_book_table_has_66() -> None:
    assert len(tsk._TSK_BOOKS) == 67  # index 0 is empty


@_REMOVED_API_SKIP
def test_tsk_expand_simple() -> None:
    refs = tsk._expand_ref("pr 8:22")
    assert refs == ["Prov.8.22"]


@_REMOVED_API_SKIP
def test_tsk_expand_range() -> None:
    refs = tsk._expand_ref("pr 8:22-24")
    assert refs == ["Prov.8.22", "Prov.8.23", "Prov.8.24"]


@_REMOVED_API_SKIP
def test_tsk_expand_comma() -> None:
    refs = tsk._expand_ref("ps 33:6,9")
    assert refs == ["Ps.33.6", "Ps.33.9"]


@_REMOVED_API_SKIP
def test_tsk_iter_records(tmp_path: Path) -> None:
    tsk_file = tmp_path / "tsk.txt"
    tsk_file.write_text(
        "1\t1\t1\t2\tbeginning\tpr 8:22-24;joh 1:1-3\n" "1\t1\t1\t3\tGod\tex 20:11\n",
        encoding="utf-8",
    )
    records = list(tsk._iter_records(tsk_file))
    crossrefs = [r for r in records if r.record_type == "CrossRef"]
    assert len(crossrefs) == 7  # 3 + 3 + 1
    assert all(r.license == "public_domain" for r in crossrefs)


@_REMOVED_API_SKIP
def test_morphgnt_parses_john_1_1(tmp_path: Path) -> None:
    src = tmp_path / "morphgnt"
    src.mkdir()
    txt = src / "64-Jn-morphgnt.txt"
    txt.write_text(
        "040101 P- -------- Ἐν Ἐν ἐν ἐν\n"
        "040101 N- ----DSF- ἀρχῇ ἀρχῇ ἀρχῇ ἀρχή\n"
        "040101 V- 3IAI-S-- ἦν ἦν ἦν εἰμί\n",
        encoding="utf-8",
    )
    records = list(morphgnt._iter_records(src))
    words = [r for r in records if r.record_type == "Word"]
    assert len(words) == 3
    assert all(r.license == "CC-BY-SA-4.0" for r in words)
    assert all(r.id.startswith("morphgnt-sblgnt:John.1.1.w") for r in words)
    parse_of_edges = [e for r in records for e in r.edges if e.rel_type == "PARSE_OF"]
    assert len(parse_of_edges) == 3


@_REMOVED_API_SKIP
def test_oshb_splits_morphemes(tmp_path: Path) -> None:
    src = tmp_path / "oshb"
    (src / "wlc").mkdir(parents=True)
    xml = src / "wlc" / "Gen.xml"
    xml.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">'
        "<osisText>"
        '<div type="book" osisID="Gen"><chapter osisID="Gen.1">'
        '<verse osisID="Gen.1.1">'
        '<w lemma="b/7225" morph="HR/Ncfsa">בְּרֵאשִׁית</w>'
        '<w lemma="1254" morph="HVqp3ms">בָּרָא</w>'
        '<w lemma="430" morph="HNcmpa">אֱלֹהִים</w>'
        "</verse></chapter></div></osisText></osis>",
        encoding="utf-8",
    )
    records = list(oshb._iter_records(src))
    words = [r for r in records if r.record_type == "Word"]
    morphemes = [r for r in records if r.record_type == "Morpheme"]
    assert len(words) == 3
    assert len(morphemes) >= 3
    assert all(r.id.startswith("oshb:") for r in words)


@_REMOVED_API_SKIP
def test_macula_greek_parses_tsv_row(tmp_path: Path) -> None:
    src = tmp_path / "mg"
    (src / "SBLGNT" / "tsv").mkdir(parents=True)
    tsv = src / "SBLGNT" / "tsv" / "macula-greek-SBLGNT.tsv"
    header = "xml:id\tref\trole\tclass\ttype\tenglish\tmandarin\tgloss\ttext\tafter\tlemma\tnormalized\tstrong\tmorph\tperson\tnumber\tgender\tcase\ttense\tvoice\tmood\tdegree\tdomain\tln\tframe\tsubjref\treferent\n"
    row = "n40001001001\tMAT 1:1!1\t\tnoun\tcommon\tbook\t\t[The] book\tΒίβλος\t \tβίβλος\tΒίβλος\t976\tN-NSF\t\tsingular\tfeminine\tnominative\t\t\t\t\t033005\t33.38\t\t\t\n"
    tsv.write_text(header + row, encoding="utf-8")
    records = list(macula_greek._iter_records(src))
    words = [r for r in records if r.record_type == "Word"]
    assert len(words) == 1
    assert words[0].id.startswith("macula-g:Matt.1.1.w")
    assert words[0].license == "CC-BY-NC-4.0"
    assert words[0].redistribute is False


@_REMOVED_API_SKIP
def test_theographic_explode_verses() -> None:
    refs = theographic._explode_verses("Gen.1.1, Exod.2.3")
    assert refs == ["Gen.1.1", "Exod.2.3"]


@_REMOVED_API_SKIP
def test_theographic_people_record(tmp_path: Path) -> None:
    src = tmp_path / "theo"
    (src / "CSV").mkdir(parents=True)
    csv_file = src / "CSV" / "People.csv"
    csv_file.write_text(
        "personLookup,name,displayTitle,gender,birthYear,deathYear,verseCount,verses\n"
        "aaron_1,Aaron,Aaron,Male,-1574,-1451,64,Gen.1.1\n",
        encoding="utf-8",
    )
    records = list(theographic._iter_records(src))
    people = [r for r in records if r.record_type == "Person"]
    assert len(people) == 1
    assert people[0].id == "person:aaron_1"
    assert people[0].license == "CC-BY-SA-4.0"


@_QUARANTINE_SKIP
def test_stepbible_parses_tahot_line(tmp_path: Path) -> None:
    src = tmp_path / "step"
    src.mkdir()
    tahot = src / "TAHOT.txt"
    tahot.write_text(
        "Gen.1.1#01=L\tבְּ/רֵאשִׁ֖ית\tbe./re.Shit\tin/ beginning\tH9003/{H7225G}\tHR/Ncfsa\t\t\tH7225G\t\t\n"
        "Gen.1.1#02=L\tבָּרָ֣א\tba.Ra'\the created\t{H1254A}\tHVqp3ms\t\t\tH1254A\t\t\n",
        encoding="utf-8",
    )
    records = list(stepbible._iter_word_records(tahot, "hb", "STEPBible-TAHOT", "stepbible-tahot"))
    words = [r for r in records if r.record_type == "Word"]
    assert len(words) == 2
    assert all(r.license == "CC-BY-4.0" for r in words)
    assert all(r.redistribute is True for r in words)


@_QUARANTINE_SKIP
def test_stepbible_parses_tvtms_psa_51(tmp_path: Path) -> None:
    src = tmp_path / "step"
    src.mkdir()
    tvtms = src / "TVTMS.txt"
    tvtms.write_text(
        "Header line that should be ignored\n"
        "OneToOne\tPsa.51:1\tPsa.51:3\tPsa.50:3\tPsa.50:3\tPsa.51:1\tPsa.50:1\tPsa.50:1\n"
        "OneToOne\tJoel.2:28\tJoel.3:1\n",
        encoding="utf-8",
    )
    out = src / "tvtms.parsed.json"
    count = stepbible.parse_tvtms(tvtms, out)
    assert count == 2
    content = out.read_text(encoding="utf-8")
    assert "english\tPsa.51.1\thebrew\tPsa.51.3\tOneToOne" in content
    assert "english\tJoel.2.28\thebrew\tJoel.3.1\tOneToOne" in content


def test_assert_counts_match_passes() -> None:
    from ingest.lexical._common import assert_counts_match

    assert_counts_match({"Word": 305000}, {"Word": (300000, 320000)})


def test_assert_counts_match_raises() -> None:
    import pytest

    from ingest.lexical._common import assert_counts_match

    with pytest.raises(AssertionError, match="Word"):
        assert_counts_match({"Word": 50000}, {"Word": (300000, 320000)})
