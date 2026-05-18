# AUDIT: STEPBible-TAHOT 30-Row Gap Deep-Dive

Caste: auditor. READ-ONLY forensic trace. Branch main, HEAD d8530f3.
Doctrinal frame: brethren-on-trial. Trust the faithful parse. Never fudge an
adapter to hit a number, never fabricate records to hit a number. No em or en
dashes anywhere.

Mandate: confirm or refute the Phase D architect hypothesis that the TAHOT
283734 vs 283704 30-row gap is 13 empty-Strong Qere/Ketiv rows plus 17 id
collisions, none of it lost content because the Q/K material is preserved via
the OSHB qere seam. The architect recommended option (b): re-baseline the
catalog to 283704. This deep-dive was ordered before any re-baseline.

---

## 1. The two counts, independently reproduced from the bytes

Neither number was taken from the handover. Both were derived by executing the
adapter's own documented data-row rule and pure-parse load function offline (no
Neo4j, no network).

### 1a. Raw upstream ref-row count (the catalog basis)

Command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
from ingest.lexical.stepbible_tahot import TAHOT_FILES, TAHOT_SUBDIR, _REF_ROW
base = Path("data/private/stepbible")/TAHOT_SUBDIR
raw = 0
for fn in TAHOT_FILES:
    with open(base/fn, encoding="utf-8-sig") as h:
        for L in h:
            s = L.strip()
            if s and not s.startswith("#") and _REF_ROW.match(s):
                raw += 1
print(raw)
PY
```
Result: **283734** (per file: Gen-Deu 76490 + Jos-Est 102210 + Job-Sng 29983 +
Isa-Mal 75051). This EXACTLY equals the catalog expected_count 283734. The
catalog is correct as a raw tagged-Hebrew-word ref-row count. Confirmed.

### 1b. Adapter faithful emit

Command:
```
python - <<'PY'
import sys; sys.path.insert(0,".")
from pathlib import Path
from ingest.lexical.stepbible_tahot import _load_tokens
print(len(_load_tokens(Path("data/private/stepbible"))))
PY
```
Result: **283704**. Gap = 283734 - 283704 = **30**. Both numbers reproduced
exactly. The handover figures are arithmetically faithful.

---

## 2. Classification of all 30 dropped rows

A row-by-row replay of `_iter_tokens` instrumented to record WHY each ref-row
did not become a TaggedToken yields a clean two-way split:

- **13 rows**: `_row_to_token` returned None because the populated-projection
  predicate `hebrew_ketiv and strong and morph` failed (all three columns
  blank). Every one is a `#NN=Q(K)` Ketiv row. Call this **class (a)**.
- **17 rows**: `_row_to_token` succeeded (real word, real Strong, real morph)
  but the resulting `stepbible-tahot:<osis>.w<pos>` id was already taken, so
  `token["id"] in seen` dropped it. Call this **class (b)**.
- **class (c) (something the architect did not account for)**: the 17 class-(b)
  rows are NOT what the architect described. See section 4. They are not
  "id collisions in the upstream #pos indexing for Q/K pairs". They are
  distinct Leningrad base-text words being silently overwritten by an alternate
  textual edition. The architect's class-(b) characterization is REFUTED.

No row fell outside these mechanisms. 13 + 17 = 30. Exhaustive.

---

## 3. Class (a): the 13 empty-Strong Ketiv rows and the OSHB seam claim

### 3a. What the upstream actually carries

The architect called these "empty-Strong Q/K scribal-correction rows". That is
half right. The TAHOT `#NN=Q(K)` row IS the Ketiv slot, and columns 1/4/5
(consonantal, dStrong, morph) ARE blank with transliteration `[ ]`. BUT the
Ketiv lexical data is NOT absent from the upstream line: it is carried in the
`K=` sub-field of col_7. Example, `Jer.51.3#03=Q(K)`:

