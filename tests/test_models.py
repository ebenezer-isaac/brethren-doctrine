"""Tests for ingest.models."""

import unicodedata
from typing import get_args

import pytest
from pydantic import ValidationError

from ingest.models import (
    TRADITION_VALUES,
    CulturalChunk,
    CulturalChunkSource,
    DoctrineTag,
    GraphEdge,
    LexicalRecord,
    LicenseTag,
)


def _source(work_id: str = "ccc", is_confessional: bool = True) -> CulturalChunkSource:
    return CulturalChunkSource(
        work_id=work_id,
        work_title="Test Work",
        author="Author",
        date_written="2025",
        is_confessional_text=is_confessional,
        anchor_id="Gen.1.1",
        language="en",
        translator=None,
    )


def _doctrine_tag(**kwargs: object) -> DoctrineTag:
    base = {
        "doctrine_coarse": "scripture",
        "doctrine_fine": "bibliology",
        "stance": "affirms",
        "confidence": 0.9,
        "evidence_phrase": "Scripture is the inspired word of God.",
    }
    base.update(kwargs)
    return DoctrineTag(**base)  # type: ignore[arg-type]


def _cultural_chunk(**kwargs: object) -> CulturalChunk:
    base = {
        "chunk_id": "chunk-1",
        "tradition": "reformed",
        "source": _source(work_id="wcf", is_confessional=True),
        "doctrine_tags": [],
        "text": "Test text.",
        "text_to_embed": "Test text.",
        "license": "public_domain",
        "redistribute": True,
        "license_note": None,
    }
    base.update(kwargs)
    return CulturalChunk(**base)  # type: ignore[arg-type]


def test_license_tag_minimal() -> None:
    t = LicenseTag(license="public_domain", redistribute=True)
    assert t.license == "public_domain"


def test_license_tag_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        LicenseTag(license="public_domain", redistribute=True, extra_field="x")  # type: ignore[call-arg]


def test_license_tag_frozen() -> None:
    t = LicenseTag(license="public_domain", redistribute=True)
    with pytest.raises(ValidationError):
        t.license = "CC-BY"  # type: ignore[misc]


def test_graph_edge_minimal() -> None:
    e = GraphEdge(to_id="n1", rel_type="NEXT")
    assert e.to_id == "n1"
    assert e.rel_type == "NEXT"


def test_graph_edge_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        GraphEdge(to_id="n1", rel_type="NEXT", weight=1.0)  # type: ignore[call-arg]


def test_lexical_record_minimal() -> None:
    r = LexicalRecord(
        record_type="Word",
        id="w-1",
        properties={"surface": "alpha"},
        license="public_domain",
        redistribute=True,
    )
    assert r.record_type == "Word"


def test_lexical_record_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        LexicalRecord(
            record_type="Word",
            id="w-1",
            properties={},
            license="public_domain",
            redistribute=True,
            bogus_field=1,  # type: ignore[call-arg]
        )


def test_lexical_record_invalid_record_type() -> None:
    with pytest.raises(ValidationError):
        LexicalRecord(
            record_type="NotAType",  # type: ignore[arg-type]
            id="w-1",
            properties={},
            license="public_domain",
            redistribute=True,
        )


def test_cultural_chunk_source_minimal() -> None:
    s = _source()
    assert s.work_id == "ccc"


def test_cultural_chunk_source_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        CulturalChunkSource(
            work_id="ccc",
            work_title="X",
            author=None,
            date_written="2025",
            is_confessional_text=True,
            anchor_id="Gen.1.1",
            language="en",
            unknown_field=1,  # type: ignore[call-arg]
        )


def test_doctrine_tag_minimal() -> None:
    t = _doctrine_tag()
    assert t.doctrine_fine == "bibliology"


def test_doctrine_tag_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        _doctrine_tag(extra=1)


def test_doctrine_tag_confidence_below_zero() -> None:
    with pytest.raises(ValidationError):
        _doctrine_tag(confidence=-0.1)


def test_doctrine_tag_confidence_zero_ok() -> None:
    assert _doctrine_tag(confidence=0.0).confidence == 0.0


