"""Concordance ingestion loaders.

Loads the spider-map data sources documented in docs/CONCORDANCE.md into
Neo4j as `:Lemma`, `:Token`, and cross-reference edges. Idempotent (Neo4j MERGE).

Sources (all CC BY 4.0 / public domain, see docs/CONCORDANCE.md):
- STEPBible TAHOT (Hebrew OT, ~423k tokens)
- STEPBible TAGNT (Greek NT, ~138k tokens)
- OSHB / MorphHB (Hebrew cross-validation, no writes — just diff logging)
- OpenBible.info cross-references (~340k vote-weighted)
- Treasury of Scripture Knowledge / scrollmapper (~500k public-domain)

Run order (one-time):
    python -m ingest.adapters.concordance_loader load-tahot   --src data/private/stepbible
    python -m ingest.adapters.concordance_loader load-tagnt   --src data/private/stepbible
    python -m ingest.adapters.concordance_loader cross-validate-oshb --src data/private/oshb
    python -m ingest.adapters.concordance_loader load-openbible --src data/private/openbible.tsv
    python -m ingest.adapters.concordance_loader load-tsk      --src data/private/tsk

Or:
    python -m ingest.adapters.concordance_loader load-all      --src data/private

Greenfield invariant: re-running any loader is safe (MERGE-based; same input
produces same graph state). To wipe and reload, drop the relevant labels in Cypher.

This module is WRITTEN as part of phase 1 (architecture rewrite) but NOT RUN
until the user gives explicit go-ahead. Ingestion is phase 1.5.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------
# Neo4j driver helpers
# ----------------------------------------------------------------------------

def _driver():
    """Returns a Neo4j driver from env vars NEO4J_URI / NEO4J_PASSWORD."""
    from neo4j import GraphDatabase  # type: ignore
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not pwd:
        raise RuntimeError("NEO4J_PASSWORD env var required")
    return GraphDatabase.driver(uri, auth=("neo4j", pwd))


def apply_constraints(driver) -> None:
    """Idempotent constraint creation. Run once before any loader.

    The Verse.verse_osis UNIQUE constraint is critical for throughput: without
    it, every MERGE (v:Verse {verse_osis: ...}) does a full label scan, which
    slows ingestion ~3.5x. Apply BEFORE loading.
    """
    cypher = [
        "CREATE CONSTRAINT lemma_strongs_uq IF NOT EXISTS "
        "FOR (l:Lemma) REQUIRE l.strongs IS UNIQUE",
        "CREATE CONSTRAINT token_id_uq IF NOT EXISTS "
        "FOR (t:Token) REQUIRE t.token_id IS UNIQUE",
        "CREATE CONSTRAINT verse_osis_uq IF NOT EXISTS "
        "FOR (v:Verse) REQUIRE v.verse_osis IS UNIQUE",
        "CREATE INDEX lemma_language IF NOT EXISTS "
        "FOR (l:Lemma) ON (l.language)",
        "CREATE INDEX token_verse IF NOT EXISTS "
        "FOR (t:Token) ON (t.verse_osis)",
    ]
    with driver.session() as s:
        for c in cypher:
            s.run(c)


# ----------------------------------------------------------------------------
# Records
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class TokenRow:
    """One word-token in the canonical text."""
    token_id: str          # e.g. 'Rom.6.3:4' (verse_osis : 1-indexed position)
    verse_osis: str        # 'Rom.6.3'
    position: int
    surface_form: str      # the inflected form
    strongs: str           # 'G3056' or 'H7706' (disambiguated where applicable)
    language: str          # 'gr' | 'he'
    morph: str             # raw morphology tag from source
    lemma_form: str | None         # dictionary form of the word
    transliteration: str | None
    gloss: str | None              # short English gloss


@dataclass(frozen=True)
class XrefRow:
    """One cross-reference edge."""
    src_osis: str          # 'Rom.6.3'
    dst_osis: str          # 'Col.2.12'
    weight: float          # OpenBible vote count, or 1.0 for TSK
    polarity: str          # 'supports' | 'contrasts' | 'parallel'
    category: str | None   # TSK classification (allusion, parallel, comparison, contrast)


# ----------------------------------------------------------------------------
# Upsert helpers
# ----------------------------------------------------------------------------

UPSERT_TOKEN = """
MERGE (l:Lemma {strongs: $strongs})
ON CREATE SET l.language = $language, l.lemma_form = $lemma_form,
              l.transliteration = $transliteration, l.gloss_short = $gloss
