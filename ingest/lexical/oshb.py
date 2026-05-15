"""OSHB MorphHB adapter (Pipeline 1).

Parses OSIS XML at `wlc/<book>.xml`. Each `<w>` element is a Hebrew word.
Slash-separated lemmas (`b/7225`) split into morphemes per OSHB convention.

License: WLC text PD, OSHB morphology CC-BY-4.0. Top-level CC-BY-4.0, redistribute True.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from lxml import etree  # type: ignore[import-untyped]

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-4.0"
LICENSE_NOTE = "OSHB morphology CC-BY-4.0; WLC base text PD"
SOURCE_SLUG = "oshb"
ID_PREFIX = "oshb"
NS = {"osis": "http://www.bibletechnologies.net/2003/OSIS/namespace"}


def _split_strongs(raw: str) -> list[str]:
    return [s for s in raw.replace(" ", "").split("/") if s]


def _iter_book(xml_path: Path) -> Iterator[LexicalRecord]:
    tree = etree.parse(str(xml_path))
    verse_seen: set[str] = set()
    for verse in tree.iter("{http://www.bibletechnologies.net/2003/OSIS/namespace}verse"):
        osis_id = verse.get("osisID")
        if not osis_id or "." not in osis_id:
            continue
        parts = osis_id.split(".")
        if len(parts) != 3:
            continue
        book, ch, vs = parts[0], int(parts[1]), int(parts[2])
        verse_id = f"verse:{osis_id}"
        if verse_id not in verse_seen:
            verse_seen.add(verse_id)
            yield LexicalRecord(
                record_type="Verse",
                id=verse_id,
                properties={"osisID": osis_id, "book": book, "chapter": ch, "verse": vs},
                license="public_domain",
                redistribute=True,
                license_note="WLC base text",
            )

        words = verse.findall(".//osis:w", NS)
        prev_word_id: str | None = None
        for pos, w in enumerate(words, start=1):
            surface = "".join(w.itertext()).strip()
            lemma = w.get("lemma", "")
            morph = w.get("morph", "")
            word_id = f"{ID_PREFIX}:{osis_id}.w{pos:02d}"

            strongs = _split_strongs(lemma)
            primary = strongs[-1] if strongs else ""
            try:
                strong, suffix = canonical_strongs(primary, lang="hb") if primary else ("", None)
            except ValueError:
                strong, _suffix = "", None

            edges: list[GraphEdge] = [
                GraphEdge(to_id=verse_id, rel_type="IN_VERSE", properties={}),
            ]
            if prev_word_id:
                edges.append(GraphEdge(to_id=prev_word_id, rel_type="NEXT_WORD", properties={}))
            for mpos, mstrong in enumerate(strongs, start=1):
                try:
                    morph_strong, _ = canonical_strongs(mstrong, lang="hb")
                except ValueError:
                    morph_strong = ""
                if morph_strong:
                    morpheme_id = f"oshb-morph:{osis_id}.w{pos:02d}.m{mpos:02d}"
                    yield LexicalRecord(
                        record_type="Morpheme",
                        id=morpheme_id,
                        properties={
                            "ref": osis_id,
                            "word_position": pos,
                            "morph_position": mpos,
                            "strong": morph_strong,
                            "source": SOURCE_SLUG,
                        },
                        license=LICENSE,
                        redistribute=True,
                        license_note=LICENSE_NOTE,
                    )
                    edges.append(
                        GraphEdge(to_id=morpheme_id, rel_type="HAS_MORPHEME", properties={})
                    )

            yield LexicalRecord(
                record_type="Word",
                id=word_id,
                properties={
                    "ref": osis_id,
                    "book": book,
                    "chapter": ch,
                    "verse": vs,
                    "position": pos,
                    "surface": surface,
                    "lemma": lemma,
                    "morph": morph,
                    "strong": strong,
                    "qere_or_ketiv": w.get("type", ""),
                    "source": SOURCE_SLUG,
                },
                edges=edges,
                text_to_embed=surface,
                license=LICENSE,
                redistribute=True,
                license_note=LICENSE_NOTE,
            )
            prev_word_id = word_id


def _iter_records(source_dir: Path) -> Iterator[LexicalRecord]:
    wlc_dir = source_dir / "wlc"
    for xml_path in sorted(wlc_dir.glob("*.xml")):
        yield from _iter_book(xml_path)


def ingest_oshb(source_dir: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(source_dir))
    finally:
        driver.close()
