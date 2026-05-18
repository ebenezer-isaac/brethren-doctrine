# AUDIT: Phase D Pre-Flight Verification

Caste: auditor. Adversarial independent reproduction from the upstream
bytes. Doctrinal frame: brethren-on-trial. Implementer self-reports were
NOT trusted; every number below was re-derived by the auditor from the
frozen upstream, not read from a commit message. No Neo4j, no docker, no
network, no embeddings. Pure offline parse only.

Scope: four session commits on branch main.

* a277a96 fix: stepbible_tahot stable id must not collapse =X onto =L
* 6a3c2c7 fix: run.py wiring open_cbgm_3_john + stepbible_ttesv
* 76ad53f chore: quarantine dead stepbible.py
* 2d28de3 fix: stepbible_ttesv stable id carries raw upstream position

HEAD at audit start: 2d28de3434b1e8c098c62affc30d46af10fbf7dd.

Reproduction environment: Windows, python 3.12.13, pytest 9.0.3,
PYTHONIOENCODING=utf-8 for Hebrew dumps.

---

## Commit a277a96 (stepbible_tahot =X over =L collapse fix)

VERDICT: PASS.

### Reproduced count

Adapter pure parse over data/private/stepbible TAHOT files
(`_load_tokens(Path('data/private/stepbible'))`):

```
emit        283721
distinct    283721
collisions  0
```

Raw qualifying ref-rows independently counted from the four TAHOT TSV
files (rows matching `_REF_ROW`): 283734. 283734 - 13 = 283721. The
reproduced emit is EXACTLY 283721. It is NOT 283704 (the fix took: the
17 =L words are no longer overwritten by 17 =X words) and NOT 283734
(the 13 faithful predicate drops were NOT wrongly resurrected).

### Drop forensics (adversarial: collision vs predicate)

The auditor replayed `_row_to_token` and instrumented the exact drop
reason for every qualifying ref-row. Result:

```
total drops    13
drop reasons   {'pred:ketiv+strong+morph': 13}
dedup drops    0
```

All 13 drops are `=Q(K)` Ketiv predicate rows with a simultaneously
blank consonantal slot, blank dStrongs and blank morph. ZERO drops are
seen-set dedup (collision) drops. This proves the count delta is the
faithful predicate drop, not a silenced collision, and that there are
ZERO residual stable-id collisions across the entire TAHOT corpus
(283734 raw - 13 predicate == 283721 distinct == 283721 emitted).

The 13 reproduced from the bytes match the docstring list exactly:
Jdg.16.25#02, Rut.3.12#05, 1Sa.9.1#04, 2Sa.13.33#15, 2Ki.5.18#23,
2Ch.34.6#07, Isa.44.24#16, Jer.38.16#10, Jer.39.12#11, Jer.51.3#03,
Lam.1.6#02, Lam.4.3#10, Ezk.48.16#12.

### 4-verse heal table (independently dumped from the bytes)

At every named verse BOTH the canonical Leningrad =L word (bare
`.wN` id) AND the off-canon =X alternate (`.wN~X` id) now exist as
distinct ids. No overwrite. Sample (full dump performed for all four):

| Verse      | =L canonical id              | =L ref_eng       | =L Strong | =X alternate id                | =X ref_eng         | =X Strong | Healed |
|------------|------------------------------|------------------|-----------|--------------------------------|--------------------|-----------|--------|
| Deu.30.16  | stepbible-tahot:Deu.30.16.w1 | Deu.30.16#01=L   | H834a     | stepbible-tahot:Deu.30.16.w1~X | Deu.30.16#0001=X   | H518a     | YES    |
| Jdg.16.14  | stepbible-tahot:Jdg.16.14.w1 | Jdg.16.14#01=L   | H8628     | stepbible-tahot:Jdg.16.14.w1~X | Jdg.16.14#0001=X   | H3462     | YES    |
| 2Sa.23.33  | stepbible-tahot:2Sa.23.33.w1 | 2Sa.23.33#01=L   | H8048     | stepbible-tahot:2Sa.23.33.w1~X | 2Sa.23.33#0001=X   | H1121a    | YES    |
| 2Ki.25.3   | stepbible-tahot:2Ki.25.3.w1  | 2Ki.25.3#01=L    | H8672     | stepbible-tahot:2Ki.25.3.w1~X  | 2Ki.25.3#0001=X    | H2320     | YES    |

