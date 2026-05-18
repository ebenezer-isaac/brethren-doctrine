# AUDIT: Position-Collapse / Id-Overwrite Blast Radius

Caste: auditor. READ-ONLY forensic blast-radius trace. Branch main, HEAD
d8530f3. Doctrinal frame: brethren-on-trial. Trust the faithful parse, never
fudge a number, never mask lost or corrupted content. No em or en dashes
anywhere.

Mandate: a confirmed defect in `ingest/lexical/stepbible_tahot.py`
(`int(m.group("pos"))` collapses zero-padded `#0001` onto `#01`, so a
132-row off-canon `=X` alternate edition silently overwrites the Leningrad
`=L` base text at 4 verses, established by docs/AUDIT_tahot_30row_deepdive.md).
This audit determines whether the same `int(pos)`-collapse / id-overwrite
defect exists in the sibling adapters that share the `<osisRef>.w<pos>`
stable-id scheme: stepbible_tagnt.py, stepbible_ttesv.py, the shared
stepbible.py helper, and oshb.py. Adversarial posture: assume the defect is
systemic until the bytes prove an adapter clean. Every number below was
reproduced offline from the real upstream bytes on disk (no Neo4j, no
network, no docker, no ingest job).

Frozen snapshot under test: `data/private/stepbible/` (TAGNT, TTESV, TAHOT
files dated 2026-05-10), `data/private/oshb/wlc/*.xml` (40 OSIS books).

---

## 0. Reference defect signature (TAHOT, already confirmed)

The TAHOT defect has three load-bearing lines:

- `stepbible_tahot.py:246` `_REF_SPLIT = re.compile(r"^(?P<osis>[A-Za-z0-9]+\.\d+\.\d+)#(?P<pos>\d+)")`
- `stepbible_tahot.py:316` `return m.group("osis"), int(m.group("pos"))`
- `stepbible_tahot.py:341` `token_id = f"stepbible-tahot:{osis}.w{pos}"`

Defect mechanism: `int("0001") == int("01") == 1`. Two distinct upstream
positions of different zero-pad width collapse to one stable id. The trigger
is upstream data that actually carries both a wide zero-padded position
(`#0001`, the off-canon `=X` alternate edition) and a narrow one (`#01`, the
`=L` Leningrad base text) at the same osis verse. TAHOT has 132 `=X` rows;
exactly 4 verses (Deu.30.16, Jdg.16.14, 2Sa.23.33, 2Ki.25.3) have `=X`
positions that integer-collide `=L` positions, producing 17 silent canonical
overwrites. The blast-radius question for each sibling is twofold: (A) is the
collapse present in the id-construction code, and (B) does the frozen
upstream snapshot actually contain the variable-width / alternate-edition
trigger.

---

## 1. stepbible_tagnt.py (highest-priority sibling) -- CLEAN

### A. Code evidence

Position parse, `stepbible_tagnt.py:268-277`:

```
def _parse_word_and_type(word_and_type: str) -> tuple[str, str] | None:
    if "#" not in word_and_type:
        return None
    osis_ref, rest = word_and_type.split("#", 1)
    pos_token = rest.split("=", 1)[0]
    ...
    return osis_ref, pos_token
```

Id construction, `stepbible_tagnt.py:313-317`:

```
digits = "".join(ch for ch in pos_token if ch.isdigit())
if not digits:
    return None
pos_padded = digits.zfill(2)
stable_id = f"{ID_PREFIX}:{osis_ref}.w{pos_padded}"
```

This is NOT `int()`-coerced and NOT `%d`-formatted. `str.zfill(2)` pads to a
MINIMUM width of 2 and never truncates: `"0001".zfill(2) == "0001"`,
`"01".zfill(2) == "01"`. Distinct wide and narrow zero-padded tokens stay
distinct. The only residual collapse class is widths below 2 (`"1".zfill(2)
== "01"` would collide with a literal `"01"`), so the structural verdict
hinges on whether TAGNT upstream emits sub-2-width or mixed-width positions.
It does not (see below). Structurally `zfill` is strictly safer than TAHOT's
`int()`.

