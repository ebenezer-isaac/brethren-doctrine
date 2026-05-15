"""STEPBible TAHOT / TAGNT / TVTMS adapter (Pipeline 1).

Parses Tagged Hebrew OT (TAHOT) and Tagged Greek NT (TAGNT) plus the
Versification mapping (TVTMS). Emits Word + Lemma records and writes a
parsed TVTMS file consumable by ingest.versification_mapper.VersificationMapper.

License is CC-BY-4.0 (redistribute True) for TAHOT/TAGNT/TVTMS. TTESV is
CC-BY-NC-4.0 (redistribute False) when present.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver, upsert_records
from ingest.models import GraphEdge, LexicalRecord

LICENSE_CCBY = "CC-BY-4.0"
LICENSE_NC = "CC-BY-NC-4.0"
LICENSE_NOTE_CCBY = "STEPBible CC BY 4.0"
LICENSE_NOTE_TTESV = "TTESV is Tyndale-NC, derivative work"

_REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)#(\d+)([=A-Za-z]*)$")
_STRONG_TOKEN_RE = re.compile(r"\{?H?G?\d+[A-Za-z]?\}?")


def _parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    m = _REF_RE.match(ref.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))


def _iter_word_records(
    text_path: Path, lang: str, source_slug: str, id_prefix: str
) -> Iterator[LexicalRecord]:
    lemma_seen: set[str] = set()
    with text_path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            parts = line.split("\t")
            ref = parts[0]
            parsed = _parse_ref(ref)
            if parsed is None:
                continue
            book, ch, vs, pos = parsed
            osis = f"{book}.{ch}.{vs}"
            word_id = f"{id_prefix}:{osis}.w{pos:02d}"
            surface = parts[1] if len(parts) > 1 else ""
            translit = parts[2] if len(parts) > 2 else ""
            translation = parts[3] if len(parts) > 3 else ""
            dstrongs = parts[4] if len(parts) > 4 else ""
            grammar = parts[5] if len(parts) > 5 else ""

            primary_strong = ""
            primary_suffix = None
            for tok in _STRONG_TOKEN_RE.findall(dstrongs):
                try:
                    primary_strong, primary_suffix = canonical_strongs(
                        tok, lang="hb" if lang == "hb" else "gk"
                    )
                    break
                except ValueError:
                    continue

            edges: list[GraphEdge] = []
            if primary_strong:
                lemma_id = f"lemma:{primary_strong}"
                edges.append(GraphEdge(to_id=lemma_id, rel_type="INSTANCE_OF", properties={}))
                if primary_strong not in lemma_seen:
                    lemma_seen.add(primary_strong)
                    yield LexicalRecord(
                        record_type="Lemma",
                        id=lemma_id,
                        properties={
                            "strong": primary_strong,
                            "suffix": primary_suffix,
                            "lang": lang,
                            "source": source_slug,
                        },
                        license=LICENSE_CCBY,
                        redistribute=True,
                        license_note=LICENSE_NOTE_CCBY,
                    )

            yield LexicalRecord(
                record_type="Word",
                id=word_id,
                properties={
                    "ref": osis,
                    "book": book,
                    "chapter": ch,
                    "verse": vs,
                    "position": pos,
                    "surface": surface,
                    "translit": translit,
                    "translation": translation,
                    "strong": primary_strong,
                    "morph": grammar,
                    "source": source_slug,
                },
                edges=edges,
                text_to_embed=f"{surface} {translation}".strip(),
                license=LICENSE_CCBY,
                redistribute=True,
                license_note=LICENSE_NOTE_CCBY,
            )


_OSIS_BK = {
    "english": ("Psa", "Psa"),
    "hebrew": ("Psa", "Psa"),
}


def _normalize_tvtms_ref(raw: str) -> str:
    """Convert `Psa.51:1` to `Psa.51.1`. Range-suffixes (e.g., `Psa.51:1-2`) → first verse."""
    raw = raw.strip().split(" ", 1)[0]
    raw = raw.split("-", 1)[0]
    raw = raw.replace(":", ".")
    return raw


def parse_tvtms(tvtms_path: Path, out_path: Path) -> int:
    """Extract OneToOne and SubdividedVerse rules; write tab-separated file. Returns rule count."""
    count = 0
    lines: list[str] = []
    with tvtms_path.open(encoding="utf-8-sig", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if "\t" not in line:
                continue
            cols = [c.strip() for c in line.split("\t")]
            if len(cols) < 3:
                continue
            rule = cols[0]
            if rule not in ("OneToOne", "SubdividedVerse"):
                continue
            nrsv_ref = cols[1] if len(cols) > 1 else ""
            heb_ref = cols[2] if len(cols) > 2 else ""
            if not nrsv_ref or not heb_ref:
                continue
            from_ref = _normalize_tvtms_ref(nrsv_ref)
            to_ref = _normalize_tvtms_ref(heb_ref)
            if "." in from_ref and "." in to_ref:
                lines.append(f"english\t{from_ref}\thebrew\t{to_ref}\t{rule}\t")
                count += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return count


def _iter_records(source_dir: Path) -> Iterator[LexicalRecord]:
    for tahot in sorted(source_dir.glob("TAHOT*.txt")):
        yield from _iter_word_records(tahot, "hb", "STEPBible-TAHOT", "stepbible-tahot")
    for tagnt in sorted(source_dir.glob("TAGNT*.txt")):
        yield from _iter_word_records(tagnt, "gk", "STEPBible-TAGNT", "stepbible-tagnt")


def ingest_stepbible(source_dir: Path, settings: Settings) -> dict[str, int]:
    tvtms_dir = source_dir / "Versification"
    tvtms_files = list(tvtms_dir.glob("TVTMS*.txt")) if tvtms_dir.exists() else []
    if tvtms_files:
        out_path = source_dir / "tvtms.parsed.json"
        parse_tvtms(tvtms_files[0], out_path)

    driver = get_lexical_driver(settings)
    try:
        return upsert_records(driver, _iter_records(source_dir))
    finally:
        driver.close()