ON MATCH SET  l.lemma_form = coalesce(l.lemma_form, $lemma_form),
              l.transliteration = coalesce(l.transliteration, $transliteration),
              l.gloss_short = coalesce(l.gloss_short, $gloss)

MERGE (v:Verse {verse_osis: $verse_osis})
ON CREATE SET v.authority_level = 1

MERGE (t:Token {token_id: $token_id})
ON CREATE SET t.verse_osis = $verse_osis, t.position = $position,
              t.surface_form = $surface_form, t.morph = $morph,
              t.language = $language,
              t.authority_level = 1, t.created_at = datetime()
ON MATCH SET  t.surface_form = $surface_form, t.morph = $morph,
              t.language = $language, t.updated_at = datetime()

MERGE (t)-[:HAS_LEMMA]->(l)
MERGE (t)-[:OCCURS_IN]->(v)
MERGE (v)-[r:CONTAINS_TOKEN]->(t)
ON CREATE SET r.position = $position
"""

UPSERT_OPENBIBLE_XREF = """
MERGE (src:Verse {verse_osis: $src_osis})
ON CREATE SET src.authority_level = 1
MERGE (dst:Verse {verse_osis: $dst_osis})
ON CREATE SET dst.authority_level = 1
MERGE (src)-[r:OPENBIBLE_REF]->(dst)
ON CREATE SET r.weight = $weight, r.polarity = $polarity
ON MATCH SET  r.weight = $weight
"""

UPSERT_TSK_XREF = """
MERGE (src:Verse {verse_osis: $src_osis})
ON CREATE SET src.authority_level = 1
MERGE (dst:Verse {verse_osis: $dst_osis})
ON CREATE SET dst.authority_level = 1
MERGE (src)-[r:TSK_REF]->(dst)
ON CREATE SET r.category = $category
"""


def _batch_upsert_tokens(driver, rows: Iterator[TokenRow], batch_size: int = 500) -> int:
    count = 0
    batch: list[TokenRow] = []
    with driver.session() as session:
        def flush():
            nonlocal batch, count
            if not batch:
                return
            with session.begin_transaction() as tx:
                for r in batch:
                    tx.run(UPSERT_TOKEN, **r.__dict__)
                tx.commit()
            count += len(batch)
            batch = []
        for r in rows:
            batch.append(r)
            if len(batch) >= batch_size:
                flush()
                if count % 5000 == 0:
                    print(f"  ...{count} tokens upserted", file=sys.stderr)
        flush()
    return count


def _batch_upsert_xrefs(driver, rows: Iterator[XrefRow], cypher: str,
                       batch_size: int = 1000) -> int:
    count = 0
    batch: list[XrefRow] = []
    with driver.session() as session:
        def flush():
            nonlocal batch, count
            if not batch:
                return
            with session.begin_transaction() as tx:
                for r in batch:
                    tx.run(cypher, src_osis=r.src_osis, dst_osis=r.dst_osis,
                           weight=r.weight, polarity=r.polarity, category=r.category)
                tx.commit()
            count += len(batch)
            batch = []
        for r in rows:
            batch.append(r)
            if len(batch) >= batch_size:
                flush()
                if count % 10000 == 0:
                    print(f"  ...{count} xrefs upserted", file=sys.stderr)
        flush()
    return count


# ----------------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------------

# STEPBible TAHOT/TAGNT files are TSV with `$`-delimited records (per STEPBible
# README). Header lines begin with `#`. Per-word records have these columns:
#   English-Heb-Ref | Heb-Ref | Order | Type | Hebrew | Strongs | Lemma | Trans
#   | Gloss | English | Morph | Notes
# (TAGNT is structurally identical with Greek substitutions.)
#
# We extract: verse_osis (from English-Heb-Ref), position (from Order), Hebrew
# (surface_form), Strongs, Lemma, Trans, Gloss, Morph.

# Mapping from STEPBible's actual book-code prefixes to OSIS standard.
# Verified by enumerating distinct ^[1-9]?[A-Za-z]+\. prefixes in TAHOT/TAGNT
# files at github.com/STEPBible/STEPBible-Data (May 2026 snapshot). Codes
# already OSIS-standard (Gen, Lev, Mal, Rom, etc.) are identity-mapped via
# book_map.get(b, b) — they don't need explicit entries.

_TAHOT_BOOK_TO_OSIS = {
    "1Ch": "1Chr", "1Ki": "1Kgs", "1Sa": "1Sam",
    "2Ch": "2Chr", "2Ki": "2Kgs", "2Sa": "2Sam",
    "Amo": "Amos", "Deu": "Deut", "Ecc": "Eccl", "Est": "Esth",
    "Exo": "Exod", "Ezk": "Ezek", "Ezr": "Ezra",
    "Jdg": "Judg", "Jol": "Joel", "Jon": "Jonah", "Jos": "Josh",
    "Nam": "Nah", "Oba": "Obad", "Pro": "Prov", "Psa": "Ps",
    "Rut": "Ruth", "Sng": "Song", "Zec": "Zech", "Zep": "Zeph",
}

_TAGNT_BOOK_TO_OSIS = {
    "1Co": "1Cor", "1Jn": "1John", "1Pe": "1Pet", "1Th": "1Thess", "1Ti": "1Tim",
    "2Co": "2Cor", "2Jn": "2John", "2Pe": "2Pet", "2Th": "2Thess", "2Ti": "2Tim",
    "3Jn": "3John",
    "Act": "Acts", "Jhn": "John", "Jud": "Jude", "Luk": "Luke",
    "Mat": "Matt", "Mrk": "Mark", "Phm": "Phlm", "Php": "Phil", "Tit": "Titus",
}


def _normalize_strongs_atom(raw: str) -> str | None:
    """Normalize a single Strong's tag like 'H07706', 'H7706a', 'G3056' -> 'H7706a' / 'G3056'."""
    if not raw:
        return None
    m = re.match(r"^([HG])0*(\d+)([A-Za-z]?)$", raw.strip())
    if not m:
        return None
    return f"{m.group(1)}{m.group(2)}{m.group(3)}"


