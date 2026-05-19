# Phase F Question ID Map (G3 resolution)

Auditor caste. Read-only faithful mapping. No em or en dashes. Brethren-on-trial:
the question bank is mapped verbatim, nothing invented. This document binds the
three RESEED_PLAN F.1 doctrinal targets
(`doc-canon-closed`, `baptism-mode`, `lords-supper-real-presence`) to the REAL
ids that exist in `questions.json` (231-entry universal bank, `$schema_version`
2.0). Phase F.1's five source-completeness invariants (word, lemma, cross-ref,
variant, syntax) traverse each chosen question's `scripture_anchors` per OSIS
ref, so every chosen id is confirmed below to carry a non-empty
`scripture_anchors` list.

Schema basis (`questions.json` field_definitions, lines 43-53;
`docs/EVIDENCE_SCHEMA.md`): `id` is a stable kebab-case slug;
`scripture_anchors` are the seed passages the inferred-baseline subagents
spider-map via concordance traversal. F.1 invariants run per anchor osisID.

---

## Mapping table

| Doctrinal target (RESEED_PLAN F.1) | Chosen questions.json id(s) | Verbatim or mapped | Question statement | scripture_anchors | Decisive textual evidence |
|---|---|---|---|---|---|
| `doc-canon-closed` | `doc-canon-closed` | VERBATIM (line 95) | "No revelation given after the apostolic age stands on par with Scripture or adds to the rule of faith." | Hebrews 1:1-2; Ephesians 2:20; Jude 1:3; Revelation 22:18-19; Galatians 1:8-9; 2 Timothy 3:16-17 | Exact id present verbatim in `questions.json`. Statement is precisely canon-closure. 6 non-empty anchors. No ambiguity. |
| `baptism-mode` | `prc-baptism-by-immersion` | MAPPED (line 2216; not verbatim) | "Baptism is administered by full immersion as a public confession of faith and identification with Christ's death, burial, and resurrection." | Romans 6:3-4; Colossians 2:12; Acts 8:36-38 | The target word "mode" denotes the manner of administration. Only this entry's statement is about the MODE itself ("administered by full immersion"). Its anchors (Rom 6:3-4 burial/resurrection identification, Col 2:12 buried with him in baptism) are the classic mode proof-texts. The subject-side entries (`prc-believers-baptism-only`, `doc-baptism-faith-precedes`, `doc-paedobaptism-not-warranted`) address WHO is baptized, not the mode. Single faithful canonical id; matches spec G3 recommendation. 3 non-empty anchors. |
| `lords-supper-real-presence` | `doc-transubstantiation-denial` (primary) | MAPPED (line 2156; not verbatim) | "The bread and wine in the Lord's Supper are not, in substance, changed into Christ's body and blood at the words of institution; the elements remain bread and wine while signifying and (under some accounts) communicating Christ's body and blood spiritually." | Hebrews 7:27; Hebrews 9:12; Hebrews 10:10-14; Acts 1:9-11; John 6:63 | This is the one entry whose proposition IS the real-presence question (substance change at the words of institution). It directly answers transubstantiation vs memorial. 5 non-empty anchors. BUT the real-presence doctrine is carried by a cluster, not a single id. See MUST-ESCALATE below. |

---

## MUST-ESCALATE: `lords-supper-real-presence` is a genuine cluster

There is no single `questions.json` id equal to "lords-supper-real-presence".
The doctrine (real presence / transubstantiation vs memorial in the Lord's
Supper) is split across several real entries. The auditor does NOT silently
collapse them. Ranked candidates with evidence (owner/orchestrator picks the
canonical slot before F1 runs):

1. **`doc-transubstantiation-denial`** (line 2156). MOST FAITHFUL single id.
   Statement directly negates the substantial change of the elements, which is
   the precise real-presence proposition. Anchors: Hebrews 7:27, Hebrews 9:12,
   Hebrews 10:10-14, Acts 1:9-11, John 6:63 (non-empty). Recommended canonical
   pick (matches spec G3 recommendation).
