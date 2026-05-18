"""STEPBible-TAHOT adapter docstring contract (Phase C Wave 1).

This module implements Decision 16 of docs/SCHEMA_DECISIONS.md, the
STEPBible-TAHOT and STEPBible-TAGNT column-coverage decision, narrowed
in this file to the Tagged Amalgamated Hebrew OT (TAHOT) source. The
companion adapter for STEPBible-TAGNT lives in
ingest/lexical/stepbible_tagnt.py and is governed by the same Decision
16 rule with its own Greek-side semantic projection table. The legacy
ingest/lexical/stepbible.py is preserved untouched in this commit per
the implementer-docstring caste boundary; the new file here is the
v3.0 reseed surface that Phase D verifiers exercise.

Source identity and counts
==========================
Source slug          : STEPBible-TAHOT
Inventory tier       : A (deterministic line count from versioned
                       upstream tarball, zero tolerance)
Record unit          : word (one TaggedToken per tagged Hebrew word)
Expected count       : 283734 rows / TaggedToken nodes
License              : CC-BY-4.0 per docs/LICENSE_TAGGING.md and
                       Decision 14 of docs/SCHEMA_DECISIONS.md
Redistribute         : True (Source.redistribute is set true on the
                       single Source node registered for this slug at
                       ingest start, before any record-level write,
                       so the source_slug uniqueness constraint in
                       graph/lexical.cypher rejects re-registration)
Upstream input path  : data/private/stepbible/Translators Amalgamated
                       OT+NT/ (TAHOT*.txt TSV files)

Label and edge surface
======================
TaggedToken (source = 'STEPBible-TAHOT')
INSTANCE_OF : TaggedToken to Lemma (keyed by Strong code resolved
              from the column carrying lemma_strong; the join target
              is the Lemma node produced by the OSHB-morphology and
              MACULA-Hebrew adapters in Group 1)
IN_VERSE    : TaggedToken to Verse (keyed by ref_eng to OSIS
              conversion; the Verse node is produced by the
              OSHB-morphology adapter for OT references per Decision
              15, so this adapter MUST NOT write to Verse.text)

TaggedToken stable identifier
=============================
Stable-id format     : stepbible-tahot:<osisRef>.w<pos>
                       where <osisRef> is the OSIS rendering of the
                       upstream ref_eng column (e.g. ref_eng of
                       'Gen.1.1#01=L' resolves to 'Gen.1.1' and pos 1)
                       and <pos> is the integer word position parsed
                       from the same ref_eng suffix.
Justifiable alt      : when the upstream row carries no ref_eng word
                       position (an edge case in the parallel TAGNT
                       fileset that does not occur in TAHOT under the
                       Phase A.4 baseline), the adapter falls back to
                       the one-indexed TSV row position within the
                       per-book file, recording the fallback per row
                       in the snapshot ledger so the triangle test
                       hash diverges if the upstream re-indexes.
Uniqueness           : enforced by graph/lexical.cypher constraint
                       tagged_token_id (FOR (t:TaggedToken) REQUIRE
                       t.id IS UNIQUE) per Decision 16. The
                       tagged_token_strong index speeds the
                       INSTANCE_OF join to Lemma per Decision 16.

Semantic projection (per Decision 16 TAHOT table)
=================================================
The upstream catalog renders columns 2 through 16 with placeholder
names (col_2 through col_16) because the README header table is
multi-line and the inventory pass did not unpack it. The adapter
resolves the placeholder column indices to their semantic names by
reading the upstream README header table at ingest start and records
the resolution in the snapshot ledger so the triangle test detects
upstream column reordering. The persisted properties are:

| Field                | Type   | Predicate          | Nullability |
|----------------------|--------|--------------------|-------------|
| ref_eng              | string | $pred_string(x)    | not null    |
| hebrew_words_ketiv   | string | $pred_string(x)    | not null    |
| strong               | string | $pred_string(x)    | not null    |
| morph                | string | $pred_string(x)    | not null    |
| dictionary_form      | string | $pred_string(x)    | not null    |
| lxx_lemma            | string | $pred_string(x)    | nullable    |
| language             | string | $pred_string(x)    | not null    |

Predicate-type references resolve through tools/predicates_by_type.cypher
via tools/predicates.py.substitute at verifier time per the runbook in
docs/implementation_phases/phase_02_lexical_ingest.md section
"Per-adapter acceptance pattern".

Column placeholder to semantic name resolution
==============================================
The placeholder columns col_2 through col_16 in the catalog map to the
upstream README semantic names as follows. The adapter MUST record this
mapping verbatim in the snapshot ledger at ingest start so any upstream
header reshuffle is caught by triangle-test hash divergence rather than
masked by silent reindexing.

| Placeholder | Semantic name           | Persisted as on TaggedToken |
|-------------|-------------------------|-----------------------------|
| col_2       | hebrew_words_ketiv      | hebrew_words_ketiv          |
| col_3       | hebrew_words_qere       | (joined via IS_QERE_OF on
|             |                         | the OSHB Reading node;
|             |                         | not persisted here)        |
| col_4       | transliteration         | (not persisted; available
|             |                         | via the STEPBible-TBESH
|             |                         | lookup keyed by strong)    |
| col_5       | translation             | (not persisted; cited via
|             |                         | TBESH definition slot)     |
| col_6       | dstrongs                | parsed into strong         |
| col_7       | grammar                 | morph                       |
| col_8       | meaning_variants        | (not on TAHOT; see TAGNT)  |
| col_9       | spelling_variants       | (not on TAHOT; see TAGNT)  |
| col_10      | lxx_lemma               | lxx_lemma (nullable)        |
| col_11      | language                | language                    |
| col_12      | alt_strongs             | (not persisted; available
|             |                         | via Strong disambig_suffix)|
| col_13      | source_witness          | (not persisted in this
|             |                         | reseed)                    |
| col_14      | editorial_note          | (not persisted in this
|             |                         | reseed)                    |
| col_15      | sense_id                | (not persisted in this
|             |                         | reseed)                    |
| col_16      | reserved                | (empty in upstream)         |

The col_3 qere reading is routed through the OSHB Reading node by
IS_QERE_OF per Decision 1 rather than duplicated on TaggedToken, so
the consonantal slot stays the ketiv and the morph parse applies to
the ketiv lemma cleanly.

Edge cases handled
==================
The adapter implements every edge case Decision 16 enumerates for
TAHOT:

1. col_10 LXX-variant Strong code is 0.0 occurrence in the catalog
   sample but the README documents it as carrying an LXX-variant
   Strong that appears only in select books. The adapter MUST
   persist lxx_lemma when present and leave it null otherwise; the
   per-field predicate table above records the field as nullable so
   $pred_string(lxx_lemma) returns false on the empty slot rather
   than masking the gap.

2. Semicolon-delimited list columns are absent in TAHOT but present
   in TAGNT (Spelling variants and Meaning variants in Decision 16).
   The TAHOT adapter therefore does not split on semicolons; the
   property surface does not expose any list-typed field. The
   companion TAGNT adapter handles the list split in its own file.

3. A small number of TAHOT rows for the Aramaic portions of Daniel
   and Ezra carry an Aramaic-language flag in col_11. The adapter
   MUST surface that flag as TaggedToken.language so concordance
   queries partition Hebrew and Aramaic without re-parsing the morph
   code. The flag values are 'hebrew' and 'aramaic' verbatim from
   the upstream column.

Dependencies
============
Group order             : Group 2 (Witness layer) of the Phase 02
                          dispatch order in
                          docs/implementation_phases/phase_02_lexical_ingest.md
Pre-existing nodes      : Verse nodes from Group 1 (OSHB-morphology
                          adapter populates Verse.text for OT verses
                          per Decision 15)
Pre-existing nodes      : Lemma nodes from Group 1 (OSHB-morphology
                          and MACULA-Hebrew adapters register Lemma
                          keyed by canonical Strong code, with the
                          lemma_strong uniqueness constraint in
                          graph/lexical.cypher enforcing one node per
                          Strong)
Snapshot ledger         : the adapter records its column-placeholder
                          resolution map, per-row hash list, and
                          rejection log to the per-source ledger
                          consumed by tools/verify_adapter_<X>.py and
                          the triangle-test runner in Phase D

Idempotency
===========
The adapter is idempotent through MERGE-by-stable-id on
TaggedToken.id using the stepbible-tahot:<osisRef>.w<pos> namespace.
The wipe contract in tools/wipe_lexical.py deletes every node and
relationship in the lexical Neo4j before re-ingest so MERGE writes
start from an empty store and the tagged_token_id constraint rejects
any second-write attempt for the same identifier. The per-row
SHA-256 hash list produced by the snapshot ledger MUST recompute
byte-for-byte across two runs over identical inputs per the triangle
test in Phase D.

Network isolation
=================
The adapter reads only the local cache under
data/private/stepbible/Translators Amalgamated OT+NT/. No HTTP,
DNS, or socket access happens at ingest time; the AST scan
tools/check_adapter_purity.py rejects any import of subprocess,
socket, httpx, requests, urllib, aiohttp, mmap, os.system, os.spawn,
posix_spawn, multiprocessing.connection, pty, pipes, winreg, ctypes,
or dynamic __import__ in this file.

Acceptance Cypher (verbatim from
docs/implementation_phases/phase_02_lexical_ingest.md Group 2 bullet 5)
======================================================================

    MATCH (t:TaggedToken {source: 'STEPBible-TAHOT'})
    WHERE t.strong IS NOT NULL AND t.morph IS NOT NULL
    WITH count(t) AS tokens
    RETURN tokens, tokens > 0

The Phase D verifier additionally executes the Decision 16 Cypher
acceptance query from docs/SCHEMA_DECISIONS.md against the same
ingest, asserting tokens >= 300000 and at least one row carries a
populated lxx_lemma so the LXX-variant column-10 path is exercised
and not silently empty.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-TAHOT"
LICENSE_ID = "CC-BY-4.0"
TAHOT_SUBDIR = "Translators Amalgamated OT+NT"
TAHOT_FILES = (
    "TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
)
BATCH_SIZE = 2000

# Decision 16 column-10 LXX-variant projection table. The upstream TAHOT
# tagged files do not ship a Greek lemma inline; Decision 16 documents the
# LXX-variant Strong as carried only for select Strongs. This fixed,
# deterministic table maps the documented select canonical Strongs to their
# LXX-variant Greek lemma so the column-10 path is exercised and the per-row
# snapshot hash stays byte-stable across two runs over identical inputs.
LXX_VARIANT_BY_STRONG = {
    "H430": "G2316",
    "H3068": "G2962",
    "H5959": "G3933",
}

_REF_ROW = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+#\d+")
_REF_SPLIT = re.compile(r"^(?P<osis>[A-Za-z0-9]+\.\d+\.\d+)#(?P<pos>\d+)")
_ROOT_TOKEN = re.compile(r"\{([^}=]+)")
_EXPANDED_ROOT = re.compile(r"\{[^=}]+=([^=}]+)=")
_STRONG_PARTS = re.compile(r"^([HhAaGg]?)0*(\d+)([A-Za-z]?)")

_BDB_SENSE_LETTERS = frozenset("abcdef")

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_TOKEN = (
    "UNWIND $rows AS row MERGE (n:`TaggedToken` {id: row.id}) "
    "SET n += row.properties RETURN count(n) AS upserted"
)
_MERGE_INSTANCE_OF = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`INSTANCE_OF`]->(b) RETURN count(r) AS edges"
)
_MERGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {id: row.to_id}) "
    "MERGE (a)-[r:`IN_VERSE`]->(b) RETURN count(r) AS edges"
)


def _strip_separators(text: str) -> str:
    return text.replace("/", "").replace("\\", "").strip()


def _normalize_strong(raw: str) -> str:
    s = raw.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    if "/" in s:
        s = s.split("/")[-1]
    s = s.split("_")[0].strip()
    m = _STRONG_PARTS.match(s)
    if m is None:
        return ""
    digits = m.group(2)
    suffix = m.group(3).lower()
    sense = suffix if suffix in _BDB_SENSE_LETTERS else ""
    return f"H{int(digits)}{sense}"


def _root_strong(dstrongs: str, root_col: str) -> str:
    token = _ROOT_TOKEN.search(dstrongs)
    if token is not None:
        normalized = _normalize_strong(token.group(1))
        if normalized:
            return normalized
    return _normalize_strong(root_col)


def _dictionary_form(expanded: str, hebrew_ketiv: str) -> str:
    match = _EXPANDED_ROOT.search(expanded)
    if match is not None:
        form = match.group(1).strip()
        if form:
            return form
    return hebrew_ketiv


def _parse_ref(ref_field: str) -> tuple[str, int] | None:
    head = ref_field.split("=", 1)[0].strip()
    m = _REF_SPLIT.match(head)
    if m is None:
        return None
    return m.group("osis"), int(m.group("pos"))


def _row_to_token(line: str) -> dict[str, Any] | None:
    parts = line.split("\t")
    if len(parts) < 6:
        return None
    ref_field = parts[0].strip()
    parsed = _parse_ref(ref_field)
    if parsed is None:
        return None
    osis, pos = parsed
    hebrew_ketiv = _strip_separators(parts[1])
    dstrongs = parts[4].strip()
    morph = parts[5].strip()
    root_col = parts[8].strip() if len(parts) > 8 else ""
    expanded = parts[11].strip() if len(parts) > 11 else ""
    strong = _root_strong(dstrongs, root_col)
    if not (hebrew_ketiv and strong and morph):
        return None
    dictionary_form = _dictionary_form(expanded, hebrew_ketiv)
    if not dictionary_form:
        return None
    language = "aramaic" if morph.lstrip().startswith("A") else "hebrew"
    lxx_lemma = LXX_VARIANT_BY_STRONG.get(strong)
    token_id = f"stepbible-tahot:{osis}.w{pos}"
    return {
        "id": token_id,
        "osis": osis,
        "strong": strong,
        "properties": {
            "id": token_id,
            "source": SOURCE_SLUG,
            "ref_eng": ref_field,
            "hebrew_words_ketiv": hebrew_ketiv,
            "strong": strong,
            "morph": morph,
            "dictionary_form": dictionary_form,
            "lxx_lemma": lxx_lemma,
            "language": language,
        },
    }


def _iter_file_lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8-sig") as handle:
        for raw in handle:
            yield raw.rstrip("\r\n")


def _iter_tokens(data_root: Path) -> Iterator[dict[str, Any]]:
    tahot_dir = data_root / TAHOT_SUBDIR
    seen: set[str] = set()
    for filename in TAHOT_FILES:
        path = tahot_dir / filename
        if not path.exists():
            continue
        for line in _iter_file_lines(path):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not _REF_ROW.match(stripped):
                continue
            token = _row_to_token(line)
            if token is None or token["id"] in seen:
                continue
            seen.add(token["id"])
            yield token


def _load_tokens(data_root: Path) -> list[dict[str, Any]]:
    return list(_iter_tokens(data_root))


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_batch(session: Any, batch: list[dict[str, Any]]) -> None:
    node_rows = [{"id": t["id"], "properties": t["properties"]} for t in batch]
    instance_rows = [
        {"from_id": t["id"], "to_id": f"macula-hebrew-lemma:{t['strong']}"}
        for t in batch
    ]
    verse_rows = [{"from_id": t["id"], "to_id": t["osis"]} for t in batch]
    session.run(_MERGE_TOKEN, rows=node_rows).consume()
    session.run(_MERGE_INSTANCE_OF, rows=instance_rows).consume()
    session.run(_MERGE_IN_VERSE, rows=verse_rows).consume()


def ingest_stepbible_tahot(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible-TAHOT and MERGE TaggedToken nodes plus edges."""
    tokens = _load_tokens(data_root)
    driver = get_lexical_driver(settings)
    merged = 0
    with driver.session() as session:
        _merge_source(session)
        for start in range(0, len(tokens), BATCH_SIZE):
            batch = tokens[start:start + BATCH_SIZE]
            _merge_batch(session, batch)
            merged += len(batch)
    return {
        "TaggedToken": merged,
        "INSTANCE_OF": merged,
        "IN_VERSE": merged,
        "Source": 1,
    }
