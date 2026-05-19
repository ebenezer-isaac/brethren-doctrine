# Phase D: MERGE Null-Property Class Audit

Caste: AUDITOR. Mode: READ-ONLY static source analysis. No code or tests modified.
Scope: every `ingest/lexical/*.py` (23 adapters) plus `ingest/lexical/_common.py`.
Branch: main. HEAD ~ d41cea0.

## 0. Defect class definition

Neo4j raises `Neo.ClientError.Statement.SemanticError: Cannot merge ... null
property value for '<prop>'` when a property inside a MERGE pattern map
(node OR relationship) evaluates to `null` at runtime. The FakeDriver
coverage harness does NOT enforce this Neo4j semantic, so the class is
invisible until a real ingest. Confirmed in production at
`macula_hebrew._MERGE_BRIDGES_LXX` (`greek_strong` null in some rows),
fixed in commit 3dc79ee (worktree aa352438b5b9326ec) by moving the
nullable attributes OUT of the MERGE pattern into a post-MERGE SET while
the identity props stayed in MERGE.

Key Neo4j nuance applied throughout this audit: the error fires ONLY for
`null` (Python `None`). An empty string `""` is a legal MERGE property
value (it produces a junk node, a data-quality problem, NOT this crash).
Classification is therefore strictly: can the pattern property be Python
`None` / absent for some real upstream row.

## 1. Sites scanned

Every MERGE in the lexical tree was enumerated. Two site categories
matter for this class:

- Relationship MERGE WITH a property map: `MERGE (a)-[r:T {..}]->(b)`
- Node MERGE whose pattern map has >1 key OR a non-`id` key

All other relationship MERGEs use the already-correct
MATCH-then-`MERGE (a)-[r:T]->(b)` form with attributes in a post-MERGE
`SET` (identity-only pattern, the faithful target shape) and are not
defect sites. Node MERGEs on a single `{id: row.id}` / `{slug: row.slug}`
key were still traced to prove the key value is non-null.

### 1a. Relationship-MERGE-with-propmap sites

| file:line | rel type | pattern-map props | classification |
|---|---|---|---|
| open_cbgm_3_john.py:509 | READS_AT | variant_unit_id | SAFE |
| macula_hebrew.py:482-483 | HAS_MACULA_ENRICHMENT | osis_ref, join_lemma | SAFE |
| macula_hebrew.py:497-500 | BRIDGES_LXX | greek_surface, greek_strong, source | EXCLUDED (fixed 3dc79ee) |
| openbible.py:308-309 | OPENBIBLE_CROSS_REF | from_osis, to_osis, source | SAFE |
| macula_greek.py:545-548 | IN_DOMAIN | domain_code, subdomain_code, source | SAFE |
| tsk.py:626-627 | CROSS_REF | source, osis_target | SAFE |
| open_cbgm_3_john.py:253 | READS_AT (docstring sample only, not executed) | variant_unit_id | N/A docstring |

### 1b. Node-MERGE multi-key or non-id-key sites

| file:line | label | pattern-map props | classification |
|---|---|---|---|
| bhsa.py:401 | TFNode | corpus, node_id | SAFE |
| open_cbgm_3_john.py:493 | Witness | siglum | SAFE |
| open_cbgm_3_john.py:497-498 | VariantUnit | variant_unit_id | SAFE |
| open_cbgm_3_john.py:502 | Reading | reading_id | SAFE |
| oshb.py:359 | Reading | reading_id | SAFE |
| stepbible_morph_codes.py:225 | MorphCode | code | SAFE |
| stepbible_tbesg.py:311 | BriefLexEntry | strong_disambig | SAFE |
| stepbible_tbesh.py:295 | BriefLexEntry | strong_disambig | SAFE |
| stepbible_tbesh.py:307 | Lemma | strong (= base_strong) | SAFE |
| stepbible_proper_nouns.py:348 | ProperNoun | proper_name_entry | SAFE |
| stepbible_proper_nouns.py:352 | Verse | osisID | SAFE |
| vulgate_clementine.py:308 | VulgateVerse | osis | SAFE |
| theographic.py:498 | Person/Place/Period/Event/Group/Tribe | entity_id | NULL-RISK-UNPROVEN |