# TAHOT dStrongs may look like:
#   {H1254A}                  — root only
#   H9003/{H7225G}            — prefix + root
#   H9009/{H0776G}\H9016      — prefix + root + punctuation
#   H9002/H9009/{H0776G}      — multiple prefixes + root
# We extract the root Strong's (the one inside {}) and ignore prefix particles
# (H9000-range syntactic markers, not lexical lemmas) and punctuation tags.
_TAHOT_ROOT_RE = re.compile(r"\{(H\d+[A-Za-z]?)\}")


def _parse_stepbible_ref(ref: str, lang: str) -> tuple[str, int] | None:
    """Parse STEPBible reference like 'Gen.1.1#01=L' or 'Rom.6.3#04=NKO' -> (osis, position)."""
    if not ref:
        return None
    head = ref.strip().split("=", 1)[0]    # strip source-type suffix '=L', '=NKO', etc.
    parts = head.split("#")
    osis_part = parts[0]
    pos = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    seg = osis_part.split(".")
    if len(seg) < 3:
        return None
    book_short, chap, verse = seg[0], seg[1], seg[2]
    book_map = _TAHOT_BOOK_TO_OSIS if lang == "he" else _TAGNT_BOOK_TO_OSIS
    book = book_map.get(book_short, book_short)
    return f"{book}.{chap}.{verse}", pos