At Deu.30.16 all six =L canonical words (w1..w6, the previously
overwritten band) are present at positions 1..6 alongside the six =X
alternates w1~X..w6~X. Same pattern verified at the other three.

### Gaming check (read the diff)

The diff is a general id-rendering rule, NOT a per-verse patch and NOT a
hardcoded count:

* `_REF_SPLIT` extended to also capture the edition tag after `=`.
* New general predicate `_is_leningrad_base(edition)`: True when the
  edition head char is in "Ll" (or no tag), False otherwise.
* New general `_token_stable_id(osis, pos, edition)`: bare
  `stepbible-tahot:<osis>.w<pos>` for the Leningrad family, else
  `<base>~<edition>` verbatim.
* No verse string ("Deu.30.16" etc.) and no integer literal 283721 /
  283704 appears anywhere in the changed code. The healed verses fall
  out of the general rule, they are not special-cased.

### 13-Ketiv OSHB x-ketiv seam spot-check (all 13, not just 5)

The docstring claims all 13 dropped Ketiv readings are materialized in
OSHB via the x-ketiv Word seam with matching Strong, so the drop is a
faithful projection choice, not lost content. The auditor pulled the K
reading Strong codes from each TAHOT row's K-reading commentary and
Strong columns and confirmed presence at the same verse in
data/private/oshb/wlc.

| TAHOT dropped row   | OSHB verse    | K-reading real Strong(s) | Present in OSHB | Note |
|---------------------|---------------|--------------------------|-----------------|------|
| Jdg.16.25#02=Q(K)   | Judg.16.25    | H3588                    | YES             | x-ketiv lemma 3588 a |
| Rut.3.12#05=Q(K)    | Ruth.3.12     | H518, H3588              | YES             | x-ketiv lemma 518 a |
| 1Sa.9.1#04=Q(K)     | 1Sam.9.1      | H3225                    | YES             | x-ketiv lemma 3225 |
| 2Sa.13.33#15=Q(K)   | 2Sam.13.33    | H518 (H3588)             | YES             | lemma 518 b present at verse (H9014 maqqef pseudo-Strong excluded) |
| 2Ki.5.18#23=Q(K)    | 2Kgs.5.18     | H4994                    | YES             | x-ketiv lemma 4994 |
| 2Ch.34.6#07=Q(K)    | 2Chr.34.6     | H2022 (H9003)            | YES             | x-ketiv lemma b/2022 (H9003 prefix pseudo-Strong excluded) |
| Isa.44.24#16=Q(K)   | Isa.44.24     | H4310, H4325             | YES             | x-ketiv lemma 4325 (the surface mi); see note |
| Jer.38.16#10=Q(K)   | Jer.38.16     | H853                     | YES             | x-ketiv lemma 853 |
| Jer.39.12#11=Q(K)   | Jer.39.12     | H518, H3588              | YES             | x-ketiv lemma 518 a |
| Jer.51.3#03=Q(K)    | Jer.51.3      | H1869                    | YES             | x-ketiv lemma 1869 |
| Lam.1.6#02=Q(K)     | Lam.1.6       | H4480 (H9014)            | YES             | x-ketiv lemma 4480 a |
| Lam.4.3#10=Q(K)     | Lam.4.3       | H3588                    | YES             | x-ketiv lemma 3588 a |
| Ezk.48.16#12=Q(K)   | Ezek.48.16    | H2568                    | YES             | x-ketiv lemma 2568 |

13 of 13 PRESENT. No lost content.

Adversarial sub-finding (resolved, NOT lost content): an initial
narrow x-ketiv-only filter showed 2Sam.13.33 with zero x-ketiv and
Isa.44.24 K-Strong H4310 absent. Deep dive into the bytes resolved
both:

