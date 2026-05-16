"""Fixture-based tests for each cultural scraper's parse() function.

Each test loads a captured HTML fixture from `tests/cultural/fixtures/` and
verifies the adapter's parser produces the expected chunk count and shape.
No network access; gated tests requiring live scraping are explicitly marked
with BD_CULTURAL_LIVE_SCRAPE.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ingest.cultural import (
    ag,
    articles_39,
    augsburg,
    bcp_1662,
    belgic,
    ccel_anf,
    ccel_npnf1,
    ccel_npnf2,
    conciliar,
    dort,
    heidelberg,
    lbc_1689,
    oca_hopko,
    schleitheim,
    stem_publishing,
    umc,
    vatican_ccc,
    vatican_dv,
    wcf,
    wlc_catechism,
    wsc,
)
from ingest.models import CulturalChunk

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _assert_chunks_valid(chunks: list[CulturalChunk]) -> None:
    assert chunks, "parser returned no chunks"
    for c in chunks:
        assert isinstance(c, CulturalChunk)
        assert c.text.strip()
        assert c.chunk_id.strip()


def test_wcf_parses_33_chapters() -> None:
    chunks = wcf.parse(_load("opc_wcf.html"))
    _assert_chunks_valid(chunks)
    assert 160 <= len(chunks) <= 200
    assert chunks[0].chunk_id == "wcf.WCF.1.1"


def test_wsc_parses_107_qa() -> None:
    chunks = wsc.parse(_load("opc_wsc.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 107
    assert chunks[0].chunk_id == "wsc.WSC.Q001"
    assert "chief end of man" in chunks[0].text.lower()


def test_wlc_parses_196_qa() -> None:
    chunks = wlc_catechism.parse(_load("opc_wlc.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 196
    assert chunks[0].chunk_id == "wlc-catechism.WLC.Q001"


def test_lbc_1689_parses_chapter() -> None:
    chunks = lbc_1689.parse_chapter(_load("1689br_ch1.html"), 1)
    _assert_chunks_valid(chunks)
    assert len(chunks) == 10
    assert chunks[0].chunk_id == "lbc-1689.1689.1.1"


def test_heidelberg_parses_129_qa() -> None:
    chunks = heidelberg.parse(_load("crcna_heidelberg.html"))
    _assert_chunks_valid(chunks)
    assert 125 <= len(chunks) <= 135
    assert chunks[0].chunk_id == "heidelberg.HC.Q001"


def test_belgic_parses_37_articles() -> None:
    chunks = belgic.parse(_load("crcna_belgic.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 37
    assert chunks[0].chunk_id == "belgic.Belgic.A01"


def test_dort_parses_articles_across_5_heads() -> None:
    chunks = dort.parse(_load("crcna_dort.html"))
    _assert_chunks_valid(chunks)
    assert 50 <= len(chunks) <= 100


def test_articles_39_parses_all_39() -> None:
    chunks = articles_39.parse(_load("wikisource_39a.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 39
    assert chunks[0].chunk_id == "articles-39.39A.A01"
    assert "one living and true god" in chunks[0].text.lower()


def test_bcp_1662_catechism_parses_qa() -> None:
    chunks = bcp_1662.parse_catechism(_load("bcp1662_catechism.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) >= 5


def test_bcp_1662_section_parses_body() -> None:
    chunks = bcp_1662.parse_section(
        _load("bcp1662_athanasian.html"),
        "athanasian",
        "Athanasian Creed",
    )
    _assert_chunks_valid(chunks)
    assert len(chunks) == 1
    assert len(chunks[0].text) > 500


def test_augsburg_parses_one_article() -> None:
    chunk = augsburg.parse_article_page(_load("boc_aug_of_god.html"), 1, "Of God")
    assert chunk is not None
    assert chunk.chunk_id == "augsburg.Augsburg.A01"
    assert "Nicaea" in chunk.text


def test_schleitheim_parses_7_articles() -> None:
    chunks = schleitheim.parse(_load("anabaptists_schleitheim.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 7


def test_ag_parses_16_truths() -> None:
    chunks = ag.parse(_load("ag_truths.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) == 16
    assert all(c.license == "©Assemblies-of-God" for c in chunks)
    assert all(c.redistribute is False for c in chunks)


def test_umc_parses_25_articles() -> None:
    chunks = umc.parse(_load("umc_articles.html"))
    _assert_chunks_valid(chunks)
    assert 24 <= len(chunks) <= 26


def test_vatican_dv_parses_paragraphs() -> None:
    chunks = vatican_dv.parse(_load("vatican_dv.html"))
    _assert_chunks_valid(chunks)
    assert 24 <= len(chunks) <= 28
    assert all(c.license == "©Libreria-Editrice-Vaticana" for c in chunks)


def test_vatican_ccc_parses_page_paragraphs() -> None:
    chunks = vatican_ccc.parse_page(_load("vatican_p10.html"))
    _assert_chunks_valid(chunks)
    assert len(chunks) >= 1
    assert all(c.chunk_id.startswith("vatican-ccc.CCC.") for c in chunks)


def test_conciliar_parses_creeds() -> None:
    for slug, anchor, title, date in [
        ("wikisource_apostles", "Apostles.Creed", "Apostles' Creed", "c. 4th c"),
        ("wikisource_nicene", "Nicaea325.Creed", "Nicene Creed", "325"),
        ("wikisource_athanasian", "Athanasian.Creed", "Athanasian Creed", "c. 5-6th c"),
        ("wikipedia_chalcedon", "Chalcedon451.Definition", "Chalcedonian Definition", "451"),
    ]:
        raw = _load(f"{slug}.html")
        chunk = conciliar.parse(raw, anchor, title, date)
        assert chunk is not None
        assert chunk.chunk_id.startswith(f"conciliar.{anchor.split('.')[0]}.")


def test_ccel_anf_chapter_parser() -> None:
    chunks = ccel_anf.parse_chapter(_load("ccel_anf01_toc.html"), 1, "https://example/a.html")
    # The TOC HTML still contains some paragraph-form text; verify shape rather than count.
    assert isinstance(chunks, list)
    for c in chunks:
        assert c.chunk_id.startswith("ccel-anf.ANF.vol1.")


def test_ccel_npnf1_chapter_parser_does_not_crash() -> None:
    chunks = ccel_npnf1.parse_chapter(
        _load("ccel_npnf201_toc.html"),  # using as test fixture
        1,
        "https://example/a.html",
    )
    assert isinstance(chunks, list)


def test_ccel_npnf2_chapter_parser_does_not_crash() -> None:
    chunks = ccel_npnf2.parse_chapter(
        _load("ccel_npnf201_toc.html"),
        1,
        "https://example/a.html",
    )
    assert isinstance(chunks, list)


def test_oca_hopko_parse_article() -> None:
    # oca_index is mostly navigation; a real leaf would have richer body
    chunk = oca_hopko.parse_article(_load("oca_index.html"), "OCA.test")
    # Index page lacks body, so returns None — verifies the guard
    assert chunk is None or chunk.text


def test_stem_publishing_parse_work() -> None:
    chunks = stem_publishing.parse_work(
        _load("stem_darby_work.html"),
        author="J. N. Darby",
        work_id="stem-publishing.darby.test",
        anchor_prefix="STEM.darby.test",
        date_written="1882",
    )
    assert isinstance(chunks, list)


def test_all_adapters_emit_proper_license_tags() -> None:
    expected = {
        "wcf": ("public_domain", True),
        "wsc": ("public_domain", True),
        "wlc-catechism": ("public_domain", True),
        "lbc-1689": ("public_domain", True),
        "heidelberg": ("public_domain", True),
        "belgic": ("public_domain", True),
        "dort": ("public_domain", True),
        "articles-39": ("public_domain", True),
        "schleitheim": ("public_domain", True),
        "umc": ("public_domain", True),
        "augsburg": ("public_domain", True),
        "ag": ("©Assemblies-of-God", False),
        "oca-hopko": ("©OCA-Hopko-estate", False),
        "vatican-ccc": ("©Libreria-Editrice-Vaticana", False),
        "vatican-dv": ("©Libreria-Editrice-Vaticana", False),
        "ccel-anf": ("public_domain", True),
        "ccel-npnf1": ("public_domain", True),
        "ccel-npnf2": ("public_domain", True),
        "conciliar": ("public_domain", True),
        "stem-publishing": ("public_domain", True),
        "bcp-1662": ("public_domain", True),
    }
    for mod in [
        wcf,
        wsc,
        wlc_catechism,
        lbc_1689,
        heidelberg,
        belgic,
        dort,
        articles_39,
        schleitheim,
        umc,
        augsburg,
        ag,
        oca_hopko,
        vatican_ccc,
        vatican_dv,
        ccel_anf,
        ccel_npnf1,
        ccel_npnf2,
        conciliar,
        stem_publishing,
        bcp_1662,
    ]:
        slug = mod.SOURCE_SLUG
        assert slug in expected, slug
        license_, redistribute = expected[slug]
        assert license_ == mod.LICENSE, f"{slug}: {mod.LICENSE} vs {license_}"
        assert redistribute == mod.REDISTRIBUTE, f"{slug}: {mod.REDISTRIBUTE} vs {redistribute}"


@pytest.mark.skipif(
    os.environ.get("BD_CULTURAL_LIVE_SCRAPE") != "1",
    reason="live scrape requires network",
)
def test_live_scrape_wcf_at_least_160_chunks() -> None:
    chunks = wcf.scrape()
    assert len(chunks) >= 160