2. **`doc-consubstantiation-affirm`** (line 2234). The Lutheran bodily real
   presence proposition ("Christ is bodily present in, with, and under the
   bread and wine"). The affirmative real-presence pole. Anchors: Acts 1:9-11,
   Luke 24:39, John 6:63, 1 Corinthians 11:23-26 (non-empty). Pick this only if
   the owner wants the affirmative-presence framing rather than the denial.
3. **`doc-supper-as-memorial`** (line 2079). The memorial pole opposite real
   presence ("primarily a memorial ... do this in remembrance of me"). Anchors:
   Luke 22:19, 1 Corinthians 11:23-26, Hebrews 10:10-14 (non-empty). Picks the
   memorial side of the same axis.
4. **`doc-supper-spiritual-communion`** (line 2097). Spiritual feeding by faith,
   "distinguishing the position from bare Zwinglian memorialism." The
   Calvinist-pneumatic-presence middle. Anchors: 1 Corinthians 10:16-17,
   John 6:53-58, John 6:63 (non-empty). Named in spec G3 as part of the cluster.
5. **`doc-ubiquity-of-christs-body`** (line 2253). Adjacent (the Lutheran
   ubiquity premise behind consubstantiation), not the presence question
   itself. Anchors: Acts 1:9-11, Luke 24:39, John 6:63,
   1 Corinthians 11:23-26 (non-empty). Lowest priority; supporting, not central.

Decisive evidence for the ranking: candidate 1's statement is the only one
whose proposition is literally "the elements are not substantially changed,"
i.e., the real-presence question stated negatively, so it is the single most
faithful slot if the owner wants exactly one id. Candidates 2-4 are the other
poles of the same doctrinal axis and would be the faithful pick only if the
owner wants the affirmative, memorial, or spiritual-communion framing
respectively. This is a genuine ambiguity of WHICH POLE, not a missing id;
hence MUST-ESCALATE rather than a silent single pick.

For `baptism-mode` there is also a near-neighbor worth recording (NOT escalated,
the primary pick is unambiguous on the word "mode"): `prc-believers-baptism-only`
(line 2196, "Baptism is for professing believers only ... faith precedes
baptism", anchors Acts 2:38, Acts 8:36-38, Acts 16:31-33, Matthew 28:19,
Mark 16:16). If the owner reads "baptism-mode" as subjects rather than manner,
this is the alternate. The literal word "mode" decides for
`prc-baptism-by-immersion`; recorded here for transparency only.

---

## scripture_anchors non-empty confirmation (F.1 prerequisite)

F.1 invariants (word / lemma+property / cross-ref / variant / syntax
completeness) run per anchor osisID; an empty anchor list would make F.1
vacuous. Confirmed non-empty for every chosen id:

| Chosen id | scripture_anchors count | Anchors |
|---|---|---|
| `doc-canon-closed` | 6 | Hebrews 1:1-2; Ephesians 2:20; Jude 1:3; Revelation 22:18-19; Galatians 1:8-9; 2 Timothy 3:16-17 |
| `prc-baptism-by-immersion` | 3 | Romans 6:3-4; Colossians 2:12; Acts 8:36-38 |
| `doc-transubstantiation-denial` | 5 | Hebrews 7:27; Hebrews 9:12; Hebrews 10:10-14; Acts 1:9-11; John 6:63 |

All three are non-empty. None of the chosen anchors falls inside the 3 John ECM
scope (F.1 invariant 4 variant-completeness will exercise its empty-set half for
every anchor here, consistent with spec gap G4).

---

## Summary for the orchestrator

- `doc-canon-closed`: VERBATIM, bind directly. No decision needed.
- `baptism-mode`: MAPPED to `prc-baptism-by-immersion` (single faithful id;
  decided by the literal word "mode" = manner of administration). Owner only
  needs to confirm if "mode" was intended as subjects, in which case use
  `prc-believers-baptism-only`.
- `lords-supper-real-presence`: MUST-ESCALATE. No verbatim id; genuine
  multi-pole cluster. Recommended canonical pick `doc-transubstantiation-denial`,
  but the owner must choose the pole (denial vs consubstantiation-affirm vs
  memorial vs spiritual-communion). The auditor does not pick silently.

Phase F.1 must not run until the owner binds the `lords-supper-real-presence`
slot. The other two are auditor-resolvable as stated. This document is the F0
artifact; it gates F1 running against real questions.
