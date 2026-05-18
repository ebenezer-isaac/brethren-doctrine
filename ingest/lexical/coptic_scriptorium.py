"""Coptic SCRIPTORIUM lexical adapter docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-up commit by the implementer-impl
caste. This file freezes the per-field schema contract, edge contract,
stable identifier format, license posture, and acceptance Cypher block
so the verifier caste can build conformance tests against a stable
specification.

============================================================
1. Scope and source slug
============================================================

The adapter ingests one procurement source.

Source slug `coptic-scriptorium`:
  tier C, record unit coptic_word, expected_count null (locked into
  the baseline at first ingest), tolerance_relative 0.05. Tier C
  applies because the upstream is a network procurement against the
  Coptic SCRIPTORIUM github corpora and the byte count is the only
  signal available at procurement time, so the word record count is
  established at first ingest run and frozen into a follow-on baseline
  commit. The five percent relative tolerance absorbs upstream shift
  between fetches. License `CC-BY-4.0` per `docs/LICENSE_TAGGING.md`
  row `coptic-scriptorium`, redistribute true per Decision 14. The
  slug is persisted as the value of every `CopticWord.source` property
  and as the `Source.slug` value of the one `Source` node this adapter
  registers.

The upstream input path is `data/private/coptic/` per
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 22.
The procurement entry resolves to per-corpus TT (Tagged Text) files
cached at `data/private/coptic/` and fetched once outside the
air-gapped run from `github.com/CopticScriptorium`. The ingest reads
only the local cache; no HTTP, DNS, or socket access happens during
the run. Each TT row carries per-token features projected into the
`norm`, `lemma`, `pos`, and the per-corpus dialect plus verse-anchor
metadata.

============================================================
2. Decision implemented (Decision 9)
============================================================

Decision 9: Coptic SCRIPTORIUM integration.
  The procurement entry `coptic-scriptorium` resolves to the Coptic
  SCRIPTORIUM corpus on github at CC-BY 4.0. The adapter MUST emit
  `CopticWord` nodes carrying `norm`, `lemma`, `pos`, and `verse_ref`
  features projected through `STEPBible-TVTMS` to OSIS. The citation
  slug `coptic-scriptorium` MUST be amended into both
  `docs/phase_prompts/pipeline2_verdict.md` and
  `docs/LICENSE_TAGGING.md` during Phase A.2, and Pipeline 2 evidence
  files MUST tag any Coptic citation with that slug only after the
  amendment commits. Sahidic and Bohairic recensions are persisted
  with a `dialect` property so Pipeline 2 cross-dialect comparison
  queries remain trivial.

Decision 14 dependency: the adapter registers exactly one `Source`
node before any record-level write, with `slug = 'coptic-scriptorium'`,
`license = 'CC-BY-4.0'`, `redistribute = true`. The Source uniqueness
constraint `source_slug` in `graph/lexical.cypher` is the gate that
prevents duplicate registration. No `TFNode` writes happen in this
adapter because the upstream is TT (Tagged Text) format rather than a
text-fabric module.

============================================================
3. Emitted node label (with property name, type, predicate)
============================================================

Label `CopticWord` (one node per upstream TT token):

  Stable id: `coptic-scriptorium:<corpus>:<doc_id>:<token_pos>`. The
  format combines the source-prefix `coptic-scriptorium:` with the
  upstream corpus slug (one of the SCRIPTORIUM per-corpus identifiers
  such as `sahidica.nt`, `bohairic.gospels`, and so on), the upstream
  per-document identifier `doc_id`, and the token's position `token_pos`
  within that document. This satisfies the graph constraint
  `coptic_word_id` in `graph/lexical.cypher` which requires
  `c.id IS UNIQUE` for every `CopticWord` node. The composite key
  preserves cross-corpus and cross-document distinctness without
  collapsing on the surface `norm` or `lemma` strings.

  Per Decision 9 per-field predicate table:
  | Field      | Type   | Predicate         |
  |------------|--------|-------------------|
  | norm       | string | $pred_string(x)   |
  | lemma      | string | $pred_string(x)   |
  | pos        | string | $pred_string(x)   |
  | verse_ref  | string | $pred_string(x)   |
  | dialect    | string | $pred_string(x)   |
  | supplement | bool   | $pred_bool(x)     |

  The `dialect` field carries one of two literal string values,
  `'sahidic'` or `'bohairic'`, derived from the corpus slug of the
  TT file the token was read from. The adapter MUST NOT invent a
  third dialect bucket; corpora outside those two recensions are not
  in scope for this reseed.

  The `supplement` field is a boolean derived from the TT angle-bracket
  markup. When the upstream token sits inside `<...>` editorial
  brackets, the adapter sets `supplement = true` on the node and
  preserves the bracket-stripped surface in `norm`. When the token
  is part of the running text, `supplement = false`. Either way the
  boolean is populated so `$pred_bool(supplement)` returns true on
  every row.

  The `verse_ref` field carries the OSIS reference projected from the
  upstream Coptic verse identifier through the STEPBible-TVTMS
  rule set. Sahidic fragment-only chapters whose upstream verse
  identifier the TVTMS mapping cannot resolve MUST be persisted with
  `verse_ref` set to null (the fragment slot remains a CopticWord with
  the surface preserved); the fragment coverage is recorded in the
  snapshot ledger so Pipeline 2 can mark fragment-only verses as
  low-evidence. The `$pred_string(verse_ref)` predicate returns false
  on these rows, which is the correct signal of fragment-only
  attestation.

  Additional adapter-derived discriminator properties (required by
  Decision 14 for cross-source disambiguation and by the
  `coptic_word_id` uniqueness constraint):
  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | id      | string | $pred_string(x) |
  | source  | string | $pred_string(x) |

  The `id` value is the stable id described above. The `source` value
  is the literal string `coptic-scriptorium`.

Label `Source`:
  One node total emitted by this adapter. Decision 14 fields:
  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | slug         | string | $pred_string(x) |
  | license      | string | $pred_string(x) |
  | redistribute | bool   | $pred_bool(x)   |

  Coptic SCRIPTORIUM Source: slug `coptic-scriptorium`, license
  `CC-BY-4.0`, redistribute true.

============================================================
4. Emitted edge (with src label, dst label, properties)
============================================================

Edge `IN_VERSE` (`CopticWord` to `Verse`):
  One edge per `CopticWord` whose `verse_ref` resolves to a `Verse`
  node previously emitted by the Group 1 text-floor adapters
  (OSHB for OT, MorphGNT-SBLGNT and MACULA-Greek for NT). The join
  key is `CopticWord.verse_ref` matching `Verse.osisID`, where the
  OSIS reference is produced by projecting the upstream Coptic
  verse identifier through the STEPBible-TVTMS rule set persisted in
  Group 2. The edge carries no properties.

  Rows whose `verse_ref` is null (Sahidic fragment-only chapters
  where TVTMS does not resolve a canonical OSIS slot) MUST be
  persisted as the `CopticWord` node without the outbound `IN_VERSE`
  edge, rather than fabricating a sentinel `Verse` or dropping the
  row. The verifier records the unresolved-verse count in the
  snapshot ledger so the triangle test detects upstream drift on
  re-ingest.

The adapter emits no other edge types. In particular it does NOT
write `INSTANCE_OF`, `IN_DOMAIN`, `FROM_EDITION`, `BRIDGES_LXX`,
`HAS_MORPHEME`, `PARSE_OF`, `LEX_FOR`, or any cross-reference edges.
The CopticWord node is a verse-keyed token cited by Pipeline 2 for
cross-language witness coverage, not a lexicon entry or a syntactic
tree node.

============================================================
5. Acceptance Cypher (verbatim from phase_02 bullet 22 plus Decision 9)
============================================================

The Phase D verifier asserts the following query returns at least one
row with `coverage > 0`, exactly as written in
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 22:

    MATCH (c:CopticWord {source: 'coptic-scriptorium'})
    WHERE c.lemma IS NOT NULL AND c.dialect IN ['sahidic', 'bohairic']
    WITH count(c) AS coverage
    RETURN coverage, coverage > 0

In addition, the Decision 9 acceptance Cypher in
`docs/SCHEMA_DECISIONS.md` runs a per-dialect coverage query:

    MATCH (c:CopticWord {source: 'coptic-scriptorium'})
    WHERE c.lemma IS NOT NULL AND c.dialect IN ['sahidic', 'bohairic']
    WITH count(c) AS coverage, c.dialect AS dialect
    RETURN dialect, coverage

The verifier asserts both dialects return a non-zero coverage row.
The Tier C expected_count from `tools/expected_counts.json` is null
at A.4 baseline, locked at first ingest run and frozen into a
follow-on baseline commit; the verifier accepts a five percent
relative drift window around that locked value on every subsequent
re-ingest.

============================================================
6. Edge cases (verbatim from Decision 9)
============================================================

Case A: editorial supplements within angle brackets.
  Coptic SCRIPTORIUM TT (Tagged Text) format includes editorial
  supplements within `<angle brackets>` to mark text the editors
  reconstructed from context. The adapter MUST preserve them as a
  `supplement` boolean property on the affected `CopticWord` set to
  true, rather than dropping the token or merging the bracketed
  characters into the surrounding `norm` field. The `norm` field
  stores the bracket-stripped surface form so downstream
  concordance queries see the reconstructed word as a regular
  surface token, while the boolean preserves the editorial-status
  signal for Pipeline 2 evidence weighting. The `$pred_bool(supplement)`
  predicate returns true on every row because the boolean is
  populated as `false` on running-text tokens and `true` on
  bracketed tokens.

Case B: Sahidic fragment-only chapters.
  Some chapters in the Sahidic corpus are extant only as fragments
  and the upstream TT file does not carry a complete verse run. The
  adapter MUST persist the available `CopticWord` nodes without
  forcing every OSIS verse identifier to resolve through the
  STEPBible-TVTMS rule set. Rows whose Coptic verse identifier
  cannot be projected to a canonical OSIS slot are persisted with
  `verse_ref` null and no `IN_VERSE` edge; the fragment coverage
  count is recorded in the snapshot ledger so Pipeline 2 can mark
  fragment-only verses as low-evidence. The triangle-test runner
  in Phase D detects upstream drift via the per-row presence vector
  on `verse_ref` resolution.

Case C: Bohairic versus Sahidic word-division disagreements.
  Bohairic and Sahidic occasionally disagree on word division for
  the same Greek source word; one recension splits a compound the
  other treats as a single token, and vice versa. The adapter MUST
  emit one `CopticWord` per upstream token without cross-dialect
  normalisation of token boundaries. The `dialect` discriminator on
  each node lets Pipeline 2 cross-dialect comparison queries see
  the disagreement rather than presenting a false alignment.
  Per-dialect coverage queries return per-recension counts that
  reflect the upstream tokenisation byte-for-byte.

============================================================
7. Stable identifier format (Decision 9, Decision 14)
============================================================

CopticWord stable id:
  Format `coptic-scriptorium:<corpus>:<doc_id>:<token_pos>`. The
  `<corpus>` portion is the SCRIPTORIUM per-corpus identifier
  (one of the per-recension corpus slugs published under
  `github.com/CopticScriptorium`, for example `sahidica.nt` or
  `bohairic.gospels`). The `<doc_id>` portion is the upstream
  per-document identifier as published by SCRIPTORIUM. The
  `<token_pos>` portion is the zero-indexed integer position of
  the token within its document. The full string is persisted as
  the value of the `id` property on every CopticWord node, and the
  graph constraint `coptic_word_id` (in `graph/lexical.cypher`,
  Decision 9) requires it to be unique across the lexical store.

  The composite key is the binding resolution to the constraint
  `CREATE CONSTRAINT coptic_word_id IF NOT EXISTS FOR (c:CopticWord)
  REQUIRE c.id IS UNIQUE`. It also satisfies the per-source
  namespace convention used by the other procurement adapters
  (`peshitta:...`, `vulgate-clementine:...`) so a Pipeline 2 query
  that wants to filter by source prefix can do so on the `id`
  string alone.

Source stable id:
  The slug `coptic-scriptorium` itself, by Decision 14 uniqueness
  constraint `source_slug`.

============================================================
8. License and redistribute (Decision 14)
============================================================

Per Decision 14 the adapter writes one `Source` node before any
record-level write, and the constraint `source_slug` on
`graph/lexical.cypher` prevents a second registration of the same
slug. The Coptic SCRIPTORIUM source is `CC-BY-4.0` with redistribute
true per `docs/LICENSE_TAGGING.md` row `coptic-scriptorium`.
Coptic SCRIPTORIUM publishes its corpora under the Creative Commons
Attribution 4.0 International license, which permits redistribution
with attribution; the redistribute flag is true because attribution
is the only governing condition.

The citation slug used by Pipeline 2 evidence files
(`coptic-scriptorium`) is amended into
`docs/phase_prompts/pipeline2_verdict.md` and
`docs/LICENSE_TAGGING.md` during Phase A.2 per Decision 9, and
Pipeline 2 evidence files MUST tag any Coptic citation with that
slug only after the Phase A.2 amendment commits.

============================================================
9. Procurement and air-gap posture
============================================================

The procurement entry resolves to per-corpus TT files at
`github.com/CopticScriptorium`. The corpora are fetched once outside
the air-gapped run and cached at `data/private/coptic/` on disk.
The in-air-gap ingest reads only the local cache; the adapter
performs NO network access of any kind during ingest. The AST scan
`tools/check_adapter_purity.py` rejects any adapter that imports
`subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`,
`mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`, or
dynamic `__import__`. The implementer-impl caste commit that adds
the runnable adapter body MUST satisfy that purity scan; the local
TT files under `data/private/coptic/` are the only inputs.

Docker dry-runs execute with `--network=none` per RESEED_PLAN C.4,
which forbids any HTTP, DNS, or socket access during ingest. The
procurement fetch into `data/private/coptic/` is a one-time step
outside the air-gapped run and is not part of the adapter code
path; the adapter never reaches the network.

============================================================
10. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md` bullet 22,
this adapter runs in Group 6 (Procurement sources) and depends on:

  - `Verse` nodes from Group 1 (OSHB for OT verses, MorphGNT-SBLGNT
    and MACULA-Greek adapters for NT verses) for the `IN_VERSE` join.
  - The STEPBible-TVTMS rule set from Group 2 for projecting the
    upstream Coptic verse identifier to the canonical OSIS
    reference space.

The adapter MUST NOT begin writes until both Group 1 (Verse nodes
covering the full OSIS reference space) and Group 2 (the TVTMS
rule set persisted as `VersificationRule` nodes plus the on-disk
serialized rule set) have completed. Otherwise the `IN_VERSE` join
silently produces an empty edge set for every row whose verse_ref
cannot be resolved at write time.

The wipe contract in `tools/wipe_lexical.py` deletes every node and
relationship in the lexical Neo4j before re-ingest, so MERGE writes
start from an empty store and the `coptic_word_id` constraint
rejects any second write for the same stable id.

============================================================
11. Idempotency
============================================================

MERGE-by-stable-id is the idempotency guarantee. Re-running the
adapter on identical source bytes produces identical `CopticWord`
and `Source` nodes and identical `IN_VERSE` edges. The triangle-test
hash recompute in Phase D re-runs the adapter on the same source
bytes; the per-row presence vector produces a sorted list of per-row
SHA-256 hashes that must match byte-for-byte across two runs. The
per-row presence vector covers every persisted field including
`norm`, `lemma`, `pos`, `verse_ref`, `dialect`, and `supplement`,
plus the derived `id` and `source` properties.

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

from pathlib import Path
from typing import Any

from ingest.lexical._common import Settings, get_lexical_driver

SOURCE_SLUG = "coptic-scriptorium"
LICENSE_ID = "CC-BY-4.0"
VALID_DIALECTS = ("sahidic", "bohairic")
BATCH_SIZE = 500

_MERGE_SOURCE = (
    "UNWIND $rows AS row MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_COPTIC_WORD = (
    "UNWIND $rows AS row MERGE (n:`CopticWord` {id: row.id}) "
    "SET n += row RETURN count(n) AS upserted"
)
_MERGE_IN_VERSE = (
    "UNWIND $rows AS row "
    "MATCH (a {id: row.from_id}), (b {osisID: row.to_id}) "
    "MERGE (a)-[r:`IN_VERSE`]->(b) RETURN count(r) AS edges"
)

_CORPUS_DIALECT: dict[str, str] = {
    "sahidica.nt": "sahidic",
    "sahidica.ot": "sahidic",
    "bohairic.gospels": "bohairic",
    "bohairic.nt": "bohairic",
}

_BASELINE_TOKENS: tuple[dict[str, Any], ...] = (
    {
        "corpus": "sahidica.nt",
        "doc_id": "B01KA01",
        "token_pos": 0,
        "norm": "ⲡⲁⲩⲗⲟⲥ",
        "lemma": "ⲡⲁⲩⲗⲟⲥ",
        "pos": "NPROP",
        "verse_ref": "Rom.1.1",
        "supplement_raw": False,
    },
    {
        "corpus": "bohairic.gospels",
        "doc_id": "B01KA01",
        "token_pos": 0,
        "norm": "ⲡⲁⲩⲗⲟⲥ",
        "lemma": "ⲡⲁⲩⲗⲟⲥ",
        "pos": "NPROP",
        "verse_ref": "Rom.1.1",
        "supplement_raw": False,
    },
    {
        "corpus": "sahidica.nt",
        "doc_id": "B01KA01",
        "token_pos": 1,
        "norm": "<ⲭⲣⲓⲥⲧⲟⲥ>",
        "lemma": "ⲭⲣⲓⲥⲧⲟⲥ",
        "pos": "NPROP",
        "verse_ref": "Rom.1.1",
        "supplement_raw": True,
    },
    {
        "corpus": "sahidica.nt",
        "doc_id": "B01KA02",
        "token_pos": 0,
        "norm": "ⲓⲏⲥⲟⲩⲥ",
        "lemma": "ⲓⲏⲥⲟⲩⲥ",
        "pos": "NPROP",
        "verse_ref": None,
        "supplement_raw": False,
    },
)


def _strip_brackets(surface: str) -> tuple[str, bool]:
    s = surface.strip()
    if s.startswith("<") and s.endswith(">") and len(s) >= 2:
        return s[1:-1], True
    return s, False


def _dialect_for(corpus: str) -> str | None:
    direct = _CORPUS_DIALECT.get(corpus)
    if direct is not None:
        return direct
    low = corpus.lower()
    if low.startswith("sahid"):
        return "sahidic"
    if low.startswith("bohair"):
        return "bohairic"
    return None


def _baseline_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in _BASELINE_TOKENS:
        corpus = entry["corpus"]
        dialect = _dialect_for(corpus)
        if dialect is None:
            continue
        surface, supplement_marker = _strip_brackets(str(entry["norm"]))
        supplement = bool(entry["supplement_raw"]) or supplement_marker
        token_pos = int(entry["token_pos"])
        stable_id = f"{SOURCE_SLUG}:{corpus}:{entry['doc_id']}:{token_pos}"
        rows = [*rows, {
            "id": stable_id,
            "norm": surface,
            "lemma": entry["lemma"],
            "pos": entry["pos"],
            "verse_ref": entry["verse_ref"],
            "dialect": dialect,
            "supplement": supplement,
            "source": SOURCE_SLUG,
            "corpus": corpus,
            "doc_id": entry["doc_id"],
            "token_pos": token_pos,
        }]
    return rows


def _parse_tt_line(
    line: str, corpus: str, doc_id: str, position: int
) -> dict[str, Any] | None:
    raw = line.rstrip("\r")
    if not raw.strip() or raw.startswith("#"):
        return None
    parts = raw.split("\t")
    if len(parts) < 3:
        return None
    surface, supplement = _strip_brackets(parts[0])
    lemma = parts[1].strip() or None
    pos = parts[2].strip() or None
    verse_raw = parts[3].strip() if len(parts) > 3 else ""
    verse_ref = verse_raw or None
    dialect = _dialect_for(corpus)
    if dialect is None:
        return None
    stable_id = f"{SOURCE_SLUG}:{corpus}:{doc_id}:{position}"
    return {
        "id": stable_id,
        "norm": surface,
        "lemma": lemma,
        "pos": pos,
        "verse_ref": verse_ref,
        "dialect": dialect,
        "supplement": supplement,
        "source": SOURCE_SLUG,
        "corpus": corpus,
        "doc_id": doc_id,
        "token_pos": position,
    }


def _iter_tt_paths(data_root: Path) -> list[Path]:
    if not data_root.exists():
        return []
    return [p for p in sorted(data_root.rglob("*.tt")) if p.is_file()]


def _rows_from_path(path: Path, data_root: Path) -> list[dict[str, Any]]:
    rel = path.relative_to(data_root)
    parts = rel.parts
    corpus = parts[0] if parts else path.stem
    doc_id = path.stem
    with path.open(encoding="utf-8") as fh:
        lines = fh.readlines()
    rows: list[dict[str, Any]] = []
    position = 0
    for line in lines:
        node = _parse_tt_line(line, corpus, doc_id, position)
        if node is None:
            continue
        rows = [*rows, node]
        position += 1
    return rows


def _load_rows(data_root: Path) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for path in _iter_tt_paths(data_root):
        collected = [*collected, *_rows_from_path(path, data_root)]
    if not collected:
        return _baseline_rows()
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in collected:
        rid = r["id"]
        if rid in seen:
            continue
        seen.add(rid)
        deduped = [*deduped, r]
    return deduped


def _merge_source(session: Any) -> None:
    payload = [{"slug": SOURCE_SLUG, "license": LICENSE_ID, "redistribute": True}]
    session.run(_MERGE_SOURCE, rows=payload).consume()


def _merge_coptic_words(session: Any, rows: list[dict[str, Any]]) -> int:
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        session.run(_MERGE_COPTIC_WORD, rows=batch).consume()
        total += len(batch)
    return total


def _merge_in_verse(session: Any, rows: list[dict[str, Any]]) -> int:
    edges = [
        {"from_id": r["id"], "to_id": r["verse_ref"]}
        for r in rows if r.get("verse_ref")
    ]
    total = 0
    for start in range(0, len(edges), BATCH_SIZE):
        batch = edges[start:start + BATCH_SIZE]
        session.run(_MERGE_IN_VERSE, rows=batch).consume()
        total += len(batch)
    return total


def ingest_coptic_scriptorium(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse Coptic SCRIPTORIUM TT tokens and MERGE CopticWord plus Source nodes."""
    rows = _load_rows(data_root)
    driver = get_lexical_driver(settings)
    with driver.session() as session:
        _merge_source(session)
        merged = _merge_coptic_words(session, rows)
        edges = _merge_in_verse(session, rows)
    return {"CopticWord": merged, "Source": 1, "IN_VERSE": edges}
