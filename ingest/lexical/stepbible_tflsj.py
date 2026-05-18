"""STEPBible TFLSJ (LSJ extract) lexical adapter docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-up commit by the implementer-impl
caste. This file freezes the per-field schema contract, edge contract,
stable identifier format, license posture, and acceptance Cypher block
so the verifier caste can build conformance tests against a stable
specification.

============================================================
1. Scope and source slug
============================================================

The adapter ingests one upstream source.

Source slug `STEPBible-TFLSJ`:
  tier A, record unit lemma, expected count 11034, tolerance 0,
  minimum 11034, maximum 11034. Tier A means the count is a
  deterministic line count from the versioned upstream release used at
  ingest, identical across reruns under tagged builds, and any
  deviation fails the acceptance gate. License `CC-BY-4.0` per
  `docs/LICENSE_TAGGING.md` row `STEPBible-TFLSJ` (LSJ formatted
  subset), redistribute true per Decision 14. The slug is also
  persisted as the value of every `LsjEntry.source` property and as
  the `Source.slug` value of the one `Source` node this adapter
  registers.

The upstream input path is `data/private/stepbible/Lexicons` per
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 10. The
upstream ships one row per LSJ-keyed Greek lemma with the columns
`strong`, `lemma`, `transliteration`, `pos`, `english`,
`lsj_definition`, plus two residual columns `col_6` and `col_7` that
the upstream uses for cross-reference annotations and that the
adapter does not persist as named fields.

============================================================
2. Decision implemented (Decision 13)
============================================================

Decision 13: STEPBible-TFLSJ (LSJ extract) node shape.
  STEPBible-TFLSJ carries `strong`, `lemma`, `transliteration`, `pos`,
  `english` at occurrence rate 0.991, and `lsj_definition` at
  occurrence rate 0.896. The adapter MUST emit one `LsjEntry` node per
  row keyed by `strong` plus `lemma` together because `strong` is not
  unique across LSJ sub-entries. The `lsj_definition` is treated as a
  long-form prose field cited under the `STEPBible-TFLSJ` slug. The
  per-field predicate table marks `english` and `lsj_definition` as
  nullable on their respective occurrence rates.

Decision 14 dependency: the adapter registers exactly one `Source`
node before any record-level write, with `slug = 'STEPBible-TFLSJ'`,
`license = 'CC-BY-4.0'`, `redistribute = true`. The Source uniqueness
constraint `source_slug` in `graph/lexical.cypher` is the gate that
prevents duplicate registration. No `TFNode` writes happen in this
adapter.

============================================================
3. Emitted node label (with property name, type, predicate)
============================================================

Label `LsjEntry` (one node per row):

  Stable id: `tflsj:<strong>:<lemma>`. The format combines the
  upstream `strong` and `lemma` fields with the source-prefix `tflsj:`
  so the `lsj_entry_id` constraint
  (`CREATE CONSTRAINT lsj_entry_id IF NOT EXISTS FOR (e:LsjEntry)
  REQUIRE e.id IS UNIQUE` in `graph/lexical.cypher`, Decision 13) is
  satisfied even though `strong` is not unique across LSJ sub-entries.
  The two-part key (`strong` plus `lemma`) is Decision 13's binding
  resolution to the non-unique-`strong` constraint and the graph-side
  uniqueness lives on the derived `id` property rather than on
  `strong` alone.

  Per Decision 13 per-field predicate table:
  | Field            | Type   | Predicate         |
  |------------------|--------|-------------------|
  | strong           | string | $pred_string(x)   |
  | lemma            | string | $pred_string(x)   |
  | lemma_unaccented | string | $pred_string(x)   |
  | transliteration  | string | $pred_string(x)   |
  | pos              | string | $pred_string(x)   |
  | english          | string | $pred_string(x)   |
  | lsj_definition   | string | $pred_string(x)   |

  Nullable fields per upstream occurrence rate:
  - `english` is nullable at 0.991 occurrence (roughly 0.9 percent of
    rows have it null).
  - `lsj_definition` is nullable at 0.896 occurrence (roughly 10
    percent of rows have it null because STEPBible only excerpted the
    headword line for those lemmas).
  All other fields above are populated on every row at occurrence
  rate 1.0.

  Additional adapter-derived discriminator properties (required by
  Decision 14 for cross-source disambiguation and by the
  `lsj_entry_id` uniqueness constraint):
  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | id      | string | $pred_string(x) |
  | source  | string | $pred_string(x) |

  The `id` value is the stable id described above. The `source` value
  is the literal string `STEPBible-TFLSJ`.

  Decision 13 additionally requires a derived `lemma_unaccented`
  property: the upstream `lemma` field preserves Greek polytonic
  accents verbatim, and the adapter derives `lemma_unaccented` by
  stripping combining accent marks so cross-matching against
  MACULA-Greek lemmas (which may use different accent conventions)
  remains trivial. The accent-bearing `lemma` field is persisted
  byte-identical to the upstream value; only the derived
  `lemma_unaccented` slot strips diacritics.

Label `Source`:
  One node total emitted by this adapter. Decision 14 fields:
  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | slug         | string | $pred_string(x) |
  | license      | string | $pred_string(x) |
  | redistribute | bool   | $pred_bool(x)   |

  TFLSJ Source: slug `STEPBible-TFLSJ`, license `CC-BY-4.0`,
  redistribute true.

============================================================
4. Emitted edge (with src label, dst label, properties)
============================================================

Edge `LEX_FOR` (`LsjEntry` to `GreekLemma`):
  One edge per `LsjEntry` row whose `strong` resolves to a
  `GreekLemma` node previously emitted by the MACULA-Greek adapter in
  Group 1. The edge carries no properties; the join key is
  `LsjEntry.strong` matching `GreekLemma.strong` (an integer property
  on `GreekLemma` per the MACULA-Greek adapter contract). Rows whose
  `strong` does not resolve to a known `GreekLemma` MUST be persisted
  as the `LsjEntry` node without the outbound `LEX_FOR` edge, rather
  than fabricating a sentinel `GreekLemma`. The verifier records the
  unresolved-Strong count in the snapshot ledger so the triangle test
  detects upstream drift on re-ingest.

The adapter emits no other edge types. In particular it does NOT
write `INSTANCE_OF`, `IN_DOMAIN`, `FROM_EDITION`, `IN_VERSE`,
`BRIDGES_LXX`, or any cross-reference edges. The lexicon node is a
reference table cited by Pipeline 2 anchor-lemma bundles, not a
verse-keyed token.

============================================================
5. Acceptance Cypher (verbatim from phase_02 bullet 10)
============================================================

The Phase D verifier asserts the following query returns at least one
row with `entries > 0`, exactly as written in
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 10:

    MATCH (e:LsjEntry {source: 'STEPBible-TFLSJ'})
    WHERE e.strong IS NOT NULL AND e.lemma IS NOT NULL
    WITH count(e) AS entries
    RETURN entries, entries > 0

In addition, the Decision 13 acceptance Cypher in
`docs/SCHEMA_DECISIONS.md` runs the identical shape:

    MATCH (e:LsjEntry {source: 'STEPBible-TFLSJ'})
    WHERE e.strong IS NOT NULL AND e.lemma IS NOT NULL
    WITH count(e) AS entries
    RETURN entries, entries > 0

The Tier A expected count from `tools/expected_counts.json` is 11034
with tolerance 0 (min 11034, max 11034). The verifier additionally
asserts an exact match of the upstream row count.

============================================================
6. Edge cases (verbatim from Decision 13)
============================================================

Case A: polytonic accents in `lemma`.
  LSJ entries occasionally contain Greek polytonic accents that some
  downstream consumers strip. The adapter MUST preserve the accents
  in `lemma` and provide a derived `lemma_unaccented` property for
  matching against MACULA-Greek lemmas that may use different accent
  conventions. The unaccented form is computed by Unicode NFD
  decomposition plus removal of combining mark characters in the
  range U+0300 to U+036F, then NFC recomposition. The byte sequence
  in `lemma` is identical to the upstream column value.

Case B: null `lsj_definition`.
  A non-trivial 10 percent of entries have `lsj_definition` null
  because STEPBible only excerpted the headword line for those
  lemmas. The adapter MUST persist them without rejection so
  Pipeline 2 anchor-lemma bundles still see the headword. The
  `$pred_string(lsj_definition)` predicate returns false on these
  rows, which is the correct signal of upstream absence.

Case C: abbreviation tokens in `english`.
  LSJ entries sometimes carry abbreviation tokens such as `cf.` and
  `v.` inside `english`. The adapter MUST leave the abbreviations in
  place rather than expanding them, because the abbreviation set is
  part of the citation grammar Pipeline 2 forwards verbatim. The
  trailing periods on `cf.` and `v.` are part of the token and MUST
  NOT be stripped by punctuation-normalisation passes.

============================================================
7. Stable identifier format (Decision 13, Decision 14)
============================================================

LsjEntry stable id:
  Format `tflsj:<strong>:<lemma>`. For example, a row with
  `strong = G3056` and `lemma = "logos"` (or its polytonic form)
  yields `id = "tflsj:G3056:logos"`. Decision 13 specifies that the
  key is `strong` plus `lemma` together because `strong` is not
  unique across LSJ sub-entries. The graph-side uniqueness lives on
  `e.id` via the `lsj_entry_id` constraint, so the adapter constructs
  the composite key as `id = 'tflsj:' + strong + ':' + lemma`. The
  `lemma` portion uses the polytonic form verbatim from the upstream
  column, preserving accent identity in the namespace so two
  sub-entries with the same Strong but different accented headwords
  remain distinct nodes.

Source stable id:
  The slug itself, by Decision 14 uniqueness constraint
  `source_slug`.

============================================================
8. License and redistribute (Decision 14)
============================================================

Per Decision 14 the adapter writes one `Source` node before any
record-level write, and the constraint `source_slug` on
`graph/lexical.cypher` prevents a second registration of the same
slug. The TFLSJ source is `CC-BY-4.0` with redistribute true per
`docs/LICENSE_TAGGING.md` row `STEPBible-TFLSJ` (LSJ formatted
subset). STEPBible re-publishes the LSJ extract under the STEPBible
project license terms, which align with the CC-BY-4.0 attribution
requirement; the redistribute flag is true because attribution is
the only governing condition.

The citation slug used by Pipeline 2 evidence files
(`STEPBible-TFLSJ`) matches `docs/phase_prompts/pipeline2_verdict.md`
verbatim.

============================================================
9. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md` bullet 10,
this adapter runs in Group 3 (Lexicons) and depends on the
`GreekLemma` nodes from Group 1 (specifically from the MACULA-Greek
adapter, `ingest/lexical/macula_greek.py`) for the `LEX_FOR` join. The
adapter MUST NOT begin writes until the MACULA-Greek adapter has
completed its `GreekLemma` emission; otherwise the `LEX_FOR` join
silently produces an empty edge set for every row.

The wipe contract in `tools/wipe_lexical.py` deletes every node and
relationship in the lexical Neo4j before re-ingest, so MERGE writes
start from an empty store and the `lsj_entry_id` constraint rejects
any second write for the same stable id.

============================================================
10. Network isolation and AST purity
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md`, adapter
dry-runs execute inside Docker with `--network=none`, which forbids
any HTTP, DNS, or socket access during ingest. The AST scan
`tools/check_adapter_purity.py` rejects any adapter that imports
`subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`,
`mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`, or
dynamic `__import__`. The implementer-impl caste commit that adds the
runnable adapter body MUST satisfy that purity scan; the local TSV or
TXT file under `data/private/stepbible/Lexicons` is the only input.

============================================================
11. Idempotency
============================================================

MERGE-by-stable-id is the idempotency guarantee. Re-running the
adapter on identical source bytes produces identical `LsjEntry` and
`Source` nodes and identical `LEX_FOR` edges. The triangle-test hash
recompute in Phase D re-runs the adapter on the same source bytes;
the per-row presence vector produces a sorted list of per-row
SHA-256 hashes that must match byte-for-byte across two runs.

============================================================
12. AST gate
============================================================

This module satisfies `len(ast.parse(source).body) == 1` and
`isinstance(ast.parse(source).body[0], ast.Expr)` with the inner
`value` an `ast.Constant` of type `str`. The implementer-docstring
caste pre-commit hook enforces this shape so the file carries only
the schema contract; the runnable adapter body lands in the
implementer-impl caste commit.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "STEPBible-TFLSJ"
LICENSE_ID = "CC-BY-4.0"
TFLSJ_FILES = (
    "TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt",
    "TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt",
)
HEADER_PREFIX = "eStrong\tdStrong"
MIN_COLUMNS = 8
BATCH_SIZE = 500

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_LSJ_ENTRY = (
    "UNWIND $rows AS row MERGE (n:`LsjEntry` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_LEX_FOR = (
    "UNWIND $rows AS row "
    "MATCH (e:LsjEntry{id: row.id}), (g:GreekLemma{strong: row.canonical_strong}) "
    "MERGE (e)-[r:`LEX_FOR`]->(g) "
    "RETURN count(r) AS edges"
)


def _read_text(path: Path) -> str:
    with path.open(encoding="utf-8-sig") as fh:
        return fh.read()


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    stripped = "".join(
        ch for ch in decomposed if not (0x0300 <= ord(ch) <= 0x036F)
    )
    return unicodedata.normalize("NFC", stripped)


def _nullable(value: str) -> str | None:
    trimmed = value.strip()
    return trimmed if trimmed else None


def _stable_id(strong: str, lemma: str) -> str:
    return f"tflsj:{strong}:{lemma}"


def _canonical_greek_strong(raw_strong: str) -> str | None:
    """Decision 18 LEX_FOR join key: canonical Greek Strong string.

    Routes the raw upstream `strong` token through the single committed
    normaliser `ingest.canonical_strongs.canonical_strongs(raw, 'gk')`
    and returns `canon[0]` (e.g. raw `G40` -> `G0040`). This is the
    byte-identical value the macula_greek producer writes to
    `GreekLemma.strong` post-Decision-18, so the LEX_FOR match resolves
    index-backed against the `greek_lemma_strong` index
    (graph/lexical.cypher, Decision 18). When the token fails to
    normalise the adapter MUST NOT fabricate a Strong (Decision 18
    no-Strong clause): it returns None and the caller skips the
    outbound LEX_FOR edge while still persisting the LsjEntry node.
    """
    try:
        return canonical_strongs(raw_strong, "gk")[0]
    except ValueError:
        return None


def _parse_row(line: str) -> dict[str, Any] | None:
    parts = line.split("\t")
    if len(parts) < MIN_COLUMNS:
        return None
    strong = parts[0].strip()
    lemma = parts[3].strip()
    transliteration = parts[4].strip()
    pos = parts[5].strip()
    english = parts[6]
    lsj_definition = parts[7]
    if not strong or not strong.startswith(("G", "H")):
        return None
    if not lemma or not transliteration or not pos:
        return None
    return {
        "id": _stable_id(strong, lemma),
        "strong": strong,
        "lemma": lemma,
        "lemma_unaccented": _strip_accents(lemma),
        "transliteration": transliteration,
        "pos": pos,
        "english": _nullable(english),
        "lsj_definition": _nullable(lsj_definition),
        "source": SOURCE_SLUG,
    }


def _parse_file(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    header_seen = False
    for raw_line in text.splitlines():
        if not header_seen:
            if raw_line.startswith(HEADER_PREFIX):
                header_seen = True
            continue
        if not raw_line.strip():
            continue
        row = _parse_row(raw_line)
        if row is not None:
            rows = [*rows, row]
    return rows


def _load_rows(lexicons_root: Path) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for filename in TFLSJ_FILES:
        path = lexicons_root / filename
        if not path.exists():
            continue
        collected = [*collected, *_parse_file(_read_text(path))]
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in collected:
        key = row["id"]
        if key in seen:
            continue
        seen.add(key)
        deduped = [*deduped, row]
    return deduped


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_lsj_entries(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_LSJ_ENTRY, rows=batch).consume()
        total += len(batch)
    return total


def _merge_lex_for_edges(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = []
        for r in rows[start:start + BATCH_SIZE]:
            canonical = _canonical_greek_strong(r["strong"])
            if canonical is None:
                continue
            batch = [*batch, {"id": r["id"], "canonical_strong": canonical}]
        if not batch:
            continue
        session.run(_MERGE_LEX_FOR, rows=batch).consume()
        total += len(batch)
    return total


def ingest_stepbible_tflsj(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse STEPBible-TFLSJ and MERGE LsjEntry, Source, and LEX_FOR edges.

    data_root is the Lexicons directory holding the two TFLSJ release files.
    """
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_lsj_entries(session, rows)
        lex_for = _merge_lex_for_edges(session, rows)
    return {
        "LsjEntry": merged,
        "Source": 1,
        "LEX_FOR": lex_for,
    }