def _iter_tahot_tsv(path: Path) -> Iterator[TokenRow]:
    """Yield TokenRow per Hebrew word from a TAHOT TSV file.

    Column layout (tab-separated):
      0: Eng (Heb) Ref & Type   e.g. 'Gen.1.1#01=L'
      1: Hebrew                  e.g. 'בְּ/רֵאשִׁ֖ית'
      2: Transliteration         e.g. 'be./re.Shit'
      3: Translation             e.g. 'in/ beginning'
      4: dStrongs                e.g. 'H9003/{H7225G}'
      5: Grammar (morph)         e.g. 'HR/Ncfsa'
      6: Meaning variants
      7: Spelling variants
      8: Root sStrong+Instance   e.g. 'H7225G'
      9: Alt Strongs+Instance
     10: Conjoin word
     11: Expanded Strong tags    e.g. 'H9003=ב=in/{H7225G=רֵאשִׁית=:beginning»first}'

    Lines starting with '#' are header/interlinear-summary lines; skip them.
    Pure prefix/suffix tokens (no `{...}` root) are skipped — they are
    syntactic particles, not lexical lemmas.
    """
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line or line.startswith("#") or line.startswith("==="):
                continue
            cols = line.split("\t")
            if len(cols) < 6:
                continue
            ref = cols[0]
            parsed = _parse_stepbible_ref(ref, "he")
            if parsed is None:
                continue
            verse_osis, position = parsed
            surface = cols[1].strip()
            translit = (cols[2].strip() or None) if len(cols) > 2 else None
            dstrongs = cols[4] if len(cols) > 4 else ""
            morph = (cols[5].strip() if len(cols) > 5 else "") or ""
            sstrong_inst = (cols[8].strip() if len(cols) > 8 else "") or ""
            expanded = cols[11] if len(cols) > 11 else ""

            # Extract root Strong's from the {} in dStrongs
            root_match = _TAHOT_ROOT_RE.search(dstrongs)
            if not root_match:
                continue
            strongs = _normalize_strongs_atom(root_match.group(1))
            if strongs is None:
                continue

            # Best-effort lemma form + gloss extraction from expanded col, e.g.
            # 'H9003=ב=in/{H7225G=רֵאשִׁית=:beginning»first}'
            lemma_form = None
            gloss = None
            exp_match = re.search(r"\{H\d+[A-Za-z]?=([^=]+)=([^}]+)\}", expanded)
            if exp_match:
                lemma_form = exp_match.group(1).strip() or None
                # gloss may have ':...»...' decoration; take the first segment
                gloss_raw = exp_match.group(2).strip()
                gloss_clean = re.sub(r"^[:»]+", "", gloss_raw).split("»")[0].split(":")[0].strip()
                gloss = gloss_clean or None

            yield TokenRow(
                token_id=f"{verse_osis}:{position}",
                verse_osis=verse_osis,
                position=position,
                surface_form=surface,
                strongs=strongs,
                language="he",
                morph=morph,
                lemma_form=lemma_form,
                transliteration=translit,
                gloss=gloss,
            )


def _iter_tagnt_tsv(path: Path) -> Iterator[TokenRow]:
    """Yield TokenRow per Greek word from a TAGNT TSV file.

    Column layout (tab-separated):
      0: Word & Type             e.g. 'Mat.1.1#01=NKO'
      1: Greek (with translit)   e.g. 'Βίβλος (Biblos)'
      2: English translation     e.g. '[The] book'
      3: dStrongs = Grammar      e.g. 'G0976=N-NSF'
      4: Dictionary form = Gloss e.g. 'βίβλος=book'
      5: editions
      6: Meaning variants
      7: Spelling variants
      8: Spanish translation
      9: Sub-meaning
     10: Conjoin word
     11: sStrong+Instance        e.g. 'G0976'
     12: Alt Strongs

    Lines starting with '#' are header/interlinear-summary lines; skip.
    """
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line or line.startswith("#") or line.startswith("==="):
                continue
            cols = line.split("\t")
            if len(cols) < 5:
                continue
            ref = cols[0]
            parsed = _parse_stepbible_ref(ref, "gr")
            if parsed is None:
                continue
            verse_osis, position = parsed

            # Greek + transliteration: 'Βίβλος (Biblos)' -> surface='Βίβλος', translit='Biblos'
            greek_col = cols[1].strip()
            translit_match = re.match(r"^(\S+)\s*(?:\(([^)]+)\))?\s*$", greek_col)
            if translit_match:
                surface = translit_match.group(1)
                translit = translit_match.group(2)
            else:
                surface = greek_col
                translit = None

            # dStrongs = Grammar : 'G0976=N-NSF'
            ds_grammar = cols[3].strip() if len(cols) > 3 else ""
            ds_parts = ds_grammar.split("=", 1)
            strongs_raw = ds_parts[0]
            morph = ds_parts[1] if len(ds_parts) > 1 else ""
            strongs = _normalize_strongs_atom(strongs_raw)
            if strongs is None:
                continue

            # Dictionary form = Gloss : 'βίβλος=book'
            dict_gloss = cols[4].strip() if len(cols) > 4 else ""
            dg_parts = dict_gloss.split("=", 1)
            lemma_form = dg_parts[0].strip() or None if dg_parts[0] else None
            gloss = dg_parts[1].strip() if len(dg_parts) > 1 else None

            yield TokenRow(
                token_id=f"{verse_osis}:{position}",
                verse_osis=verse_osis,
                position=position,
                surface_form=surface,
                strongs=strongs,
                language="gr",
                morph=morph,
                lemma_form=lemma_form,
                transliteration=translit,
                gloss=gloss,
            )


