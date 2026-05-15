"""Treasury of Scripture Knowledge (TSK) cross-reference adapter (Pipeline 1).

Parses `tskxref.txt` (CrossWire-derived). Each line: book chapter verse seq
keyword refs. Refs are semicolon-separated `<abbr> <ch>:<vs>[,<vs>][-<vs>]`.

License: public_domain, redistribute True. Versification: KJV scheme;
remap via TVTMS on ingest where applicable.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE = "public_domain"
LICENSE_NOTE = "1880 Treasury of Scripture Knowledge, public domain"
SOURCE_SLUG = "tsk"

_TSK_BOOKS = [
    "",
    "Gen",
    "Exod",
    "Lev",
    "Num",
    "Deut",
    "Josh",
    "Judg",
    "Ruth",
    "1Sam",
    "2Sam",
    "1Kgs",
    "2Kgs",
    "1Chr",
    "2Chr",
    "Ezra",
    "Neh",
    "Esth",
    "Job",
    "Ps",
    "Prov",
    "Eccl",
    "Song",
    "Isa",
    "Jer",
    "Lam",
    "Ezek",
    "Dan",
    "Hos",
    "Joel",
    "Amos",
    "Obad",
    "Jonah",
    "Mic",
    "Nah",
    "Hab",
    "Zeph",
    "Hag",
    "Zech",
    "Mal",
    "Matt",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Rom",
    "1Cor",
    "2Cor",
    "Gal",
    "Eph",
    "Phil",
    "Col",
    "1Thess",
    "2Thess",
    "1Tim",
    "2Tim",
    "Titus",
    "Phlm",
    "Heb",
    "Jas",
    "1Pet",
    "2Pet",
    "1John",
    "2John",
    "3John",
    "Jude",
    "Rev",
]

_ABBR_TO_OSIS = {
    "ge": "Gen",
    "ex": "Exod",
    "le": "Lev",
    "nu": "Num",
    "de": "Deut",
    "jos": "Josh",
    "jud": "Judg",
    "ru": "Ruth",
    "1sa": "1Sam",
    "2sa": "2Sam",
    "1ki": "1Kgs",
    "2ki": "2Kgs",
    "1ch": "1Chr",
    "2ch": "2Chr",
    "ezr": "Ezra",
    "ne": "Neh",
    "es": "Esth",
    "job": "Job",
    "ps": "Ps",
    "pr": "Prov",
    "ec": "Eccl",
    "so": "Song",
    "isa": "Isa",
    "jer": "Jer",
    "la": "Lam",
    "eze": "Ezek",
    "da": "Dan",
    "ho": "Hos",
    "joe": "Joel",
    "am": "Amos",
    "ob": "Obad",
    "jon": "Jonah",
    "mic": "Mic",
    "na": "Nah",
    "hab": "Hab",
    "zep": "Zeph",
    "hag": "Hag",
    "zec": "Zech",
    "mal": "Mal",
    "mt": "Matt",
    "mr": "Mark",
    "lu": "Luke",
    "joh": "John",
    "ac": "Acts",
    "ro": "Rom",
    "1co": "1Cor",
    "2co": "2Cor",
    "ga": "Gal",
    "eph": "Eph",
    "php": "Phil",
    "col": "Col",
    "1th": "1Thess",
    "2th": "2Thess",
    "1ti": "1Tim",
    "2ti": "2Tim",
    "tit": "Titus",
    "phm": "Phlm",
    "heb": "Heb",
    "jas": "Jas",
    "1pe": "1Pet",
    "2pe": "2Pet",
    "1jo": "1John",
    "2jo": "2John",
    "3jo": "3John",
    "jude": "Jude",
    "re": "Rev",
}

_REF_RE = re.compile(r"^([1-3]?[a-z]+)\s+(\d+):(\S+)$")


def _expand_ref(token: str) -> list[str]:
    """Expand 'pr 8:22-24' into ['Prov.8.22', 'Prov.8.23', 'Prov.8.24']. Returns OSIS refs."""
    token = token.strip().lower()
    m = _REF_RE.match(token)
    if not m:
        return []
    abbr = m.group(1)
    book = _ABBR_TO_OSIS.get(abbr)
    if not book:
        return []
    chap = int(m.group(2))
    verses_part = m.group(3)
    out: list[str] = []
    for chunk in verses_part.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            try:
                start, end = int(a), int(b)
                for v in range(start, end + 1):
                    out.append(f"{book}.{chap}.{v}")
            except ValueError:
                continue
        else:
            try:
                out.append(f"{book}.{chap}.{int(chunk)}")
            except ValueError:
                continue
    return out


def _iter_records(tsk_path: Path) -> Iterator[LexicalRecord]:
    verse_seen: set[str] = set()
    with tsk_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            try:
                book_num = int(parts[0])
                chap = int(parts[1])
                verse = int(parts[2])
                seq = int(parts[3])
            except ValueError:
                continue
            if book_num < 1 or book_num >= len(_TSK_BOOKS):
                continue
            book = _TSK_BOOKS[book_num]
            from_ref = f"{book}.{chap}.{verse}"
            from_id = f"verse:{from_ref}"
            keyword = parts[4]
            refs_field = parts[5]
            if from_id not in verse_seen:
                verse_seen.add(from_id)
                yield LexicalRecord(
                    record_type="Verse",
                    id=from_id,
                    properties={
                        "osisID": from_ref,
                        "book": book,
                        "chapter": chap,
                        "verse": verse,
                    },
                    license=LICENSE,
                    redistribute=True,
                    license_note="Verse stub",
                )
            for token in refs_field.split(";"):
                for to_ref in _expand_ref(token):
                    to_id = f"verse:{to_ref}"
                    if to_id not in verse_seen:
                        verse_seen.add(to_id)
                        toks = to_ref.split(".")
                        yield LexicalRecord(
                            record_type="Verse",
                            id=to_id,
                            properties={
                                "osisID": to_ref,
                                "book": toks[0],
                                "chapter": int(toks[1]),
                                "verse": int(toks[2]),
                            },
                            license=LICENSE,
                            redistribute=True,
                            license_note="Verse stub",
                        )
                    edge_id = f"cross:tsk:{from_ref}:{seq}:{to_ref}"
                    yield LexicalRecord(
                        record_type="CrossRef",
                        id=edge_id,
                        properties={
                            "from_ref": from_ref,
                            "to_ref": to_ref,
                            "source": SOURCE_SLUG,
                            "rank": seq,
                            "keyword": keyword,
                        },
                        edges=[
                            GraphEdge(
                                to_id=to_id,
                                rel_type="CROSS_REF",
                                properties={
                                    "source": SOURCE_SLUG,
                                    "rank": seq,
                                    "license": LICENSE,
                                    "redistribute": True,
                                },
                            )
                        ],
                        license=LICENSE,
                        redistribute=True,
                        license_note=LICENSE_NOTE,
                    )


def ingest_tsk(tsk_path: Path, settings: Settings) -> dict[str, int]:
    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(tsk_path))
    finally:
        driver.close()
