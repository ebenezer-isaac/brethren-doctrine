"""MACULA Greek lexical adapter docstring contract (Phase C, Wave 1).

This module is intentionally a single docstring expression. The runnable
implementation is added in a follow-up commit by the implementer-impl
caste. This file freezes the per-field schema contract, edge contract,
stable identifier format, license posture, and acceptance Cypher block
so the verifier caste can build conformance tests against a stable
specification.

============================================================
1. Scope and source slugs
============================================================

The adapter ingests two MACULA Greek editions as distinct rows keyed by
edition slug.

Source slug `MACULA-Greek-Nestle1904`:
  tier A, record unit word, expected count 137779, tolerance 0,
  minimum 137779, maximum 137779. Tier A means the count is a
  deterministic element count from the upstream frozen XML release and
  any deviation fails the acceptance gate. License CC-BY-4.0 per
  Decision 14, redistribute true. The edition slug is also persisted as
  the value of every `Word.source` property emitted from this edition.

Source slug `MACULA-Greek-SBLGNT`:
  tier A, record unit word, expected count 137741, tolerance 0,
  minimum 137741, maximum 137741. License composite: SBLGNT base text
  under the SBLGNT EULA, MACULA syntactic enrichment CC-BY-4.0,
  MARBLE Louw-Nida CC-BY-NC-4.0. Decision 14 records `Source.license`
  as the effective composite slug `CC-BY-NC-4.0` because the most
  restrictive component governs redistribution; `Source.redistribute`
  is false for this edition. The edition slug is the value of every
  `Word.source` property emitted from this edition.

Both editions populate the same node labels and the same edge types.
Disambiguation between editions is by `source` property and by the
stable-id namespace prefix, never by label specialisation.

============================================================
2. Decisions implemented (Decisions 2, 4, 14, 15)
============================================================

Decision 2: Louw-Nida domain encoding.
  The MACULA Greek `ln` field is a colon-delimited string of the form
  `domain:subdomain`. The adapter splits it into `domain_code` (int)
  and `subdomain_code` (int) and stores them on the `IN_DOMAIN`
  relationship rather than on the `LouwNidaDomain` node, because the
  same domain node is reached by multiple distinct subdomain edges.
  The `LouwNidaDomain` node identity is the integer `domain_code`
  alone, which yields a single node per top-level domain rather than
  per subdomain combination.

Decision 4: Hebrew-to-Greek bridge granularity.
  This adapter is on the receiving end of the bridge. MACULA-Hebrew
  emits `BRIDGES_LXX` edges keyed by `greekstrong`, and those edges
  target the `GreekLemma` nodes created here. The adapter therefore
  MUST emit `GreekLemma` nodes whose stable id is constructed in a way
  that MACULA-Hebrew can reproduce by Strong number alone, while still
  satisfying the per-edition namespacing required by Decision 2's
  cross-edition disagreement rule.

Decision 14: Strong / Source / TFNode constraint policy.
  The adapter registers exactly two `Source` nodes (one per edition)
  before any record-level write. Each `Source` carries `slug`,
  `license`, `redistribute`. The Source uniqueness constraint
  `source_slug` in `graph/lexical.cypher` is the gate that prevents
  duplicate registration. No `TFNode` writes happen in this adapter
  (text-fabric is the BHSA path, not MACULA).

Decision 15: Verse.text population policy.
  MACULA-Greek MUST NOT write `Verse.text`. The canonical NT surface
  is owned by `ingest/lexical/morphgnt.py` (MorphGNT-SBLGNT) per
  Decision 15. The adapter MAY MERGE a `Verse` node by `osisID` to
  attach `IN_VERSE` edges, but it MUST NOT set the `text` property.
  The acceptance Cypher in section 5 verifies that no Verse node has
  acquired text from this adapter alone (the verifier checks that
  Verses populated solely by MACULA-Greek leave `text` null until
  MorphGNT writes it).

============================================================
3. Emitted node labels (with property name, type, predicate)
============================================================

Label `Word` (one node per row, both editions):
  Stable id: `<edition>:<xml:id>` where `<edition>` is one of
  `MACULA-Greek-Nestle1904` or `MACULA-Greek-SBLGNT`, and `<xml:id>`
  is the verbatim MACULA token identifier.

  Per Decision 2 per-field predicate table:
  | Field      | Type   | Predicate         |
  |------------|--------|-------------------|
  | xml:id     | string | $pred_string(x)   |
  | ref        | string | $pred_string(x)   |
  | lemma      | string | $pred_string(x)   |
  | normalized | string | $pred_string(x)   |
  | strong     | int    | $pred_int(x)      |
  | morph      | string | $pred_string(x)   |
  | gloss      | string | $pred_string(x)   |
  | domain     | string | $pred_string(x)   |
  | ln         | string | $pred_string(x)   |
  | text       | string | $pred_string(x)   |

  Additional discriminator properties (not in the Decision 2 table,
  required by Decision 14 for cross-source disambiguation):
  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | source  | string | $pred_string(x) |
  | edition | string | $pred_string(x) |

  The `source` value equals the edition slug verbatim. The `edition`
  value is the short form used in stable ids (`Nestle1904` or
  `SBLGNT`).

Label `GreekLemma`:
  Stable id format unchanged by Decision 18: `<source>:strong-<int:05d>`
  (the id namespacing clause explicitly keeps `.id` AS-IS). Per Decision
  18 (KEY-MG-STRONG, producer authority) the adapter writes `strong` as
  the canonical Strong STRING `canonical_strongs(str(strong),'gk')[0]`
  (e.g. `G0040`, never the integer `40`). This canonical `.strong` is
  the single cross-source join key every Greek consumer (tagnt, tbesg,
  tflsj) matches on, and it backs the Decision 4 `BRIDGES_LXX` Strong
  lookup keyed by `greekstrong`.

  Unresolvable Strong (Decision 18 line 642 / line 681, binding): a
  confirmed slice of the frozen MACULA-Greek upstream carries the
  `strong` cell as a `+`-joined COMPOUND of component Strongs for Greek
  crasis / multi-stem word-forms (e.g. `1537+4053` ἐκπερισσῶς,
  `5228+1537+4053` ὑπερεκπερισσοῦ, `1501+5140` εἰκοσιτρεῖς, `1417+3461`
  δισμυριάς). `canonical_strongs` RAISES `ValueError` on such a token
  (no Decision authorises a compound split; Decision 18 line 644 forbids
  hand-rolling one). Per Decision 18 line 642/681 the adapter MUST NOT
  fabricate a Strong: it takes the section-4 INSTANCE_OF skip path, so
  the row emits NO `GreekLemma` node and NO `INSTANCE_OF` edge while the
  `Word` node still writes with every property (its raw `strong` int per
  Decision 2 is unaffected). The skip is counted (`_unresolved_strong`
  in the returned dict) and a deterministic stderr line is emitted; it
  is never silent and never raises. Because `GreekLemma` MERGEs on `id`
  (a unique `<source>:strong-<int:05d>` namespace) and `.strong` is a
  post-MERGE SET attribute, a skipped row creates no node at all, so it
  cannot collide on `greek_lemma_id` nor introduce a null-in-MERGE.

  | Field   | Type   | Predicate       |
  |---------|--------|-----------------|
  | id      | string | $pred_string(x) |
  | lemma   | string | $pred_string(x) |
  | strong  | string | $pred_string(x) |
  | source  | string | $pred_string(x) |
  | edition | string | $pred_string(x) |

  Uniqueness is enforced by the `greek_lemma_id` constraint on `id`
  in `graph/lexical.cypher`.

Label `LouwNidaDomain`:
  One node per distinct top-level Louw-Nida domain code observed
  across either edition.

  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | id           | string | $pred_string(x) |
  | domain_code  | int    | $pred_int(x)    |
  | source       | string | $pred_string(x) |

  `id` is the stringified integer `domain_code` so the
  `louw_nida_id` uniqueness constraint and the
  `louw_nida_code` composite index in `graph/lexical.cypher` both
  apply. The `source` slot is the literal string
  `MACULA-Greek-Louw-Nida` to record provenance.

Label `Source`:
  Two nodes total emitted by this adapter, one per edition. Decision
  14 fields:
  | Field        | Type   | Predicate       |
  |--------------|--------|-----------------|
  | slug         | string | $pred_string(x) |
  | license      | string | $pred_string(x) |
  | redistribute | bool   | $pred_bool(x)   |

  Nestle1904 Source: slug `MACULA-Greek-Nestle1904`, license
  `CC-BY-4.0`, redistribute true.
  SBLGNT Source: slug `MACULA-Greek-SBLGNT`, license `CC-BY-NC-4.0`,
  redistribute false.

============================================================
4. Emitted edges (with src label, dst label, properties)
============================================================

Edge `INSTANCE_OF` (`Word` to `GreekLemma`):
  One edge per Word row. No edge properties. Establishes the lemma
  membership of the word occurrence. The edge is joined on
  `GreekLemma.id` (unchanged by Decision 18), not on a Strong type
  match: the Word's `strong` (int) and the GreekLemma's `strong`
  (canonical string per Decision 18) MUST agree in NUMBER (the same
  upstream Strong produced both), not in literal type. Rows where the
  row has no resolvable Strong MUST be persisted without the
  `INSTANCE_OF` edge rather than fabricating a sentinel lemma.

Edge `IN_DOMAIN` (`Word` to `LouwNidaDomain`):
  One edge per distinct `(strong, domain_code, subdomain_code)`
  tuple per word occurrence per Decision 2 polysemy rule. The edge
  carries the per-Decision-2 split:

  | Edge property    | Type | Predicate    |
  |------------------|------|--------------|
  | domain_code      | int  | $pred_int(x) |
  | subdomain_code   | int  | $pred_int(x) |
  | source           | string | $pred_string(x) |

  The `source` property on the edge records the edition that produced
  the assignment so cross-edition disagreement is queryable. When a
  Strong code is annotated with multiple Louw-Nida senses across
  different occurrences in the same edition (polysemy), the adapter
  emits one `IN_DOMAIN` per distinct `(strong, domain_code,
  subdomain_code)` tuple. The adapter MUST NOT collapse polysemy into
  a single edge by majority vote.

Edge `FROM_EDITION` (`Word` to `Source`):
  One edge per Word, no properties. Provides constant-time edition
  filtering without parsing the `Word.source` property at query time.

The adapter emits no other edge types. In particular it does NOT
write `IN_VERSE`, `NEXT_WORD`, `PARSE_OF`, or `BRIDGES_LXX`. The
MorphGNT adapter owns `PARSE_OF` (per Decision 15 dispatch order)
and MACULA-Hebrew owns `BRIDGES_LXX` (per Decision 4).

============================================================
5. Acceptance Cypher (verbatim from phase_02 bullet 3)
============================================================

The Phase D verifier asserts the following query returns at least one
row with `with_ln > 0`, exactly as written in
`docs/implementation_phases/phase_02_lexical_ingest.md` bullet 3:

    MATCH (w:Word)
    WHERE w.source IN ['MACULA-Greek-Nestle1904', 'MACULA-Greek-SBLGNT']
      AND w.ln IS NOT NULL
    WITH count(w) AS with_ln
    RETURN with_ln, with_ln > 0

In addition, the Decision 2 sub-query in `docs/SCHEMA_DECISIONS.md`
runs against the Nestle1904 edition and asserts conformance of the
`ln` split:

    MATCH (w:Word {source: 'MACULA-Greek-Nestle1904'})
    WHERE w.ln IS NOT NULL
    WITH w, split(w.ln, ':') AS parts
    WHERE size(parts) = 2 AND toInteger(parts[0]) > 0
    RETURN count(w) AS conformant

============================================================
6. Edge cases (verbatim from Decision 2)
============================================================

Case A: literal `n/a` coercion.
  A small slice of MACULA-Greek-Nestle1904 records emit `domain` and
  `ln` populated with the literal string `n/a` when MARBLE annotators
  left the slot empty. The adapter MUST coerce these to a true null
  so `$pred_string(ln)` returns false and the `LouwNidaDomain` edge
  is suppressed. Word nodes still write, with `domain` and `ln`
  unset. No `IN_DOMAIN` edge is emitted for those rows.

Case B: polysemy on Strong code.
  Some Strong codes carry multiple Louw-Nida senses across
  occurrences. The adapter MUST create one `IN_DOMAIN` relationship
  per distinct Strong-plus-domain tuple rather than averaging or
  picking the first, so the semantic-neighbor query returns the full
  sense set. Polysemy is detected at the `(strong, domain_code,
  subdomain_code)` tuple level; identical tuples across occurrences
  collapse onto one edge.

Case C: cross-edition `ln` disagreement.
  MACULA-Greek-SBLGNT and MACULA-Greek-Nestle1904 occasionally
  disagree on the `ln` value for the same lemma in the same verse
  owing to text-critical divergences. The adapter MUST record both
  with the differentiating `source` property on the `IN_DOMAIN`
  relationship rather than merging on a winner-take-all rule.
  Specifically, the adapter persists two `IN_DOMAIN` edges from the
  two distinct Word nodes (one per edition; see stable-id rule
  in section 3) to the corresponding `LouwNidaDomain` nodes, each
  edge carrying its own `source` slot. Verifier queries that filter
  by `source` then see the disagreement cleanly.

============================================================
7. Verse.text policy (Decision 15)
============================================================

The `Verse` node label is shared across the lexical store and carries
a canonical surface `text` property per OSIS reference. Decision 15
locks ownership: MorphGNT-SBLGNT writes `Verse.text` for NT verses,
OSHB-morphology writes it for OT verses. MACULA-Greek MUST NOT write
`Verse.text` under any condition. The adapter MAY read upstream
per-word `text` tokens (the MACULA Greek `text` field documented in
Decision 2's per-field predicate table) and persist them on the
`Word` node, but the `Verse.text` slot remains untouched so the
MorphGNT adapter populates it without an ingest-order race.

============================================================
8. License and redistribute (Decision 14)
============================================================

Per Decision 14 the adapter writes one `Source` node per edition
before any record-level write, and the constraint `source_slug` on
`graph/lexical.cypher` prevents a second registration of the same
slug. The Nestle1904 edition is straightforward CC-BY-4.0 with
redistribute true. The SBLGNT edition is the composite slug
`CC-BY-NC-4.0` because the SBLGNT base text is under the SBLGNT EULA
and MARBLE Louw-Nida is CC-BY-NC-4.0; the most restrictive component
governs the effective license, so redistribute is false. The
`license` and `redistribute` properties on the `Source` node are the
canonical reference for downstream Pipeline 2 citation gating.

The license slugs above match the entries in
`docs/LICENSE_TAGGING.md`. The citation slugs used by Pipeline 2
evidence files (`MACULA-Greek-Nestle1904` and `MACULA-Greek-SBLGNT`)
match `docs/phase_prompts/pipeline2_verdict.md` verbatim.

============================================================
9. Stable identifier format (Decision 2, Decision 14)
============================================================

GreekLemma stable id:
  Format `<edition>:<xml:id>`, e.g.
  `MACULA-Greek-SBLGNT:n40001001001` for the SBLGNT token whose
  MACULA `xml:id` is `n40001001001`.

Word stable id:
  Format `<edition>:<xml:id>`, identical pattern. The Word and the
  GreekLemma created for that word's first occurrence share the
  xml:id portion of the namespace; uniqueness is preserved because
  the two labels carry their own constraints
  (`word_id` and `greek_lemma_id` in `graph/lexical.cypher`).

LouwNidaDomain stable id:
  Format `<domain_code>` as string, e.g. `"12"` for domain 12.
  Subdomain is captured on the relationship, not the node, per
  Decision 2.

Source stable id:
  The slug itself, by Decision 14 uniqueness constraint
  `source_slug`.

============================================================
10. Dependence and dispatch order
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md` bullet 3,
this adapter runs in Group 1 alongside OSHB-morphology and
MACULA-Hebrew. It has no dependence on OSHB Word nodes because the
Greek text floor is independent of the Hebrew text floor. MorphGNT-
SBLGNT (Group 1 bullet 4) depends on the MACULA-Greek-SBLGNT Word
nodes for the `PARSE_OF` join, so the MACULA-Greek adapter must
complete before MorphGNT begins. The wipe contract in
`tools/wipe_lexical.py` deletes every node and relationship in the
lexical Neo4j before re-ingest, so MERGE writes start from an empty
store and the constraints reject any second write for the same
stable id.

============================================================
11. Network isolation and AST purity
============================================================

Per `docs/implementation_phases/phase_02_lexical_ingest.md`, adapter
dry-runs execute inside Docker with `--network=none`, which forbids
any HTTP, DNS, or socket access during ingest. The AST scan
`tools/check_adapter_purity.py` rejects any adapter that imports
`subprocess`, `socket`, `httpx`, `requests`, `urllib`, `aiohttp`,
`mmap`, `os.system`, `os.spawn*`, `posix_spawn`,
`multiprocessing.connection`, `pty`, `pipes`, `winreg`, `ctypes`, or
dynamic `__import__`. The implementer-impl caste commit that adds
the runnable adapter body MUST satisfy that purity scan; the local
TSV files at `data/private/macula-greek/` are the only inputs.

============================================================
12. Idempotency
============================================================

MERGE-by-stable-id is the idempotency guarantee. Re-running the
adapter on identical source bytes produces identical Word,
GreekLemma, LouwNidaDomain, Source nodes and identical
INSTANCE_OF, IN_DOMAIN, FROM_EDITION edges. The triangle-test hash
recompute in Phase D re-runs the adapter on the same source bytes;
the per-row presence vector produces a sorted list of per-row
SHA-256 hashes that must match byte-for-byte across two runs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterator

from ingest.canonical_strongs import canonical_strongs
from ingest.lexical._common import Settings, get_lexical_driver

EDITION_NESTLE = "Nestle1904"
EDITION_SBLGNT = "SBLGNT"
SOURCE_SLUG_NESTLE = "MACULA-Greek-Nestle1904"
SOURCE_SLUG_SBLGNT = "MACULA-Greek-SBLGNT"
LOUW_NIDA_PROVENANCE = "MACULA-Greek-Louw-Nida"
LICENSE_NESTLE = "CC-BY-4.0"
LICENSE_SBLGNT = "CC-BY-NC-4.0"
NULL_LITERAL = "n/a"
BATCH_SIZE = 2000

_EDITION_FILES: dict[str, str] = {
    EDITION_NESTLE: "macula-greek-Nestle1904.tsv",
    EDITION_SBLGNT: "macula-greek-SBLGNT.tsv",
}

_EDITION_TO_SOURCE: dict[str, str] = {
    EDITION_NESTLE: SOURCE_SLUG_NESTLE,
    EDITION_SBLGNT: SOURCE_SLUG_SBLGNT,
}

# Phase D T17 / ledger row KEY-MGNT-PARSEOF, resolved via A2 Option A
# (owner-chosen; docs/PHASE_D_A2_EVIDENCE.md). The MorphGNT-SBLGNT adapter
# binds its PARSE_OF edge to the MACULA-Greek-SBLGNT Word it parses. The
# contractual Word.id is the MACULA TEI xml:id (`<edition>:<xml:id>`,
# section 3 / 9 of this module's docstring) which MorphGNT can never
# reconstruct, so the join was zero-resolving (A2 evidence section 3). Per
# Option A this adapter ADDS a loss-free alias property `osis_wpos` derived
# from data it already reads (the `ref` column plus the post-`!` in-verse
# position), rendered byte-identically to the key MorphGNT builds in
# ingest/lexical/morphgnt.py `_parse_of_edge_row`:
# `f"{osis_book}.{int(chapter)}.{int(verse)}.w{position:02d}"` e.g.
# `John.1.1.w01`. Word.id, Word count, and every existing property/edge are
# byte-unchanged; only this alias is added. MorphGNT then MATCHes
# `(:Word {source:'MACULA-Greek-SBLGNT', osis_wpos:<key>})`, backed by the
# `word_osis_wpos` composite index on (Word.source, Word.osis_wpos) the
# architect adds to graph/lexical.cypher in parallel.
#
# `_MACULA_GREEK_BOOK_TO_OSIS` maps every uppercase MACULA-Greek `ref` book
# token (the USFM/Paratext 3-letter scheme; the same family convention the
# verified macula_hebrew `_MACULA_BOOK_TO_OSIS` strict bijection uses, and
# the `JHN -> John` row is byte-confirmed in PHASE_D_A2_EVIDENCE.md
# section 1) to the exact OSIS abbreviation MorphGNT's `OSIS_BOOKS` tuple
# carries (Matt..Rev, 01..27). The OSIS values below are the verbatim
# entries of that tuple, so the alias is byte-identical to the MorphGNT
# join key by construction, not a guess. macula_greek is self-contained
# (no cross-adapter import). Greek SBLGNT (NT) only. Fail-closed: if a
# row's `ref` is empty, structurally unexpected, carries a book token
# absent from this map, or has no derivable in-verse position, `osis_wpos`
# is left absent (the row still writes with id and every other property
# intact) so the PARSE_OF edge simply does not form. A missing alias is a
# faithful edge-count shortfall, never a mis-link.
_MACULA_GREEK_BOOK_TO_OSIS: dict[str, str] = {
    "MAT": "Matt",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Rom",
    "1CO": "1Cor",
    "2CO": "2Cor",
    "GAL": "Gal",
    "EPH": "Eph",
    "PHP": "Phil",
    "COL": "Col",
    "1TH": "1Thess",
    "2TH": "2Thess",
    "1TI": "1Tim",
    "2TI": "2Tim",
    "TIT": "Titus",
    "PHM": "Phlm",
    "HEB": "Heb",
    "JAS": "Jas",
    "1PE": "1Pet",
    "2PE": "2Pet",
    "1JN": "1John",
    "2JN": "2John",
    "3JN": "3John",
    "JUD": "Jude",
    "REV": "Rev",
}


def _osis_wpos(ref: str | None) -> str | None:
    """Derive the MorphGNT PARSE_OF join key from a MACULA-Greek `ref`.

    Upstream MACULA-Greek SBLGNT `ref` is the MACULA reference form
    `BOOK C:V!w` (uppercase USFM book token, ASCII space, `chapter:verse`,
    `!`, 1-based in-verse word position), e.g. `JHN 1:1!1`. The returned
    alias is byte-identical to the key MorphGNT builds in
    ingest/lexical/morphgnt.py `_parse_of_edge_row`:
    `f"{osis_ref}.w{position:02d}"` where `osis_ref` is
    `f"{book}.{int(chapter)}.{int(verse)}"` (chapter and verse as decimal
    integers with NO zero padding, per morphgnt `_osis_ref`) and the
    position is 2-digit zero-padded (`w01`). The book token is mapped
    through `_MACULA_GREEK_BOOK_TO_OSIS` to the same OSIS abbreviation
    MorphGNT's `OSIS_BOOKS` tuple emits.

    Loss-free: every component (book, chapter, verse, position) is taken
    verbatim from the `ref` string macula_greek already reads; nothing is
    dropped or invented. Fail-closed: returns None (so the alias is absent
    and the PARSE_OF edge cannot form) when `ref` is empty, missing the
    book/`chapter:verse`/`!position` structure, carries a book token absent
    from the verified map, or carries a non-integer chapter/verse/position.
    A None here is a faithful edge-count shortfall, never a mis-link.
    KEY-MGNT-PARSEOF / A2 Option A.
    """
    text = _coerce_string(ref) if ref is not None else None
    if text is None:
        return None
    bare, sep, pos_part = text.partition("!")
    if not sep:
        return None
    pos_token = pos_part.strip()
    if not pos_token.isdigit():
        return None
    book_part, book_sep, chap_verse = bare.strip().partition(" ")
    if not book_sep:
        return None
    osis_book = _MACULA_GREEK_BOOK_TO_OSIS.get(book_part)
    if osis_book is None:
        return None
    chapter, colon, verse = chap_verse.strip().partition(":")
    if not colon:
        return None
    chapter = chapter.strip()
    verse = verse.strip()
    if not chapter.isdigit() or not verse.isdigit():
        return None
    return f"{osis_book}.{int(chapter)}.{int(verse)}.w{int(pos_token):02d}"

_MERGE_SOURCE_CYPHER = (
    "UNWIND $rows AS row "
    "MERGE (n:`Source` {slug: row.slug}) "
    "SET n += row "
    "RETURN count(n) AS upserted"
)

_MERGE_WORD_CYPHER = (
    "UNWIND $rows AS row "
    "MERGE (n:`Word` {id: row.id}) "
    "SET n += row "
    "RETURN count(n) AS upserted"
)

_MERGE_LEMMA_CYPHER = (
    "UNWIND $rows AS row "
    "MERGE (n:`GreekLemma` {id: row.id}) "
    "SET n += row "
    "RETURN count(n) AS upserted"
)

_MERGE_DOMAIN_CYPHER = (
    "UNWIND $rows AS row "
    "MERGE (n:`LouwNidaDomain` {id: row.id}) "
    "SET n += row "
    "RETURN count(n) AS upserted"
)

_MERGE_INSTANCE_OF_CYPHER = (
    "UNWIND $rows AS row "
    "MATCH (w:`Word` {id: row.from_id}) "
    "MATCH (l:`GreekLemma` {id: row.to_id}) "
    "MERGE (w)-[r:`INSTANCE_OF`]->(l) "
    "RETURN count(r) AS upserted"
)

_MERGE_IN_DOMAIN_CYPHER = (
    "UNWIND $rows AS row "
    "MATCH (w:`Word` {id: row.from_id}) "
    "MATCH (d:`LouwNidaDomain` {id: row.to_id}) "
    "MERGE (w)-[r:`IN_DOMAIN` "
    "{domain_code: row.domain_code, "
    "subdomain_code: row.subdomain_code, "
    "source: row.source}]->(d) "
    "RETURN count(r) AS upserted"
)

_MERGE_FROM_EDITION_CYPHER = (
    "UNWIND $rows AS row "
    "MATCH (w:`Word` {id: row.from_id}) "
    "MATCH (s:`Source` {slug: row.to_slug}) "
    "MERGE (w)-[r:`FROM_EDITION`]->(s) "
    "RETURN count(r) AS upserted"
)


def _coerce_string(value: str) -> str | None:
    """Return trimmed value, or None when empty or the literal n/a sentinel."""
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or trimmed == NULL_LITERAL:
        return None
    return trimmed


def _coerce_strong(value: str) -> int | None:
    s = _coerce_string(value)
    if s is None:
        return None
    cleaned = "".join(ch for ch in s if ch.isdigit())
    if not cleaned:
        return None
    return int(cleaned)


def _canonical_strong_or_none(strong: int) -> str | None:
    """Return the canonical Greek Strong string, or None when unresolvable.

    Decision 18 (KEY-MG-STRONG) binds `GreekLemma.strong` to the single
    normaliser `ingest.canonical_strongs.canonical_strongs(raw, lang='gk')`
    and forbids any hand-rolled Strong normaliser (SCHEMA_DECISIONS.md line
    644). `canonical_strongs` RAISES `ValueError` (it has no sentinel
    return) for any token it cannot resolve to a single canonical Strong.

    A confirmed slice of frozen MACULA-Greek upstream carries the
    `strong` cell as a `+`-joined COMPOUND of the component Strongs for
    Greek crasis / multi-stem word-forms, e.g. `1537+4053` (ἐκπερισσῶς =
    ἐκ G1537 + περισσῶς G4053), `5228+1537+4053` (ὑπερεκπερισσοῦ),
    `1501+5140` (εἰκοσιτρεῖς), `1417+3461` (δισμυριάς). The adapter's
    `_coerce_strong` digit-strip collapses `1537+4053` to the integer
    `15374053`, and `canonical_strongs('15374053','gk')` then raises
    `ValueError: unrecognized Strong's encoding: '15374053'` (8 digits
    exceeds the `\\d{1,5}` the normaliser accepts). Uncaught, that
    ValueError propagated through `_flush` / `_process_edition` /
    `ingest_macula_greek` (no try/except in run.py) and killed the entire
    pass-1 reseed at adapter #6.

    No Decision (2 or 18) specifies a compound-`+`-split or
    first-component rule for the Greek `GreekLemma.strong` join key, and
    Decision 18 line 644 explicitly forbids hand-rolling one. Decision 18
    line 642 / line 681 is binding: when `canonical_strongs` raises
    (empty, malformed, non-Strong), the producing adapter MUST NOT
    fabricate a Strong. It either skips the Strong attachment or routes to
    a documented sentinel. This adapter's docstring section 4 INSTANCE_OF
    clause already mandates the SKIP path ("Rows where the row has no
    resolvable Strong MUST be persisted without the INSTANCE_OF edge
    rather than fabricating a sentinel lemma"), so this returns None and
    `_row_lemma_payload` emits no GreekLemma and no INSTANCE_OF for the
    row; the Word node still writes with every property (including its
    raw `strong` int per Decision 2, which is unaffected). This mirrors
    the verified macula_hebrew `_canonical` try/except ValueError -> None
    pattern (ingest/lexical/macula_hebrew.py). Determinism: pure function
    of the frozen upstream cell. KEY-MG-STRONG / Decision 18.
    """
    try:
        return canonical_strongs(str(strong), "gk")[0]
    except ValueError:
        return None


def _split_ln_pair(token: str) -> tuple[int, int] | None:
    """Split a single Louw-Nida code token like '93.169a' into (domain, subdomain).

    Trailing variant letters on the subdomain are stripped before int conversion.
    Returns None when the token cannot be parsed as two non-empty numeric parts.
    """
    if "." in token:
        head, tail = token.split(".", 1)
    elif ":" in token:
        head, tail = token.split(":", 1)
    else:
        return None
    head = head.strip()
    tail = tail.strip()
    if not head or not tail:
        return None
    sub_digits = "".join(ch for ch in tail if ch.isdigit())
    if not head.isdigit() or not sub_digits:
        return None
    return int(head), int(sub_digits)


def _ln_tokens(ln_value: str | None) -> list[str]:
    if ln_value is None:
        return []
    return [tok for tok in ln_value.replace("\t", " ").split() if tok]


def _row_word_payload(edition: str, fields: dict[str, str]) -> dict[str, Any]:
    xml_id = _coerce_string(fields.get("xml:id", ""))
    source = _EDITION_TO_SOURCE[edition]
    ref = _coerce_string(fields.get("ref", ""))
    payload: dict[str, Any] = {
        "id": f"{source}:{xml_id}" if xml_id else None,
        "xml_id": xml_id,
        "ref": ref,
        "lemma": _coerce_string(fields.get("lemma", "")),
        "normalized": _coerce_string(fields.get("normalized", "")),
        "strong": _coerce_strong(fields.get("strong", "")),
        "morph": _coerce_string(fields.get("morph", "")),
        "gloss": _coerce_string(fields.get("gloss", "")),
        "domain": _coerce_string(fields.get("domain", "")),
        "ln": _coerce_string(fields.get("ln", "")),
        "text": _coerce_string(fields.get("text", "")),
        "source": source,
        "edition": edition,
    }
    # Phase D T17 / KEY-MGNT-PARSEOF, A2 Option A: the MorphGNT-SBLGNT
    # PARSE_OF edge targets the MACULA-Greek-SBLGNT edition only, so the
    # loss-free `osis_wpos` join alias is emitted only for SBLGNT rows.
    # The Nestle1904 edition is byte-untouched (no new property). The
    # alias is added only when it derives faithfully; a None drops the
    # key entirely (fail-closed) rather than fabricating a partial value.
    if edition == EDITION_SBLGNT:
        osis_wpos = _osis_wpos(ref)
        if osis_wpos is not None:
            payload = {**payload, "osis_wpos": osis_wpos}
    return payload


def _row_lemma_payload(edition: str, word: dict[str, Any]) -> dict[str, Any] | None:
    strong = word.get("strong")
    lemma = word.get("lemma")
    if strong is None or lemma is None:
        return None
    # Decision 18 producer authority (KEY-MG-STRONG): GreekLemma.strong is
    # the canonical Strong STRING (canon[0], e.g. 'G0040'), never an int.
    # When canonical_strongs cannot resolve the token (confirmed frozen
    # upstream: `+`-joined compound Strongs for Greek crasis/multi-stem
    # word-forms; see _canonical_strong_or_none), Decision 18 line 642/681
    # FORBIDS fabricating a Strong and this adapter's docstring section 4
    # mandates the skip path: no GreekLemma node, no INSTANCE_OF edge for
    # the row. Returning None here (the existing `if lemma is not None`
    # guard in _process_edition already drives the faithful skip) keeps
    # the Word node and every property intact and never raises.
    canonical = _canonical_strong_or_none(strong)
    if canonical is None:
        return None
    source = _EDITION_TO_SOURCE[edition]
    lemma_id = f"{source}:strong-{int(strong):05d}"
    return {
        "id": lemma_id,
        "lemma": lemma,
        # Every Greek consumer (tagnt, tbesg, tflsj) joins on this exact
        # canonical value. GreekLemma.id namespacing
        # (<source>:strong-<int:05d>) is unchanged by Decision 18.
        "strong": canonical,
        "source": source,
        "edition": edition,
    }


def _row_domain_payload(domain_code: int) -> dict[str, Any]:
    return {
        "id": str(domain_code),
        "domain_code": int(domain_code),
        "source": LOUW_NIDA_PROVENANCE,
    }


def _iter_tsv_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        header_line = fh.readline()
        if not header_line:
            return
        header = header_line.rstrip("\r\n").split("\t")
        for raw in fh:
            line = raw.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < len(header):
                parts = [*parts, *([""] * (len(header) - len(parts)))]
            yield {header[i]: parts[i] for i in range(len(header))}


def _flush(session: Any, cypher: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    session.run(cypher, rows=rows).consume()
    return len(rows)


def _merge_sources(session: Any) -> int:
    payload = [
        {
            "slug": SOURCE_SLUG_NESTLE,
            "license": LICENSE_NESTLE,
            "redistribute": True,
        },
        {
            "slug": SOURCE_SLUG_SBLGNT,
            "license": LICENSE_SBLGNT,
            "redistribute": False,
        },
    ]
    session.run(_MERGE_SOURCE_CYPHER, rows=payload).consume()
    return len(payload)


def _process_edition(
    session: Any,
    edition: str,
    tsv_path: Path,
    lemma_seen: set[str],
    domain_seen: set[int],
) -> dict[str, int]:
    counts = {
        "Word": 0,
        "GreekLemma": 0,
        "LouwNidaDomain": 0,
        "INSTANCE_OF": 0,
        "IN_DOMAIN": 0,
        "FROM_EDITION": 0,
        # Decision 18 line 642/681 skip-path surfacing: a strong-and-lemma
        # bearing row whose upstream `strong` cell does not resolve to a
        # single canonical Greek Strong (confirmed frozen upstream:
        # `+`-joined compound Strongs for crasis/multi-stem forms). The
        # Word still writes; no GreekLemma / INSTANCE_OF for the row. This
        # is counted, never silent, never raising, never fabricated.
        "_unresolved_strong": 0,
    }
    word_batch: list[dict[str, Any]] = []
    lemma_batch: list[dict[str, Any]] = []
    domain_batch: list[dict[str, Any]] = []
    instance_batch: list[dict[str, Any]] = []
    in_domain_batch: list[dict[str, Any]] = []
    from_edition_batch: list[dict[str, Any]] = []
    source_slug = _EDITION_TO_SOURCE[edition]
    per_word_in_domain_keys: set[tuple[str, int, int]] = set()

    for fields in _iter_tsv_rows(tsv_path):
        word = _row_word_payload(edition, fields)
        if word["id"] is None:
            continue
        word_batch = [*word_batch, word]
        from_edition_batch = [
            *from_edition_batch,
            {"from_id": word["id"], "to_slug": source_slug},
        ]
        lemma = _row_lemma_payload(edition, word)
        if (
            lemma is None
            and word.get("strong") is not None
            and word.get("lemma") is not None
        ):
            # Both strong and lemma present, so the only None path is an
            # unresolvable canonical Strong (Decision 18 line 642/681
            # faithful skip). Surface it; the Word still persists below.
            counts["_unresolved_strong"] += 1
        if lemma is not None:
            if lemma["id"] not in lemma_seen:
                lemma_seen.add(lemma["id"])
                lemma_batch = [*lemma_batch, lemma]
            instance_batch = [
                *instance_batch,
                {"from_id": word["id"], "to_id": lemma["id"]},
            ]
        ln_value = word.get("ln")
        if ln_value is not None and word.get("strong") is not None:
            for token in _ln_tokens(ln_value):
                pair = _split_ln_pair(token)
                if pair is None:
                    continue
                d_code, s_code = pair
                key = (word["id"], d_code, s_code)
                if key in per_word_in_domain_keys:
                    continue
                per_word_in_domain_keys.add(key)
                if d_code not in domain_seen:
                    domain_seen.add(d_code)
                    domain_batch = [*domain_batch, _row_domain_payload(d_code)]
                in_domain_batch = [
                    *in_domain_batch,
                    {
                        "from_id": word["id"],
                        "to_id": str(d_code),
                        "domain_code": d_code,
                        "subdomain_code": s_code,
                        "source": source_slug,
                    },
                ]
        if len(word_batch) >= BATCH_SIZE:
            counts["Word"] += _flush(session, _MERGE_WORD_CYPHER, word_batch)
            word_batch = []
            counts["GreekLemma"] += _flush(
                session, _MERGE_LEMMA_CYPHER, lemma_batch
            )
            lemma_batch = []
            counts["LouwNidaDomain"] += _flush(
                session, _MERGE_DOMAIN_CYPHER, domain_batch
            )
            domain_batch = []
            counts["INSTANCE_OF"] += _flush(
                session, _MERGE_INSTANCE_OF_CYPHER, instance_batch
            )
            instance_batch = []
            counts["IN_DOMAIN"] += _flush(
                session, _MERGE_IN_DOMAIN_CYPHER, in_domain_batch
            )
            in_domain_batch = []
            counts["FROM_EDITION"] += _flush(
                session, _MERGE_FROM_EDITION_CYPHER, from_edition_batch
            )
            from_edition_batch = []

    counts["Word"] += _flush(session, _MERGE_WORD_CYPHER, word_batch)
    counts["GreekLemma"] += _flush(session, _MERGE_LEMMA_CYPHER, lemma_batch)
    counts["LouwNidaDomain"] += _flush(
        session, _MERGE_DOMAIN_CYPHER, domain_batch
    )
    counts["INSTANCE_OF"] += _flush(
        session, _MERGE_INSTANCE_OF_CYPHER, instance_batch
    )
    counts["IN_DOMAIN"] += _flush(
        session, _MERGE_IN_DOMAIN_CYPHER, in_domain_batch
    )
    counts["FROM_EDITION"] += _flush(
        session, _MERGE_FROM_EDITION_CYPHER, from_edition_batch
    )
    return counts


def ingest_macula_greek(
    data_root: Path, settings: Settings
) -> dict[str, int]:
    """Parse MACULA Greek Nestle1904 and SBLGNT TSV releases and MERGE the graph.

    Reads TSV releases at data_root / <edition> / tsv / macula-greek-<edition>.tsv
    and emits Word, GreekLemma, LouwNidaDomain, Source nodes plus INSTANCE_OF,
    IN_DOMAIN, FROM_EDITION edges per the docstring contract above.
    """
    driver = get_lexical_driver(settings)
    totals: dict[str, int] = {
        "Word": 0,
        "GreekLemma": 0,
        "LouwNidaDomain": 0,
        "Source": 0,
        "INSTANCE_OF": 0,
        "IN_DOMAIN": 0,
        "FROM_EDITION": 0,
        # Decision 18 line 642/681 faithful skip-path surfacing (see
        # _canonical_strong_or_none / _process_edition). Counted, not
        # silent; the reseed never crashes on an unresolvable Strong.
        "_unresolved_strong": 0,
    }
    lemma_seen: set[str] = set()
    domain_seen: set[int] = set()
    with driver.session() as session:
        totals["Source"] = _merge_sources(session)
        for edition in (EDITION_NESTLE, EDITION_SBLGNT):
            tsv_path = data_root / edition / "tsv" / _EDITION_FILES[edition]
            if not tsv_path.exists():
                continue
            edition_counts = _process_edition(
                session, edition, tsv_path, lemma_seen, domain_seen
            )
            # Deterministic stderr surfacing (one line per edition, only
            # when the skip path fired) so an unresolvable Strong is never
            # silent. Decision 18 line 642/681; KEY-MG-STRONG.
            unresolved = edition_counts.get("_unresolved_strong", 0)
            if unresolved:
                print(
                    f"macula_greek: edition={_EDITION_TO_SOURCE[edition]} "
                    f"unresolved_strong={unresolved} "
                    "(compound/non-Strong upstream `strong` cell; "
                    "GreekLemma+INSTANCE_OF skipped per Decision 18 "
                    "line 642/681, Word persisted)",
                    file=sys.stderr,
                )
            for key, value in edition_counts.items():
                totals[key] = totals.get(key, 0) + value
    return totals