_RANGE_RE = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)-([A-Za-z0-9]+)\.(\d+)\.(\d+)$")


def _expand_osis_range(osis: str) -> list[str]:
    """Expand an OpenBible OSIS range like 'Prov.8.22-Prov.8.30' into individual
    verse OSIS strings. Same-chapter ranges expand fully; cross-chapter ranges
    return endpoints only (full expansion would require canonical verse counts
    per chapter — punt for now, the endpoints are still usable as edges).
    """
    if "-" not in osis:
        return [osis]
    m = _RANGE_RE.match(osis)
    if not m:
        return [osis]
    book1, ch1, v1, book2, ch2, v2 = m.groups()
    if book1 == book2 and ch1 == ch2:
        v_start, v_end = int(v1), int(v2)
        if v_end < v_start or v_end - v_start > 50:
            return [f"{book1}.{ch1}.{v_start}", f"{book2}.{ch2}.{v_end}"]
        return [f"{book1}.{ch1}.{v}" for v in range(v_start, v_end + 1)]
    return [f"{book1}.{ch1}.{v1}", f"{book2}.{ch2}.{v2}"]


def _iter_openbible(path: Path) -> Iterator[XrefRow]:
    """Parse openbible.info cross-references TSV.

    Format: from_verse \\t to_verse \\t votes
    Verse ranges in the to_verse column are expanded into individual edges
    (~26% of openbible refs are ranges).
    """
    with path.open("r", encoding="utf-8") as fh:
        rdr = csv.reader(fh, delimiter="\t")
        for row in rdr:
            if not row or row[0].startswith("From"):
                continue
            if len(row) < 3:
                continue
            try:
                votes = int(row[2])
            except ValueError:
                continue
            for src in _expand_osis_range(row[0]):
                for dst in _expand_osis_range(row[1]):
                    yield XrefRow(
                        src_osis=src,
                        dst_osis=dst,
                        weight=float(votes),
                        polarity="parallel",
                        category=None,
                    )


# TSK book_key (1-66) → OSIS book code; verified against ariseshinestudio/TSK readme.
_TSK_BOOK_KEY_TO_OSIS = {
    1: "Gen", 2: "Exod", 3: "Lev", 4: "Num", 5: "Deut",
    6: "Josh", 7: "Judg", 8: "Ruth", 9: "1Sam", 10: "2Sam",
    11: "1Kgs", 12: "2Kgs", 13: "1Chr", 14: "2Chr",
    15: "Ezra", 16: "Neh", 17: "Esth", 18: "Job", 19: "Ps",
    20: "Prov", 21: "Eccl", 22: "Song", 23: "Isa", 24: "Jer",
    25: "Lam", 26: "Ezek", 27: "Dan", 28: "Hos", 29: "Joel",
    30: "Amos", 31: "Obad", 32: "Jonah", 33: "Mic", 34: "Nah",
    35: "Hab", 36: "Zeph", 37: "Hag", 38: "Zech", 39: "Mal",
    40: "Matt", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Rom", 46: "1Cor", 47: "2Cor", 48: "Gal", 49: "Eph",
    50: "Phil", 51: "Col", 52: "1Thess", 53: "2Thess",
    54: "1Tim", 55: "2Tim", 56: "Titus", 57: "Phlm", 58: "Heb",
    59: "Jas", 60: "1Pet", 61: "2Pet", 62: "1John", 63: "2John",
    64: "3John", 65: "Jude", 66: "Rev",
}