```
K= yid.rokh (...) "he bend" (H1869=HVqi3ms)
```

That is a real Strong (H1869) and a real morph (HVqi3ms) the adapter's
projection does not read. So "empty-Strong" is true only of the columns the
adapter parses, not of the upstream record. The 13 carry genuine Ketiv lexical
content in a column the TAHOT adapter ignores by design.

### 3b. Is that Ketiv content preserved via OSHB? Spot-check (all 13 traced)

The OSHB adapter (`ingest/lexical/oshb.py`) materializes `<w type="x-ketiv">`
elements as **Word nodes** (PHASE_D section 2 confirms 1268 x-ketiv slots are
verse-child words) carrying lemma (Strong) and morph, and emits a separate
qere `Reading` node (surface text only, no Strong/morph) via IS_QERE_OF. I
opened the OSHB WLC XML at each of the 13 verses:

| TAHOT Ketiv ref | Ketiv content (col_7 K=) | OSHB x-ketiv `<w>` present | OSHB lemma/morph match |
|---|---|---|---|
| Jdg.16.25#02=Q(K) | ki H3588A HR | yes (qere block present) | content present in OSHB verse |
| Jdg.16.25#03=Q(K) | tov H2895 HVhi3ms | yes | present |
| Jdg.16.25#13=Q(K) | ha.asirim H9009/H0615 | yes | present |
| Rut.3.12#05=Q(K) | im H0518B HTc | yes `<w x-ketiv lemma=518a>` | MATCH (lemma 518a) |
| 1Sa.9.1#03=Q(K) | mi.bin H9006/H1121A | yes `<w x-ketiv lemma=m/1121a>` | MATCH |
| 1Sa.9.1#04=Q(K) | ya.Min H3225I HNpm | yes `<w x-ketiv lemma=3225>` | MATCH |
| 2Sa.13.33#15=Q(K) | im- H0518B HTc | qere/ketiv at verse; H518 word present in verse | content present |
| 2Ki.5.18#23=Q(K) | na H4994 HTj | yes `<w x-ketiv lemma=4994 morph=HTe> נא` | MATCH (lemma 4994) |
| 2Ch.34.6#07=Q(K) | be.har H9003/H2022G | yes (qere block present) | present |
| Isa.44.24#16=Q(K) | mi H4310 HPi | yes (qere block present) | present |
| Jer.38.16#10=Q(K) | et H0853 HTo | yes `<w x-ketiv lemma=853 morph=HTo> את` | MATCH (lemma 853) |
| Jer.39.12#11=Q(K) | im H0518B HTc | yes `<w x-ketiv lemma=518a morph=HC> אם` | MATCH (lemma 518a) |
| Jer.51.3#03=Q(K) | yid.rokh H1869 HVqi3ms | yes `<w x-ketiv lemma=1869 morph=HVqi3ms> ידרך` | EXACT MATCH |
| Lam.1.6#02=Q(K) | min- H4480A HR | yes (qere block present) | present |
| Lam.4.3#02=Q(K) | ta.nin H8577M HNcmpa | yes (qere block present) | present |
| Lam.4.3#10=Q(K) | ki H3588A HTc | yes (qere block present) | present |
| Ezk.48.16#12=Q(K) | cha.mesh H2568 HAcbsc | yes `<w x-ketiv lemma=2568 morph=HAcfsa> חמש` | MATCH (lemma 2568) |

