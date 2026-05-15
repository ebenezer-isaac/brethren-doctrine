"""MACULA Greek lexical adapter (Pipeline 1).

Parses `SBLGNT/tsv/macula-greek-SBLGNT.tsv` and `Nestle1904/tsv/*.tsv`.
Emits Word + Lemma records, plus Source nodes (`SBLGNT`, `Nestle1904`) with
FROM_EDITION edges. License composite: SBLGNT text under SBLGNT-EULA; syntax
CC-BY-4.0; Louw-Nida MARBLE CC-BY-NC-4.0. Top-level CC-BY-NC-4.0, redistribute False.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-NC-4.0"
LICENSE_NOTE = "Composite: SBLGNT-EULA; MACULA syntax CC-BY-4.0; MARBLE LN CC-BY-NC-4.0"

_OSIS_NT = {
    "MAT": "Matt",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Rom",
    "1CO": "1Cor",
    "2CO": "2Cor",
    "GAL": "Gal",
    "EPH": "Eph",
    "PHP": "Phil",
    "COL": "Col",
    "1TH": "1Thess",
    "2TH": "2Thess",
    "1TI": "1Tim",
    "2TI": "2Tim",
    "TIT": "Titus",
    "PHM": "Phlm",
    "HEB": "Heb",
    "JAS": "Jas",
    "1PE": "1Pet",
    "2PE": "2Pet",
    "1JN": "1John",
    "2JN": "2John",
    "3JN": "3John",
    "JUD": "Jude",
    "REV": "Rev",
}


def _parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    try:
        head, pos = ref.split("!", 1)
        book_raw, cv = head.strip().split(" ", 1)
        chap, verse = cv.split(":")
        book = _OSIS_NT.get(book_raw.upper(), book_raw)
        return book, int(chap), int(verse), int(pos)
    except (ValueError, KeyError):
        return None


def _iter_tsv_records(
    tsv_path: Path, source_slug: str, edition: str, id_prefix: str
) -> Iterator[LexicalRecord]:
    lemma_seen: set[str] = set()
    verse_seen: set[str] = set()
    yield LexicalRecord(
        record_type="Variant",
        id=f"source:{edition}",
        properties={"edition": edition, "kind": "Source"},
        license=LICENSE,
        redistribute=False,
        license_note=LICENSE_NOTE,
    )
    prev_word_id: str | None = None
    prev_verse_id: str | None = None
    with tsv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            ref = row.get("ref", "")
            parsed = _parse_ref(ref)
            if parsed is None:
                continue
            book, ch, vs, pos = parsed
            osis_ref = f"{book}.{ch}.{vs}"
            word_id = f"{id_prefix}:{osis_ref}.w{pos:02d}"
            verse_id = f"verse:{osis_ref}"

            strong_raw = row.get("strong", "")
            try:
                strong, suffix = canonical_strongs(strong_raw, lang="gk")
            except ValueError:
                strong, suffix = "", None

            edges: list[GraphEdge] = [
                GraphEdge(to_id=f"source:{edition}", rel_type="FROM_EDITION", properties={}),
                GraphEdge(to_id=verse_id, rel_type="IN_VERSE", properties={}),
            ]
            if prev_verse_id == verse_id and prev_word_id:
                edges.append(GraphEdge(to_id=prev_word_id, rel_type="NEXT_WORD", properties={}))

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
                            "suffix": suffix,
                            "lemma": row.get("lemma", ""),
                            "lang": "gk",
                            "source": source_slug,
                        },
                        text_to_embed=row.get("gloss", ""),
                        license=LICENSE,
                        redistribute=False,
                        license_note=LICENSE_NOTE,
                    )

            if verse_id not in verse_seen:
                verse_seen.add(verse_id)
                yield LexicalRecord(
                    record_type="Verse",
                    id=verse_id,
                    properties={"osisID": osis_ref, "book": book, "chapter": ch, "verse": vs},
                    license="public_domain",
                    redistribute=True,
                    license_note="Nestle1904 PD baseline; SBLGNT under EULA",
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
                    "surface": row.get("text", ""),
                    "lemma": row.get("lemma", ""),
                    "strong": strong,
                    "morph": row.get("morph", ""),
                    "gloss": row.get("gloss", ""),
                    "louw_nida_domain": row.get("domain", ""),
                    "source": source_slug,
                },
                edges=edges,
                text_to_embed=f"{row.get('text', '')} {row.get('gloss', '')}".strip(),
                license=LICENSE,
                redistribute=False,
                license_note=LICENSE_NOTE,
            )
            prev_word_id = word_id
            prev_verse_id = verse_id


def _iter_records(source_dir: Path) -> Iterator[LexicalRecord]:
    sblgnt = source_dir / "SBLGNT" / "tsv" / "macula-greek-SBLGNT.tsv"
    if sblgnt.exists():
        yield from _iter_tsv_records(sblgnt, "macula-greek-sblgnt", "SBLGNT", "macula-g")
    n1904_dir = source_dir / "Nestle1904" / "tsv"
    if n1904_dir.exists():
        for tsv_path in sorted(n1904_dir.glob("*.tsv")):
            yield from _iter_tsv_records(
                tsv_path, "macula-greek-N1904", "Nestle1904", "macula-g-n1904"
            )


def ingest_macula_greek(source_dir: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(source_dir))
    finally:
        driver.close()
