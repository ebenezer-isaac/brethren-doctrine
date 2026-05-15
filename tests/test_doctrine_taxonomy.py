"""Tests for ingest.doctrine_taxonomy."""

from ingest.doctrine_taxonomy import COARSE_SLUGS, FINE_SLUGS, FINE_TO_COARSE


def test_fine_slugs_count() -> None:
    assert len(FINE_SLUGS) == 26


def test_coarse_slugs_count() -> None:
    assert len(COARSE_SLUGS) == 11


def test_fine_to_coarse_covers_every_fine_slug() -> None:
    assert set(FINE_TO_COARSE.keys()) == FINE_SLUGS


def test_every_value_in_coarse_slugs() -> None:
    assert set(FINE_TO_COARSE.values()) <= COARSE_SLUGS


def test_marker_slugs_map_to_theology_proper() -> None:
    assert FINE_TO_COARSE["cult-marker"] == "theology-proper"
    assert FINE_TO_COARSE["heterodoxy-marker"] == "theology-proper"


def test_bibliology_maps_to_scripture() -> None:
    assert FINE_TO_COARSE["bibliology"] == "scripture"


def test_ethics_fine_slugs_map_to_ethics() -> None:
    for slug in (
        "christian-ethics",
        "marriage-and-sexuality",
        "family-and-discipleship",
        "money-and-stewardship",
        "engagement-with-world",
        "calendar-and-customs",
    ):
        assert FINE_TO_COARSE[slug] == "ethics"