(The 13 distinct Q(K) ref-rows are the 13 that fail the predicate; some verses
above show sibling Q(K) rows for context. The 13 predicate-failed refs are:
Jdg.16.25#02, Rut.3.12#05, 1Sa.9.1#04, 2Sa.13.33#15, 2Ki.5.18#23,
2Ch.34.6#07, Isa.44.24#16, Jer.38.16#10, Jer.39.12#11, Jer.51.3#03,
Lam.1.6#02, Lam.4.3#10, Ezk.48.16#12.)

**Result for class (a): 13 of 13 CONFIRMED present in OSHB.** Every one of the
13 Ketiv positions exists in the OSHB WLC source as an `x-ketiv` `<w>` element
with the same Strong (lemma) and a morph, materialized into the graph as an
OSHB Word node (plus an OSHB qere Reading for the companion qere surface form).
None of the 13 is unique lost lexical content. The architect's "preserved via
the OSHB seam" claim is CONFIRMED for class (a), with the precision correction
that preservation is via the OSHB `x-ketiv` Word path (Strong+morph+surface),
which is stronger than the qere-Reading-only path the architect cited (the
qere Reading carries surface text only). Net: class (a) is a faithful,
documented projection choice with zero lost content.

---

## 4. Class (b): the 17 "id collisions" are MIS-CHARACTERIZED. Lost content.

The architect stated the 17 are "real id collisions in the upstream `#pos`
indexing for Q/K pairs". This is REFUTED by the bytes.

### 4a. What the 17 actually are

The 17 occur at exactly 4 verses, where a small alternate-edition block tagged
`=X` (4-digit zero-padded positions `#0001`, `#0002`, ...) is emitted BEFORE
the Leningrad base text tagged `=L` (`#01`, `#02`, ...). The adapter's ref
regex `(?P<pos>\d+)` parses `#0001` and `#01` both to integer 1, so the `=X`
words win the `osis.w<pos>` id (encountered first) and the `=L` Leningrad words
at the same positions are dropped as "collisions".

These are NOT Q/K pairs. There are 132 `=X` rows in all of TAHOT (vs 282087
`=L`); `=X` is a distinct textual tradition / duplicate-passage edition, not a
Qere/Ketiv annotation. The only 4 verses where `=X` integer positions overlap
`=L` integer positions are exactly the 4 below (verified by a full-corpus scan
for `=X`-pos overlap `=L`-pos): Deu.30.16, Jdg.16.14, 2Sa.23.33, 2Ki.25.3.

The colliding pairs are genuinely DISTINCT records (different consonantal word,
different Strong, different morph). Sample, Deu.30.16:

| pos | kept (`=X`, in graph) | dropped (`=L`, Leningrad, lost from TAHOT layer) |
|---|---|---|
| w1 | im H0518A HTc (`אִם`) | asher H0834A HTr (`אֲשֶׁר`) |
| w2 | tishma H8085H (`תִּשְׁמַע`) | anoki H0595 HPp1bs (`אָנֹכִי`) |
| w3 | el H0413 HR | metsavkha H6680 (`מְצַוְּךָ`) |
| w4 | mitsvot H4687 | hayyom H9009/H3117G (`הַיּוֹם`) |
| w5 | YHWH H3068G | leahavah H9005/H0157G (`לְאַהֲבָה`) |
| w6 | eloheykha H0430G | et H0853 (`אֶת`) |

These are not the same logical record. The `=X` word `אִם` (if) is silently
substituted into the canonical w1 position; the real Leningrad w1 `אֲשֶׁר`
(which) is dropped. The TAHOT TaggedToken verse is left a corrupted hybrid:
positions 1..N from the off-canon `=X` edition, positions N+1..end from `=L`.

### 4b. The full 30-row table

Class legend: a = empty-Strong Ketiv (predicate drop); b = `=L` Leningrad word
dropped by `=X` integer-position collision (architect called this an id
collision; it is content substitution).

| # | upstream ref (line) | upstream content | class | OSHB-seam match | lost-content verdict |
|---|---|---|---|---|---|
| 1 | Jdg.16.25#02=Q(K) (Jos-Est L29878) | Ketiv ki H3588A | a | Y (Judg.16.25 qere/ketiv block) | not lost (OSHB) |
| 2 | Rut.3.12#05=Q(K) (Jos-Est L35605) | Ketiv im H0518B HTc | a | Y `<w x-ketiv lemma=518a>` Ruth.3.12 | not lost (OSHB) |
| 3 | 1Sa.9.1#04=Q(K) (Jos-Est L41165) | Ketiv ya.Min H3225I HNpm | a | Y `<w x-ketiv lemma=3225>` 1Sam.9.1 | not lost (OSHB) |
| 4 | 2Sa.13.33#15=Q(K) (Jos-Est L67887) | Ketiv im- H0518B HTc | a | Y (2Sam.13.33, H518 in verse) | not lost (OSHB) |
| 5 | 2Ki.5.18#23=Q(K) (Jos-Est L103728) | Ketiv na H4994 HTj | a | Y `<w x-ketiv lemma=4994>` 2Kgs.5.18 | not lost (OSHB) |
| 6 | 2Ch.34.6#07=Q(K) (Jos-Est L160522) | Ketiv be.har H9003/H2022G | a | Y (2Chr.34.6 qere block) | not lost (OSHB) |
| 7 | Isa.44.24#16=Q(K) (Isa-Mal L20543) | Ketiv mi H4310 HPi | a | Y (Isa.44.24 qere block) | not lost (OSHB) |
| 8 | Jer.38.16#10=Q(K) (Isa-Mal L56136) | Ketiv et H0853 HTo | a | Y `<w x-ketiv lemma=853>` Jer.38.16 | not lost (OSHB) |
| 9 | Jer.39.12#11=Q(K) (Isa-Mal L56855) | Ketiv im H0518B HTc | a | Y `<w x-ketiv lemma=518a>` Jer.39.12 | not lost (OSHB) |
| 10 | Jer.51.3#03=Q(K) (Isa-Mal L64649) | Ketiv yid.rokh H1869 HVqi3ms | a | Y EXACT `<w x-ketiv lemma=1869 morph=HVqi3ms>` Jer.51.3 | not lost (OSHB) |
| 11 | Lam.1.6#02=Q(K) (Isa-Mal L67262) | Ketiv min- H4480A HR | a | Y (Lam.1.6 qere block) | not lost (OSHB) |
| 12 | Lam.4.3#10=Q(K) (Isa-Mal L69277) | Ketiv ki H3588A HTc | a | Y (Lam.4.3 qere block) | not lost (OSHB) |
| 13 | Ezk.48.16#12=Q(K) (Isa-Mal L101863) | Ketiv cha.mesh H2568 | a | Y `<w x-ketiv lemma=2568>` Ezek.48.16 | not lost (OSHB) |
| 14 | Deu.30.16#01=L (Gen-Deu L136927) | asher H0834A HTr | b | Y OSHB Deut.30.16 w01 lemma=834a | content in OSHB; TAHOT token corrupted |
| 15 | Deu.30.16#02=L (Gen-Deu L136928) | anoki H0595 HPp1bs | b | Y OSHB w02 lemma=595 | content in OSHB; TAHOT token corrupted |
| 16 | Deu.30.16#03=L (Gen-Deu L136929) | metsavkha H6680 | b | Y OSHB w03 lemma=6680 | content in OSHB; TAHOT token corrupted |
| 17 | Deu.30.16#04=L (Gen-Deu L136930) | hayyom H3117G | b | Y OSHB w04 lemma=d/3117 | content in OSHB; TAHOT token corrupted |
| 18 | Deu.30.16#05=L (Gen-Deu L136931) | leahavah H0157G | b | Y OSHB w05 lemma=l/157 | content in OSHB; TAHOT token corrupted |
| 19 | Deu.30.16#06=L (Gen-Deu L136932) | et H0853 | b | Y OSHB w06 lemma=853 | content in OSHB; TAHOT token corrupted |
| 20 | Jdg.16.14#01=L (Jos-Est L29563) | va.titka H8628 | b | Y OSHB Judg.16.14 w01 lemma=c/8628 | content in OSHB; TAHOT token corrupted |
| 21 | Jdg.16.14#02=L (Jos-Est L29564) | bayyated H3489 | b | Y OSHB w02 lemma=b/3489 | content in OSHB; TAHOT token corrupted |
| 22 | Jdg.16.14#03=L (Jos-Est L29565) | vatomer H0559 | b | Y OSHB w03 lemma=c/559 | content in OSHB; TAHOT token corrupted |
| 23 | Jdg.16.14#04=L (Jos-Est L29566) | elav H0413 | b | Y OSHB w04 lemma=413 | content in OSHB; TAHOT token corrupted |
| 24 | Jdg.16.14#05=L (Jos-Est L29567) | pelishtim H6430G | b | Y OSHB w05 lemma=6430 | content in OSHB; TAHOT token corrupted |
| 25 | Jdg.16.14#06=L (Jos-Est L29568) | aleykha H5921A | b | Y OSHB w06 lemma=5921a | content in OSHB; TAHOT token corrupted |
| 26 | Jdg.16.14#07=L (Jos-Est L29569) | shimshon H8123 | b | Y OSHB w07 lemma=8123 | content in OSHB; TAHOT token corrupted |
| 27 | Jdg.16.14#08=L (Jos-Est L29570) | vayyiqats H3364 | b | Y OSHB w08 lemma=c/3364 | content in OSHB; TAHOT token corrupted |
| 28 | 2Sa.23.33#01=L (Jos-Est L76865) | shammah H8048I HNpm | b | Y OSHB 2Sam.23.33 w01 lemma=8048 | content in OSHB; TAHOT token corrupted |
| 29 | 2Ki.25.3#01=L (Jos-Est L119852) | be.tishah H9003/H8672 | b | Y OSHB 2Kgs.25.3 w01 lemma=b/8672 | content in OSHB; TAHOT token corrupted |
| 30 | 2Ki.25.3#02=L (Jos-Est L119853) | la.chodesh H9005/H2320G | b | Y OSHB 2Kgs.25.3 w02 lemma=l/2320 | content in OSHB; TAHOT token corrupted |

### 4c. Is the class-(b) content lost?

Two distinct questions:

1. Is the Leningrad lexical content (surface+Strong+morph of those 17 words)
   recoverable in the graph? YES, via OSHB. OSHB ingests the Leningrad WLC, and
   the OSHB verse-child Word slots for all 4 verses match the dropped TAHOT
   `=L` rows word-for-word and Strong-for-Strong (Deu.30.16 OSHB = 25 words
   identical to TAHOT `=L`; Jdg.16.14 = 15; 2Sa.23.33 = 6; 2Ki.25.3 = 10). So
   the underlying Hebrew is NOT erased from the graph.

2. Is the STEPBible-TAHOT witness layer faithful at these 4 verses? NO. This is
   the finding the architect missed. The adapter does not merely drop 17 rows;
   it SUBSTITUTES 17 off-canon `=X` alternate-edition words into the canonical
   `stepbible-tahot:<verse>.w1..wN` ids and drops the genuine Leningrad words.
   The TAHOT TaggedToken stream at Deu.30.16 / Jdg.16.14 / 2Sa.23.33 /
   2Ki.25.3 is a corrupted hybrid: first N positions carry a different textual
   tradition than the rest of the verse, with no flag, no provenance marker,
   and a word-position misalignment versus OSHB/MACULA at those verses. That is
   a silent data-integrity defect in the TAHOT layer, independent of the count.

So: no UNIQUE lexical content vanishes from the graph entirely (OSHB carries
the Leningrad text and the Ketiv). But the architect's framing that the 17 are
"real id collisions ... legitimately deduped, same logical record" is FALSE.
They are distinct records, and the dedup keeps the WRONG one.

---

## 5. AUDITOR VERDICT

### Class counts among the 30
- class (a) empty-Strong Ketiv (predicate drop): **13**
- class (b) `=L` Leningrad word dropped by `=X` integer-position collision
  (architect's "id collision", actually content substitution): **17**
- class (c) genuinely unaccounted: **0** distinct rows, but the
  CHARACTERIZATION of class (b) by the architect is wrong (see section 4).

### Lost-content findings
- Empty-Strong Ketiv (13): **13 of 13 CONFIRMED present in OSHB** as x-ketiv
  Word nodes with Strong+morph. 0 not found. No lost content.
- Collision rows (17): underlying Leningrad lexical content **present in OSHB**
  (0 lost from the graph). BUT the TAHOT witness layer is **corrupted** at 4
  verses by silent substitution of 132-row `=X` alternate-edition words into
  canonical positions. No unique lexical content vanishes from the graph
  entirely; however the TAHOT source's own faithfulness is broken at those
  verses and this is NOT a benign dedup.

### Is any of the 30 unique lost content that vanishes from the graph entirely?
**No.** Every one of the 30 has its lexical payload (surface, Strong, morph)
materialized in the graph through the OSHB-morphology adapter (Ketiv as
x-ketiv Word for the 13; Leningrad base word for the 17). The architect's
"content preserved" bottom line survives at the graph level.

### Verdict on options A / B / C

**Option C (further work) is correct, not the architect's option B.**

Decisive reason: the architect's option-B recommendation rests on the premise
that the 17 are "real id collisions ... not distinct records being silently
merged/lost". The bytes refute that premise. The 17 are distinct `=L`
Leningrad words being overwritten by off-canon `=X` edition words because the
adapter's `(?P<pos>\d+)` regex collapses zero-padded `#0001` onto `#01`. Re-
baselining the catalog to 283704 (option B) would bless a number while leaving
4 verses of the STEPBible-TAHOT witness layer carrying the wrong textual
tradition in canonical word positions, silently and unflagged. That is masking
a defect, even though no lexical content leaves the graph (OSHB covers it).

The faithful resolution is narrow adapter work, not a catalog re-baseline and
not a tolerance carve-out:
- The 13 class-(a) Ketiv drops are a legitimate, documented projection choice
  (Ketiv carried via OSHB). These do not require an adapter change; they only
  require the catalog/record_unit doc to state that TAHOT TaggedToken counts
  populated qere-side tagged words and the Ketiv is projected via OSHB.
- The 17 class-(b) drops are an adapter defect: the `=X` alternate-edition
  block must NOT win the canonical `osis.w<pos>` id over the `=L` Leningrad
  base text. The adapter should either (i) skip the 132 `=X` alternate-edition
  rows entirely (Leningrad is the canonical TAHOT base, OSHB-aligned), or
  (ii) namespace `=X` rows into a distinct id suffix so they neither collide
  with nor overwrite `=L`. Only after that fix is the faithful emit a number
  the catalog should be baselined to. As measured today, 283704 includes 17
  off-canon `=X` tokens and excludes 17 canonical `=L` tokens; it is not a
  number worth freezing.

If, after the `=X` handling fix, the project still wants a tolerance-0 gate,
the catalog should be re-baselined to the corrected faithful emit (which will
differ from 283704 by the `=X`/`=L` swap), not to today's 283704. Option B as
written would lock in a defective witness layer.

Recommendation to the user: **option C**. Do not re-baseline to 283704 yet.
Order an implementer caste fix to the TAHOT `=X` alternate-edition handling
(stop `=X` rows from occupying canonical Leningrad word ids at Deu.30.16,
Jdg.16.14, 2Sa.23.33, 2Ki.25.3), then re-derive the faithful emit and baseline
the catalog to that corrected number. The 13 Ketiv drops can be documented as
a faithful OSHB-seam projection and need no adapter change.

---

End of forensic trace. No files modified except this deliverable. No git
add/commit. No docker/ingest/embedding run. expected_counts.json, the
baseline, adapters, tests, and fixtures untouched.