# TSK lowercase abbreviation → OSIS book code; from the canonical Torrey 1834 schema.
_TSK_ABBREV_TO_OSIS = {
    "ge": "Gen", "ex": "Exod", "le": "Lev", "nu": "Num", "de": "Deut",
    "jos": "Josh", "jud": "Judg", "ru": "Ruth",
    "1sa": "1Sam", "2sa": "2Sam", "1ki": "1Kgs", "2ki": "2Kgs",
    "1ch": "1Chr", "2ch": "2Chr", "ezr": "Ezra", "ne": "Neh", "es": "Esth",
    "job": "Job", "ps": "Ps", "pr": "Prov", "ec": "Eccl", "so": "Song",
    "isa": "Isa", "jer": "Jer", "la": "Lam", "eze": "Ezek", "da": "Dan",
    "ho": "Hos", "joe": "Joel", "am": "Amos", "ob": "Obad", "jon": "Jonah",
    "mic": "Mic", "na": "Nah", "hab": "Hab", "zep": "Zeph", "hag": "Hag",
    "zec": "Zech", "mal": "Mal",
    "mt": "Matt", "mr": "Mark", "lu": "Luke", "joh": "John", "ac": "Acts",
    "ro": "Rom", "1co": "1Cor", "2co": "2Cor", "ga": "Gal", "eph": "Eph",
    "php": "Phil", "col": "Col", "1th": "1Thess", "2th": "2Thess",
    "1ti": "1Tim", "2ti": "2Tim", "tit": "Titus", "phm": "Phlm",
    "heb": "Heb", "jas": "Jas", "1pe": "1Pet", "2pe": "2Pet",
    "1jo": "1John", "2jo": "2John", "3jo": "3John", "jude": "Jude", "re": "Rev",
}


def _parse_tsk_ref_token(token: str) -> Iterator[str]:
    """Parse a TSK reference like 'pr 8:22-24' or 'ge 1:10,12,18' or 'ps 33:6,9'
    into individual OSIS verse strings."""
    token = token.strip().lower()
    if not token:
        return
    parts = token.split(maxsplit=1)
    if len(parts) != 2:
        return
    abbrev, ref_part = parts[0], parts[1]
    osis_book = _TSK_ABBREV_TO_OSIS.get(abbrev)
    if not osis_book or ":" not in ref_part:
        return
    chap_str, verse_spec = ref_part.split(":", 1)
    try:
        chap = int(chap_str.strip())
    except ValueError:
        return
    for piece in verse_spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            try:
                start, end = piece.split("-", 1)
                start_v = int(start.strip())
                end_v = int(end.strip())
                if end_v < start_v or end_v - start_v > 80:
                    yield f"{osis_book}.{chap}.{start_v}"
                    yield f"{osis_book}.{chap}.{end_v}"
                else:
                    for v in range(start_v, end_v + 1):
                        yield f"{osis_book}.{chap}.{v}"
            except ValueError:
                continue
        else:
            try:
                yield f"{osis_book}.{chap}.{int(piece)}"
            except ValueError:
                continue


def _iter_tsk(path: Path) -> Iterator[XrefRow]:
    """Parse the canonical TSK tskxref.txt (Torrey 1834, public domain).

    Format: book_key\\tchapter\\tverse\\tsort_order\\tword\\treference_list
    reference_list is semicolon-separated tokens like 'pr 8:22-24;ps 33:6,9'.

    Each (source verse, anchor word) row produces one XrefRow per resolved
    target verse. category records the anchor word for downstream introspection.

    Encoding: TSK 1834 sometimes contains non-UTF-8 bytes (older typography,
    smart quotes, em-dashes). We open with errors='replace' to keep bad bytes
    from aborting the load — anchor-word fields may have a replacement char in
    rare cases but the structural fields (book_key/chapter/verse/refs) are
    always ASCII.
    """
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) < 6:
                continue
            try:
                book_key = int(cols[0])
                chap = int(cols[1])
                verse = int(cols[2])
            except ValueError:
                continue
            src_book = _TSK_BOOK_KEY_TO_OSIS.get(book_key)
            if not src_book:
                continue
            src_osis = f"{src_book}.{chap}.{verse}"
            anchor_word = cols[4].strip()
            ref_list = cols[5]
            for token in ref_list.split(";"):
                for dst_osis in _parse_tsk_ref_token(token):
                    yield XrefRow(
                        src_osis=src_osis,
                        dst_osis=dst_osis,
                        weight=1.0,
                        polarity="parallel",
                        category=anchor_word[:80] if anchor_word else None,
                    )