All `{slug: row.slug}` Source MERGEs (every adapter) use a module-level
`SOURCE_SLUG` constant: provably non-null, SAFE, not tabulated
individually. All `{id: row.id}` node MERGEs were traced (results in
section 2); their `id` is an f-string built from parse-guarded
components: SAFE.

Total relationship-MERGE-with-propmap sites scanned: 6 executed
(plus BRIDGES_LXX excluded as already fixed; plus 1 docstring sample).
Total node-MERGE multi-key / non-id-key sites scanned: 13 (excluding
the uniform SOURCE_SLUG and f-string-id node MERGEs which were also
traced and are SAFE).

Result: SAFE = 18 of 19 in-scope sites. NULL-RISK = 1
(theographic entity_id, NULL-RISK-UNPROVEN, IDENTITY-bearing).

## 2. Per-adapter findings with row-builder evidence

### open_cbgm_3_john.py  (caste: per owning phase)
- READS_AT `{variant_unit_id}` (line 509): `variant_unit_id` built at
  line 597 `f"{BOOK}.{CHAPTER}.{verse}/{unit_segment}"` after the
  `_APP_RE` match guard (line 590 `if match is None: return None`);
  all f-string components non-null. **SAFE.**
- Witness `{siglum}` (493): siglum constructed at 696
  `base if marker is None else f"{base}{marker}"`, then guarded
  `if siglum not in witness_props: continue` (697-698). `_split_hand`
  (559-563) always returns a non-null string for the base. **SAFE.**
- VariantUnit `{variant_unit_id}` (497), Reading `{reading_id}` (502):
  f-string ids (`reading_id` = `f"{variant_unit_id}-{reading_name}"`
  line 608, lacuna `f"{variant_unit_id}-lac"` line 727). **SAFE.**
- ATTESTED_BY, CORRECTOR_OF: MATCH-then-MERGE, no pattern propmap.
  **SAFE.**

### macula_hebrew.py  (caste: per owning phase) -- 3dc79ee cross-check
- BRIDGES_LXX: EXCLUDED, fixed in 3dc79ee (nullable
  `greek_surface`/`greek_strong` moved out of MERGE into SET; identity
  is `(h.id, g.id)` via MATCH). Cross-check of the post-fix source
  confirms the remaining MERGEs are clean:
- HAS_MACULA_ENRICHMENT `{osis_ref, join_lemma}` (482-483): guarded at
  line 700 `if osis is not None and row["lemma"] is not None:` before
  the enrichment row is appended (701-707). `_osis_ref` (565-593)
  returns `None` on any malformed ref but the guard drops the row
  faithfully rather than emitting a null key. Both pattern props
  provably non-null. **SAFE.**
- INSTANCE_OF (490): MATCH-then-MERGE, no propmap. **SAFE.**
- Node MERGEs (Source/MaculaToken/Lemma/GreekLemma) all `{id}` /
  `{slug}` with constructed-string ids. **SAFE.**
- macula_hebrew confirmed clean per 3dc79ee audit. No further action.

### openbible.py  (caste: per owning phase)
- OPENBIBLE_CROSS_REF `{from_osis, to_osis, source}` (308-309):
  row builder at 394-405 computes `from_osis`/`to_osis` via
  `_project_to_osis`, then quarantine-guards
  `if not from_osis or not to_osis or votes is None: continue`
  (line 397). `source` = `SOURCE_SLUG` constant. `votes` is in the
  post-MERGE `SET r.votes` (line 310), correctly NOT in the pattern
  (Decision 5 mandates votes excluded from MERGE key). All three
  pattern props provably non-null. **SAFE.**

### macula_greek.py  (caste: per owning phase)
- IN_DOMAIN `{domain_code, subdomain_code, source}` (545-548):
  `d_code, s_code = pair` where `pair = _split_ln_pair(token)` with
  guard `if pair is None: continue` (755-756). `_split_ln_pair`
  (581-600) returns `tuple[int,int]` only after `head.isdigit()` and
  `sub_digits` non-empty checks, else `None`; it can never return a
  tuple containing `None`. `source` = `source_slug` =
  `_EDITION_TO_SOURCE[edition]` (dict lookup; KeyError not None).
  All three pattern props provably non-null. **SAFE.**
- INSTANCE_OF, FROM_EDITION: MATCH-then-MERGE, no propmap. **SAFE.**

