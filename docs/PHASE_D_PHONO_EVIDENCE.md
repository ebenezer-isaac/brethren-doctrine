# Phase D ETCBC-phono Forensic Evidence (Auditor caste, owner per-source review)

READ-ONLY offline reproduction from the frozen text-fabric modules on disk.
HEAD at audit start: branch main, 02ebae8. No lexical Neo4j was queried.
No code, tests, expected_counts, baseline, adapters, or run.py were modified.
This document is the only write. No git commit performed.

Doctrinal frame: brethren-on-trial. The parse is trusted, the catalog is
the thing under test. The adapter is faithful per Decision 3 and is NOT
proposed for change. This document lays out evidence and both owner
options without pre-deciding.

---

## 0. Resolved upstream paths and release tags

Authoritative source for paths is the adapter code itself.

ETCBC-phono feature file (from `ingest/lexical/etcbc_phono.py` line 293-295,
constant `PHONO_TF_PATH`):

```
C:/Users/Ebenezer/text-fabric-data/github/ETCBC/phono/tf/2021/phono.tf
```

Sibling file present in the same module directory (NOT read by the
emptiness rule, recorded for completeness):

```
C:/Users/Ebenezer/text-fabric-data/github/ETCBC/phono/tf/2021/phono_trailer.tf
```

(the module ships `phono.tf` and `phono_trailer.tf`, plus `otext@phono.tf`
and `__checkout__.txt`; there is no file named `phono_sep`.)

BHSA module root (from `ingest/lexical/bhsa.py` line 380, constant
`TF_ROOT`); the word-slot universe is read from `otype.tf` here:

```
C:/Users/Ebenezer/text-fabric-data/github/ETCBC/bhsa/tf/2021/otype.tf
```

Text-fabric release tags (`__checkout__.txt` in each module dir):

| Module | tag | commit |
|---|---|---|
| ETCBC/phono | v2.1 | gaba4367b49750089e4e4122415a77cac43bd97bc |
| ETCBC/bhsa  | v1.8.1 | gb112c161cfd21eae403d51a2733740d8743460e7 |

Both feature files declare `@version=2021` and
`@dateWritten=2021-12-09` in their headers, so the phono feature and the
BHSA word universe are the same frozen 2021 data version. The phono
header is `@description=phonological transcription` and
`@provenance=computed by the phono notebook, see
https://github.com/ETCBC/phono`.

---

## 1. The three numbers (with exact commands)

The adapter's exact parse logic was copied byte-for-byte from
`ingest/lexical/etcbc_phono.py` (`_read_tf_body`, `_parse_phono_feature`,
`_phono_value`) and `ingest/lexical/bhsa.py` (`_parse_otype_runs`) into a
read-only audit script and run against the frozen files on disk.

Adapter emptiness rule reproduced verbatim
(`ingest/lexical/etcbc_phono.py` line 344-345):

```python
def _phono_value(raw: str) -> Any:
    return raw if raw.strip() != "" else None
```

The adapter builds one row per node id in
`range(WORD_NODE_MIN=1, WORD_NODE_MAX+1=426591)`
(`ingest/lexical/etcbc_phono.py` line 354-356) and applies `_phono_value`
to `values.get(node_id, "")`.

Reproduction command (from repo root
`e:/projects-working-dir/brethren-doctrine`):

```
python tmp_phono_audit.py
```

(`tmp_phono_audit.py` is the read-only forensic script; it imports
nothing from the live store and only opens the two frozen feature files.
It is an audit scratch file, not part of the pipeline.)

Results:

| # | Quantity | Value | File-level evidence |
|---|---|---|---|
| (i) | Catalog expectation | **426590** | `tools/expected_counts.json` `sources["ETCBC-phono"].expected_count` = 426590, `min`=426590, `max`=426590, `tolerance`=0, `tier`="A", `record_unit`="word" |
| (i) | Catalog tier_rationale (exact claim) | see below | quoted verbatim from the JSON |
| (ii) | Total BHSA word slots (`otype==word`) | **426590** | `otype.tf` body first run line is `1-426590\tword`; `_parse_otype_runs` yields `runs["word"]=(1,426590)`; count = 426590 - 1 + 1 = 426590. Equals 426590 exactly: TRUE |
| (iii) | Faithful non-null phono count | **420166** | per the adapter emptiness rule over node ids 1..426590 |
| (iii) | Null phono count | **6424** | 426590 - 420166 |
| (iii) | nonnull + null | **426590** | reconciles to the full word universe exactly |
| (iii) | occurrence_rate = nonnull/total | **0.984941** | 420166 / 426590, to 6 decimals |