# ----------------------------------------------------------------------------
# Loader entry points
# ----------------------------------------------------------------------------

def _chained(*iters: Iterator[TokenRow]) -> Iterator[TokenRow]:
    for it in iters:
        yield from it


def load_tahot(src_dir: Path) -> int:
    """Load STEPBible TAHOT into Neo4j. Returns token count.

    TAHOT ships as 4 chunks (Gen-Deu, Jos-Est, Job-Sng, Isa-Mal). All are loaded.
    """
    candidates = sorted(list(src_dir.rglob("TAHOT*.txt")) + list(src_dir.rglob("TAHOT*.tsv")))
    candidates = [p for p in candidates if "OLD format" not in str(p)]
    if not candidates:
        raise FileNotFoundError(f"No TAHOT TSV under {src_dir}")
    print(f"loading TAHOT from {len(candidates)} files:", file=sys.stderr)
    for p in candidates:
        print(f"  {p.name}", file=sys.stderr)
    drv = _driver()
    apply_constraints(drv)
    iters = [_iter_tahot_tsv(p) for p in candidates]
    n = _batch_upsert_tokens(drv, _chained(*iters))
    drv.close()
    print(f"TAHOT: {n} tokens upserted", file=sys.stderr)
    return n


def load_tagnt(src_dir: Path) -> int:
    """Load STEPBible TAGNT into Neo4j. Returns token count.

    TAGNT ships as 2 chunks (Mat-Jhn, Act-Rev). Both are loaded.
    """
    candidates = sorted(list(src_dir.rglob("TAGNT*.txt")) + list(src_dir.rglob("TAGNT*.tsv")))
    if not candidates:
        raise FileNotFoundError(f"No TAGNT TSV under {src_dir}")
    print(f"loading TAGNT from {len(candidates)} files:", file=sys.stderr)
    for p in candidates:
        print(f"  {p.name}", file=sys.stderr)
    drv = _driver()
    apply_constraints(drv)
    iters = [_iter_tagnt_tsv(p) for p in candidates]
    n = _batch_upsert_tokens(drv, _chained(*iters))
    drv.close()
    print(f"TAGNT: {n} tokens upserted", file=sys.stderr)
    return n


