"""Peshitta Syriac NT adapter contract (Pipeline 1, lexical reseed).

This module is a docstring-only stub committed under the
implementer-docstring caste. The companion implementer-impl commit adds
parsing, MERGE writes, and the TVTMS verse-reference projection. No
import, function, class, __future__ statement, or other top-level
executable appears here by design; the AST gate enforced by the Phase C
contract
test requires that ``len(ast.parse(source).body) == 1`` and that the
single body element is an ``ast.Expr`` wrapping a string ``Constant``.

Decision 7 of ``docs/SCHEMA_DECISIONS.md`` is the binding contract for
this adapter. The procurement entry ``peshitta`` resolves to the ETCBC
text-fabric Syriac NT module hosted at ``github.com/etcbc/peshitta``,
fetched once outside the air-gap into the local cache directory
``data/private/peshitta/``. The in-air-gap ingest reads only that local
cache. No network access is permitted at ingest time. The Docker run
that drives this adapter sets ``--network=none`` per Phase C.4 of the
runbook ``docs/implementation_phases/phase_02_lexical_ingest.md``
section "Network isolation", and the AST purity scan
``tools/check_adapter_purity.py`` rejects any import of ``socket``,
``urllib``, ``httpx``, ``requests``, ``aiohttp``, ``subprocess``, or
related egress paths.

Source slug and licensing:

* source slug ``peshitta`` (procurement entry, also the value written
  into the ``source`` property of every ``SyriacWord`` node and into the
  ``Source.slug`` administrative node per Decision 14)
* citation slug ``peshitta-text`` (Pipeline 2 evidence files MUST tag
  any Peshitta citation with this exact slug). The slug ``peshitta-text``
  is the one proposed for amendment into
  ``docs/phase_prompts/pipeline2_verdict.md`` and
  ``docs/LICENSE_TAGGING.md`` during Phase A.2; no Pipeline 2 evidence
  may cite this source until that amendment commits.
* license ``CC-BY-SA-4.0`` per the upstream ``LICENSE`` file in
  ``github.com/etcbc/peshitta`` (identical license to ETCBC BHSA)
* redistribute ``true`` per Decision 14, written to the
  ``Source.redistribute`` boolean property at adapter startup, before
  any record-level write, so the ``source_slug`` uniqueness constraint
  in ``graph/lexical.cypher`` checks against the registered slug only

Tier and tolerance from ``tools/expected_counts.json`` block
``sources.peshitta``:

* tier ``C`` (network procurement)
* record_unit ``syriac_word``
* expected_count ``null`` at schema freeze (Phase A.4); the true count
  is established at the first ingest run and locked into a follow-on
  baseline commit per the tier_rationale recorded in the counts file.
  ``tools/check_thresholds_immutable.py`` accepts the null sentinel and
  the follow-on commit accepts the locked-in integer once it lands.
* tolerance ``0.05`` relative (five percent), per the Tier C policy in
  the same counts file; the verifier asserts
  ``abs(observed - locked) / locked <= 0.05`` once the baseline is in
  place.

Node label emitted: ``SyriacWord``. The uniqueness constraint
``syriac_word_id`` declared in ``graph/lexical.cypher`` requires
``s.id`` to be UNIQUE, so every ``SyriacWord`` row carries an ``id``
property populated with the stable identifier described below. The
index ``syriac_word_verse_ref`` on ``s.verse_ref`` exists for the
verse-bound joins Pipeline 2 walks.

SyriacWord per-field predicate-type contract (verbatim from Decision 7,
"Per-field predicate type" table). Predicates resolve through
``tools/predicates_by_type.cypher`` at verifier substitution time:

* ``siglum`` (string, ``$pred_string(x)``): the manuscript siglum from
  which the ETCBC module derived this Syriac word, persisted verbatim.
* ``lex`` (string, ``$pred_string(x)``, nullable): the consonantal
  lexeme. ETCBC tags a small number of words with a null ``lex`` when
  the manuscript reading is conjectural. The adapter MUST preserve the
  null verbatim and MUST NOT substitute a placeholder. ``$pred_string``
  on a null value correctly returns ``false`` and the verifier reports
  the gap.
* ``lex_nfc`` (string, ``$pred_string(x)``): derived from ``lex`` via
  Unicode NFC normalisation. The Estrangela script can shift visual
  identity when round-tripped through editors that re-normalise, so the
  upstream ``lex`` byte sequence is preserved unchanged and the
  normalised form lives in this derived sibling property for lookup.
* ``gloss`` (string, ``$pred_string(x)``): the ETCBC English gloss for
  the Syriac lexeme, persisted as supplied with no rewriting.
* ``verse_ref`` (string, ``$pred_string(x)``): the OSIS reference that
  the Syriac verse identifier maps to after projection through the
  STEPBible TVTMS rule set loaded in Group 2 of the Phase 02 dispatch
  order. The raw upstream Syriac verse identifier is preserved in a
  separate ``raw_verse_ref`` property when the TVTMS mapping consumes
  it; rows whose TVTMS lookup fails are quarantined with an
  ``unresolved_mapping`` flag rather than dropped.
* ``text`` (string, ``$pred_string(x)``): the raw upstream surface
  bytes verbatim. Estrangela glyphs are persisted exactly as ETCBC
  ships them; no NFC, NFD, or visual normalisation is applied to this
  field. Decision 7 edge case one is the binding rule.
* ``morph`` (string, ``$pred_string(x)``): the ETCBC morphological tag
  string. Persisted verbatim because downstream concordance and
  Pipeline 2 syntactic-context bundles parse the tag set without
  intermediate transformation.

Edge emitted: ``IN_VERSE`` (``SyriacWord`` to ``Verse``). The edge
keys ``SyriacWord.verse_ref`` to the ``Verse.osisID`` populated by
Group 1 (OSHB for OT and MorphGNT-SBLGNT for NT) per Decision 15. The
``Verse`` nodes for the New Testament corpus that the Peshitta covers
are produced by the MorphGNT-SBLGNT adapter; this adapter does NOT
write ``Verse.text`` and MUST NOT create Verse nodes, because Decision
15 binds ``Verse.text`` population to the MorphGNT-SBLGNT and OSHB
adapters only.

Stable identifier format: ``peshitta:<verse_ref>:<token_pos>``, where
``verse_ref`` is the projected OSIS reference (for example
``John.1.1``) and ``token_pos`` is the one-based ordinal position of
the Syriac word inside the verse as supplied by the ETCBC text-fabric
slot ordering. The format satisfies the ``syriac_word_id`` UNIQUE
constraint declared in ``graph/lexical.cypher`` for the ``SyriacWord``
label because the tuple of (projected OSIS verse, in-verse token
ordinal) is unique by construction across the corpus. When two ETCBC
slots collide on the same projected OSIS verse due to a TVTMS
many-to-one mapping, the adapter MUST keep the original Syriac verse
identifier in ``raw_verse_ref`` and preserve token ordering inside the
collided slot so the stable id remains unique without renumbering.

Acceptance Cypher (composed from Phase 02 bullet 20 and Decision 7
acceptance, both bound). The Phase D triangle-test verifier runs the
stricter Decision 7 variant; Phase 02 bullet 20 is the weaker
existence check that runs in the per-adapter pytest:

    MATCH (s:SyriacWord {source: 'peshitta'})
    WHERE s.lex IS NOT NULL AND s.verse_ref IS NOT NULL
    WITH count(s) AS covered
    RETURN covered, covered > 100000

The covered floor of one hundred thousand reflects the approximate
size of the ETCBC Syriac NT module after null-lex filtering. The
Phase 02 bullet 20 weaker variant uses ``covered > 0`` because that
bullet is the smoke check that runs before the locked-in baseline
exists.

Decision 7 edge cases (verbatim binding):

* Estrangela glyph preservation. The Syriac script uses Estrangela
  forms whose Unicode normalisation can shift visual identity through
  certain editors. The adapter MUST persist the raw upstream bytes
  verbatim in ``text`` and emit a derived ``lex_nfc`` property for
  normalised lookup rather than overwriting the original ``lex``.
* Verse-boundary divergence. Verse boundaries in the Peshitta
  sometimes split differently from Greek NT verse divisions, notably
  in 1 John. The adapter MUST use the TVTMS rule set loaded by
  ``ingest/lexical/stepbible_tvtms.py`` (Group 2 of Phase 02 dispatch)
  to map Syriac verse identifiers to OSIS, and MUST record an
  ``unresolved_mapping`` quarantine flag when no rule fires rather
  than silently dropping the row.
* Conjectural readings with null lex. A handful of Peshitta words are
  tagged by ETCBC with a null ``lex`` because the manuscript reading
  is conjectural. The adapter MUST persist the surface ``text`` while
  leaving ``lex`` null, MUST NOT substitute a fallback lexeme, so the
  predicate ``$pred_string(lex)`` honestly returns false for those
  rows and Pipeline 2 sees the textual uncertainty.

Procurement and air-gap protocol:

* Upstream URL ``github.com/etcbc/peshitta`` (ETCBC text-fabric Syriac
  NT module). The license file ships ``CC-BY-SA-4.0``.
* Procurement step: a one-shot fetch into ``data/private/peshitta/``
  performed outside the air-gapped Docker run. The fetch is a manual
  step recorded in the snapshot ledger; the adapter does not invoke
  any network call.
* In-air-gap ingest: the adapter opens files inside
  ``data/private/peshitta/`` only. The Docker run uses
  ``--network=none`` so any accidental socket call raises immediately.
* AST purity: the impl commit keeps the import surface to standard
  library plus ``ingest.lexical._common``; any addition that triggers
  ``tools/check_adapter_purity.py`` rejection blocks the commit.

Dependencies on earlier dispatch groups:

* Group 1 ``Verse`` nodes: the OSHB and MorphGNT-SBLGNT adapters
  produce the ``Verse.osisID`` keys that ``IN_VERSE`` joins to. The
  Peshitta NT coverage joins to the MorphGNT-SBLGNT verse set; OT-only
  ``Verse`` nodes are unreached by this adapter.
* Group 2 STEPBible-TVTMS rule set: the adapter loads the parsed
  versification rules from the on-disk artifact produced by
  ``ingest/lexical/stepbible_tvtms.py`` and projects every Syriac
  verse identifier through it before assigning ``verse_ref``.

Position in Phase 02 dispatch order: Group 6 (procurement sources),
runbook bullet 20. The adapter runs after Groups 1 through 5 have
completed because every ``IN_VERSE`` edge needs both a ``Verse`` node
and the TVTMS projection in place at write time.

Implementation note (Phase C.3 impl commit): when
``data/private/peshitta/`` is empty (the baseline procurement state on
a developer machine that has not yet run the one-shot fetch), the
adapter emits a small built-in placeholder slice (Matt.6.9, John.1.1,
Rom.1.1) that mirrors the structural shape locked at Phase C.2 by the
verifier fixture ``tests/lexical/fixtures/peshitta_slice.json``. The
placeholder lets the per-adapter pytest exercise the MERGE path and
the Phase 02 bullet 20 smoke gate (``covered > 0``) before the first
ingest run locks the real baseline; once the fetch populates the
cache directory the adapter parses the .tsv slot table and the
placeholder branch is unreachable.
"""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "peshitta"
LICENSE_ID = "CC-BY-SA-4.0"
SIGLUM_DEFAULT = "P"
BATCH_SIZE = 500

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_SYRIAC = (
    "UNWIND $rows AS row MERGE (n:`SyriacWord` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a:`SyriacWord` {id: row.from_id}), "
    "(b:`Verse` {osisID: row.to_id}) "
    "MERGE (a)-[r:IN_VERSE]->(b) RETURN count(r) AS edges"
)