### B. Reproduced from the real upstream bytes

Position-token width census over all qualifying rows of both TAGNT files
(`TAGNT Mat-Jhn`, `TAGNT Act-Rev`), using the adapter's own
`_iter_data_rows` / `_parse_word_and_type`:

```
pos-token (rawlen, digitlen) distribution:
  rawlen=2 digitlen=2  count=142096
non-pure-digit pos tokens: 0
```

Every one of 142096 qualifying position tokens is exactly two digits. There
is zero width variance, zero `#0001`-style wide token, zero bare `#1`, zero
non-digit. `zfill(2)` on a 2-char digit string is the identity map.

Full pure-parse reproduction (`_iter_data_rows` + `_row_to_token`):

- (i) raw qualifying rows emitted by `_row_to_token`: **142096**
- (ii) distinct stable ids: **142096**
- (iii) collisions (raw minus distinct): **0**

Collision dump: empty. No id is emitted twice.

The TAGNT edition sigla exist (`NKO` 132894, `N(k)O` 2627, `K` 1657, `O`,
etc., parsed off the segment AFTER `#pos=`), but they are witness-attestation
tags packed after the position, not a competing zero-padded position block
like TAHOT's `=X`. There is no `=X`-vs-`=L` dual-width position mechanism in
TAGNT.

Independent corroboration: even the defective `int(pos)` code path (the dead
stepbible.py helper, section 3) run over the TAGNT bytes produces
137835 raw / 137835 distinct / **0 collisions**. The collapse cannot fire on
TAGNT regardless of which adapter parses it, because the triggering
upstream data does not exist in the TAGNT snapshot.

### C. Classification: CLEAN

int-collapse present: NO (`zfill`, not `int`). Triggering upstream: NO.
Collisions: 0. TAGNT is collision-proof on the frozen snapshot AND
structurally hardened against the TAHOT collapse class.

### D. Prescribed fix

None required for the position-collapse / id-overwrite defect. TAGNT does not
share the defect.

(Out-of-scope observation, recorded for the architect, NOT part of this
blast-radius verdict and requiring no action here: the faithful TAGNT emit is
142096 distinct tokens; the catalog `STEPBible-TAGNT.expected_count` is
141720, a +376 delta. This is an emit-count question, not a collision or an
overwrite. No canonical record is overwritten. It is unrelated to the
pos-collapse defect and is flagged only so it is not mistaken later for
collision damage.)

---

## 2. stepbible_ttesv.py -- AT-RISK (latent; no collision in the snapshot)

### A. Code evidence

Position extraction, `stepbible_ttesv.py:409-417`:

```
def _first_position(raw_positions: str) -> int | None:
    for p in raw_positions.split("+"):
        if not p:
            continue
        try:
            return int(p)
        except ValueError:
            continue
    return None
```

Id construction, `stepbible_ttesv.py:428-432`:

```
def _row_for_verse(book, chap, verse, pos, primary_strong):
    osis_ref = f"{book}.{chap}.{verse}"
    token_id = f"stepbible-ttesv:{osis_ref}.w{pos:02d}"
```

`int(p)` then `f"{pos:02d}"` is EXACTLY the TAHOT collapse pattern:
`int("01") == int("1") == int("001") == 1`, all rendered `w01`. The
int-collapse IS present in the code.

### B. Reproduced from the real upstream bytes

The TTESV file in the frozen snapshot lives at
`data/private/stepbible/Tagged-Bibles/TTESV - ... CC BY-NC.txt`.
(Path-resolution note: the live wiring calls
`ingest_stepbible_ttesv(STEPBIBLE_ROOT, ...)` and the adapter then opens
`STEPBIBLE_ROOT / TTESV_FILENAME`, i.e. directly under `stepbible/`, where
the file is NOT present, so under the live wiring `path.exists()` is false
and the adapter emits zero rows. That is a separate path defect outside this
audit's pos-collapse mandate and is flagged for the architect, not fixed
here. This section audits the collision behaviour against the real file at
its actual location, which is the correct adversarial test of the
pos-collapse blast radius.)