def cross_validate_oshb(src_dir: Path, log_path: Path | None = None) -> int:
    """Cross-validate TAHOT (already loaded into Neo4j) against OSHB OSIS XML.

    Walks each OSHB book XML, counts words per verse, and diffs against the
    Token count per verse_osis in Neo4j. Logs per-verse divergences to
    logs/oshb_vs_tahot.diff. Returns the count of verses with divergence.

    A non-zero divergence count is INFORMATIONAL, not a hard failure: TAHOT and
    OSHB are independently maintained and minor differences (Qere/Ketiv, edition
    choices) are expected. A divergence rate above 5% suggests something is
    actually wrong with the loader, however.
    """
    print(f"cross-validating OSHB from {src_dir}", file=sys.stderr)
    log = log_path or (ROOT / "logs" / "oshb_vs_tahot.diff")
    log.parent.mkdir(exist_ok=True)

    try:
        from lxml import etree  # type: ignore
    except ImportError:
        msg = "lxml not installed; OSHB cross-validation skipped"
        log.write_text(f"# {msg}\n", encoding="utf-8")
        print(msg, file=sys.stderr)
        return 0

    wlc_dir = src_dir / "wlc"
    if not wlc_dir.is_dir():
        wlc_dir = next((p for p in src_dir.rglob("wlc") if p.is_dir()), None)
    if wlc_dir is None or not wlc_dir.is_dir():
        msg = f"OSHB wlc/ directory not found under {src_dir}"
        log.write_text(f"# {msg}\n", encoding="utf-8")
        print(msg, file=sys.stderr)
        return 0

    drv = _driver()
    ns = {"osis": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
    diffs: list[str] = []
    total_verses = 0

    with drv.session() as session:
        for xml_file in sorted(wlc_dir.glob("*.xml")):
            try:
                tree = etree.parse(str(xml_file))
            except Exception as e:
                diffs.append(f"# parse-error {xml_file.name}: {e}")
                continue
            root = tree.getroot()
            for verse_el in root.iter(f"{{{ns['osis']}}}verse"):
                osis_id = verse_el.get("osisID") or verse_el.get("sID")
                if not osis_id or "-" in osis_id:
                    continue
                w_elements = verse_el.findall(f".//{{{ns['osis']}}}w")
                oshb_count = len(w_elements)
                if oshb_count == 0:
                    continue
                total_verses += 1
                # Count Hebrew tokens for this verse via the HAS_LEMMA->Lemma path
                # (Token.language is set on new loads but the Lemma path is robust
                # against tokens loaded before that field was added).
                rec = session.run(
                    "MATCH (t:Token {verse_osis:$v})-[:HAS_LEMMA]->(l:Lemma {language:'he'}) "
                    "RETURN count(t) AS n",
                    v=osis_id,
                ).single()
                tahot_count = (rec or {}).get("n", 0) if rec else 0
                if abs(tahot_count - oshb_count) > 1:
                    diffs.append(
                        f"{osis_id}\tTAHOT={tahot_count}\tOSHB={oshb_count}"
                    )
    drv.close()

    header = [
        f"# OSHB vs TAHOT cross-validation",
        f"# verses_checked: {total_verses}",
        f"# verses_diverged: {len(diffs)}",
        f"# divergence_rate: {len(diffs)/total_verses*100:.2f}% (informational; not a failure)",
        "",
    ]
    log.write_text("\n".join(header + diffs), encoding="utf-8")
    print(
        f"OSHB cross-check: {total_verses} verses checked, {len(diffs)} divergent "
        f"({len(diffs)/total_verses*100:.2f}%) — see {log}",
        file=sys.stderr,
    )
    return len(diffs)


def load_openbible(src_path: Path) -> int:
    """Load openbible.info cross-references."""
    print(f"loading OpenBible refs from {src_path}", file=sys.stderr)
    drv = _driver()
    apply_constraints(drv)
    n = _batch_upsert_xrefs(drv, _iter_openbible(src_path), UPSERT_OPENBIBLE_XREF)
    drv.close()
    print(f"OpenBible: {n} xrefs upserted", file=sys.stderr)
    return n


def load_tsk(src_path: Path) -> int:
    """Load TSK cross-references from the canonical Torrey 1834 tskxref.txt
    (ariseshinestudio/TSK). Accepts either the file directly or a directory
    containing it."""
    if src_path.is_dir():
        candidate = src_path / "tskxref.txt"
        if not candidate.exists():
            candidate = next(src_path.rglob("tskxref.txt"), None)
        if candidate is None:
            raise FileNotFoundError(f"tskxref.txt not found under {src_path}")
        src_path = candidate
    print(f"loading TSK refs from {src_path}", file=sys.stderr)
    drv = _driver()
    apply_constraints(drv)
    n = _batch_upsert_xrefs(drv, _iter_tsk(src_path), UPSERT_TSK_XREF)
    drv.close()
    print(f"TSK: {n} xrefs upserted", file=sys.stderr)
    return n


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    for cmd in ("load-tahot", "load-tagnt", "cross-validate-oshb",
                "load-openbible", "load-tsk", "load-all"):
        s = sub.add_parser(cmd)
        s.add_argument("--src", type=Path, required=True,
                       help="Source directory or file (see docstring)")

    args = p.parse_args()

    if args.cmd == "load-tahot":
        load_tahot(args.src)
    elif args.cmd == "load-tagnt":
        load_tagnt(args.src)
    elif args.cmd == "cross-validate-oshb":
        cross_validate_oshb(args.src)
    elif args.cmd == "load-openbible":
        load_openbible(args.src)
    elif args.cmd == "load-tsk":
        load_tsk(args.src)
    elif args.cmd == "load-all":
        base = args.src
        load_tahot(base / "stepbible")
        load_tagnt(base / "stepbible")
        cross_validate_oshb(base / "oshb")
        ob = next(base.rglob("openbible*.tsv"), None) or next(base.rglob("cross_references*.tsv"), None)
        if ob:
            load_openbible(ob)
        tsk = next(base.rglob("tsk*.csv"), None)
        if tsk:
            load_tsk(tsk)
    return 0


if __name__ == "__main__":
    sys.exit(main())