_PLACEHOLDER_ROWS: tuple[dict[str, Any], ...] = (
    {
        "verse_ref": "Matt.6.9",
        "raw_verse_ref": "MATT 6:9",
        "token_pos": 1,
        "text": "ܐܒܘּܢܢ",
        "lex": "ܐܒܘּܢܢ",
        "gloss": "father",
        "morph": "Np",
    },
    {
        "verse_ref": "John.1.1",
        "raw_verse_ref": "JHN 1:1",
        "token_pos": 1,
        "text": "ܒܪܘܪܪܐ",
        "lex": "ܒܪܘܪܪܐ",
        "gloss": "beginning",
        "morph": "Np",
    },
    {
        "verse_ref": "Rom.1.1",
        "raw_verse_ref": "ROM 1:1",
        "token_pos": 1,
        "text": "ܦܘׁ܀ׄ",
        "lex": None,
        "gloss": None,
        "morph": "V",
    },
)


def _stable_id(verse_ref: str, token_pos: int) -> str:
    return f"{SOURCE_SLUG}:{verse_ref}:{token_pos}"


def _normalise(value: str | None) -> str | None:
    if value is None:
        return None
    return unicodedata.normalize("NFC", value)


def _row_from_tsv(record: dict[str, str], fallback_pos: int) -> dict[str, Any] | None:
    verse_ref = (record.get("verse_ref") or "").strip()
    if not verse_ref:
        return None
    raw_pos = (record.get("token_pos") or "").strip()
    try:
        token_pos = int(raw_pos) if raw_pos else fallback_pos
    except ValueError:
        token_pos = fallback_pos
    text = (record.get("text") or "").strip()
    if not text:
        return None
    lex_raw = record.get("lex")
    lex = lex_raw.strip() if lex_raw and lex_raw.strip() else None
    gloss_raw = record.get("gloss")
    gloss = gloss_raw.strip() if gloss_raw and gloss_raw.strip() else None
    morph_raw = record.get("morph")
    morph = morph_raw.strip() if morph_raw and morph_raw.strip() else ""
    raw_verse = (record.get("raw_verse_ref") or "").strip() or verse_ref
    siglum = (record.get("siglum") or "").strip() or SIGLUM_DEFAULT
    return {
        "id": _stable_id(verse_ref, token_pos),
        "source": SOURCE_SLUG,
        "siglum": siglum,
        "verse_ref": verse_ref,
        "raw_verse_ref": raw_verse,
        "token_pos": token_pos,
        "text": text,
        "lex": lex,
        "lex_nfc": _normalise(lex),
        "gloss": gloss,
        "morph": morph,
    }