Catalog `tier_rationale` exact text (verbatim from
`tools/expected_counts.json` `sources["ETCBC-phono"]`):

> "ETCBC phonetic transcription ships one phono value per BHSA word slot
> in the same text-fabric module. Total equals the BHSA word slot count
> exactly because the feature is keyed one-to-one with word identifiers."

This catalog claim ("one phono value per BHSA word slot ... one-to-one")
is the assertion under test. The reproduced data shows phono is NOT
one-to-one with all 426590 slots: 6424 word slots carry no phono value.
The occurrence rate 0.984941 matches the adapter docstring's stated
"0.984 occurrence rate" / "1.6 percent null rate"
(`ingest/lexical/etcbc_phono.py` lines 63-65, 95-97, 200-211). The
adapter docstring is internally consistent with the data; the catalog
`expected_count`/`tolerance` row is the artifact that conflicts with the
faithful parse.

---

## 2. Null-phono slot characterization

### 2.1 The null set is one perfectly homogeneous structural class

Every one of the 6424 null-phono slots has the identical BHSA feature
signature (no exceptions, counts are exact, not sampled):

| BHSA feature | value on ALL 6424 null-phono slots | count |
|---|---|---|
| `g_word` | `-` (bare maqqef, the literal hyphen) | 6424 / 6424 |
| `g_word_utf8` | absent / none | 6424 / 6424 |
| `lex` | `H` (the Hebrew definite article ה lexeme) | 6424 / 6424 |
| `sp` (part of speech) | `art` (article) | 6424 / 6424 |
| phono key state | key ABSENT from `phono.tf` entirely (not present-but-blank) | 6424 / 6424 |
| `phono_trailer` | absent / none (no interword material either) | 6424 / 6424 |

Set identity proof: the set of word slots with `g_word == '-'` and the
set of null-phono word slots are **exactly the same set**.
`maqqef-only slots = 6424`, `null-phono = 6424`,
`identical set = True`, `maqqef-not-null = 0`, `null-not-maqqef = 0`.

### 2.2 What this class actually is (and what it is NOT)

These are the **assimilated / elided definite-article slots**. BHSA
tokenizes a maqqef-joined prefixed form into separate word slots. When
the inseparable preposition (בְּ, לְ, כְּ) absorbs the definite article ה,
BHSA still emits a distinct word slot for the article lexeme `H` (sp
`art`), but its surface `g_word` is the bare maqqef `-` and it has no
independent UTF-8 surface and no independent spoken realisation. The
phono notebook therefore emits no phono entry for that slot: the
article's sound is already folded into the vowel of the preceding
preposition slot.

Worked proof from contiguous slots (Genesis 1:5 region):

| slot | g_word | g_word_utf8 | lex | sp | phono |
|---|---|---|---|---|---|
| 60 | `>:ELOHI70JM` | אֱלֹהִ֤ים | `>LHJM/` | subs | `ʔᵉlōhˈîm` |
| 61 | `L@-` | לָ | `L` | prep | `lā` |
| **62** | `-` | (none) | `H` | art | **None** |
| 63 | `>OWR03` | אֹור֙ | `>WR/` | subs | `ʔôr` |
| 64 | `JO80WM` | יֹ֔ום | `JWM/` | subs | `yˈôm` |

Slot 61 is the preposition לָ (`L@-`) carrying phono `lā`; the `ā` is the
article's vowel assimilated onto the preposition. Slot 62 is the article
ה itself (lex `H`, sp `art`), surface reduced to the bare maqqef,
phonetically silent on its own slot, hence no phono entry. The sound is
not lost: it lives on slot 61. This is faithful structural tokenization,
not data loss.

This DIVERGES from the Phase D triage characterization. The triage
(`docs/PHASE_D_HARNESS_TRIAGE.md` lines 324-360, 444) described the null
class as "~6800 ketiv-only slots with no spoken realisation". The
byte-level reproduction shows:

- The exact null count is **6424**, not ~6800.
- The class is the **assimilated definite article** (`g_word='-'`,
  lex `H`, sp `art`), **not** ketiv-only.
- Cross-check against the BHSA `qere.tf` feature ("word
  pointed-transliterated masoretic reading correction", from "additional
  ketiv/qere file provided by the ETCBC"): there are **1867**
  qere-marked word slots. The intersection of qere-marked slots with
  null-phono slots is **0**. The qere/ketiv class and the null-phono
  class are completely disjoint. All 1867 qere-marked slots have a
  non-null phono value.

The triage's adapter-faithfulness conclusion still holds (the adapter
honestly writes null for slots upstream has no phono for, applies no
fallback substitution), but its *causal label* for the null class was
incorrect. The corrected, evidence-backed cause is the assimilated
article, and it is still a faithful structural artifact, not lost
content.