* 2Sa.13.33#15=Q(K) is a Qere-with-no-written-Ketiv predicate row
  (K = 'im-, H518B). OSHB writes the reading at 2Sam.13.33 as a
  regular Word `lemma="518 b"` (not x-ketiv tagged because WLC treats
  it as a non-marked reading). The lexical payload H518 is present at
  the verse. Materialized, not lost.
* Isa.44.24#16=Q(K): the row's Strong column 9 carries `H4310, H4325G`
  (the famous mi-ati / me-ati ketiv/qere). OSHB writes TWO x-ketiv
  Words at Isa.44.24: `<w type="x-ketiv" lemma="4325">mi</w>` and
  `<w type="x-ketiv" lemma="854">at/i</w>`. The Ketiv surface mi
  resolves to H4325 in both sources. Materialized as an x-ketiv Word
  with matching Strong. Not lost.

The only Strongs ever "absent" are H9014 (maqqef link) and H9003
(prefixed-preposition pseudo-Strong), which are STEPBible-internal
grammatical pseudo-Strongs, not lexemes. OSHB legitimately does not
carry them as separate lemmas. Their absence is correct, not a gap.

### Gate exit codes (commit a277a96)

| Gate                                                  | Exit |
|-------------------------------------------------------|------|
| pytest tests/lexical/test_stepbible_tahot_coverage.py | 0 (17 passed, 13 skipped, 94.16s) |
| check_adapter_purity --file stepbible_tahot.py        | 0 (clean) |
| verify_no_deferral --path stepbible_tahot.py          | 0 (zero deferral markers) |
| check_caste --rev a277a96                             | 0 (caste=implementer-impl files=1) |

No test asserted the old collided behaviour; the suite passed with no
test change.

---

## Commit 6a3c2c7 (run.py wiring open_cbgm_3_john + stepbible_ttesv)

VERDICT: PASS.

### Resolved data_root and file existence

From run.py constants:

```
STEPBIBLE_TAGGED_BIBLES_ROOT = data/private/stepbible/Tagged-Bibles
OPEN_CBGM_ROOT               = tmp/poc/cbgm
```

Real files at the resolved roots (asserted to exist):

* tmp/poc/cbgm/3_john.db                                  EXISTS
* tmp/poc/cbgm/3_john_collation.xml                       EXISTS
* data/private/stepbible/Tagged-Bibles/TTESV ... CC BY-NC.txt  EXISTS

The OLD wired paths are absent on disk:
data/private/open-cbgm-3-john (does not exist) and
data/private/stepbible/TTESV...txt at STEPBIBLE_ROOT (does not exist).
Under the pre-fix wiring both adapters would have read nothing. Diff
shows only the two data_root values changed plus two new path
constants; no signature or parse-semantic change.

### Pure-parse counts via the resolved run.py paths

```
open_cbgm_3_john : Witness=142  VariantUnit=116  Reading=470  total nodes=728
stepbible_ttesv  : emit 31127   distinct 31127   collisions 0
```

open_cbgm = 728 nodes, exactly as claimed. ttesv = 31127 tokens,
exactly as claimed.

### Gate exit codes (commit 6a3c2c7)

| Gate                       | Exit |
|----------------------------|------|
| check_caste --rev 6a3c2c7  | 0 (caste=implementer-impl files=1) |

---

## Commit 76ad53f (quarantine dead stepbible.py)

VERDICT: PASS.

### No live import of the bare module

Full-repo grep for `import stepbible` / `from ingest.lexical.stepbible
import` / `ingest.lexical.stepbible` / `stepbible._` / `parse_tvtms` /
`_iter_word_records`:

* The ONLY live code reference is the stale dead test scaffolding
  tests/lexical/test_parsers.py:18 (module-level tuple import) and its
  two calls at lines 206 and 224.
* ingest/lexical/stepbible_tvtms.py:43 is a docstring mention only, not
  an import.
* run.py imports only the per-source `ingest_stepbible_*` adapters,
  never the bare module.

### Defective code fully removed, every entry point raises

Pre-quarantine stepbible.py (76ad53f^) confirmed to have carried the
defect: line 34 `int(m.group(4))` and line 53
`f"{id_prefix}:{osis}.w{pos:02d}"` (the identical int(pos)+{pos:02d}
collapse class). Post-quarantine stepbible.py has NO int()/`:02d` code,
no revivable parse path. All five former entry points raise
RuntimeError: `_parse_ref`, `_iter_word_records`, `parse_tvtms`,
`_iter_records`, `ingest_stepbible`.

check_adapter_purity --file stepbible.py: exit 0 (clean).

### Full tests/lexical regression categorization

`python -m pytest -q tests/lexical`: 24 failed, 411 passed, 300
skipped, exit 0 (1685s). Every failure accounted for:

* 2 NEW intended quarantine RuntimeErrors (the expected delta):
  test_parsers.py::test_stepbible_parses_tahot_line and
  ::test_stepbible_parses_tvtms_psa_51.
* 16 PRE-EXISTING stale-scaffolding AttributeErrors in test_parsers.py
  (test_macula_hebrew x2, test_openbible x4, test_tsk x5,
  test_morphgnt x1, test_oshb x1, test_macula_greek x1,
  test_theographic x2). 76ad53f touched ONLY
  ingest/lexical/stepbible.py; none of these target modules was
  modified, so they fail identically at 76ad53f^ (= 6a3c2c7). Not a
  regression.
* 6 PRE-EXISTING catalog-reconciliation [SCHEMA-REVISION] family
  failures (test_*expected*count*_from_expected_counts_json for
  open_cbgm_3_john, oshb, stepbible_proper_nouns, stepbible_tagnt,
  stepbible_ttesv, theographic). These assert stale
  tools/expected_counts.json numbers against faithful parse counts.
  None of the four commits touched tests or expected_counts.json.
  Architect-caste reconciliation items, documented in
  PHASE_D_CATALOG_RECONCILIATION.md. Not a regression.

ZERO hidden regressions. The only new failures vs the clean baseline
are the 2 intended quarantine RuntimeErrors.

### Gate exit codes (commit 76ad53f)

| Gate                                       | Exit |
|--------------------------------------------|------|
| check_adapter_purity --file stepbible.py   | 0 (clean) |
| python -m pytest -q tests/lexical          | 0 (24 failed all accounted, 411 passed) |
| check_caste --rev 76ad53f                  | 0 (caste=implementer files=1) |

Note: ITEM 5 of the commit (stepbible_ttesv left UNCHANGED, STOP) is a
separate decision later actioned by commit 2d28de3 (which DID change
the ttesv id). The 76ad53f STOP claim is internally consistent with
2d28de3 superseding it.

---

## Commit 2d28de3 (stepbible_ttesv stable id carries raw upstream position)

VERDICT: PASS.

### Determinism (two pure parses over the real upstream)

```
run 1 emit 31127  distinct 31127  collisions 0
run 2 emit 31127  distinct 31127  collisions 0
sha256 run1 = 6acbc7fb87e62318651cf3a960d6afe4c48c5c4ccdc6d4b9684b92286448ec76
sha256 run2 = 6acbc7fb87e62318651cf3a960d6afe4c48c5c4ccdc6d4b9684b92286448ec76
EQUAL
```

The reproduced post-fix sha256 matches the commit's stated post-fix
sha256 byte-for-byte.

### Structural distinctness of the renderer

`_row_for_verse(...)` post-fix renders the raw position string verbatim:

```
render raw '1'   -> stepbible-ttesv:Gen.1.1.w1
render raw '01'  -> stepbible-ttesv:Gen.1.1.w01
render raw '001' -> stepbible-ttesv:Gen.1.1.w001
all distinct: True
```

render("1") != render("01") != render("001"). The int()-collapse class
is structurally impossible.

### Churn enumeration (adversarial: exactly 5, no silent move)

Pre-fix id set re-derived by re-rendering the same parsed rows the old
way `f".w{int(raw):02d}"`. Diff vs post-fix:

```
pre-fix distinct ids   31127
post-fix distinct ids  31127
ids that moved          5
distinct osis_ref       31127
```

The 5 moved ids match the commit's enumerated list EXACTLY (each a
single-digit raw first position .wNN -> .wN):

