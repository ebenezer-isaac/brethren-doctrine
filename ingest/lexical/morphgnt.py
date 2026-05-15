"""MorphGNT SBLGNT adapter (Pipeline 1).

Parses `<NN-Bk-morphgnt.txt>` files. Each line is space-delimited with 7 fields:
BBCCVV POS parsing text word_form normalized lemma.

Emits Word records with source `morphgnt-sblgnt`, plus PARSE_OF edges to the
matching MACULA Greek SBLGNT Word (same BCV + position). License is CC-BY-SA-4.0
(redistribute True with SA propagation).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "CC-BY-SA-4.0"
LICENSE_NOTE = "MorphGNT morphology CC-BY-SA-4.0; SBLGNT text under SBLGNT-EULA"
SOURCE_SLUG = "morphgnt-sblgnt"
ID_PREFIX = "morphgnt-sblgnt"

_OSIS_NT_NUM = {
    "01": "Matt",
    "02": "Mark",
    "03": "Luke",
    "04": "John",
    "05": "Acts",
    "06": "Rom",
    "07": "1Cor",
    "08": "2Cor",
    "09": "Gal",
    "10": "Eph",
    "11": "Phil",
    "12": "Col",
    "13": "1Thess",
    "14": "2Thess",
    "15": "1Tim",
    "16": "2Tim",
    "17": "Titus",
    "18": "Phlm",
    "19": "Heb",
    "20": "Jas",
    "21": "1Pet",
    "22": "2Pet",
    "23": "1John",
    "24": "2John",
    "25": "3John",
    "26": "Jude",
    "27": "Rev",
}


def _iter_file(txt_path: Path) -> Iterator[LexicalRecord]:
    last_ref: str | None = None
    pos = 0
    with txt_path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            bbccvv = parts[0]
            if len(bbccvv) != 6 or not bbccvv.isdigit():
                continue
            book_num = bbccvv[0:2]
            chap = int(bbccvv[2:4])
            verse = int(bbccvv[4:6])
            book = _OSIS_NT_NUM.get(book_num, book_num)
            ref = f"{book}.{chap}.{verse}"
            if ref != last_ref:
                last_ref = ref
                pos = 0
            pos += 1

            pos_tag = parts[1]
            parsing = parts[2]
            text = parts[3]
            normalized = parts[5] if len(parts) > 5 else ""
            lemma = parts[6] if len(parts) > 6 else ""

            word_id = f"{ID_PREFIX}:{ref}.w{pos:02d}"
            macula_id = f"macula-g:{ref}.w{pos:02d}"

            edges = [
                GraphEdge(to_id="source:SBLGNT", rel_type="FROM_EDITION", properties={}),
                GraphEdge(to_id=macula_id, rel_type="PARSE_OF", properties={}),
            ]
            yield LexicalRecord(
                record_type="Word",
                id=word_id,
                properties={
                    "ref": ref,
                    "book": book,
                    "chapter": chap,
                    "verse": verse,
                    "position": pos,
                    "surface": text,
                    "lemma": lemma,
                    "normalized": normalized,
                    "pos_tag": pos_tag,
                    "parsing": parsing,
                    "source": SOURCE_SLUG,
                },
                edges=edges,
                text_to_embed=text,
                license=LICENSE,
                redistribute=True,
                license_note=LICENSE_NOTE,
            )


def _iter_records(source_dir: Path) -> Iterator[LexicalRecord]:
    yield LexicalRecord(
        record_type="Variant",
        id="source:SBLGNT",
        properties={"edition": "SBLGNT", "kind": "Source"},
        license=LICENSE,
        redistribute=True,
        license_note=LICENSE_NOTE,
    )
    for txt_path in sorted(source_dir.glob("*-morphgnt.txt")):
        yield from _iter_file(txt_path)


def ingest_morphgnt(source_dir: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(source_dir))
    finally:
        driver.close()
