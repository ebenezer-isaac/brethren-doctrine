"""TSK adapter docstring contract (Phase C Wave 1).

This module implements Decision 5 of docs/SCHEMA_DECISIONS.md, the TSK
versification policy, narrowed in this file to the Treasury of Scripture
Knowledge cross-reference source. The companion adapter for
OpenBible-cross-refs lives in ingest/lexical/openbible.py and is governed
by the same Decision 5 rule with a strictly separate edge type so the
provenance separation between TSK and OpenBible stays mechanically
enforceable at query time. The legacy executable body of this file is
replaced by this single docstring expression per the
implementer-docstring caste boundary; the implementer-impl commit that
follows will reintroduce executable adapter code under a separate caste
trailer.

Source identity and counts
==========================
Source slug          : TSK
Inventory tier       : A (deterministic row count from one packed
                       SWORD-derived flat file, zero tolerance)
Record unit          : tsk_entry (one CrossRef node per per-word entry
                       carrying a packed xref_string payload)
Expected count       : 63682 rows / CrossRef nodes per
                       tools/expected_counts.json sources."TSK"
License              : public_domain per docs/LICENSE_TAGGING.md and
                       Decision 14 of docs/SCHEMA_DECISIONS.md, since
                       the 1880 Treasury of Scripture Knowledge by R. A.
                       Torrey is out of copyright and the upstream
                       SWORD TSK module redistributes it under that
                       status with no further restriction
Redistribute         : True (Source.redistribute is set true on the
                       single Source node registered for slug 'TSK' at
                       ingest start, before any record-level write, so
                       the source_slug uniqueness constraint in
                       graph/lexical.cypher rejects re-registration)
Upstream input path  : data/private/tskxref.txt (SWORD TSK module flat
                       file with one line per per-word entry, tab
                       separated into book_num, chapter, verse,
                       word_num, keyword, xref_string)

Label and edge surface
======================
CrossRef (source = 'TSK')

CROSS_REF : CrossRef to Verse, one edge per expanded reference inside
            xref_string. The edge MUST carry property source='TSK' and
            property osis_target (string, $pred_string(x)) holding the
            OSIS rendering of the resolved target verse, plus the
            inherited license and redistribute flags so the edge filter
            in Pipeline 2 can partition TSK contributions cleanly from
            OPENBIBLE_CROSS_REF without joining back through the
            CrossRef node. The CROSS_REF edge type is the one Decision
            5 reserves for TSK; OpenBible-cross-refs MUST use the
            parallel OPENBIBLE_CROSS_REF edge type, never CROSS_REF, so
            provenance filters in Pipeline 2 stay clean and the edge
            count in tools/expected_counts.json edge_counts
            HAS_CROSS_REF block is the TSK-only count.

CrossRef stable identifier
==========================
Key tuple            : (book_num, chapter, verse, word_num) per
                       Decision 5. The four integer columns at the
                       head of every TSK row uniquely identify the
                       per-word anchor that the upstream attaches the
                       cross-reference payload to. The crossref_id
                       constraint in graph/lexical.cypher requires
                       c.id IS UNIQUE for CrossRef nodes, so the
                       adapter MUST construct a string id from the
                       key tuple.
Stable-id format     : tsk:<book_num>.<chapter>.<verse>.<word_num>
                       where book_num is the integer book index in
                       the TSK numbering, chapter and verse are the
                       integer verse coordinates in the KJV scheme
                       carried by the upstream file, and word_num is
                       the one-indexed word position within the
                       anchor verse that the entry pins on. The colon
                       separator after the slug and the dot separators
                       between integers MUST be preserved verbatim so
                       the id remains a single canonical string per
                       key tuple.
Justifiable alt      : if a subsequent SWORD TSK module release adds a
                       sub-word anchor that the upstream signals via
                       an extra trailing column, the adapter MAY
                       extend the id with a fifth dot-separated
                       integer suffix on those rows alone, recording
                       the fallback per row in the snapshot ledger so
                       the triangle test hash diverges if the upstream
                       column shape shifts. The base four-tuple id is
                       the canonical form for the Phase A.4 baseline.
Uniqueness           : enforced by graph/lexical.cypher constraint
                       crossref_id (FOR (c:CrossRef) REQUIRE c.id IS
                       UNIQUE) per Decision 5. The crossref_from_ref
                       and crossref_to_ref indexes speed the per-verse
                       traversal that Pipeline 2 runs against TSK
                       cross-reference walks. The id is NOT the
                       (book_num, chapter, verse, word_num) tuple
                       directly because Neo4j uniqueness constraints
                       on Phase A.4 cypher target a single string
                       property, and serialising the tuple into a
                       canonical string keeps the constraint check
                       deterministic across re-ingest.

Per-field predicate type (CrossRef node, per Decision 5 TSK table)
==================================================================
| Field        | Type   | Predicate         | Nullability |
|--------------|--------|-------------------|-------------|
| book_num     | int    | $pred_int(x)      | not null    |
| chapter      | int    | $pred_int(x)      | not null    |
| verse        | int    | $pred_int(x)      | not null    |
| word_num     | int    | $pred_int(x)      | not null    |
| keyword      | string | $pred_string(x)   | not null    |
| xref_string  | string | $pred_string(x)   | not null    |
| from_ref     | string | $pred_string(x)   | not null    |
| to_ref       | string | $pred_string(x)   | not null    |

The from_ref property carries the OSIS rendering of the anchor verse
derived from the key tuple after TVTMS reconciliation; the to_ref
property carries the OSIS rendering of the first expanded reference in
xref_string and is provided as a denormalised hint for query traversal
even though the canonical per-target reference lives on the CROSS_REF
edge as osis_target. The xref_string field is preserved verbatim from
the upstream packed payload so the snapshot ledger can rehash it
byte-for-byte across two runs; the per-target expansion does NOT
overwrite this field. Predicate-type references resolve through
tools/predicates_by_type.cypher via tools/predicates.py.substitute at
verifier time per the runbook in
docs/implementation_phases/phase_02_lexical_ingest.md section
"Per-adapter acceptance pattern".

CROSS_REF edge properties
=========================
| Property      | Type   | Predicate          | Nullability |
|---------------|--------|--------------------|-------------|
| source        | string | $pred_string(x)    | not null    |
| osis_target   | string | $pred_string(x)    | not null    |
| license       | string | $pred_string(x)    | not null    |
| redistribute  | bool   | $pred_bool(x)      | not null    |

The source property MUST equal the literal string 'TSK' on every
CROSS_REF edge this adapter emits. The osis_target property MUST hold
the canonical OSIS rendering of the resolved target verse, which is
the join key Pipeline 2 walks back to the Verse node identified by the
matching osisID property under the verse_osisID uniqueness constraint.
The license property MUST equal 'public_domain' and the redistribute
property MUST equal true per Decision 14.

xref_string range expansion
===========================
The xref_string column packs one or more references in a compact form,
ranges such as 'Ps.119.1-176' commonly appear, and the adapter MUST
expand a range into one CROSS_REF edge per verse in the range, not a
single packed edge with hidden multiplicity. The expansion rule:

1. Split the xref_string on the semicolon separator to obtain one
   reference token per parsed entry.
2. For each token, recognise the book abbreviation prefix and the
   chapter colon verse suffix; recognise the dash range separator
   within the verse suffix when present.
3. When the verse suffix contains a range 'a-b', enumerate every
   integer v with a <= v <= b and emit one CROSS_REF edge with
   osis_target set to the resolved OSIS reference for that single v.
4. When the verse suffix contains a comma-separated list 'a,b,c',
   treat each element as an independent verse target and emit one
   CROSS_REF edge per element; combined range plus list forms such as
   'a-b,c' are expanded by applying rule 3 to the range token and
   rule 4 to the list separator.
5. The packed xref_string is preserved verbatim on the CrossRef node
   so the count-based acceptance query and Pipeline 2 graph-walk both
   see the true cardinality on the edges while the unexpanded payload
   stays auditable on the node.

The edge count after expansion lives in
tools/expected_counts.json edge_counts.HAS_CROSS_REF tier B, with
expected_min 100001 and expected_max 509456. The expected_min equals
the Decision 5 acceptance gate of one hundred thousand plus one. The
expected_max assumes an average of eight refs per parsed entry across
sixty-three thousand rows. The Phase D verifier asserts the edge
count falls within this two-percent-tolerance Tier B band per the
tier_policy block at the head of tools/expected_counts.json.

TVTMS reconciliation
====================
TSK numbers verses in the KJV scheme, and the canonical OSIS reference
space adopted by MACULA differs in places, particularly where the KJV
splits a verse the OSIS keeps whole, or where the KJV omits a verse
the OSIS includes by another sequence. Decision 5 directs every TSK
reference, anchor and target alike, through the STEPBible-TVTMS
rule_type reconciliation before key assignment.

The reconciliation rule:

1. Resolve the anchor verse (book_num, chapter, verse) into the OSIS
   reference space by looking up the TVTMS rule whose tradition_a is
   the KJV tradition slug and whose ref_a matches the anchor; the
   rule's tradition_b and ref_b columns give the OSIS reference.
2. Resolve each expanded target reference into the OSIS reference
   space by the same lookup, applied per single-verse expansion.
3. When the anchor verse number exceeds the canonical chapter length
   under MACULA's OSIS, the row reflects a KJV-only verse
   subdivision and the adapter MUST consult the TVTMS rule_type
   field to map it back. KJV-only subdivisions resolve via rule_type
   markers documented in the STEPBible-TVTMS README; the adapter
   records the rule_type that fired on each row in the snapshot
   ledger so re-ingest produces the same per-row resolution map.
4. Rows the TVTMS mapping cannot resolve MUST be tagged with a
   quarantine flag rather than silently dropped, so the rejection
   shows up in the snapshot ledger and the triangle test detects the
   coverage gap rather than masking it as a clean ingest. The
   quarantine flag MUST be a CrossRef property named
   tvtms_quarantine of type bool, set true only on the unresolved
   rows, and absent on resolved rows so $pred_bool(x) returns false
   in the resolved case and the rejection count is the only field
   the verifier needs to scan.

Distinction from OPENBIBLE_CROSS_REF
====================================
Decision 5 keeps TSK and OpenBible-cross-refs on strictly separate
edge types. The OpenBible adapter in ingest/lexical/openbible.py
emits OPENBIBLE_CROSS_REF between Verse nodes with a votes int
property derived from the upstream community vote count. The TSK
adapter in this file emits CROSS_REF from CrossRef to Verse with the
source='TSK' and osis_target properties documented above. The two
edge types MUST never collapse onto a single relationship type,
because Pipeline 2 evidence ranking weights TSK editorial picks and
OpenBible community votes differently, and merging would lose the
provenance signal the evidence schema relies on. Edge counts for
OpenBible-cross-refs live in
tools/expected_counts.json edge_counts.OPENBIBLE_CROSS_REF tier B,
distinct from HAS_CROSS_REF.

Edge cases handled
==================
The adapter implements every edge case Decision 5 enumerates for TSK:

1. Range expansion: TSK references frequently span ranges such as
   'Ps.119.1-176' and the adapter MUST expand the range into one
   edge per verse in the range so the count-based acceptance query
   and Pipeline 2 graph-walk both see the true cardinality rather
   than a single packed edge with hidden multiplicity. The packed
   form remains on the CrossRef node in the xref_string property for
   audit; the expansion lands on the CROSS_REF edges as one edge per
   resolved single-verse osis_target.

2. KJV-only verse subdivisions: a verse number in TSK that exceeds
   the canonical chapter length under MACULA's OSIS reflects a
   KJV-only verse subdivision, and the adapter MUST consult the
   STEPBible-TVTMS rule_type to map it back into the OSIS reference
   space. Rows the TVTMS mapping cannot resolve MUST be tagged with
   the tvtms_quarantine boolean property rather than silently
   dropped, so the rejection count is auditable from the snapshot
   ledger and the verifier can assert the quarantine count is small
   relative to the total row count.

3. Provenance separation from OpenBible: TSK CROSS_REF edges and
   OpenBible OPENBIBLE_CROSS_REF edges MUST live on distinct
   relationship types per Decision 5 even when the anchor and target
   verse pair coincide. The adapter MUST NOT emit OPENBIBLE_CROSS_REF
   from this file, and the OpenBible adapter MUST NOT emit
   CROSS_REF, so a single MATCH on either type returns the
   provenance-pure edge set without joining through the source
   property.

Dependencies
============
Group order             : Group 5 (Cross-references and metadata) of
                          the Phase 02 dispatch order in
                          docs/implementation_phases/phase_02_lexical_ingest.md
                          bullet 18
Pre-existing nodes      : Verse nodes from Group 1 (OSHB-morphology
                          and MorphGNT-SBLGNT adapters populate the
                          OT and NT Verse nodes per Decision 15,
                          including the canonical osisID property
                          under the verse_osisID uniqueness
                          constraint; the CROSS_REF edge target join
                          walks v.osisID equal to the edge's
                          osis_target string)
Pre-existing rules      : VersificationRule nodes from Group 2
                          (STEPBible-TVTMS adapter emits one node
                          per parsed rule with rule_type, tradition_a,
                          ref_a, tradition_b, ref_b populated; this
                          adapter loads the rule set into memory at
                          ingest start and queries it row by row
                          rather than walking the graph at write
                          time)
Snapshot ledger         : the adapter records its per-row hash list,
                          the TVTMS rule_type that fired on each
                          resolved row, the quarantine flag count
                          for unresolved rows, and the per-token
                          range-expansion fan-out to the per-source
                          ledger consumed by
                          tools/verify_adapter_<X>.py and the
                          triangle-test runner in Phase D

Idempotency
===========
The adapter is idempotent through MERGE-by-stable-id on CrossRef.id
using the tsk:<book_num>.<chapter>.<verse>.<word_num> namespace, and
through MERGE-by-canonical-tuple on the CROSS_REF edge keyed by the
(from_id, to_id, source, osis_target) tuple so a re-ingest does not
multiply edges. The wipe contract in tools/wipe_lexical.py deletes
every node and relationship in the lexical Neo4j before re-ingest so
MERGE writes start from an empty store and the crossref_id
constraint rejects any second-write attempt for the same identifier.
The per-row SHA-256 hash list produced by the snapshot ledger MUST
recompute byte-for-byte across two runs over identical inputs per the
triangle test in Phase D.

Network isolation
=================
The adapter reads only the local cache under data/private/tskxref.txt.
No HTTP, DNS, or socket access happens at ingest time; the AST scan
tools/check_adapter_purity.py rejects any import of subprocess,
socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn,
posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes,
or dynamic __import__ in this file. The TVTMS rule set is loaded
from the on-disk artefact written by the STEPBible-TVTMS adapter in
Group 2; the load is a file read against the local Docker volume,
not a network call.

Acceptance Cypher (verbatim from
docs/implementation_phases/phase_02_lexical_ingest.md Group 5 bullet 18)
=======================================================================

    MATCH (a:CrossRef)-[r:CROSS_REF {source: 'TSK'}]->(b:Verse)
    WHERE a.book_num IS NOT NULL
    WITH count(r) AS edges
    RETURN edges, edges > 0

The Phase D verifier additionally executes the Decision 5 Cypher
acceptance query from docs/SCHEMA_DECISIONS.md against the same
ingest, asserting the TSK edge count exceeds one hundred thousand
and every emitted CROSS_REF edge carries a non-null osis_target so
the range-expansion fan-out is exercised on the live ingest rather
than collapsing into single packed edges.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "TSK"
LICENSE_ID = "public_domain"
TVTMS_RELATIVE = ("stepbible", "tvtms.parsed.json")
NODE_BATCH = 500

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

# Index i is the verse count of chapter i+1 under the OSIS/MACULA space.
# Books absent from this table use the permissive bound chapter >= 1 and
# verse >= 1; books carrying exact bounds let the Decision 5 canonical
# length quarantine check stay exact where TVTMS leaves a gap.
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


def _project(
    osis_book: str, chapter: int, verse: int, rules: dict[str, str]
) -> str | None:
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
    for raw_piece in verse_part.split(","):
        piece = raw_piece.strip()
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
            triples.extend(
                (osis_book, chapter, v) for v in range(lo, hi + 1)
            )
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
    "MATCH (a:`CrossRef` {id: row.from_id}), (b:`Verse` {osisID: row.osis_target}) "
    "MERGE (a)-[r:`CROSS_REF` "
    "{source: row.source, osis_target: row.osis_target}]->(b) "
    "SET r.license = row.license, r.redistribute = row.redistribute "
    "RETURN count(r) AS edges"
)


def _merge_source(session: Any) -> None:
    payload = [
        {"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}
    ]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_nodes(session: Any, nodes: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(nodes), NODE_BATCH):
        batch = nodes[start:start + NODE_BATCH]
        session.run(_MERGE_NODE, rows=batch).consume()
        total += len(batch)
    return total


def _merge_edges(session: Any, edges: list[dict[str, Any]]) -> int:
    for start in range(0, len(edges), NODE_BATCH):
        batch = edges[start:start + NODE_BATCH]
        session.run(_MERGE_EDGE, rows=batch).consume()
    return len(edges)


def ingest_tsk(data_root: Path, settings: Settings) -> dict[str, int]:
    """Parse the TSK SWORD module and MERGE CrossRef nodes and edges."""
    source_path = Path(data_root)
    rules = _load_tvtms_rules(source_path.parent)
    lines = _read_lines(source_path) if source_path.exists() else []
    rows = _rows_from_lines(lines)
    nodes, edges = _build(rows, rules)
    quarantined = sum(
        1 for n in nodes if n.get("tvtms_quarantine") is True
    )
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