### 2.3 Anomaly flag

Per the task instruction to flag loudly if ANY null slot is not
explainable as a faithful structural class: **no anomaly**. 100% (6424
of 6424) of null-phono slots are the single homogeneous
assimilated-article class (`g_word='-'`, lex `H`, sp `art`), with set
identity = True and zero residue in either direction. None is random
data loss. None is a key-mismatch artifact (the phono feature is keyed
by the same word node ids; the gap is the upstream notebook's deliberate
non-emission for phonetically silent article slots, not a join failure).

### 2.4 Null-slot category table

| Category | Definition | Count |
|---|---|---|
| Assimilated definite article | `g_word == '-'` AND `lex == 'H'` AND `sp == 'art'` | 6424 |
| phono key ABSENT from feature | node id never appears in `phono.tf` | 6424 |
| phono present-but-blank | node id in `phono.tf` with empty/whitespace value | 0 |
| null AND qere-marked (ketiv-only) | intersection with `qere.tf` slots | 0 |
| Unexplained / possible lost content | not in any faithful class above | **0** |
| Total null-phono | | **6424** |

The two "Assimilated" and "phono key ABSENT" rows describe the same 6424
slots from two angles (structural identity and mechanism). The null is
caused by upstream non-emission for a structurally silent slot, not by a
blank value and not by a key mismatch.

---

## 3. Five worked examples

Slot id, book.chapter.verse, BHSA surface of the slot and its
left-neighbor, reason phono is blank, faithfulness proof.

| slot | ref | g_word (this slot) | left neighbor (carries the sound) | reason phono blank | faithful artifact proof |
|---|---|---|---|---|---|
| 62 | Genesis.1.5 | `-` (lex `H`, sp `art`) | slot 61 `L@-` prep, phono `lā` | article ה assimilated into preceding preposition; slot has no independent surface or sound | qere `<MISSING>` (not a ketiv slot); sound present on slot 61; structural tokenization, content intact |
| 67 | Genesis.1.5 | `-` (lex `H`, sp `art`) | preposition slot carries the vowel | same assimilated-article mechanism | not qere-marked; faithful split, no loss |
| 110 | Genesis.1.7 | `-` (lex `H`, sp `art`) | preposition slot carries the vowel | same | not qere-marked; faithful split, no loss |
| 120 | Genesis.1.7 | `-` (lex `H`, sp `art`) | preposition slot carries the vowel | same | not qere-marked; faithful split, no loss |
| 129 | Genesis.1.8 | `-` (lex `H`, sp `art`) | preposition slot carries the vowel | same | not qere-marked; faithful split, no loss |

All five (and all 6424) are the same class: the article-lexeme slot
whose surface reduced to the bare maqqef, phonetically realized on the
preceding preposition slot. `phono_raw='<absent>'` in every case (the
node id is simply not present in `phono.tf`), and `qere='<MISSING>'`
confirms none is a ketiv/qere-correction slot.

---

## 4. Determinism proof

The frozen 2021 module yields a byte-identical result every run. The
audit script parses `phono.tf` twice independently and hashes the full
sorted (node_id, phono_value) pair list under the adapter emptiness
rule:

```
pass1 nonnull = 420166   pass2 nonnull = 420166   equal = True
pass1 sha256  = 425f2c7acff95f90b89f8d6d508f8d2eadd168e66137661ef215c718b1d6fbd4
pass2 sha256  = 425f2c7acff95f90b89f8d6d508f8d2eadd168e66137661ef215c718b1d6fbd4
byte-identical = True
```