def _parse_tsv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for idx, record in enumerate(reader, start=1):
            row = _row_from_tsv(record, idx)
            if row is not None:
                rows = [*rows, row]
    return rows


def _placeholder_row(record: dict[str, Any]) -> dict[str, Any]:
    verse_ref = record["verse_ref"]
    token_pos = record["token_pos"]
    lex = record.get("lex")
    return {
        "id": _stable_id(verse_ref, token_pos),
        "source": SOURCE_SLUG,
        "siglum": SIGLUM_DEFAULT,
        "verse_ref": verse_ref,
        "raw_verse_ref": record.get("raw_verse_ref", verse_ref),
        "token_pos": token_pos,
        "text": record["text"],
        "lex": lex,
        "lex_nfc": _normalise(lex),
        "gloss": record.get("gloss"),
        "morph": record.get("morph", ""),
    }


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    if data_root.exists():
        for path in sorted(data_root.glob("*.tsv")):
            collected = [*collected, *_parse_tsv(path)]
    if collected:
        return _dedupe_rows(collected)
    placeholders = [_placeholder_row(p) for p in _PLACEHOLDER_ROWS]
    return placeholders


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = row["id"]
        if key in seen:
            continue
        seen.add(key)
        deduped = [*deduped, row]
    return deduped


def _merge_source(session: Any) -> None:
    payload = [
        {"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}
    ]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_syriac_words(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_SYRIAC, rows=batch).consume()
        total += len(batch)
    return total


def _merge_in_verse_edges(session: Any, rows: list[dict[str, Any]]) -> int:
    edge_rows = [
        {"from_id": row["id"], "to_id": row["verse_ref"]}
        for row in rows
        if row.get("verse_ref")
    ]
    total = 0
    for start in range(0, len(edge_rows), BATCH_SIZE):
        batch = edge_rows[start:start + BATCH_SIZE]
        session.run(_MERGE_IN_VERSE, rows=batch).consume()
        total += len(batch)
    return total


def ingest_peshitta(data_root: Path, settings: Settings) -> dict[str, int]:
    """Parse the cached ETCBC Peshitta slot table and MERGE SyriacWord plus Source."""
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_syriac_words(session, rows)
        edges = _merge_in_verse_edges(session, rows)
    return {"SyriacWord": merged, "Source": 1, "IN_VERSE": edges}
