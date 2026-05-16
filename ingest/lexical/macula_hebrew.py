"""MACULA Hebrew lexical adapter (Pipeline 1).

Parses lowfat TEI XML (`WLC/lowfat/<book>-<chapter>-lowfat.xml`). Emits
LexicalRecord instances: Word (per `<w>`), Lemma (deduplicated by Strong),
Verse (synthesized from `ref`), plus NEXT_WORD, HAS_WORD, INSTANCE_OF and
GLOSSES_GREEK_LEMMA bridge edges.

License is a composite: WLC text PD; OSHB morphology CC-BY-4.0; Clear syntax
CC-BY-4.0; MARBLE/SDBH word senses CC-BY-NC-4.0. Top-level license collapses
to the strictest: CC-BY-NC-4.0, redistribute=False.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-NC-4.0"
LICENSE_NOTE = "Composite: WLC PD; MACULA syntax CC-BY-4.0; MARBLE/SDBH CC-BY-NC-4.0"
SOURCE_SLUG = "macula-hebrew"
ID_PREFIX = "macula-h"

_OSIS_BOOK = {
    "GEN": "Gen",
    "EXO": "Exod",
    "LEV": "Lev",
    "NUM": "Num",
    "DEU": "Deut",
    "JOS": "Josh",
    "JDG": "Judg",
    "RUT": "Ruth",
    "1SA": "1Sam",
    "2SA": "2Sam",
    "1KI": "1Kgs",
    "2KI": "2Kgs",
    "1CH": "1Chr",
    "2CH": "2Chr",
    "EZR": "Ezra",
    "NEH": "Neh",
    "EST": "Esth",
    "JOB": "Job",
    "PSA": "Ps",
    "PRO": "Prov",
    "ECC": "Eccl",
    "SNG": "Song",
    "ISA": "Isa",
    "JER": "Jer",
    "LAM": "Lam",
    "EZK": "Ezek",
    "DAN": "Dan",
    "HOS": "Hos",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obad",
    "JON": "Jonah",
    "MIC": "Mic",
    "NAM": "Nah",
    "HAB": "Hab",
    "ZEP": "Zeph",
    "HAG": "Hag",
    "ZEC": "Zech",
    "MAL": "Mal",
}


def _parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    """Parse `GEN 1:1!1` → (Gen, 1, 1, 1) or `Gen 1:1!1` → same."""
    try:
        head, pos = ref.split("!", 1)
        book_raw, cv = head.strip().split(" ", 1)
        chap, verse = cv.split(":")
        book = _OSIS_BOOK.get(book_raw.upper(), book_raw)
        return book, int(chap), int(verse), int(pos)
    except (ValueError, KeyError):
        return None


def _iter_words(xml_path: Path) -> Iterator[dict[str, str]]:
    tree = etree.parse(str(xml_path))
    for w in tree.iter("w"):
        attrs = {k: v for k, v in w.attrib.items() if v}
        attrs["text"] = (w.text or "").strip()
        yield attrs


def _word_records(source_dir: Path) -> Iterator[LexicalRecord]:
    lemma_seen: set[str] = set()
    verse_seen: set[str] = set()
    lowfat_dir = source_dir / "WLC" / "lowfat"
    for xml_path in sorted(lowfat_dir.glob("*-lowfat.xml")):
        prev_word_id: str | None = None
        prev_verse_id: str | None = None
        for attrs in _iter_words(xml_path):
            ref = attrs.get("ref", "")
            parsed = _parse_ref(ref)
            if parsed is None:
                continue
            book, ch, vs, pos = parsed
            osis_ref = f"{book}.{ch}.{vs}"
            word_id = f"{ID_PREFIX}:{osis_ref}.w{pos:02d}"
            verse_id = f"verse:{osis_ref}"

            strong_raw = attrs.get("strongnumberx") or attrs.get("stronglemma") or ""
            try:
                strong, strong_suffix = canonical_strongs(strong_raw, lang="hb")
            except ValueError:
                strong, strong_suffix = "", None

            edges: list[GraphEdge] = []
            if prev_verse_id == verse_id and prev_word_id:
                edges.append(GraphEdge(to_id=prev_word_id, rel_type="NEXT_WORD", properties={}))
            edges.append(GraphEdge(to_id=verse_id, rel_type="IN_VERSE", properties={}))
            if strong:
                lemma_id = f"lemma:{strong}"
                edges.append(GraphEdge(to_id=lemma_id, rel_type="INSTANCE_OF", properties={}))
                if strong not in lemma_seen:
                    lemma_seen.add(strong)
                    yield LexicalRecord(
                        record_type="Lemma",
                        id=lemma_id,
                        properties={
                            "strong": strong,
                            "suffix": strong_suffix,
                            "lemma": attrs.get("lemma", ""),
                            "lang": "hb",
                            "source": SOURCE_SLUG,
                        },
                        text_to_embed=attrs.get("gloss", ""),
                        license=LICENSE,
                        redistribute=False,
                        license_note=LICENSE_NOTE,
                    )
            if attrs.get("greekstrong"):
                try:
                    greek_strong, _ = canonical_strongs(attrs["greekstrong"], lang="gk")
                except ValueError:
                    greek_strong = ""
                if greek_strong:
                    edges.append(
                        GraphEdge(
                            to_id=f"lemma:{greek_strong}",
                            rel_type="GLOSSES_GREEK_LEMMA",
                            properties={"greek_strong": greek_strong},
                        )
                    )

            if verse_id not in verse_seen:
                verse_seen.add(verse_id)
                yield LexicalRecord(
                    record_type="Verse",
                    id=verse_id,
                    properties={
                        "osisID": osis_ref,
                        "book": book,
                        "chapter": ch,
                        "verse": vs,
                    },
                    license="public_domain",
                    redistribute=True,
                    license_note="WLC base text",
                )

            yield LexicalRecord(
                record_type="Word",
                id=word_id,
                properties={
                    "ref": osis_ref,
                    "book": book,
                    "chapter": ch,
                    "verse": vs,
                    "position": pos,
                    "surface": attrs.get("text", ""),
                    "lemma": attrs.get("lemma", ""),
                    "strong": strong,
                    "morph": attrs.get("morph", ""),
                    "gloss": attrs.get("gloss", ""),
                    "sdbh": attrs.get("sdbh", ""),
                    "source": SOURCE_SLUG,
                },
                edges=edges,
                text_to_embed=f"{attrs.get('text', '')} {attrs.get('gloss', '')}".strip(),
                license=LICENSE,
                redistribute=False,
                license_note=LICENSE_NOTE,
            )
            prev_word_id = word_id
            prev_verse_id = verse_id


def ingest_macula_hebrew(source_dir: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _word_records(source_dir))
    finally:
        driver.close()