def test_doctrine_tag_confidence_half_ok() -> None:
    assert _doctrine_tag(confidence=0.5).confidence == 0.5


def test_doctrine_tag_confidence_one_ok() -> None:
    assert _doctrine_tag(confidence=1.0).confidence == 1.0


def test_doctrine_tag_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        _doctrine_tag(confidence=1.1)


def test_doctrine_tag_evidence_phrase_max_chars() -> None:
    with pytest.raises(ValidationError):
        _doctrine_tag(evidence_phrase="x" * 501)


def test_doctrine_tag_evidence_phrase_29_words_ok() -> None:
    phrase = " ".join(["w"] * 29)
    assert _doctrine_tag(evidence_phrase=phrase).evidence_phrase == phrase


def test_doctrine_tag_evidence_phrase_30_words_ok() -> None:
    phrase = " ".join(["w"] * 30)
    assert _doctrine_tag(evidence_phrase=phrase).evidence_phrase == phrase


def test_doctrine_tag_evidence_phrase_31_words_raises() -> None:
    phrase = " ".join(["w"] * 31)
    with pytest.raises(ValidationError, match="30 words"):
        _doctrine_tag(evidence_phrase=phrase)


def test_doctrine_tag_fine_must_be_in_taxonomy() -> None:
    with pytest.raises(ValidationError, match="not in taxonomy"):
        _doctrine_tag(doctrine_fine="not-a-real-slug")


def test_doctrine_tag_fine_valid_slug() -> None:
    assert _doctrine_tag(doctrine_fine="cult-marker").doctrine_fine == "cult-marker"


def test_cultural_chunk_minimal() -> None:
    c = _cultural_chunk()
    assert c.chunk_id == "chunk-1"


def test_cultural_chunk_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        _cultural_chunk(unknown_field=1)


def test_cultural_chunk_doctrine_tags_max_5() -> None:
    tags = [_doctrine_tag() for _ in range(6)]
    with pytest.raises(ValidationError):
        _cultural_chunk(doctrine_tags=tags)


def test_cultural_chunk_doctrine_tags_5_ok() -> None:
    tags = [_doctrine_tag() for _ in range(5)]
    assert len(_cultural_chunk(doctrine_tags=tags).doctrine_tags) == 5


def test_tradition_values_count() -> None:
    assert len(get_args(TRADITION_VALUES)) == 12


def test_tradition_values_includes_plymouth_brethren() -> None:
    assert "plymouth-brethren" in get_args(TRADITION_VALUES)


def test_cultural_chunk_text_nfc_normalized() -> None:
    decomposed = "café"
    composed = unicodedata.normalize("NFC", decomposed)
    c = _cultural_chunk(text=decomposed, text_to_embed=composed)
    assert c.text == composed


def test_cultural_chunk_text_curly_quotes_preserved() -> None:
    text = "He said “word”"
    c = _cultural_chunk(text=text, text_to_embed=text)
    assert "“" in c.text
    assert "”" in c.text


def test_cultural_chunk_warns_on_ccc_non_confessional_magisterial() -> None:
    with pytest.warns(UserWarning, match="Audit the confessional flag"):
        _cultural_chunk(
            tradition="catholic-magisterial",
            source=_source(work_id="ccc", is_confessional=False),
        )


def test_cultural_chunk_no_warning_on_blog_post() -> None:
    import warnings as warnings_mod

    with warnings_mod.catch_warnings():
        warnings_mod.simplefilter("error")
        _cultural_chunk(
            tradition="catholic-magisterial",
            source=_source(work_id="some-blog-post", is_confessional=False),
        )


def test_cultural_chunk_no_warning_on_ccc_confessional_true() -> None:
    import warnings as warnings_mod

    with warnings_mod.catch_warnings():
        warnings_mod.simplefilter("error")
        _cultural_chunk(
            tradition="catholic-magisterial",
            source=_source(work_id="ccc", is_confessional=True),
        )


def test_cultural_chunk_empty_text_rejected() -> None:
    with pytest.raises(ValidationError):
        _cultural_chunk(text="")


def test_cultural_chunk_empty_text_to_embed_rejected() -> None:
    with pytest.raises(ValidationError):
        _cultural_chunk(text_to_embed="")
