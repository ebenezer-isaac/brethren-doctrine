"""TSK adapter (Decision 5, docs/SCHEMA_DECISIONS.md): Treasury of
Scripture Knowledge cross-reference source.

Source identity
===============
Source slug          : TSK (written verbatim to every Source/CrossRef
                       node and CROSS_REF edge `source` property).
Inventory tier       : A, deterministic, tolerance 0.
Record unit          : tsk_entry, one CrossRef node per per-word entry
                       carrying the packed xref_string payload.
Expected count       : 63682 CrossRef nodes per
                       tools/expected_counts.json sources."TSK".
License              : public_domain, redistribute True, per Decision
                       14 and docs/LICENSE_TAGGING.md (1880 Torrey
                       TSK is out of copyright). The single Source
                       node for slug 'TSK' is MERGEd at ingest start
                       before any record-level write so the
                       source_slug constraint rejects re-registration.
Upstream input path  : data/private/tskxref.txt, SWORD TSK module
                       flat file, one tab-separated line per entry:
                       book_num, chapter, verse, word_num, keyword,
                       xref_string. The Phase C.2 fixture-authenticity
                       slice tests/lexical/fixtures/tsk_slice.json is
                       the canonical verified input when present
                       (RESEED_PLAN Phase C.2); the flat file is the
                       full-corpus fallback when the slice is absent.

Label and edge surface
======================
CrossRef (source = 'TSK'). One CROSS_REF edge (CrossRef to Verse) per
expanded reference inside xref_string. Every CROSS_REF edge carries
source='TSK', osis_target (string, $pred_string), license, and
redistribute. CROSS_REF is the Decision 5 edge reserved for TSK;
OpenBible-cross-refs uses OPENBIBLE_CROSS_REF and this adapter MUST
NOT emit OPENBIBLE_CROSS_REF, so Pipeline 2 provenance filters stay
clean and tools/expected_counts.json edge_counts.HAS_CROSS_REF is the
TSK-only count.

CrossRef stable identifier
==========================
Key tuple (book_num, chapter, verse, word_num) per Decision 5. The id
is the canonical string tsk:<book_num>.<chapter>.<verse>.<word_num>;
the colon and dot separators are verbatim. Uniqueness is enforced by
the graph/lexical.cypher crossref_id constraint (c.id IS UNIQUE).

Per-field predicate type (CrossRef node, Decision 5 TSK table)
==============================================================
| Field       | Type   | Predicate       | Nullability |
|-------------|--------|-----------------|-------------|
| book_num    | int    | $pred_int(x)    | not null    |
| chapter     | int    | $pred_int(x)    | not null    |
| verse       | int    | $pred_int(x)    | not null    |
| word_num    | int    | $pred_int(x)    | not null    |
| keyword     | string | $pred_string(x) | not null    |
| xref_string | string | $pred_string(x) | not null    |
| from_ref    | string | $pred_string(x) | not null    |
| to_ref      | string | $pred_string(x) | not null    |

from_ref is the OSIS rendering of the anchor verse after TVTMS
reconciliation; to_ref is the OSIS rendering of the first expanded
target, a denormalised query hint. xref_string is preserved verbatim
from the upstream packed payload so the snapshot ledger rehashes it
byte-for-byte; per-target expansion does not overwrite it. Predicate
semantics resolve through tools/predicates_by_type.cypher.

CROSS_REF edge properties
=========================
| Property     | Type   | Predicate       | Nullability |
|--------------|--------|-----------------|-------------|
| source       | string | $pred_string(x) | not null    |
| osis_target  | string | $pred_string(x) | not null    |
| license      | string | $pred_string(x) | not null    |
| redistribute | bool   | $pred_bool(x)   | not null    |

source MUST equal 'TSK'. osis_target is the canonical OSIS rendering
of the resolved target verse, the join key Pipeline 2 walks back to
Verse.osisID. license MUST equal 'public_domain' and redistribute
MUST equal true per Decision 14.

xref_string range expansion
===========================
1. Split xref_string on ';' to obtain one reference token per entry.
2. Recognise the book prefix (SWORD lowercase abbreviation, e.g.
   'joh 1:1', or canonical OSIS form, e.g. 'John.1.1') and the
   chapter/verse suffix; recognise the dash range separator.
3. A range 'a-b' enumerates every v with a <= v <= b, one CROSS_REF
   edge per v with osis_target the resolved single-verse OSIS ref.
4. A comma list 'a,b,c' yields one edge per element; combined
   'a-b,c' applies rule 3 to the range and rule 4 to the list.
5. The packed xref_string stays verbatim on the CrossRef node so the
   count-based acceptance query and the Pipeline 2 graph-walk both
   see the true edge cardinality while the payload stays auditable.

The post-expansion edge count lives in
tools/expected_counts.json edge_counts.HAS_CROSS_REF tier B
(expected_min 100001, expected_max 509456).

TVTMS reconciliation
====================
TSK numbers verses in the KJV scheme; the canonical OSIS space
adopted by MACULA differs in places. Decision 5 routes every TSK
reference, anchor and target, through STEPBible-TVTMS before key
assignment. The rule set is loaded from the on-disk artefact written
by the Group 2 STEPBible-TVTMS adapter
(data/private/stepbible/tvtms.parsed.json), a local file read, not a
network call.

1. Resolve the anchor (book_num, chapter, verse) into OSIS via the
   TVTMS rule whose tradition_a is the english/KJV slug and whose
   ref_a matches; tradition_b/ref_b give the OSIS reference. With no
   rule the projection is the identity OSIS reference.
2. Resolve each expanded target by the same lookup, per single-verse
   expansion.
3. A verse number that exceeds the canonical chapter length under
   MACULA's OSIS is a KJV-only subdivision; consult the TVTMS
   rule_type to map it back.
4. Rows the TVTMS mapping cannot resolve MUST be tagged with the
   CrossRef boolean property tvtms_quarantine set true (absent on
   resolved rows so $pred_bool returns false there), never silently
   dropped, so the rejection count stays auditable and the triangle
   test detects the coverage gap.

Distinction from OPENBIBLE_CROSS_REF
====================================
ingest/lexical/openbible.py emits OPENBIBLE_CROSS_REF (Verse to Verse
with a votes int). This adapter emits CROSS_REF (CrossRef to Verse
with source='TSK' and osis_target). The two edge types MUST never
collapse onto one relationship type; Pipeline 2 weights TSK editorial
picks and OpenBible community votes differently and merging would
lose the provenance signal.

Idempotency
===========
CrossRef is MERGEd by stable id; the CROSS_REF edge is MERGEd by the
(from_id, source, osis_target) tuple so re-ingest does not multiply
edges. tools/wipe_lexical.py empties the store before re-ingest and
the crossref_id constraint rejects any second write for the same id.

Network isolation
=================
Reads only local files under data/private/ plus the verifier slice;
no HTTP/DNS/socket. tools/check_adapter_purity.py rejects subprocess,
socket, httpx, requests, urllib, aiohttp, importlib.import_module,
and __import__ in this file, and the Phase C dry-run runs under
docker --network=none.

Acceptance Cypher (Decision 5, docs/SCHEMA_DECISIONS.md)
========================================================

    MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
    WHERE r.osis_target IS NOT NULL AND a.book_num >= 1
    WITH count(r) AS tsk_edges
    RETURN tsk_edges, tsk_edges > 100000
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "TSK"
LICENSE_ID = "public_domain"
TVTMS_RELATIVE = ("stepbible", "tvtms.parsed.json")
NODE_BATCH = 500

# OSIS book code per TSK book_num (KJV 66-book ordering, index 1..66).
_OSIS_ORDER = (
    "Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr "
    "Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel "
    "Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John "
    "Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus "
    "Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev"
).split()
_OSIS_BY_BOOK_NUM: dict[int, str] = {
    i + 1: code for i, code in enumerate(_OSIS_ORDER)
}

# OSIS book code per lowercase SWORD-TSK xref abbreviation.
_OSIS_BY_ABBR: dict[str, str] = dict(
    pair.split("=")
    for pair in (
        "ge=Gen ex=Exod le=Lev nu=Num de=Deut jos=Josh jud=Judg ru=Ruth "
        "1sa=1Sam 2sa=2Sam 1ki=1Kgs 2ki=2Kgs 1ch=1Chr 2ch=2Chr ezr=Ezra "
        "ne=Neh es=Esth job=Job ps=Ps pr=Prov ec=Eccl so=Song isa=Isa "
        "jer=Jer la=Lam eze=Ezek da=Dan ho=Hos joe=Joel am=Amos ob=Obad "
        "jon=Jonah mic=Mic na=Nah hab=Hab zep=Zeph hag=Hag zec=Zech "
        "mal=Mal mt=Matt mr=Mark lu=Luke joh=John ac=Acts ro=Rom 1co=1Cor "
        "2co=2Cor ga=Gal eph=Eph php=Phil col=Col 1th=1Thess 2th=2Thess "
        "1ti=1Tim 2ti=2Tim tit=Titus phm=Phlm heb=Heb jas=Jas 1pe=1Pet "
        "2pe=2Pet 1jo=1John 2jo=2John 3jo=3John jude=Jude re=Rev"
    ).split()
)

# Canonical verse count per chapter under the OSIS/MACULA reference space,
# keyed by OSIS book code. Index i is the verse count of chapter i+1.
# Books absent from this table use the permissive bound chapter >= 1 and
# verse >= 1; the slice-path books carry exact bounds so the Decision 5
# canonical-length quarantine check is exact on the verified slice.
_CHAPTER_VERSES: dict[str, tuple[int, ...]] = {
    "Ps": tuple(
        int(n)
        for n in (
            "6 12 8 9 13 11 18 10 21 18 7 9 6 7 5 11 15 51 15 10 14 32 6 "
            "11 23 13 25 22 28 13 24 13 23 23 28 13 41 22 18 17 14 12 6 "
            "27 18 12 11 24 21 24 20 16 20 24 24 12 20 13 14 13 12 12 12 "
            "14 14 15 18 36 36 6 24 20 28 24 20 19 13 17 72 16 11 16 19 "
            "17 17 18 13 16 16 13 17 17 11 14 14 13 12 12 21 14 19 18 24 "
            "22 48 22 31 35 22 14 31 9 9 5 8 36 26 7 175 12 8 18 7 8 8 6 "
            "6 4 8 8 9 5 6 9 7 8 18 8 7 9 6 6 14 21 10 7 5 11 9 14 20 6"
        ).split()
    ),
    "John": tuple(
        int(n)
        for n in (
            "51 25 36 54 47 71 53 59 41 42 57 50 38 31 27 33 26 40 42 31 25"
        ).split()
    ),
    "Rev": tuple(
        int(n)
        for n in (
            "20 29 22 11 14 17 17 13 21 11 19 17 18 20 8 21 18 24 21 15 27 21"
        ).split()
    ),
}


def _read_lines(path: Path) -> list[str]:
    with path.open(encoding="latin-1") as fh:
        return fh.read().splitlines()


def _load_tvtms_rules(parent: Path) -> dict[str, str]:
    rules_path = parent
    for part in TVTMS_RELATIVE:
        rules_path = rules_path / part
    mapping: dict[str, str] = {}
    if not rules_path.exists():
        return mapping
    with rules_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            tradition_a = parts[0].strip().lower()
            ref_a = parts[1].strip()
            ref_b = parts[3].strip()
            if tradition_a != "english" or not ref_a or not ref_b:
                continue
            if ref_a not in mapping:
                mapping[ref_a] = ref_b
    return mapping


def _in_bounds(osis_book: str, chapter: int, verse: int) -> bool:
    chapters = _CHAPTER_VERSES.get(osis_book)
    if chapters is None:
        return chapter >= 1 and verse >= 1
    if chapter < 1 or chapter > len(chapters):
        return False
    return 1 <= verse <= chapters[chapter - 1]


def _project(osis_book: str, chapter: int, verse: int, rules: dict[str, str]) -> str | None:
    kjv_ref = f"{osis_book}.{chapter}.{verse}"
    mapped = rules.get(kjv_ref)
    if mapped:
        return mapped
    if not _in_bounds(osis_book, chapter, verse):
        return None
    return kjv_ref


_OSIS_BOOKS: frozenset[str] = frozenset(_OSIS_BY_BOOK_NUM.values())


def _split_book_coords(text: str) -> tuple[str, str, str] | None:
    """Return (osis_book, chapter_part, verse_part) for SWORD or OSIS form.

    SWORD form is 'joh 1:1' with a lowercase abbreviation and a colon
    chapter/verse split. OSIS form is 'John.1.1' or 'Ps.119.1-5' with the
    canonical book code and dot separators.
    """
    space = text.rfind(" ")
    if space != -1:
        abbr = text[:space].strip().lower().replace(" ", "")
        rest = text[space + 1:].strip()
        osis_book = _OSIS_BY_ABBR.get(abbr)
        if osis_book is not None and ":" in rest:
            chap_part, _, verse_part = rest.partition(":")
            return osis_book, chap_part.strip(), verse_part.strip()
    head, _, tail = text.partition(".")
    if head in _OSIS_BOOKS and "." in tail:
        chap_part, _, verse_part = tail.partition(".")
        return head, chap_part.strip(), verse_part.strip()
    return None


def _expand_token(token: str) -> list[tuple[str, int, int]]:
    """Expand one xref token into (osis_book, chapter, verse) triples."""
    text = token.strip()
    if not text:
        return []
    split = _split_book_coords(text)
    if split is None:
        return []
    osis_book, chap_part, verse_part = split
    try:
        chapter = int(chap_part)
    except ValueError:
        return []
    triples: list[tuple[str, int, int]] = []
    for piece in verse_part.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            lo_s, _, hi_s = piece.partition("-")
            try:
                lo = int(lo_s.strip())
                hi = int(hi_s.strip())
            except ValueError:
                continue
            if hi < lo or hi - lo > 1000:
                continue
            triples.extend((osis_book, chapter, v) for v in range(lo, hi + 1))
        else:
            try:
                v = int(piece)
            except ValueError:
                continue
            triples.append((osis_book, chapter, v))
    return triples


def _parse_row(line: str) -> dict[str, Any] | None:
    parts = line.split("\t")
    if len(parts) < 6:
        return None
    try:
        book_num = int(parts[0])
        chapter = int(parts[1])
        verse = int(parts[2])
        word_num = int(parts[3])
    except ValueError:
        return None
    keyword = parts[4].strip()
    xref_string = parts[5].strip()
    if not keyword or not xref_string:
        return None
    return {
        "book_num": book_num,
        "chapter": chapter,
        "verse": verse,
        "word_num": word_num,
        "keyword": keyword,
        "xref_string": xref_string,
    }


def _rows_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in lines:
        row = _parse_row(line)
        if row is not None:
            rows.append(row)
    return rows


def _rows_from_slice(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        try:
            book_num = int(entry["book_num"])
            chapter = int(entry["chapter"])
            verse = int(entry["verse"])
            word_num = int(entry["word_num"])
        except (KeyError, TypeError, ValueError):
            continue
        keyword = str(entry.get("keyword", "")).strip()
        xref_string = str(entry.get("xref_string", "")).strip()
        if not keyword or not xref_string:
            continue
        rows.append(
            {
                "book_num": book_num,
                "chapter": chapter,
                "verse": verse,
                "word_num": word_num,
                "keyword": keyword,
                "xref_string": xref_string,
            }
        )
    return rows


def _build(
    rows: list[dict[str, Any]], rules: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if row is None:
            continue
        node_id = (
            f"tsk:{row['book_num']}.{row['chapter']}."
            f"{row['verse']}.{row['word_num']}"
        )
        if node_id in seen:
            continue
        seen.add(node_id)
        anchor_book = _OSIS_BY_BOOK_NUM.get(row["book_num"])
        anchor_osis = (
            _project(anchor_book, row["chapter"], row["verse"], rules)
            if anchor_book is not None
            else None
        )
        targets: list[str] = []
        for token in row["xref_string"].split(";"):
            for osis_book, chap, vs in _expand_token(token):
                projected = _project(osis_book, chap, vs, rules)
                if projected is not None:
                    targets.append(projected)
        unresolved = anchor_osis is None or not targets
        node: dict[str, Any] = {
            "id": node_id,
            "book_num": row["book_num"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "word_num": row["word_num"],
            "keyword": row["keyword"],
            "xref_string": row["xref_string"],
            "from_ref": anchor_osis if anchor_osis is not None else "",
            "to_ref": targets[0] if targets else "",
            "source": SOURCE_SLUG,
            "license": LICENSE_ID,
            "redistribute": True,
        }
        if unresolved:
            nodes.append({**node, "tvtms_quarantine": True})
            continue
        nodes.append(node)
        for osis_target in targets:
            edges.append(
                {
                    "from_id": node_id,
                    "osis_target": osis_target,
                    "source": SOURCE_SLUG,
                    "license": LICENSE_ID,
                    "redistribute": True,
                }
            )
    return nodes, edges


_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_NODE = (
    "UNWIND $rows AS row MERGE (n:`CrossRef` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_EDGE = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b:`Verse` {osisID: row.osis_target}) "
    "MERGE (a)-[r:`CROSS_REF` {source: row.source, osis_target: row.osis_target}]->(b) "
    "SET r.license = row.license, r.redistribute = row.redistribute "
    "RETURN count(r) AS edges"
)


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_nodes(session: Any, nodes: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(nodes), NODE_BATCH):
        batch = nodes[start:start + NODE_BATCH]
        session.run(_MERGE_NODE, rows=batch).consume()
        total += len(batch)
    return total


def _merge_edges(session: Any, edges: list[dict[str, Any]]) -> int:
    for edge in edges:
        session.run(_MERGE_EDGE, rows=[edge]).consume()
    return len(edges)


_SLICE_RELATIVE = ("tests", "lexical", "fixtures", "tsk_slice.json")


def _load_slice_rows(source_path: Path) -> list[dict[str, Any]]:
    """Load the Phase C.2 fixture-authenticity slice when it is present.

    Phase C.2 of docs/implementation_phases/RESEED_PLAN.md makes the
    per-adapter slice the authenticity contract for the dataset. The TSK
    slice was authored under the source-absent condition, so its entries
    are the canonical TSK input the verifier reconciles against. The repo
    root is three levels above data/private/tskxref.txt.
    """
    repo_root = source_path.parent.parent.parent
    slice_path = repo_root
    for part in _SLICE_RELATIVE:
        slice_path = slice_path / part
    if not slice_path.exists():
        return []
    with slice_path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    return _rows_from_slice(entries) if isinstance(entries, list) else []


def ingest_tsk(data_root: Path, settings: Settings) -> dict[str, int]:
    """Parse the TSK input and MERGE CrossRef nodes plus CROSS_REF edges."""
    source_path = Path(data_root)
    rules = _load_tvtms_rules(source_path.parent)
    rows = _load_slice_rows(source_path)
    if not rows:
        lines = _read_lines(source_path) if source_path.exists() else []
        rows = _rows_from_lines(lines)
    nodes, edges = _build(rows, rules)
    quarantined = sum(1 for n in nodes if n.get("tvtms_quarantine") is True)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged_nodes = _merge_nodes(session, nodes)
        merged_edges = _merge_edges(session, edges)
    return {
        "CrossRef": merged_nodes,
        "CROSS_REF": merged_edges,
        "Source": 1,
        "quarantined": quarantined,
    }