| Pre-fix id                       | Post-fix id                     |
|----------------------------------|---------------------------------|
| stepbible-ttesv:Exo.38.28.w01    | stepbible-ttesv:Exo.38.28.w1    |
| stepbible-ttesv:Jdg.15.11.w03    | stepbible-ttesv:Jdg.15.11.w3    |
| stepbible-ttesv:1Ch.23.5.w04     | stepbible-ttesv:1Ch.23.5.w4     |
| stepbible-ttesv:1Ch.29.4.w03     | stepbible-ttesv:1Ch.29.4.w3     |
| stepbible-ttesv:2Ch.12.3.w01     | stepbible-ttesv:2Ch.12.3.w1     |

No other id silently moved. 31127 distinct osisRef == 31127 distinct
ids == 31127 emitted: none vanished, none added. The parse-semantic
path (int(p) try/except piece selection) is unchanged; only the id
string render and the derived position int changed.

### Gate exit codes (commit 2d28de3)

| Gate                                          | Exit |
|-----------------------------------------------|------|
| check_adapter_purity --file stepbible_ttesv.py| 0 (clean) |
| verify_no_deferral --path stepbible_ttesv.py  | 0 (zero deferral markers) |
| check_caste --rev 2d28de3                     | 0 (caste=implementer files=1) |