### tsk.py  (caste: per owning phase)
- CROSS_REF `{source, osis_target}` (626-627): `targets` built
  (577-582) appending only `projected` values where
  `if projected is not None`. Edges emitted (602-611) only when NOT
  `unresolved` (`unresolved = anchor_osis is None or not targets`,
  line 583), so `targets` is non-empty and every element non-null.
  `source` = `SOURCE_SLUG`. `license`/`redistribute` are in the
  post-MERGE SET (628), correctly outside the pattern. Both pattern
  props provably non-null. **SAFE.**

### bhsa.py  (caste: per owning phase)
- TFNode `{corpus, node_id}` (401): row builder `_tfnode_rows`
  (838-852) emits `{"corpus": CORPUS, "node_id": nid, ...}` where
  `CORPUS = "bhsa"` (module constant, line 379) and
  `nid = int(item["node_id"])` (847). `int()` never returns `None`
  (raises on bad input rather than yielding null). Both pattern
  props provably non-null. **SAFE.**
- BhsaWord/Phrase/Clause `{id}`: `_sid(int(...))` f-string. **SAFE.**
- CONTAINS_PHRASE/WORD, IN_VERSE: MATCH-then-MERGE, no propmap.
  **SAFE.**

### oshb.py  (caste: per owning phase)
- Reading `{reading_id}` (359): `reading_id` =
  `f"oshb-reading:{osis_ref}.w{pos_pad}.qere"` (line 623), f-string,
  always non-null. Other node MERGEs key `{id}` from f-strings.
  Rel-MERGEs (HAS_MORPHEME, IN_VERSE, INSTANCE_OF, IS_QERE_OF,
  FROM_EDITION) MATCH-then-MERGE, no propmap. **SAFE.**

### stepbible_morph_codes.py  (caste: per owning phase)
- MorphCode `{code}` (225): row builder guards
  `if not code or not meaning or code in seen: continue` (269);
  `code` = `parts[0]` non-empty string. **SAFE.**

### stepbible_tbesg.py  (caste: per owning phase)
- BriefLexEntry `{strong_disambig}` (311): `_row_to_node` guards
  `if not _ESTRONG_PATTERN.match(base_strong): return None` (353),
  `strong_disambig = _disambig_token(...)` returns a non-empty
  string. **SAFE.** LEX_FOR MATCH-then-MERGE no propmap. **SAFE.**

### stepbible_tbesh.py  (caste: per owning phase)
- BriefLexEntry `{strong_disambig}` (295) and Lemma
  `{strong: base_strong}` (307): builder (388-417) guards
  `if not e_strong or not e_strong.startswith(("H","G")): return
  None` (395); `disambig = _extract_disambig(...) or e_strong`
  (always non-empty); `base = _canonical_base_strong(base)` returns
  a string. Both keys provably non-null. **SAFE.**
  LEX_FOR/FROM_EDITION MATCH-then-MERGE no propmap. **SAFE.**

### stepbible_proper_nouns.py  (caste: per owning phase)
- ProperNoun `{proper_name_entry}` (348): `_normalise_node` guards
  `if not entry or language not in VALID_LANGUAGES: return None`
  (492); node rows dropped when None. **SAFE.**
- Verse `{osisID}` (352) for NAMED_AT: `_named_at_rows` (598-611)
  guards `if not OSIS_REF_RE.match(osis): continue`; `osis`
  non-empty; `proper_name_entry` comes from an already-guarded node
  row. **SAFE.**

### vulgate_clementine.py  (caste: per owning phase)
- VulgateVerse `{osis}` (308): `_row_from_osis` guards
  `if not osis: return None` (392); rows dropped when None
  (418). **SAFE.**

### stepbible_ttesv.py / stepbible_tahot.py / stepbible_tagnt.py  (caste: per owning phase)
- All node MERGEs `{id}` / `{slug}`; `id` is an f-string
  (`stepbible-ttesv:{osis_ref}.w{pos_raw}` line 466;
  `_token_stable_id(osis,pos,edition)` tahot 425;
  `{ID_PREFIX}:{osis_ref}.w{pos_padded}` tagnt 326) built only after
  parse guards return None and drop the row. INSTANCE_OF / IN_VERSE
  / FROM_EDITION MATCH-then-MERGE, no propmap. **SAFE.**