Position-piece width census over the real TTESV bytes
(`positions.split("+")` pieces inside every matched tag field):

```
(len=1, digit, no-leading-zero)   126
(len=2, digit, no-leading-zero)   243802
(len=2, digit, HAS-leading-zero)  142874
(len=3, digit, no-leading-zero)   334
```

So TTESV upstream DOES carry mixed-width, leading-zero positions (`1`, `01`,
`001`). The int-collapse trigger data IS structurally present at the
position-piece level. This is why the adapter is AT-RISK and not CLEAN.

However, the TTESV adapter does not emit one token per word. Per its frozen
docstring and `_parse_all_rows` (`stepbible_ttesv.py:452-489`), it emits
exactly ONE TaggedToken per verse line, keyed on that verse's FIRST tag's
first position only (`break` at line 480, `if chosen_pos is None: continue`).
Full pure-parse reproduction over the real bytes:

- verse segments parsed: 31219; tag fields matched: 366678
- (i) raw qualifying verse-line rows: **31127**
- (ii) distinct stable ids: **31127**
- (iii) collisions (raw minus distinct): **0**

Collision dump: empty.

Why no collision despite the trigger data being present: the id is
`stepbible-ttesv:<Book.C.V>.w<firstpos>`, one per verse line, and each verse
line is unique, so two distinct upstream records never compete for one id.
The mixed-width leading-zero variance occurs per-word WITHIN a verse, but
only the verse's first position ever reaches `f"{pos:02d}"`. The collapse is
armed in the code but the adapter's verse-granular record_unit means the
frozen snapshot presents no record pair that collides.

### C. Classification: AT-RISK (latent)

int-collapse present: YES (`int(p)` + `f"{pos:02d}"`, line 417/432).
Triggering upstream: PARTIAL (mixed-width leading-zero positions exist in the
bytes, but the adapter's one-token-per-verse-line record_unit means none of
them collide today). Collisions in the frozen snapshot: 0. The defect is
latent: if the record_unit is ever changed to one-token-per-tagged-word
(which the docstring's "one row per tagged English surface word" wording and
the catalog record_unit `tagged_word` arguably call for) WITHOUT first
hardening the position rendering, the `01`/`1`/`001` width variance would
immediately produce silent same-verse overwrites of the TAHOT class.

### D. Prescribed fix

Make the stable id preserve the upstream zero-pad width instead of
collapsing through `int`. One-line change at `stepbible_ttesv.py:432`,
carrying the raw position string (not the int) into the id, e.g. derive a
`pos_str` that keeps the upstream token verbatim and use
`token_id = f"stepbible-ttesv:{osis_ref}.w{pos_str}"`, or normalise every
position to a single fixed width wider than the maximum observed (3) so no
two distinct upstream widths can ever map together. With the current
verse-granular record_unit the corrected faithful emit is unchanged at
**31127** (zero collisions today, the fix is purely hardening against the
latent regression). If the record_unit is later widened to per-word, the fix
must be in place BEFORE that change or the overwrite fires.

(Out-of-scope observation, no action here: faithful verse-line emit 31127 vs
catalog `STEPBible-TTESV.expected_count` 31272, and the record_unit
`tagged_word` vs the adapter's per-verse emit, are separate prior-audit
topics, not collision damage.)

---

## 3. stepbible.py (shared helper) -- DEFECTIVE in code, but DEAD (not wired)

### A. Code evidence

`stepbible.py:26` `_REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)#(\d+)([=A-Za-z]*)$")`

`stepbible.py:30-34`:

```
def _parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    m = _REF_RE.match(ref.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
```

`stepbible.py:53` `word_id = f"{id_prefix}:{osis}.w{pos:02d}"`

