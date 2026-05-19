# Phase D Systemic Class Audit: canonical_strongs raise-class

Caste: AUDITOR. Mode: READ-ONLY static source plus frozen-upstream analysis.
Audit target: HEAD 995d3b7, branch main. No Neo4j touched, no ingest run, no
code or test modified. Sole deliverable is this file.

Defect class: `ingest.canonical_strongs.canonical_strongs(raw, lang)` RAISES
`ValueError` (it returns no sentinel) for any token it cannot resolve. The
Decision-18 wave added `canonical_strongs(raw, ...)[0]` call sites. An
uncaught one propagates the ValueError through run.py (no try/except) and
kills the whole reseed. This is the class that took relaunch attempt 3
(macula_greek, "unrecognized Strong's encoding: '15374053'", a digit-stripped
compound crasis Strong `1537+4053`).

---

## 1. canonical_strongs raise-spec (ingest/canonical_strongs.py, lines 20-82)

Signature: `canonical_strongs(raw: str, lang: Lang | None = None) -> tuple[str, str | None]`.
Return shape: a 2-tuple `(canonical_string, suffix_or_None)`. Every adapter
caller uses `canon[0]` (the canonical string) and discards or separately keeps
`canon[1]`. There is NO non-raising mode and NO documented sentinel return.
Failure is signalled ONLY by raising `ValueError`. The faithful contract is
therefore per-caller `try/except ValueError`, exactly as Decision 18 line 13
("No-Strong / unresolvable token ... the producing adapter MUST NOT fabricate
a Strong. It either skips the Strong attachment ... or routes to the adapter's
documented sentinel node. The canonical form is never the empty string.").

Accepted encodings (each returns, never raises):

| Regex (line) | Form | Returns |
|---|---|---|
| `_RE_PREFIXED` L14 | `^([HhGg])(\d{1,5})([A-Za-z])?$` e.g. `H430`, `g40a`, `{H0430G}` after brace strip | `(PREFIX + digits.zfill(4) + UPPER suffix, suffix)` |
| `_RE_NUM_SPACE_LETTER` L15 | `^(\d{1,5})\s+([A-Za-z])$` e.g. `1254 a` | `(prefix+digits.zfill(4)+SUFFIX, SUFFIX)` ONLY if lang given |
| `_RE_NUM_LETTER` L16 | `^(\d{1,5})([A-Za-z])$` e.g. `1254a` | same, ONLY if lang given |
| `_RE_NUM` L17 | `^(\d{1,5})$` e.g. `430` | `(prefix+digits.zfill(4), None)` ONLY if lang given |

Pre-processing before the regex tries: `strip()`; `{...}` curly braces
stripped; if `/` present, the portion AFTER the first `/` is used when
non-empty (so `b/7225` -> `7225`).

EXACT raise sites (quoted, all `ValueError`):

- L26 `raise ValueError(f"raw must be str, got {type(raw).__name__}")` -- non-str input.
- L29 `raise ValueError("empty input")` -- empty / whitespace-only after strip.
- L34 `raise ValueError(f"empty curly-brace content: {raw!r}")` -- `{}` or `{ }`.
- L55 `raise ValueError(f"ambiguous {raw!r}: provide lang='hb' or lang='gk'")` -- bare `NNN<sp>L`, no lang.
- L63 same message -- bare `NNNL`, no lang.
- L71 same message -- bare `NNN`, no lang.
- **L74 `raise ValueError(f"unrecognized Strong's encoding: {raw!r}")`** -- THE confirmed class. Any token that matches NONE of the four regexes after pre-processing. This includes: anything over 5 digits (`zfill(4)` only pads, `\d{1,5}` caps at 5), digit-stripped compound Strongs (`15374053` from `1537+4053`), multi-letter or embedded-symbol tokens, `+`-joined crasis forms, garbage cells.

Conditions that CANNOT raise when lang is always supplied (every adapter call
passes `lang`/`"hb"`/`"gk"`): the three ambiguity raises L55/L63/L71 are
unreachable for adapter callers. The reachable raises for adapter callers are
L26 (non-str), L29 (empty), L34 (empty braces), and L74 (unrecognized,
including over-5-digit and compound). L74 is the live, thrice-confirmed one.

---

## 2. Per-call-site table

Scope: `ingest/`. No `canonical_strongs` call in `tools/`, `embeddings/`,
`pipeline2/`, or `run.py` (verified by repo-wide grep). `tests/` and
`.claude/worktrees/*` copies are OUT OF SCOPE for fixing (stale agent
worktrees / test harness; `tests/test_canonical_strongs.py` exercises the
raise behaviour deliberately and is not a reseed path). Nine real adapter
call sites total, listed in run.py DATASETS order.

| # run | file:line | function | raw source -> upstream field | guarded? | real-data can raise L74? evidence | verdict | faithful fix |
|---|---|---|---|---|---|---|---|
| 1 | ingest/lexical/oshb.py:450 | `_strong_segment` (`canonical, suffix = canonical_strongs(s, lang="hb")`) | OSHB `lemma`/`@lemma` segment after slash split; single-letter prefix codes pre-filtered (L447) | YES `try/except ValueError -> return None, None` (L449-452) | Guarded; OSHB lemma tokens are H-prefixed or bare digits, prefix codes filtered; any residual unrecognized -> None | SAFE | none (already faithful skip) |
| 2 | ingest/lexical/macula_hebrew.py:575 | `_canonical` (`return canonical_strongs(text, lang=lang)`) | `strongnumberx` / `greekstrong` attrs, pre-cleaned by `_clean` (None on blank) | YES `try/except ValueError -> None` (L574-577) | Guarded; cross-check confirms genuine SAFE | SAFE | none (reference faithful pattern) |
| 6 | **ingest/lexical/macula_greek.py:655** | `_row_lemma_payload` (`"strong": canonical_strongs(str(strong), "gk")[0]`) | `_coerce_strong(word["strong"])` int; upstream MACULA-Greek `strong` cell carries `+`-joined COMPOUND crasis Strongs digit-stripped to 8 digits | **NO -- uncaught at HEAD** (the b270a9c fix lives in worktree branch `worktree-agent-a574a379d97e4bec4`, NOT in HEAD ancestry; `git merge-base --is-ancestor b270a9c HEAD` = false) | **YES, confirmed real data.** 11 frozen-upstream rows (Nestle1904 6, SBLGNT 5): `1537+4053` ekperissos Mark 14:31; `5228+1537+4053` hyperekperissou Eph 3:20, 1Th 3:10, 1Th 5:13; `1501+5140` eikositreis 1Cor 10:8; `1417+3461` dismyrias Rev 9:16. `_coerce_strong` -> `15374053`, `canonical_strongs('15374053','gk')` raises L74 | **CRASH-RISK** | apply the b270a9c `_canonical_strong_or_none` pattern: `_row_lemma_payload` returns None on the unresolved path so the row emits NO GreekLemma and NO INSTANCE_OF; Word still writes (raw int Word.strong per Decision 2 unaffected); count `_unresolved_strong`; deterministic stderr; never raise. GreekLemma MERGEs on `id`, `.strong` is post-MERGE SET, so a skipped row creates no node: no collision, no null-in-MERGE. |
| 9 | ingest/lexical/stepbible_tahot.py:345 | `_normalize_strong` (`return canonical_strongs(s, "hb")[0]`) | dStrongs cell, brace + underscore stripped (L339-341) | YES `try/except ValueError -> ""` (L344-347) | Guarded; `""` triggers existing populated-projection row-drop (no fabricate, Decision 18) | SAFE | none |
| 10 | ingest/lexical/stepbible_tagnt.py:288 | `_strong_from_grammar` (`return canonical_strongs(raw, "gk")[0]`) | dStrongsGrammar before `=` | YES `try/except ValueError -> ""` (L287-290) | Guarded; `""` -> row-drop guard | SAFE | none |
| 11 | ingest/lexical/stepbible_ttesv.py:400 | `_canonical_for_book` (`canonical, _suffix = canonical_strongs(raw, lang=lang_hint)`) | `_split_strong_field` regex tokens, per-book lang inferred | YES `try/except ValueError -> None` (L399-402) | Guarded; None -> edge skipped; ttesv self-produces its own Lemma/GreekLemma id space (Decision 18 line 29, E1/E2, not required to change) | SAFE | none |
| 12 | ingest/lexical/stepbible_tbesh.py:367 | `_canonical_base_strong` (`return canonical_strongs(raw_base_strong, "hb")[0]`) | suffix-stripped base Strong | YES `try/except ValueError -> raw_base_strong` (L366-369) | Guarded; on raise returns the token unchanged (no fabricate, no canonical mint); will simply fail to match a Lemma -> LEX_FOR yields no edge, faithful | SAFE | none |
| 13 | ingest/lexical/stepbible_tbesg.py:449 | `_canonical_greek_strong` (`return canonical_strongs(raw_base_strong, "gk")[0]`) | BriefLexEntry.base_strong | YES `try/except ValueError -> None` (L448-451); caller `_merge_lex_for` skips LEX_FOR when None | Guarded; None -> no LEX_FOR edge, LsjEntry/BriefLex node still persists | SAFE | none |
| 14 | ingest/lexical/stepbible_tflsj.py:368 | `_canonical_greek_strong` (`return canonical_strongs(raw_strong, "gk")[0]`) | LSJ `strong` token | YES `try/except ValueError -> None` (L367-370); caller skips LEX_FOR, keeps LsjEntry | Guarded; None -> no LEX_FOR edge | SAFE | none |

DATASETS positions 2/3/4/5/7/8 (bhsa, etcbc_phono, etcbc_parallels, morphgnt,
stepbible_morph_codes) and 15+ have NO canonical_strongs call (verified).

---

## 3. Classification summary

- Total real adapter call sites: **9**.
- SAFE: **8** (oshb, macula_hebrew, stepbible_tahot, stepbible_tagnt,
  stepbible_ttesv, stepbible_tbesh, stepbible_tbesg, stepbible_tflsj).
- CRASH-RISK: **1** (macula_greek.py:655).

Cross-check requested:

- `macula_hebrew.py:575` `_canonical`: try/except ValueError -> None,
  pre-cleaned input. Genuinely **SAFE**.
- `macula_greek.py:655`: the b270a9c fix (`_canonical_strong_or_none`,
  `_row_lemma_payload` -> None, `_unresolved_strong` surface) IS NOT in HEAD.
  `git branch --contains b270a9c` shows only `worktree-agent-a574a379d97e4bec4`;
  `git merge-base --is-ancestor b270a9c HEAD` = NOT ancestor. At the audited
  HEAD (995d3b7) line 655 is the bare uncaught `canonical_strongs(str(strong),
  "gk")[0]`. **NOT SAFE at HEAD. CRASH-RISK.** The fix exists and is verified
  in its worktree; it must be brought into the relaunch-4 line (cherry-pick /
  merge b270a9c, or re-apply the identical single-file patch) before
  relaunch-4 reaches adapter #6, or relaunch-4 dies exactly as attempt 3 did.

---

## 4. DEFECT LEDGER (CRASH-RISK sites, one single-file fix each)

### DL-1 (the only open CRASH-RISK): macula_greek.py:655

- Site: `ingest/lexical/macula_greek.py`, `_row_lemma_payload`, line 655,
  `"strong": canonical_strongs(str(strong), "gk")[0]` (uncaught).
- Trigger on frozen upstream: 11 GreekLemma rows whose `strong` cell is a
  `+`-joined compound crasis/multi-stem Strong; `_coerce_strong` digit-strips
  to an 8-digit int; `canonical_strongs` raises L74 `unrecognized Strong's
  encoding: '15374053'`. Propagates uncaught through `_flush` ->
  `_process_edition` -> `ingest_macula_greek` -> run.py (no try/except) ->
  kills the entire reseed at DATASETS position 6.
- Faithful single-file fix (mirror macula_hebrew `_canonical` and the
  b270a9c `_canonical_strong_or_none` exactly; no second file, no
  schema/test/cypher change):
  1. Add `_canonical_strong_or_none(strong) -> str | None`: `try: return
     canonical_strongs(str(strong), "gk")[0] except ValueError: return None`.
  2. In `_row_lemma_payload`: compute `canon = _canonical_strong_or_none(strong)`;
     if `canon is None` return `None` (NO GreekLemma, NO INSTANCE_OF emitted
     for this row); else `"strong": canon`.
  3. Surface, never silent: count `_unresolved_strong` in the returned dict
     and emit a deterministic per-edition stderr line.
  4. Decision 18 line 644 forbids a hand-rolled compound `+`-split or
     first-component rule -- DO NOT add one. The skip is the faithful path.
- Why this is faithful and non-destructive: `GreekLemma` MERGEs on unique
  `id` (`<source>:strong-<int:05d>`); `.strong` is a post-MERGE SET attribute.
  A skipped row creates NO node, so no collision, no duplicate, no
  null-in-MERGE, no node-identity change. Word still writes with every
  property; raw int `Word.strong` (Decision 2) is untouched. Only the 11
  genuinely unresolvable GreekLemma rows lose their node + INSTANCE_OF, which
  is exactly the Decision 18 line 13 no-Strong skip.
- Owning caste: implementer-impl (single-file ingest adapter fix).
- Authorization: Decision 18 line 13 + line 52 expressly sanction the skip
  ("MUST NOT fabricate a Strong ... skips the Strong attachment"). NO
  MUST-ESCALATE: no SCHEMA_DECISION is violated by the skip; the schema
  mandates it. (b270a9c proved ValueError_escaped=0, 275520/275520 Words
  persisted, INSTANCE_OF=275509=275520-11, over frozen upstream.)

No other open CRASH-RISK sites: the other 8 are already guarded with the
faithful try/except pattern (verified line by line in section 2).

---

## 5. FIX WAVE for relaunch-4 (parallel-safe, one task per file)

Only one file needs a change for THIS class. The wave is a single task.

| task | file (single touch) | owning caste | action | parallel-safe |
|---|---|---|---|---|
| FW-1 | ingest/lexical/macula_greek.py | implementer-impl | Bring the b270a9c fix into the relaunch-4 line: cherry-pick/merge commit b270a9c, OR re-apply the identical single-file `_canonical_strong_or_none` + `_row_lemma_payload`-returns-None + `_unresolved_strong` patch. Verify `ValueError` cannot escape `ingest_macula_greek` over frozen MACULA-Greek upstream. | YES (no other file shares this defect; touches one adapter only) |

Sequencing for the orchestrator: macula_greek is DATASETS position 6.
Relaunch-4 will reach it AFTER oshb(1), macula_hebrew(2), bhsa(3),
etcbc_phono(4), etcbc_parallels(5). All five preceding adapters are
class-clean (oshb and macula_hebrew guarded; bhsa/etcbc have no
canonical_strongs call). With FW-1 applied, the next canonicalizing adapters
(tahot 9, tagnt 10, ttesv 11, tbesh 12, tbesg 13, tflsj 14) are ALL already
guarded, so relaunch-4 has zero remaining serial crash points in this class.

---

## Final ledger

- canonical_strongs raise conditions: non-str (L26), empty/whitespace (L29),
  empty curly braces (L34), ambiguous-no-lang (L55/L63/L71, unreachable for
  adapter callers since all pass lang), and THE class -- unrecognized
  encoding L74 (any non-matching token: over-5-digit, `+`-joined compound
  crasis, embedded symbols, garbage). No sentinel; failure is ValueError only.
- Total real adapter call sites: 9. SAFE: 8. CRASH-RISK: 1.
- CRASH-RISK list, run.py DATASETS order (the orchestrator's crash order):
  - position 6 -- `ingest/lexical/macula_greek.py:655`,
    `_row_lemma_payload`. Faithful skip: add `_canonical_strong_or_none`
    (try/except ValueError -> None), return None from `_row_lemma_payload`
    on unresolved so NO GreekLemma and NO INSTANCE_OF emit, Word still
    writes, count + stderr `_unresolved_strong`, never raise, never split,
    never fabricate. (Fix already authored as b270a9c but NOT in HEAD
    ancestry -- it must be merged/re-applied into relaunch-4.)
- macula_greek b270a9c: SAFE *as a commit/in its worktree* but **NOT
  applied at HEAD 995d3b7** -> macula_greek is CRASH-RISK on the audited
  branch until b270a9c is brought in. macula_hebrew (`_canonical`,
  try/except ValueError -> None): verified genuinely SAFE.
- canonical_strongs non-raising helper: NOT recommended as a library
  change. Decision 18 line 13 already names per-caller skip-or-sentinel as
  the contract and line 644 forbids hand-rolled normalisation. The faithful
  pattern is the per-caller `try/except ValueError -> adapter no-Strong
  path`, already the standard in 8 of 9 sites and in the b270a9c fix. Adding
  a sentinel-returning helper would invite silent swallowing and is not
  sanctioned by Decision 18; keep raising, keep catching per caller.
- MUST-ESCALATE: none. The Decision-18 skip is explicitly authorized by
  SCHEMA_DECISIONS.md Decision 18 lines 13 and 52; no schema decision is
  violated by the faithful skip.