### stepbible_tflsj.py / stepbible_tvtms.py  (caste: per owning phase)
- Node MERGEs `{id}` / `{slug}`; `id` =
  `_stable_id(strong, lemma)` (tflsj 388) / `stable` (tvtms 352)
  f-string ids. LEX_FOR MATCH-then-MERGE no propmap. **SAFE.**

### etcbc_parallels.py  (caste: per owning phase)
- PARALLEL_OF (339): MATCH-then-MERGE WITHOUT property map.
  Contract section 6 (lines 156-186) explicitly mandates the
  MATCH-then-MERGE form precisely because a single MERGE with a
  property map on a nullable tuple is unsafe. Already correct.
  **SAFE.**

### etcbc_phono.py  (caste: per owning phase)
- Only Source `{slug}` MERGE (SOURCE_SLUG). Enrichment is
  MATCH-then-SET (no node/edge MERGE on parsed data). **SAFE.**

### morphgnt.py  (caste: per owning phase)
- Word/Verse `{id}` (f-string ids); Source `{slug}`. IN_VERSE,
  PARSE_OF MATCH-then-MERGE no propmap. **SAFE.**

### peshitta.py  (caste: per owning phase)
- SyriacWord `{id}` = `_stable_id(verse_ref, token_pos)` after
  guards `if not verse_ref: return None` (275),
  `if not text: return None` (283). IN_VERSE MATCH-then-MERGE
  no propmap. **SAFE.**

### coptic_scriptorium.py  (caste: per owning phase)
- CopticWord `{id}` = `stable_id` f-string after parse guards
  returning None (491/494/502). IN_VERSE MATCH-then-MERGE
  no propmap. **SAFE.**

### theographic.py  (caste: per owning phase) -- THE ONE NULL-RISK
- All six entity labels are MERGEd via
  `_MERGE_NODE_TEMPLATE` (line 498):
  `MERGE (n:`{label}` {entity_id: row.entity_id})`. `entity_id` is
  the SOLE MERGE key.
- Row builders:
  - `_person_node` (574-588): `rid = rec.get("id", "")`;
    `entity_id = _slug(fields, rid, "slug", "personLookup")`.
  - `_place_node` (591-614): same pattern, `_slug(fields, rid,
    "slug", "placeLookup")`.
  - `_event_node` (617-626): `entity_id = rid` DIRECTLY, NO slug
    fallback at all (highest risk path).
  - `_group_node` (629-640): `entity_id = rid` DIRECTLY.
  - `_period_nodes` (654-693): `entity_id = slug` f-string
    (`period-bce-..` / `period-ce-..`). **This sub-path SAFE.**
- `_slug` (543-548): returns the first `fields[key]` that is a
  non-empty space-free string, else falls back to `record_id`
  (= `rid`).
- `_records` (537-540): filters ONLY non-dict entries. It does NOT
  filter records whose `id` is missing or explicitly JSON `null`.
- Null path: `rec.get("id", "")` returns `""` for an ABSENT key
  (empty string -> legal MERGE value, junk node, NOT this crash),
  BUT returns Python `None` for a PRESENT key whose JSON value is
  `null` (`dict.get` default applies only to absent keys, not
  present-but-null keys). For `_event_node` / `_group_node`
  (`entity_id = rid` with no slug fallback) and for the
  `_person_node` / `_place_node` no-usable-slug branch, an upstream
  record with `"id": null` yields `entity_id = None`, which flows
  straight into the MERGE pattern map and triggers the exact
  `Neo.ClientError.Statement.SemanticError` null-property class.
- The cached Airtable-style release normally always carries a record
  `id`, so this may never fire on the current snapshot; but the
  parser provides NO guard, the harness cannot prove the upstream
  invariant, and the contract treats upstream schema drift as
  expected (Decision 10 mandates a snapshot ledger precisely to
  detect drift). Static null-safety is therefore NOT provable.
  Per the conservative rule: **NULL-RISK-UNPROVEN**, reason: the
  upstream record `id` (Airtable record id) is consumed unguarded
  and a null/JSON-null `id` with no usable slug fallback produces a
  null MERGE key; the parser does not enforce the
  `id present and non-null` invariant the contract assumes.