`pos = int(m.group(4))` then `f"{pos:02d}"`. This is the IDENTICAL collapse
to TAHOT, bit for bit. `_iter_records` (`stepbible.py:158-163`) globs
`TAHOT*.txt` and `TAGNT*.txt` directly under `source_dir` and feeds both
through this same `int(pos)` path with prefixes `stepbible-tahot` and
`stepbible-tagnt`.

### B. Reproduced from the real upstream bytes

Running this helper's exact `_parse_ref` + `word_id` over the real TAHOT
bytes:

- raw qualifying rows: **282239**
- distinct stable ids: **282222**
- collisions: **17**, at 4 verses
  (Deu.30.16 x6, Jdg.16.14 x8, 2Sa.23.33 x1, 2Ki.25.3 x2)

Collision dump (every one is an off-canon `=X` 4-digit position overwriting
the canonical `=L` 2-digit Leningrad word at the same integer position):

```
stepbible-tahot:Deu.30.16.w01 <- ['Deu.30.16#0001=X', 'Deu.30.16#01=L']
stepbible-tahot:Deu.30.16.w02 <- ['Deu.30.16#0002=X', 'Deu.30.16#02=L']
stepbible-tahot:Deu.30.16.w03 <- ['Deu.30.16#0003=X', 'Deu.30.16#03=L']
stepbible-tahot:Deu.30.16.w04 <- ['Deu.30.16#0004=X', 'Deu.30.16#04=L']
stepbible-tahot:Deu.30.16.w05 <- ['Deu.30.16#0005=X', 'Deu.30.16#05=L']
stepbible-tahot:Deu.30.16.w06 <- ['Deu.30.16#0006=X', 'Deu.30.16#06=L']
stepbible-tahot:Jdg.16.14.w01 <- ['Jdg.16.14#0001=X', 'Jdg.16.14#01=L']
... (Jdg.16.14 w02..w08 identical pattern) ...
stepbible-tahot:2Sa.23.33.w01 <- ['2Sa.23.33#0001=X', '2Sa.23.33#01=L']
stepbible-tahot:2Ki.25.3.w01  <- ['2Ki.25.3#0001=X', '2Ki.25.3#01=L']
stepbible-tahot:2Ki.25.3.w02  <- ['2Ki.25.3#0002=X', '2Ki.25.3#02=L']
```

This is the exact 17-row `=X`-overwrites-`=L` corruption from
docs/AUDIT_tahot_30row_deepdive.md, reproduced independently here through
the shared helper code path. The defect is real and identical.

Same helper over the real TAGNT bytes: 137835 raw / 137835 distinct /
**0 collisions** (TAGNT has no triggering `=X` data, corroborating
section 1).

### C. Classification: DEFECTIVE (code), but DEAD CODE (not in the blast radius of the live ingest)

int-collapse present: YES (line 34 `int(m.group(4))` + line 53
`f"{pos:02d}"`). Triggering upstream: YES for its TAHOT glob path (17
collisions), NO for its TAGNT glob path. BUT: `ingest_stepbible` from
`stepbible.py` is NOT imported by `ingest/lexical/run.py` and is not
referenced by any wired adapter (verified: `run.py` imports and dispatches
the per-dataset modules `ingest_stepbible_tahot`, `ingest_stepbible_tagnt`,
`ingest_stepbible_ttesv`, `ingest_oshb`; grep for any live import of
`stepbible.ingest_stepbible` returns no matches). It is legacy dead code. It
does not run in Phase D live ingest, so it does not enlarge the operative
blast radius beyond TAHOT.

### D. Prescribed fix

Because it is dead code the safest faithful action is removal (delete
`ingest/lexical/stepbible.py`, or quarantine it) so it cannot be revived and
silently reintroduce the TAHOT-class corruption. If it is kept, it needs the
SAME fix prescribed for TAHOT: stop `=X` rows occupying canonical `=L`
positions (skip the 132 `=X` rows, or namespace `=X` into a distinct id
suffix, or carry the raw zero-padded position string into the id instead of
`int`). Implementer decision, not auditor. This audit only flags it; it is
not on the must-fix-before-Phase-D path because it is not wired.

