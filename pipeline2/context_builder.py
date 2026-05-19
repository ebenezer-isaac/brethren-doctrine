"""Build the lexical context bundle that Pipeline 2 subagents consume.

Queries the lexical Neo4j (apparatus + interlinear + concordance) only. No
cultural store touch. The output shape matches the "Inputs" contract in
docs/phase_prompts/pipeline2_verdict.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from neo4j import Driver

from ingest.lexical._common import Settings, get_lexical_driver

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "questions.json"

CROSS_REF_LIMIT = 20
SEMANTIC_NEIGHBOR_LIMIT = 15
VARIANT_LIMIT = 10
SYNTACTIC_LIMIT = 20
ANCHOR_LEMMA_LIMIT = 40

_REF_PATTERN = re.compile(
    r"^(?P<book>[1-3]?\s?[A-Za-z]+)\s+(?P<chapter>\d+):(?P<verses>\d+(?:-\d+)?)$"
)

_OSIS_BOOKS: dict[str, str] = {
    "Genesis": "Gen",
    "Exodus": "Exod",
    "Leviticus": "Lev",
    "Numbers": "Num",
    "Deuteronomy": "Deut",
    "Joshua": "Josh",
    "Judges": "Judg",
    "Ruth": "Ruth",
    "1 Samuel": "1Sam",
    "2 Samuel": "2Sam",
    "1 Kings": "1Kgs",
    "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr",
    "2 Chronicles": "2Chr",
    "Ezra": "Ezra",
    "Nehemiah": "Neh",
    "Esther": "Esth",
    "Job": "Job",
    "Psalm": "Ps",
    "Psalms": "Ps",
    "Proverbs": "Prov",
    "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song",
    "Isaiah": "Isa",
    "Jeremiah": "Jer",
    "Lamentations": "Lam",
    "Ezekiel": "Ezek",
    "Daniel": "Dan",
    "Hosea": "Hos",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Obad",
    "Jonah": "Jonah",
    "Micah": "Mic",
    "Nahum": "Nah",
    "Habakkuk": "Hab",
    "Zephaniah": "Zeph",
    "Haggai": "Hag",
    "Zechariah": "Zech",
    "Malachi": "Mal",
    "Matthew": "Matt",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Romans": "Rom",
    "1 Corinthians": "1Cor",
    "2 Corinthians": "2Cor",
    "Galatians": "Gal",
    "Ephesians": "Eph",
    "Philippians": "Phil",
    "Colossians": "Col",
    "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess",
    "1 Timothy": "1Tim",
    "2 Timothy": "2Tim",
    "Titus": "Titus",
    "Philemon": "Phlm",
    "Hebrews": "Heb",
    "James": "Jas",
    "1 Peter": "1Pet",
    "2 Peter": "2Pet",
    "1 John": "1John",
    "2 John": "2John",
    "3 John": "3John",
    "Jude": "Jude",
    "Revelation": "Rev",
}


def to_osis(human_ref: str) -> list[str]:
    """Convert a human ref like 'John 1:1-3' to OSIS BCV refs.

    Returns a list of single-verse refs (one per verse in a range).
    """
    m = _REF_PATTERN.match(human_ref.strip())
    if not m:
        return []
    book = m.group("book").strip()
    osis_book = _OSIS_BOOKS.get(book)
    if not osis_book:
        return []
    chapter = m.group("chapter")
    verses = m.group("verses")
    if "-" in verses:
        lo_s, hi_s = verses.split("-")
        lo, hi = int(lo_s), int(hi_s)
        return [f"{osis_book}.{chapter}.{v}" for v in range(lo, hi + 1)]
    return [f"{osis_book}.{chapter}.{verses}"]


def load_question(question_id: str) -> dict[str, Any]:
    raw = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    for q in raw["questions"]:
        if q["id"] == question_id:
            return q  # type: ignore[no-any-return]
    raise KeyError(f"question id {question_id!r} not in questions.json")


def _anchor_refs(question: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for human in question.get("scripture_anchors", []):
        refs.extend(to_osis(human))
    return refs


# RESEED_PLAN F.1 invariant 4 / Decision 6 / phase_02 variant scope:
# the only ECM/CBGM apparatus ingested is 3 John, verse range 1.1
# through 1.15 inclusive. Any anchor verse outside this exact window
# has no variant apparatus by construction, so the bundle must declare
# not_in_ecm_scope honestly rather than emit a silently empty
# variant_units with no signal that the silence is structural.
_ECM_SCOPE_BOOK = "3John"
_ECM_SCOPE_CHAPTER = 1
_ECM_SCOPE_VERSE_LO = 1
_ECM_SCOPE_VERSE_HI = 15

_ECM_REF_PATTERN = re.compile(r"^3John\.(?P<chapter>\d+)\.(?P<verse>\d+)$")


def _in_ecm_scope(osis_refs: list[str]) -> bool:
    """True iff at least one anchor ref lies in the ingested ECM window.

    Pure: no I/O. The ingested apparatus is exactly
    3John.1.1 .. 3John.1.15 (Decision 6). A single in-window anchor is
    enough for the bundle to be "in scope"; only when every anchor is
    outside the window is the apparatus structurally absent.
    """
    for ref in osis_refs:
        m = _ECM_REF_PATTERN.match(ref)
        if m is None:
            continue
        if int(m.group("chapter")) != _ECM_SCOPE_CHAPTER:
            continue
        verse = int(m.group("verse"))
        if _ECM_SCOPE_VERSE_LO <= verse <= _ECM_SCOPE_VERSE_HI:
            return True
    return False


def _query_anchor_lemmas(driver: Driver, refs: list[str]) -> list[dict[str, Any]]:
    cypher = """
    UNWIND $refs AS ref
    MATCH (v:Verse {osisID: ref})<-[:IN_VERSE]-(w:Word)-[:INSTANCE_OF]->(l:Lemma)
    WITH l, count(DISTINCT w) AS local_count
    OPTIONAL MATCH (:Word)-[:INSTANCE_OF]->(l)
    WITH l, local_count, count(*) AS occurrences_in_canon
    RETURN l.strong AS strong,
           l.lemma AS lemma,
           coalesce(l.transliteration, l.lemma) AS transliteration,
           occurrences_in_canon,
           true AS in_anchors
    ORDER BY local_count DESC, occurrences_in_canon DESC, elementId(l)
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(cypher, refs=refs, limit=ANCHOR_LEMMA_LIMIT)
        return [dict(rec) for rec in result]