- IDENTITY classification: **IDENTITY-BEARING.** SCHEMA_DECISIONS
  Decision 10 (docs/SCHEMA_DECISIONS.md lines 328-369):
  `entity_id` IS the canonical identifier and the SOLE MERGE key;
  the acceptance query (lines 335-338) REQUIRES
  `p.entity_id IS NOT NULL`; edge case (line 342) mandates the slug
  be preserved as `entity_id` so persons do not collapse on display
  name. `entity_id` is not a payload attribute; it cannot be moved
  to a post-MERGE SET (it is the merge predicate). Therefore the
  ATTRIBUTE-move-to-SET remedy used for macula_hebrew
  BRIDGES_LXX does NOT apply here.
- Remedy: **IDENTITY-MUST-ESCALATE.** A null `entity_id` means the
  entity cannot exist faithfully under Decision 10. The faithful
  fix is a row-builder guard that, when no non-null identifier can
  be derived (no usable slug AND `rec.get("id")` is None/empty),
  faithfully DROPS the record (consistent with the contract's
  "MUST NOT invent fields" and the every-other-adapter
  parse-guard-then-drop pattern), and the drop count must be
  surfaced (snapshot ledger / quarantine), NOT silently emit a
  null/empty-string junk node. The exact drop-vs-sentinel choice
  and the ledger surfacing are an owning-phase decision under
  Decision 10; the auditor MUST NOT guess it. Escalate.

## 3. DEFECT LEDGER

| # | file:line | label/rel | pattern-prop | class | IDENTITY? | owning adapter | caste | prescribed single-file fix |
|---|---|---|---|---|---|---|---|---|
| D-1 | theographic.py:498 (key produced at 576-577, 593-594, 619-622, 631-635 via `_slug`/`rid`) | Person, Place, Event, Group, Tribe node MERGE `{entity_id}` | entity_id | NULL-RISK-UNPROVEN | YES (Decision 10) | theographic.py | per owning phase | IDENTITY-MUST-ESCALATE. In the row builders (`_person_node`, `_place_node`, `_event_node`, `_group_node`, and the `_records` intake), enforce the `entity_id present and non-null` invariant Decision 10 assumes: derive a non-null identifier or faithfully DROP the record with the drop surfaced in the snapshot ledger/quarantine. Do NOT move entity_id to a post-MERGE SET (it is the sole MERGE key). Do NOT silently emit a null/empty-string node. Exact drop-vs-sentinel and ledger mechanism is an owning-phase Decision-10 call; escalate before implementing. |

No other NULL-RISK instances. macula_hebrew BRIDGES_LXX excluded
(already fixed, 3dc79ee). All other 18 in-scope MERGE-pattern sites
proven SAFE with row-builder evidence in section 2.

## 4. FIX WAVE (single-touch, parallel-safe)

One task, one file. Only one adapter carries a NULL-RISK
MERGE-pattern property, so the wave is a single task and relaunch-3
will not rediscover this class serially.

| wave task | file | scope | dependency | gate |
|---|---|---|---|---|
| FW-1 | ingest/lexical/theographic.py | D-1: guard `entity_id` non-null at the row-builder / `_records` boundary per Decision 10; faithfully drop + surface unidentifiable records; entity_id stays the MERGE key | none (single file, no cross-adapter coupling) | ESCALATE first: confirm drop-vs-sentinel and ledger surfacing with the Decision-10 owner before code change |

No other adapter requires a touch. After FW-1 is escalated, decided,
and applied, the whole MERGE-null-property class is closed and a
clean relaunch (attempt 3) will not crash serially on this class.

## 5. Verification notes / limits

- FakeDriver does not enforce Neo4j MERGE-null semantics; this audit
  is pure static source tracing, intentionally adversarial: every
  site assumed unsafe until the row-builder proved non-nullability.
- Empty-string MERGE keys (theographic absent-`id` -> `""`) are a
  data-quality concern (junk node) but NOT this crash class; flagged
  inside D-1 for completeness, the crash trigger is the explicit
  JSON-`null` `id` path producing Python `None`.
- macula_hebrew confirmed clean post-3dc79ee (BRIDGES_LXX fixed;
  HAS_MACULA_ENRICHMENT and INSTANCE_OF independently re-proven
  SAFE here).
- `_common.py` shared loader uses the already-correct pattern
  (node `{id: row.id}`, relationship `MERGE (a)-[r]->(b) SET r +=
  row.properties` with NO pattern propmap); it is the faithful
  target shape, not a defect site. Its `row.id` non-nullability is
  the responsibility of each record-builder feeding it; no lexical
  adapter audited here routes a nullable id into it.