---

## 4. oshb.py -- CLEAN

### A. Code evidence

OSHB does not derive position from a `#pos` upstream string at all. Position
is a synthetic per-verse counter incremented on every `<w>` element,
`oshb.py:641-657`:

```
position = 0
...
for child in verse_elem:
    tag = _strip_ns(child.tag)
    if tag == "w":
        position += 1
        ...
        word_id = _emit_word(... position ...)
```

Id construction, `oshb.py:507-508`:

```
pos_pad = f"{position:02d}"
word_id = f"oshb:{osis_ref}.w{pos_pad}"
```

`position` is an in-process integer that counts 1..N over the verse's `<w>`
children. It is never parsed from a zero-padded upstream token, so the
"two distinct upstream positions of different zero-pad width collapse" class
is structurally impossible: there is no upstream position string to vary in
width. `f"{position:02d}"` here only sets a display minimum on a counter
that is already unique per verse.

Qere/ketiv handling: every `<w>` (including `x-ketiv` and `x-qere`)
increments `position` (line 647 is unconditional on tag == "w"), so a ketiv
word and any following word each get their own distinct position. The qere
companion is emitted not as a Word but as a separate `Reading` node in a
disjoint namespace `oshb-reading:<osisRef>.w<pos>.qere`
(`oshb.py:603`), so it cannot collide with a Word id. Multi-edition slots do
not exist in the OSHB OSIS XML model the way TAHOT `=X`/`=L` do.

### B. Reproduced from the real upstream bytes

Full pure-parse of all 40 `data/private/oshb/wlc/*.xml` books via the
adapter's own `_process_book`:

- (i) raw Word rows: **305507**
- (ii) distinct Word stable ids: **305507**
- (iii) Word id collisions: **0**
- Reading rows: 1244; distinct reading_id: 1244; Reading collisions: **0**
- qere_or_ketiv distribution on Word: `'' 304239`, `'x-ketiv' 1268`
  (every x-ketiv word holds its own incremented position, none overwritten)

Collision dump: empty for both Word and Reading.

### C. Classification: CLEAN

int-collapse present: NO (position is a synthetic sequential counter, not a
parsed upstream token; no width to collapse). Triggering upstream: NO
(OSIS XML has no `=X`/`=L` dual-position edition block; qere is namespaced
to a disjoint Reading id). Collisions: 0. The id scheme is collision-proof
by construction.

### D. Prescribed fix

None required. OSHB does not share the defect and cannot, given a
sequential-counter position.

(Out-of-scope observation, no action: faithful Word emit 305507 vs catalog
`OSHB-morphology.expected_count` 306785 is a separate emit-count topic, not
collision damage. No record is overwritten.)

---

## 5. BLAST-RADIUS VERDICT TABLE

| adapter | int-collapse in code | triggering upstream in frozen snapshot | collisions reproduced | class | corrected faithful count |
|---|---|---|---|---|---|
| stepbible_tahot.py (reference, already confirmed) | YES (`int(pos)` L316 + L341) | YES (132 `=X` rows; 4 verses collide `=L`) | 17 (silent canonical overwrite) | DEFECTIVE | per the TAHOT deep-dive, after `=X` handling fix (not 283704) |
| stepbible_tagnt.py | NO (`zfill(2)`, never truncates) | NO (all 142096 pos tokens fixed 2-digit; no `=X` block) | 0 | CLEAN | 142096 (unchanged; no fix needed) |
| stepbible_ttesv.py | YES (`int(p)` L417 + `{pos:02d}` L432) | PARTIAL (mixed-width `1`/`01`/`001` exist, but verse-granular record_unit means none collide) | 0 | AT-RISK (latent) | 31127 (unchanged; fix is hardening only) |
| stepbible.py (shared helper) | YES (`int(m.group(4))` L34 + `{pos:02d}` L53) | YES on its TAHOT glob (17), NO on TAGNT | 17 (TAHOT path) | DEFECTIVE but DEAD (not wired into run.py) | n/a; remove or quarantine, else apply TAHOT fix |
| oshb.py | NO (synthetic sequential `position` counter) | NO (no `#pos` upstream token; qere namespaced disjoint) | 0 | CLEAN | 305507 (unchanged; no fix needed) |