def _query_anchor_verses(driver: Driver, refs: list[str]) -> list[dict[str, Any]]:
    cypher = """
    UNWIND $refs AS ref
    MATCH (v:Verse {osisID: ref})
    OPTIONAL MATCH (v)<-[:IN_VERSE]-(w:Word)
    OPTIONAL MATCH (w)-[:HAS_MORPHEME]->(m:Morpheme)
    WITH v, w, collect(DISTINCT {morph: coalesce(m.morph, m.morph_code, ''), lemma: m.lemma}) AS morphology
    RETURN v.osisID AS ref,
           collect(DISTINCT {
             surface: w.surface,
             strong: w.strong,
             morphology: morphology
           }) AS words,
           coalesce(v.syntactic_role, '') AS syntactic_role
    """
    with driver.session() as session:
        result = session.run(cypher, refs=refs)
        return [
            {"ref": rec["ref"], "morphology": rec["words"], "syntactic_role": rec["syntactic_role"]}
            for rec in result
        ]


def _query_cross_refs(driver: Driver, refs: list[str]) -> list[dict[str, Any]]:
    cypher = """
    UNWIND $refs AS ref
    MATCH (cr:CrossRef {from_ref: ref})
    RETURN cr.from_ref AS from_ref,
           cr.to_ref AS to_ref,
           coalesce(cr.source, 'openbible') AS source,
           coalesce(cr.votes, 1) AS votes
    ORDER BY votes DESC, elementId(cr)
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(cypher, refs=refs, limit=CROSS_REF_LIMIT)
        return [
            {
                "from": rec["from_ref"],
                "to": rec["to_ref"],
                "source": rec["source"],
                "votes": rec["votes"],
            }
            for rec in result
        ]


def _query_semantic_neighbors(driver: Driver, anchor_strongs: list[str]) -> list[dict[str, Any]]:
    if not anchor_strongs:
        return []
    cypher = """
    UNWIND $strongs AS s
    MATCH (anchor:Lemma {strong: s})
    OPTIONAL MATCH (anchor)-[:LOUW_NIDA_DOMAIN]->(d:LouwNidaDomain)<-[:LOUW_NIDA_DOMAIN]-(neigh:Lemma)
    WHERE neigh.strong <> anchor.strong
    WITH neigh, d
    ORDER BY elementId(neigh), elementId(d)
    LIMIT $limit
    RETURN neigh.strong AS strong,
           neigh.lemma AS lemma,
           d.code AS louw_nida,
           coalesce(neigh.sdbh_domain, '') AS sdbh
    """
    with driver.session() as session:
        result = session.run(cypher, strongs=anchor_strongs, limit=SEMANTIC_NEIGHBOR_LIMIT)
        return [dict(rec) for rec in result]


def _query_variant_units(driver: Driver, refs: list[str]) -> list[dict[str, Any]]:
    cypher = """
    UNWIND $refs AS ref
    MATCH (v:Verse {osisID: ref})-[:HAS_VARIANT]->(vu:Variant)
    OPTIONAL MATCH (vu)-[:HAS_READING]->(rd:Reading)
    WITH v, vu, collect({witness: rd.witness, text: rd.text}) AS readings
    ORDER BY elementId(vu)
    RETURN v.osisID AS ref,
           vu.id AS variant_id,
           readings
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(cypher, refs=refs, limit=VARIANT_LIMIT)
        return [
            {"ref": rec["ref"], "variant_id": rec["variant_id"], "readings": rec["readings"]}
            for rec in result
        ]


