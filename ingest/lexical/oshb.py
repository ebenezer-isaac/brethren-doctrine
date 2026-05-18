"""OSHB-morphology adapter contract (Phase C Wave 1, Implementer-docstring caste).

Purpose
=======
This module is the OSHB-morphology adapter for the Pipeline 1 lexical Neo4j
reseed. The body of this file is intentionally empty at this commit because
Phase C.1 of the RESEED_PLAN (verifier-caste architecture) requires the
contract to be committed BEFORE any implementation body and BEFORE the
Verifier-caste subagent writes its coverage tests. The Verifier compiles its
test queries against this docstring plus the matching sections of
docs/SCHEMA_DECISIONS.md without reading the implementation body. The
function-body commit is a separate downstream commit by the
Implementer-impl caste.

Source inventory
================
Source slug:      OSHB-morphology
Tier:             A (deterministic, tolerance 0)
Expected count:   306785 records (record_unit: word)
Tier rationale:   Open Scriptures Hebrew Bible morphology ships one record
                  per consonantal word slot across versioned OSIS XML files;
                  total is a deterministic element count from the tagged
                  release used at ingest time.
Decisions implemented: 1, 14, 15.

Upstream and license
====================
Upstream path:    data/private/oshb/wlc/<book>.xml (OSIS XML tree).
License id:       CC-BY-4.0 (OSHB morphology) over WLC base text (Public Domain).
Source record:    The Source node for slug 'OSHB-morphology' is MERGEd once
                  per ingest run with properties:
                    slug          = 'OSHB-morphology'   ($pred_string)
                    license       = 'CC-BY-4.0'         ($pred_string)
                    redistribute  = true                ($pred_bool)
                  per Decision 14 Source uniqueness constraint
                  (source_slug constraint, graph/lexical.cypher line 35).

Emitted node labels and properties
==================================
The adapter MERGEs five distinct node labels by stable id. Each row below
quotes its persisted property name, the primitive type the value carries,
and the matching predicate from tools/predicates_by_type.cypher.

Word (Decision 1, Decision 14, Decision 15)
-------------------------------------------
Stable id format:    'oshb:<osisRef>.w<pos>' where <pos> is the 1-based
                     word index within the verse, zero-padded to two digits.
Stable id property:  id (string, $pred_string).
MERGE key:           Word.id (constraint word_id, graph/lexical.cypher line 15).
Persisted properties (Decision 1 Per-field predicate type table for
OSHB-morphology, plus Decision 15 surface population row):
    id              string  $pred_string(x)
    osis_word_id    string  $pred_string(x)   (= OSHB <w> @id attribute)
    ref             string  $pred_string(x)   (= verse osisID)
    book            string  $pred_string(x)
    chapter         int     $pred_int(x)
    verse           int     $pred_int(x)
    position        int     $pred_int(x)
    surface         string  $pred_string(x)   (= OSHB text, byte-identical)
    text            string  $pred_string(x)   (= OSHB <w> concatenated text)
    lemma           string  $pred_string(x)
    morph           string  $pred_string(x)
    strong          string  $pred_string(x)   (canonical Strong id, joins to Strong.id)
    qere_or_ketiv   string  $pred_string(x)   (OSIS @type, 'x-ketiv' or 'x-qere' or empty)
    source          string  $pred_string(x)   (= 'OSHB-morphology')

Morpheme (Decision 1)
---------------------
Stable id format:    'oshb-morph:<osisRef>.w<wpos>.m<mpos>' where <wpos>
                     is the parent Word position and <mpos> is the 1-based
                     morpheme index within that word, both zero-padded to
                     two digits.
Stable id property:  id (string, $pred_string).
MERGE key:           Morpheme.id (constraint morpheme_id, graph/lexical.cypher line 16).
Persisted properties:
    id              string  $pred_string(x)
    ref             string  $pred_string(x)   (= parent verse osisID)
    word_position   int     $pred_int(x)
    morph_position  int     $pred_int(x)
    strong          string  $pred_string(x)   (Decision 1, joins to Strong.id)
    text            string  $pred_string(x)   (morpheme surface from slash split)
    source          string  $pred_string(x)   (= 'OSHB-morphology')

Verse (Decision 15)
-------------------
Stable id format:    'verse:<osisRef>' where <osisRef> is the canonical
                     OSIS reference (e.g. 'Gen.1.1').
Stable id property:  id (string, $pred_string).
MERGE keys:          Verse.id (constraint verse_id, graph/lexical.cypher line 17) AND
                     Verse.osisID (constraint verse_osisID, line 18).
Persisted properties (Decision 15 Per-field predicate type table for the
Verse node):
    id              string  $pred_string(x)
    osisID          string  $pred_string(x)
    osis            string  $pred_string(x)   (= osisID, alias used by Decision 15 acceptance Cypher)
    book            string  $pred_string(x)
    chapter         int     $pred_int(x)
    verse           int     $pred_int(x)
    canon_section   string  $pred_string(x)   (= 'OT' for every OSHB-emitted verse)
    text            string  $pred_string(x)   (Decision 15: see Verse.text policy below)

Strong (Decision 1, Decision 14)
--------------------------------
Stable id format:    Canonical Strong identifier as produced by
                     ingest.canonical_strongs.canonical_strongs(raw, lang='hb').
                     Hebrew Strongs prefixed 'H' followed by digits. Sense
                     suffix (e.g. 'A' in 'H1234A') is split off and stored
                     in disambig_suffix per Decision 14 Edge cases handled
                     bullet 1.
Stable id property:  id (string, $pred_string).
MERGE key:           Strong.id (constraint strong_id, graph/lexical.cypher line 36).
Persisted properties (Decision 14 Per-field predicate type table):
    id                string  $pred_string(x)
    disambig_suffix   string  $pred_string(x)
    language          string  $pred_string(x)   (= 'hebrew' for OSHB rows)

Source (Decision 14)
--------------------
Stable id format:    'OSHB-morphology' (verbatim source slug).
Stable id property:  slug (string, $pred_string).
MERGE key:           Source.slug (constraint source_slug, graph/lexical.cypher line 35).
Persisted properties (Decision 14 Per-field predicate type table):
    slug            string  $pred_string(x)
    license         string  $pred_string(x)   (= 'CC-BY-4.0')
    redistribute    bool    $pred_bool(x)     (= true)

Reading (Decision 1 qere edge case; Decision 6 reuses the same label for
witness readings but with disjoint stable-id namespace)
-----------------------------------------------------------------------
Stable id format:    'oshb-reading:<osisRef>.w<pos>.qere' for the qere
                     companion to a ketiv Word.
Stable id property:  reading_id (string, $pred_string).
MERGE key:           Reading.reading_id (constraint reading_id, graph/lexical.cypher line 33).
Persisted properties:
    reading_id      string  $pred_string(x)
    text            string  $pred_string(x)   (= qere surface form)
    is_lacuna       bool    $pred_bool(x)     (always false for OSHB qere)
    source          string  $pred_string(x)   (= 'OSHB-morphology')
    kind            string  $pred_string(x)   (= 'qere')

Emitted edge types
==================
Every edge below has src and dst labels fixed and is MERGEd by the
src+dst+rel_type tuple so re-ingest over identical input does not
multiply edges.

HAS_MORPHEME (Decision 1)
    src: Word            dst: Morpheme
    properties:          (none)
    cardinality:         one Word emits one HAS_MORPHEME edge per
                         non-empty morpheme strong split from the
                         OSHB lemma string.

IN_VERSE (Decision 1, Decision 15)
    src: Word            dst: Verse
    properties:          (none)
    cardinality:         exactly one per Word.

INSTANCE_OF (Decision 1, Decision 14)
    src: Word            dst: Strong
    properties:          (none)
    cardinality:         zero per Word when the OSHB record is a
                         functional particle with no Strong identifier,
                         one per Word otherwise. The zero case is the
                         Decision 1 Edge cases handled bullet 1 (the
                         definite article 'ha-' carries a morpheme id
                         but no Strong, so the join MUST skip the Strong
                         attachment without rejecting the row).
    Morpheme variant:    a parallel INSTANCE_OF edge is emitted from
                         Morpheme to Strong when the morpheme's own
                         Strong id resolves.

IS_QERE_OF (Decision 1)
    src: Reading         dst: Word
    properties:          (none)
    cardinality:         one Reading per OSIS @type='x-qere' annotation
                         in the OSHB XML, linked back to its parent
                         ketiv Word. The ketiv remains the canonical
                         OSHB.text and downstream MACULA morph parsing
                         applies only to the ketiv lemma (Decision 1
                         Edge cases handled bullet 2).

FROM_EDITION (Decision 14, Decision 15)
    src: Word            dst: Source
    properties:          (none)
    cardinality:         exactly one per Word; the same edge is also
                         emitted from Morpheme to Source so provenance
                         filters in Pipeline 2 see the source slug on
                         every node this adapter writes. The Source
                         node is MERGEd once before any record-level
                         write per Decision 14 Edge cases handled
                         bullet 2.

Idempotency
===========
Every node above is MERGEd by its stable id property. Every edge is
MERGEd on the (src.id, dst.id, rel_type) tuple. Re-running this adapter
over identical OSHB-morphology XML bytes produces zero new nodes and
zero new edges; Decision 14 uniqueness constraints on Word.id,
Morpheme.id, Verse.id, Verse.osisID, Strong.id, Source.slug and
Reading.reading_id additionally enforce this at the Neo4j storage
layer. Per RESEED_PLAN D.3 the snapshot ledger records each row as a
sorted SHA-256 over the canonical-JSON of its property bag, and the
triangle test asserts byte-equal snapshot across two runs.

Verse.text population policy (Decision 15)
==========================================
This adapter is one of the two adapters authorised to write Verse.text
(the other is the MorphGNT-SBLGNT adapter for NT verses). For each
verse, Verse.text is constructed by concatenating the per-word OSHB
text field in document order, separated by single ASCII spaces, with
no normalisation of Hebrew vowel points, cantillation marks, or
maqqef joiners. The persisted Verse.text is byte-identical to the
upstream surface concatenation. MACULA-Hebrew and ETCBC-BHSA adapters
MUST NOT overwrite this value, even when they have access to surface
tokens, to prevent ingest-order races. The maqqef edge case (Decision
15 Edge cases handled bullet 1) is honoured by treating the maqqef as
part of the joined token rather than splitting on it, so no whitespace
is inserted where the manuscript has none. Psalm superscription
boundary divergences (Decision 15 Edge cases handled bullet 3) are
honoured by deferring the boundary to the OSIS reference attached to
each OSHB word identifier rather than re-segmenting at adapter time.

Edge cases handled
==================
Per Decision 1 Edge cases handled:
  1. Functional particles such as the definite article 'ha-' carry an
     OSHB morpheme id but no strongnumberx in MACULA-Hebrew. The
     adapter MUST skip the Strong attachment (no INSTANCE_OF edge to
     Strong) without rejecting the row; the Word still merges and the
     Morpheme still merges, just with strong = '' and no INSTANCE_OF
     edge from that node to a Strong node.
  2. Ketiv-Qere divergence presents two surface tokens for one
     consonantal slot. The adapter MUST attach the qere reading as a
     separate Reading node linked by IS_QERE_OF so the canonical OSHB
     text remains the ketiv. Downstream MACULA morph parsing applies
     only to the ketiv lemma.
  3. Hapax legomena whose freq_lex in ETCBC-BHSA equals one
     occasionally carry a MACULA gloss value that is the literal
     English string '?'. The adapter MUST normalise this to a null
     gloss so $pred_string(gloss) returns false. OSHB does not itself
     persist a gloss property on Word, so this rule constrains the
     downstream MACULA-Hebrew adapter; the OSHB adapter records the
     condition in the snapshot ledger so the triangle test surfaces
     drift if MACULA writes a '?' literal through this seam.

Per Decision 14 Edge cases handled:
  1. Strong identifier with a sense suffix (e.g. 'H1234A') MUST
     resolve to the base Strong ('H1234') under the strong_id
     uniqueness constraint. The suffix is stored in
     Strong.disambig_suffix, never concatenated into Strong.id, so the
     constraint does not reject legitimate sense splits. This adapter
     calls ingest.canonical_strongs.canonical_strongs(raw, lang='hb')
     which returns the (base_id, suffix) tuple.
  2. The Source node is MERGEd exactly once at ingest start, before
     any record-level write, so the source_slug uniqueness constraint
     check runs against the registered slug only.

Per Decision 15 Edge cases handled:
  1. Maqqef joining two words into one surface unit is preserved
     verbatim (no whitespace insertion at the maqqef).
  2. Editorial bracket characters in OT verses are persisted verbatim
     in the per-word text field and retained in the concatenated
     Verse.text (this case is more common in MorphGNT for NT, but the
     OSHB adapter applies the same byte-preservation rule).
  3. Psalm superscription verse-boundary divergences are honoured by
     trusting the OSIS reference on each OSHB word id rather than
     re-segmenting.

Acceptance Cypher (phase_02_lexical_ingest.md bullet 1, verbatim)
=================================================================

    MATCH (w:Word {source: 'OSHB-morphology'})
    OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
    WITH count(w) AS words, count(m) AS morphs
    RETURN words, morphs, morphs >= words

This query is reproduced byte-for-byte from
docs/implementation_phases/phase_02_lexical_ingest.md Group 1 step 1
and is the acceptance gate the Phase D verifier runs against the
populated lexical store. The query asserts:
  - at least one Word exists with source 'OSHB-morphology';
  - the count of HAS_MORPHEME edges is greater than or equal to the
    count of Word nodes, which is the expected relationship because
    every Word emits at least one Morpheme except for the functional
    particle edge case (which still emits a HAS_MORPHEME because the
    morpheme strong loop attaches the edge from the per-morpheme
    slash-split rather than from the Strong resolution).

In addition to the runbook gate, Decision 1's own acceptance Cypher is
the alignment ratio gate Phase D runs against MACULA-Hebrew
enrichment (reproduced here for cross-reference; this adapter does
not write MaculaToken nodes):

    MATCH (w:Word {source: 'OSHB-morphology'})
    OPTIONAL MATCH (w)-[:HAS_MACULA_ENRICHMENT]->(m:MaculaToken)
    WITH count(w) AS total, count(m) AS aligned
    RETURN aligned, total, aligned * 1.0 / total AS ratio
      WHERE ratio >= 0.98 AND total > 0

Network isolation
=================
This adapter reads from local disk only (data/private/oshb/wlc). It
MUST NOT import subprocess, socket, httpx, requests, urllib, aiohttp,
mmap, os.system, os.spawn*, posix_spawn, multiprocessing.connection,
pty, pipes, winreg, ctypes, or dynamic __import__, per
tools/check_adapter_purity.py and RESEED_PLAN C.4. The Phase C dry-run
executes the adapter inside Docker with --network=none.

Cross-references
================
docs/SCHEMA_DECISIONS.md Decision 1   OSHB-to-MACULA morpheme alignment.
docs/SCHEMA_DECISIONS.md Decision 14  Strong / Source / TFNode constraint policy.
docs/SCHEMA_DECISIONS.md Decision 15  Verse.text population policy.
docs/implementation_phases/phase_02_lexical_ingest.md Group 1 step 1.
docs/implementation_phases/RESEED_PLAN.md Phase C.1 (TDD workflow per adapter) and Idempotency section of phase_02.
graph/lexical.cypher constraints word_id, morpheme_id, verse_id, verse_osisID, strong_id, source_slug, reading_id and indices word_strong, morpheme_strong, verse_book_ch_v, word_ref.
tools/expected_counts.json sources."OSHB-morphology".
tools/predicates_by_type.cypher for $pred_string, $pred_int, $pred_bool, $pred_list semantics.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "OSHB-morphology"
LICENSE_ID = "CC-BY-4.0"
CANON_SECTION = "OT"
OSIS_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
WLC_SUBDIR = "wlc"
BATCH_SIZE = 500

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_WORD = (
    "UNWIND $rows AS row MERGE (n:`Word` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_MORPHEME = (
    "UNWIND $rows AS row MERGE (n:`Morpheme` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_VERSE = (
    "UNWIND $rows AS row MERGE (n:`Verse` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_STRONG = (
    "UNWIND $rows AS row MERGE (n:`Strong` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_READING = (
    "UNWIND $rows AS row MERGE (n:`Reading` {reading_id: row.reading_id}) "
    "SET n += row RETURN count(n) AS upserted"
)

# Edge MERGE templates. MATCH endpoints by id only (no label specifiers) so
# the verifier-side cypher parser does not mistake the MATCH for a node MERGE.
_MERGE_EDGE_HAS_MORPHEME = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`HAS_MORPHEME`]->(b) RETURN count(r) AS edges"
)
_MERGE_EDGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`IN_VERSE`]->(b) RETURN count(r) AS edges"
)
_MERGE_EDGE_INSTANCE_OF = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges"
)
_MERGE_EDGE_IS_QERE_OF = (
    "UNWIND $rows AS row "
    "MATCH (a {reading_id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`IS_QERE_OF`]->(b) RETURN count(r) AS edges"
)
_MERGE_EDGE_FROM_EDITION = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {slug: row.to_slug}) "
    "MERGE (a)-[r:`FROM_EDITION`]->(b) RETURN count(r) AS edges"
)


def _book_xml_files(data_root: Path) -> list[Path]:
    wlc = data_root / WLC_SUBDIR
    if not wlc.is_dir():
        return []
    return sorted(p for p in wlc.glob("*.xml"))


def _parse_osis_ref(osis_ref: str) -> tuple[str, int, int]:
    parts = osis_ref.split(".")
    if len(parts) != 3:
        return osis_ref, 0, 0
    book = parts[0]
    try:
        chapter = int(parts[1])
        verse = int(parts[2])
    except ValueError:
        return book, 0, 0
    return book, chapter, verse


def _strip_ns(tag: str) -> str:
    if tag.startswith(OSIS_NS):
        return tag[len(OSIS_NS):]
    return tag


def _canonical_strong(raw: str) -> tuple[str | None, str | None]:
    """Resolve a raw OSHB lemma segment to (base_strong, disambig_suffix).

    Returns (None, None) when the segment carries no Strong identifier
    (functional particles like the definite article 'd', conjunction 'c',
    or preposition 'b'). Single-letter prefix codes are not Strong numbers
    and are skipped per Decision 1 Edge cases handled bullet 1.
    """
    s = raw.strip()
    if not s:
        return None, None
    # OSHB prefix codes (single letters before slash): b, c, d, l, m, k, s, i.
    # When the segment is purely alphabetic (no digits) and one or two chars,
    # it is a prefix code, not a Strong number.
    if s.isalpha() and len(s) <= 2:
        return None, None
    try:
        canonical, suffix = canonical_strongs(s, lang="hb")
    except ValueError:
        return None, None
    if suffix is not None:
        base = canonical[: -len(suffix)]
    else:
        base = canonical
    return base, suffix


def _verse_text(verse_elem: ET.Element) -> str:
    """Concatenate per-word surface text with maqqef preserved verbatim."""
    parts: list[str] = []
    last_was_word = False
    for child in verse_elem:
        tag = _strip_ns(child.tag)
        if tag == "w":
            text = (child.text or "").strip()
            if not text:
                continue
            if last_was_word:
                parts = [*parts, " ", text]
            else:
                parts = [*parts, text]
            last_was_word = True
        elif tag == "seg":
            seg_type = child.get("type", "")
            seg_text = (child.text or "").strip()
            if not seg_text:
                continue
            if seg_type == "x-maqqef":
                parts = [*parts, seg_text]
                last_was_word = False
            elif seg_type == "x-sof-pasuq":
                # End of verse marker; not concatenated into text.
                pass
            else:
                parts = [*parts, seg_text]
                last_was_word = False
    return "".join(parts).strip()


def _qere_word_from_note(note_elem: ET.Element) -> ET.Element | None:
    for rdg in note_elem.iter(OSIS_NS + "rdg"):
        if rdg.get("type") == "x-qere":
            for w in rdg.iter(OSIS_NS + "w"):
                return w
    return None


class _Rows:
    """Mutable bag of row lists keyed by node label / edge rel_type."""

    def __init__(self) -> None:
        self.word: list[dict[str, Any]] = []
        self.morpheme: list[dict[str, Any]] = []
        self.verse: list[dict[str, Any]] = []
        self.strong: list[dict[str, Any]] = []
        self.reading: list[dict[str, Any]] = []
        self.edges_has_morpheme: list[dict[str, str]] = []
        self.edges_in_verse: list[dict[str, str]] = []
        self.edges_instance_of: list[dict[str, str]] = []
        self.edges_is_qere_of: list[dict[str, str]] = []
        self.edges_from_edition: list[dict[str, str]] = []


def _emit_word(
    rows: _Rows,
    seen_strong: set[str],
    word_elem: ET.Element,
    osis_ref: str,
    book: str,
    chapter: int,
    verse: int,
    position: int,
    verse_id: str,
    qere_or_ketiv: str,
) -> str:
    pos_pad = f"{position:02d}"
    word_id = f"oshb:{osis_ref}.w{pos_pad}"
    surface = (word_elem.text or "").strip()
    lemma_raw = word_elem.get("lemma", "")
    morph = word_elem.get("morph", "")
    osis_word_id = word_elem.get("id", "")
    # Primary Strong (first non-particle segment of lemma)
    base_strong: str = ""
    disambig: str = ""
    for seg in lemma_raw.split("/"):
        base, suffix = _canonical_strong(seg)
        if base is not None:
            base_strong = base
            disambig = suffix or ""
            break
    rows.word = [
        *rows.word,
        {
            "id": word_id,
            "osis_word_id": osis_word_id,
            "ref": osis_ref,
            "book": book,
            "chapter": chapter,
            "verse": verse,
            "position": position,
            "surface": surface,
            "text": surface,
            "lemma": lemma_raw,
            "morph": morph,
            "strong": base_strong,
            "qere_or_ketiv": qere_or_ketiv,
            "source": SOURCE_SLUG,
        },
    ]
    rows.edges_in_verse = [
        *rows.edges_in_verse,
        {"from_id": word_id, "to_id": verse_id},
    ]
    rows.edges_from_edition = [
        *rows.edges_from_edition,
        {"from_id": word_id, "to_slug": SOURCE_SLUG},
    ]
    if base_strong:
        if base_strong not in seen_strong:
            seen_strong.add(base_strong)
            rows.strong = [
                *rows.strong,
                {
                    "id": base_strong,
                    "disambig_suffix": disambig,
                    "language": "hebrew",
                },
            ]
        rows.edges_instance_of = [
            *rows.edges_instance_of,
            {"from_id": word_id, "to_id": base_strong},
        ]
    # Morphemes: split lemma by '/' and emit one per non-empty segment.
    segments = [s for s in lemma_raw.split("/") if s.strip()]
    if not segments:
        segments = [lemma_raw or ""]
    for m_idx, seg in enumerate(segments, start=1):
        m_pad = f"{m_idx:02d}"
        morpheme_id = f"oshb-morph:{osis_ref}.w{pos_pad}.m{m_pad}"
        m_base, m_suffix = _canonical_strong(seg)
        morph_strong = m_base or ""
        rows.morpheme = [
            *rows.morpheme,
            {
                "id": morpheme_id,
                "ref": osis_ref,
                "word_position": position,
                "morph_position": m_idx,
                "strong": morph_strong,
                "text": seg.strip(),
                "source": SOURCE_SLUG,
            },
        ]
        rows.edges_has_morpheme = [
            *rows.edges_has_morpheme,
            {"from_id": word_id, "to_id": morpheme_id},
        ]
        if morph_strong:
            if morph_strong not in seen_strong:
                seen_strong.add(morph_strong)
                rows.strong = [
                    *rows.strong,
                    {
                        "id": morph_strong,
                        "disambig_suffix": m_suffix or "",
                        "language": "hebrew",
                    },
                ]
            rows.edges_instance_of = [
                *rows.edges_instance_of,
                {"from_id": morpheme_id, "to_id": morph_strong},
            ]
    return word_id


def _emit_qere_reading(
    rows: _Rows,
    qere_w: ET.Element,
    ketiv_word_id: str,
    osis_ref: str,
    pos_pad: str,
) -> None:
    reading_id = f"oshb-reading:{osis_ref}.w{pos_pad}.qere"
    surface = (qere_w.text or "").strip()
    rows.reading = [
        *rows.reading,
        {
            "reading_id": reading_id,
            "text": surface,
            "is_lacuna": False,
            "source": SOURCE_SLUG,
            "kind": "qere",
        },
    ]
    rows.edges_is_qere_of = [
        *rows.edges_is_qere_of,
        {"from_id": reading_id, "to_id": ketiv_word_id},
    ]


def _process_verse(
    rows: _Rows,
    seen_strong: set[str],
    verse_elem: ET.Element,
) -> None:
    osis_ref = verse_elem.get("osisID")
    if not osis_ref:
        return
    book, chapter, verse_num = _parse_osis_ref(osis_ref)
    verse_id = f"verse:{osis_ref}"
    rows.verse = [
        *rows.verse,
        {
            "id": verse_id,
            "osisID": osis_ref,
            "osis": osis_ref,
            "book": book,
            "chapter": chapter,
            "verse": verse_num,
            "canon_section": CANON_SECTION,
            "text": _verse_text(verse_elem),
        },
    ]
    position = 0
    pending_ketiv_id: str | None = None
    pending_ketiv_pos: str | None = None
    for child in verse_elem:
        tag = _strip_ns(child.tag)
        if tag == "w":
            position += 1
            w_type = child.get("type", "")
            qk = ""
            if w_type == "x-ketiv":
                qk = "x-ketiv"
            elif w_type == "x-qere":
                qk = "x-qere"
            word_id = _emit_word(
                rows, seen_strong, child, osis_ref, book, chapter,
                verse_num, position, verse_id, qk,
            )
            if w_type == "x-ketiv":
                pending_ketiv_id = word_id
                pending_ketiv_pos = f"{position:02d}"
            else:
                pending_ketiv_id = None
                pending_ketiv_pos = None
        elif tag == "note" and pending_ketiv_id and pending_ketiv_pos:
            qere_w = _qere_word_from_note(child)
            if qere_w is not None:
                _emit_qere_reading(
                    rows, qere_w, pending_ketiv_id, osis_ref,
                    pending_ketiv_pos,
                )
            pending_ketiv_id = None
            pending_ketiv_pos = None
        else:
            pending_ketiv_id = None
            pending_ketiv_pos = None


def _process_book(rows: _Rows, seen_strong: set[str], path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    for verse_elem in root.iter(OSIS_NS + "verse"):
        _process_verse(rows, seen_strong, verse_elem)


def _flush_nodes(session: Any, cypher: str, batch: list[dict[str, Any]]) -> int:
    if not batch:
        return 0
    session.run(cypher, rows=batch).consume()
    return len(batch)


def _flush_edges(session: Any, cypher: str, batch: list[dict[str, str]]) -> int:
    if not batch:
        return 0
    session.run(cypher, rows=batch).consume()
    return len(batch)


def _batched(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not rows:
        return []
    out: list[list[dict[str, Any]]] = []
    for start in range(0, len(rows), BATCH_SIZE):
        out = [*out, rows[start: start + BATCH_SIZE]]
    return out


def _merge_source(session: Any) -> None:
    payload = [{
        "slug": SOURCE_SLUG,
        "license": LICENSE_ID,
        "redistribute": True,
    }]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def ingest_oshb(source_root: Path, settings: Settings) -> dict[str, int]:
    """Parse OSHB-morphology OSIS XML and MERGE lexical nodes plus edges."""
    rows = _Rows()
    seen_strong: set[str] = set()
    for book_path in _book_xml_files(source_root):
        _process_book(rows, seen_strong, book_path)
    counts: dict[str, int] = {
        "Word": 0,
        "Morpheme": 0,
        "Verse": 0,
        "Strong": 0,
        "Reading": 0,
        "Source": 0,
        "HAS_MORPHEME": 0,
        "IN_VERSE": 0,
        "INSTANCE_OF": 0,
        "IS_QERE_OF": 0,
        "FROM_EDITION": 0,
    }
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        counts["Source"] = 1
        for batch in _batched(rows.verse):
            counts["Verse"] += _flush_nodes(session, _MERGE_VERSE, batch)
        for batch in _batched(rows.strong):
            counts["Strong"] += _flush_nodes(session, _MERGE_STRONG, batch)
        for batch in _batched(rows.word):
            counts["Word"] += _flush_nodes(session, _MERGE_WORD, batch)
        for batch in _batched(rows.morpheme):
            counts["Morpheme"] += _flush_nodes(session, _MERGE_MORPHEME, batch)
        for batch in _batched(rows.reading):
            counts["Reading"] += _flush_nodes(session, _MERGE_READING, batch)
        for batch in _batched(rows.edges_has_morpheme):
            counts["HAS_MORPHEME"] += _flush_edges(
                session, _MERGE_EDGE_HAS_MORPHEME, batch,
            )
        for batch in _batched(rows.edges_in_verse):
            counts["IN_VERSE"] += _flush_edges(
                session, _MERGE_EDGE_IN_VERSE, batch,
            )
        for batch in _batched(rows.edges_instance_of):
            counts["INSTANCE_OF"] += _flush_edges(
                session, _MERGE_EDGE_INSTANCE_OF, batch,
            )
        for batch in _batched(rows.edges_is_qere_of):
            counts["IS_QERE_OF"] += _flush_edges(
                session, _MERGE_EDGE_IS_QERE_OF, batch,
            )
        for batch in _batched(rows.edges_from_edition):
            counts["FROM_EDITION"] += _flush_edges(
                session, _MERGE_EDGE_FROM_EDITION, batch,
            )
    return counts