The non-null count is reproduced identically across two passes and the
SHA-256 over the canonical (node_id, value) projection is identical,
matching the adapter Idempotency contract
(`ingest/lexical/etcbc_phono.py` lines 182-196: "Re-running this adapter
over identical text-fabric phono feature bytes produces ... the same
phono value byte-identically ... The 1.6 percent null rate for ketiv-only
slots is preserved across reruns"). The data substantiates the
determinism claim; only the causal label "ketiv-only" in that docstring
sentence is imprecise (the real class is the assimilated article, count
6424). Exact reproduction command:

```
python tmp_phono_audit.py
```

run from `e:/projects-working-dir/brethren-doctrine` against the frozen
modules at the absolute paths in section 0.

---

## 5. Owner-decision options (numbers filled in)

This is the 8th catalog-vs-reality mismatch of the same class as the
original 7. The adapter is faithful and is NOT changed. The decision is
purely a catalog (`tools/expected_counts.json`) revision. Both options
below make a faithful ingest pass; they differ in what the Tier A gate
asserts and what the catalog documents as the contract.

### Option A: re-baseline to the reproduced faithful non-null count

Re-baseline `sources["ETCBC-phono"]` to the reproduced non-null phono
count and clarify the record unit to mean "word slot with non-null
phono".

`tools/expected_counts.json` `sources["ETCBC-phono"]` key changes:

| key | from | to |
|---|---|---|
| `expected_count` | `426590` | `420166` |
| `min` | `426590` | `420166` |
| `max` | `426590` | `420166` |
| `tolerance` | `0` | `0` (unchanged) |
| `tier` | `"A"` | `"A"` (unchanged) |
| `record_unit` | `"word"` | `"word slot with non-null phono"` |
| `tier_rationale` | "...ships one phono value per BHSA word slot ... one-to-one ..." | revise to state phono is attached at 0.984941 occurrence over 426590 word slots; 6424 assimilated-article slots (g_word `-`, lex `H`, sp `art`) carry no phono by upstream design; the deterministic non-null count is 420166 |

Gate behavior under Option A given the faithful ingest: the Tier A
tolerance-0 gate counts BhsaWord nodes with non-null phono and asserts
exactly 420166. The faithful ingest produces exactly 420166 non-null
phono attachments (deterministic, byte-identical across runs), so the
gate PASSES with zero tolerance and still binds tightly: any drift in
the non-null count (e.g. a parse regression or a different module
version) fails the gate immediately. This keeps a strict deterministic
floor specifically on the phono attachment.

### Option B: drop the separate non-null gate; gate on slot coverage

Drop the separate non-null tier-A-0 count gate for ETCBC-phono and gate
phono on total BhsaWord slot coverage instead (identical to ETCBC-BHSA),
treating phono as an optional per-slot property, not a counted record.

`tools/expected_counts.json` `sources["ETCBC-phono"]` key changes:

| key | from | to |
|---|---|---|
| `expected_count` | `426590` | `426590` (unchanged: now means word-slot coverage, same universe as ETCBC-BHSA) |
| `min` | `426590` | `426590` (unchanged) |
| `max` | `426590` | `426590` (unchanged) |
| `tolerance` | `0` | `0` (unchanged) |
| `tier` | `"A"` | `"A"` (unchanged) |
| `record_unit` | `"word"` | `"word"` (unchanged; documents that phono is an OPTIONAL property attached over the 426590 word-slot universe, with a known 6424-slot assimilated-article null gap; not a record count) |
| `tier_rationale` | "...one phono value per BHSA word slot ... one-to-one..." | revise to: phono is an optional property attached to the 426590 ETCBC-BHSA word slots; the gate asserts the BhsaWord slot universe equals 426590 (same as ETCBC-BHSA), and the per-slot null gap (6424 assimilated-article slots) is faithful and not counted as a record shortfall |

Gate behavior under Option B given the faithful ingest: the gate asserts
the BhsaWord slot universe == 426590 (the same assertion ETCBC-BHSA
already makes). The faithful BHSA ingest produces exactly 426590 BhsaWord
nodes, so the gate PASSES. The per-slot phono presence/absence is no
longer a tolerance-0 record count; it becomes the permissive runbook
acceptance gate already present in the adapter docstring
(`ingest/lexical/etcbc_phono.py` lines 229-243:
`MATCH (w:BhsaWord) WHERE w.phono IS NOT NULL ... RETURN with_phono,
with_phono > 0`), i.e. "at least one phono attached". This removes the
duplicate strict count on phono and avoids encoding the 6424-slot
upstream gap as a hard number that future module versions could shift.

### Trade-off summary (neutral, owner decides)

- Option A keeps a strict deterministic Tier-A-0 floor on the phono
  attachment specifically (420166), catching any phono parse drift, at
  the cost of hard-coding an upstream-derived number that is tied to the
  2021 module's exact assimilated-article tokenization.
- Option B aligns ETCBC-phono's gate with ETCBC-BHSA (both gate the same
  426590 word-slot universe), models phono honestly as an optional
  per-slot property, and stops encoding the structural null gap as a
  counted shortfall, at the cost of no longer having a tolerance-0 count
  specifically on phono coverage (drift in phono would only be caught by
  the permissive `with_phono > 0` runbook gate, not the strict count).

Both options leave the adapter untouched and produce a passing gate on
the faithful ingest. No third option is recommended as fait accompli;
this is owner-decision input only.