def _query_syntactic_context(driver: Driver, refs: list[str]) -> list[dict[str, Any]]:
    cypher = """
    UNWIND $refs AS ref
    MATCH (v:Verse {osisID: ref})
    OPTIONAL MATCH (v)-[:HAS_CLAUSE]->(c:Clause)
    OPTIONAL MATCH (c)-[:HAS_PHRASE]->(p:Phrase)
    WITH v, c, p
    ORDER BY elementId(v), elementId(c), elementId(p)
    RETURN v.osisID AS ref,
           coalesce(c.text, '') AS clause,
           coalesce(p.text, '') AS phrase,
           coalesce(p.etcbc_function, '') AS etcbc_function
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(cypher, refs=refs, limit=SYNTACTIC_LIMIT)
        return [dict(rec) for rec in result]


def build_lexical_context_bundle(
    question_id: str, settings: Settings | None = None
) -> dict[str, Any]:
    """Construct the lexical bundle for one question."""
    question = load_question(question_id)
    osis_refs = _anchor_refs(question)

    if settings is None:
        settings = Settings()  # type: ignore[call-arg]
    driver = get_lexical_driver(settings)
    try:
        anchor_lemmas = _query_anchor_lemmas(driver, osis_refs)
        anchor_strongs = [al["strong"] for al in anchor_lemmas]
        anchor_verses = _query_anchor_verses(driver, osis_refs)
        cross_refs = _query_cross_refs(driver, osis_refs)
        semantic_neighbors = _query_semantic_neighbors(driver, anchor_strongs)
        variant_units = _query_variant_units(driver, osis_refs)
        syntactic_context = _query_syntactic_context(driver, osis_refs)
    finally:
        driver.close()

    # RESEED_PLAN F.1 invariant 4: anchors outside the ingested ECM
    # window (3John.1.1 .. 3John.1.15, Decision 6) have no variant
    # apparatus by construction. Declare that structurally rather than
    # leave an unexplained empty variant_units. Variant population logic
    # above is unchanged; this only adds the honest scope flag.
    not_in_ecm_scope = not _in_ecm_scope(osis_refs)

    return {
        "question_id": question_id,
        "question_statement": question["statement"],
        "question_metadata": {
            "category": question.get("category"),
            "subcategory": question.get("subcategory"),
            "kind": question.get("kind"),
            "scripture_anchors": question.get("scripture_anchors", []),
            "historical_consensus": question.get("historical_consensus"),
            "brethren_distinctive": question.get("brethren_distinctive", False),
        },
        "lexical_context_bundle": {
            "anchor_lemmas": anchor_lemmas,
            "anchor_verses": anchor_verses,
            "cross_refs": cross_refs,
            "semantic_domain_neighbors": semantic_neighbors,
            "variant_units": variant_units,
            "not_in_ecm_scope": not_in_ecm_scope,
            "syntactic_context": syntactic_context,
        },
        "schema_version": "3.0",
    }