---

## Global gates

| Gate                                       | Exit | Result |
|--------------------------------------------|------|--------|
| check_caste --range 91ee518..HEAD          | 0    | Every commit in range OK (115 commits, all caste-clean) |
| git status (clean except untracked docs)   | n/a  | Only AUDIT_pos_collapse_blast_radius.md, AUDIT_tahot_30row_deepdive.md, PHASE_D_CATALOG_RECONCILIATION.md untracked; no tracked modification |

Each of the four commits touched exactly one file, matching its
declared caste:

* a277a96 -> ingest/lexical/stepbible_tahot.py (implementer-impl)
* 6a3c2c7 -> ingest/lexical/run.py (implementer-impl)
* 76ad53f -> ingest/lexical/stepbible.py (implementer)
* 2d28de3 -> ingest/lexical/stepbible_ttesv.py (implementer)

No adapter, test, fixture, run-config, expected_counts, baseline or
check_caste was modified by the auditor. The auditor wrote only this
verification doc and (per the task) commits the auditor-caste audit
docs.

---

## Final GO / NO-GO

### (a) Architect TAHOT [SCHEMA-REVISION] #2 baselining

GO. Baseline STEPBible-TAHOT expected_count to **283721**.

Justification, reproduced from the bytes:
283734 raw qualifying ref-rows minus exactly 13 faithful empty-Strong
=Q(K) Ketiv predicate drops == 283721 distinct TaggedToken == 283721
emitted, with ZERO residual stable-id collisions corpus-wide. The 13
drops are not lost content: 13 of 13 are materialized in OSHB at the
same verse with a matching real Strong via the x-ketiv / resolved
Word seam (only STEPBible-internal pseudo-Strongs H9014/H9003 are
legitimately absent). The 17 =L canonical words formerly overwritten by
17 =X off-canon words are restored as distinct ids and the =X
alternates are retained, healing Deu.30.16, Jdg.16.14, 2Sa.23.33,
2Ki.25.3.

### (b) Phase D ingest readiness

GO.

* run.py wiring is correct for both formerly-broken adapters
  (open_cbgm_3_john -> tmp/poc/cbgm = 728 nodes; stepbible_ttesv ->
  data/private/stepbible/Tagged-Bibles = 31127 tokens).
* The dead defective stepbible.py is quarantined with no revivable
  int(pos)-collapse path and no live import; the only test delta is the
  2 intended RuntimeErrors.
* stepbible_ttesv id is hardened (raw verbatim position, deterministic
  sha256 6acbc7fb...448ec76, 5 enumerated churn ids, 0 collisions)
  before the greenfield reseed.
* All four commits pass purity, no-deferral, and the full caste range
  gate; tree is clean.

No gaming, no lost content, no hidden regression found. All four
commits PASS adversarial verification.