---

## 6. AUDITOR VERDICT

Counts among the in-scope adapters:

- DEFECTIVE: 1 in live code path (stepbible_tahot.py, the already-confirmed
  reference). Plus 1 DEFECTIVE-but-DEAD module (stepbible.py) that is not
  wired and therefore not in the operative blast radius.
- AT-RISK (latent): 1 (stepbible_ttesv.py). Collapse is armed in code; the
  frozen snapshot does not collide only because the adapter emits one token
  per verse line. Not a current data-integrity loss, but a regression
  waiting on any record_unit change.
- CLEAN: 2 (stepbible_tagnt.py, oshb.py), each proven collision-proof from
  the bytes (TAGNT also structurally hardened by `zfill`; OSHB by a
  synthetic counter).

The defect is NOT systemic. It does NOT spread to TAGNT or OSHB. The
adversarial assumption is refuted by the bytes for those two.

### Must be fixed by an implementer before Phase D live ingest

1. `ingest/lexical/stepbible_tahot.py` -- the confirmed defect. 17 silent
   canonical `=L` overwrites by off-canon `=X`. Already on the implementer
   queue per docs/AUDIT_tahot_30row_deepdive.md. This audit confirms it is
   the ONLY adapter in the live wiring currently producing the silent
   canonical-overwrite corruption.

That is the only adapter that MUST be fixed to stop active corruption.

Strongly recommended, same change-set:

2. `ingest/lexical/stepbible_ttesv.py` -- harden the id rendering
   (preserve the upstream position string / fixed-wide pad instead of
   `int(p)` -> `{pos:02d}`) so the latent collapse cannot fire if the
   record_unit is ever corrected to per-word. No current data loss; this is
   defence in depth on a known-armed defect at the same verse-id scheme.

3. `ingest/lexical/stepbible.py` -- dead, defective, and a revival hazard
   (it carries the exact TAHOT 17-collision corruption and would also route
   TAGNT through `int(pos)`). Delete or quarantine so it cannot be
   reintroduced. Not blocking Phase D because not wired, but it should not
   survive into the reseed unaddressed.

No fix required for stepbible_tagnt.py or oshb.py.

### Is TAGNT specifically defective?

NO. TAGNT is CLEAN, with decisive proof from the bytes:

- The code uses `digits.zfill(2)` (`stepbible_tagnt.py:316`), which pads to a
  minimum of 2 and never truncates, so it cannot collapse a wide zero-padded
  position onto a narrow one the way TAHOT's `int()` does.
- Every one of the 142096 qualifying upstream position tokens is exactly
  two digits (width census: `rawlen=2 digitlen=2 count=142096`, zero
  variance, zero `#0001`-style token, zero bare `#1`). The collapse has no
  trigger data even if the code were defective.
- Full pure-parse reproduction: 142096 raw rows -> 142096 distinct stable
  ids -> 0 collisions. Empty collision dump.
- Cross-check: even the DEFECTIVE `int(pos)` shared helper, run over the
  same TAGNT bytes, yields 137835 raw / 137835 distinct / 0 collisions. The
  collapse cannot fire on TAGNT regardless of adapter, because TAGNT has no
  `=X`-class variable-width alternate-edition position block.

TAGNT carries no silent canonical overwrite. It does not need the TAHOT fix.

---

End of forensic blast-radius trace. No files modified except this
deliverable. No git add/commit. No docker/ingest/embedding run.
expected_counts.json, the baseline, every adapter, test, and fixture
untouched.
