# Handover Prompt for Deriving the Source-Inferred `baseline.json`

> Paste this entire document into a fresh Claude Code session at the project root
> (`e:\projects-working-dir\brethren-doctrine`). The receiving model is the
> **orchestrator**; it spawns one subagent per question via `tools/baseline_orchestrator.py`.

---

## Mission

Derive a **tradition-neutral lexical-philological baseline** for the 231 questions in
[questions.json](../questions.json), producing `baseline.json` and per-question
audit trails in `evidence/<id>.json`. The baseline is the original-language exegetical
floor that all eight major lineages (Eastern Orthodox, Catholic, Lutheran, Anglican,
Reformed, Methodist, Anabaptist, Pentecostal) can audit, prior to any single
tradition's confessional commitment.

Each verdict is settled by **apparatus + interlinear + concordance**. Counter-witness
traditions are recorded as **diagnostic information** for the reader, showing how
each lineage reads the same lexical text. They do not vote on `affirms`,
`cult_marker_if_denied`, `would_die_for`, or `confidence`. Confessions
(Reformed-Baptist, Reformed paedobaptist, Catholic, Orthodox, Lutheran, Anglican,
Anabaptist) are NOT in the baseline as authority; they are recorded as
`counter_witness[]` entries.

Brethren-adjacent teaching notes (`source-docs/`, `parsed/`) are **not consulted at
all** during baseline derivation. They are respondent material that lives in
`responses/<id>.json` files contributed by the specific church or elder who affirms
them, including Ebenezer himself when he fills out his own questionnaire.

This baseline run is autofill drudge-work for a community questionnaire round.
Trusted-elder collaborators correct and refine it; the consolidated baseline
downstream is used to evaluate potential churches Ebenezer is considering visiting
or joining. See [docs/QUESTION_SCHEMA.md](../docs/QUESTION_SCHEMA.md) for the
question bank shape and [docs/ANSWER_SCHEMA.md](../docs/ANSWER_SCHEMA.md) for the
locked answer + evidence shape.

### The three pillars

Every question runs through three pillars, in this order:

| # | Pillar | Source | Purpose |
|---|---|---|---|
| 1 | **Concordance** | TAHOT + TAGNT lemma index, OSHB Hebrew morphology, OpenBible + TSK cross-references via Neo4j Cypher (see [CONCORDANCE.md](../docs/CONCORDANCE.md)) | Mechanical `analogia scripturae`. Every Strong's lemma in the anchor verses is spider-mapped to every occurrence in the canon. Selection bias dies at the data layer. |
| 2 | **Hermeneutics** | Recorded per verdict in `evidence.hermeneutics` (see [HERMENEUTICS.md](../docs/HERMENEUTICS.md)) | Interpretive lens, frameworks in play, figures of speech, genre, competing-lens verdicts. Forces the subagent to surface *how* the verdict was reached, not just *what* it concluded. |
| 3 | **Counter-witness** | Patristic, Catholic magisterial, Lutheran, Anglican, Anabaptist, Methodist, Pentecostal, Reformed, Eastern Orthodox primary sources via web fetch (see Method Step 6) | Diagnostic information for the reader showing how each major lineage reads the same lexical text. Encouraged for diagnostic completeness on every question. Does NOT vote on `affirms`, `cult_marker_if_denied`, `would_die_for`, or `confidence`. |

### The bar

`apparatus + interlinear + concordance` settle every verdict. Confessions never
override Scripture. Counter-witness traditions are diagnostic information about
how each lineage reads the same text; they do not vote on any verdict field.

**Cult-marker bar requires two conditions, both canonical:**

1. **Moral entailment**: `would_die_for=true`. Denial means denial of the gospel
   itself or a core Trinitarian or Christological boundary clearly mandated by
   Scripture's own lexical pattern, not by a council or confession's settlement.
2. **Canonical demonstration from Scripture**: apparatus + interlinear yield an
   unambiguous lexical reading affirming the doctrine, AND concordance demonstrates
   the doctrine across the canon (not from a single passage). The Bible itself
   does the work.

**Lineage agreement does NOT grant or withhold cult-marker status.** If apparatus
plus interlinear plus concordance unambiguously affirm a doctrine and denial
constitutes denial of the gospel, the cult-marker stands regardless of how many
historical traditions happen to confess it in those exact terms. Conversely,
unanimous lineage agreement on a doctrine that lacks unambiguous canonical
demonstration does NOT clear the bar.

**The Brethren-on-trial discipline is preserved through canonical demonstration.**
Most Brethren distinctives (eldership polity, weekly breaking of bread, baptism
mode, dispensational hermeneutics) lack unambiguous pan-canonical lexical support
and will fail condition 2 honestly. The discipline is the canon itself, not
ecumenical vote-counting.

**Even Trinity is not exempt.** Each question, including the Nicene-Chalcedonian
foundations (Trinity, full deity and humanity of Christ, bodily resurrection,
Scripture as inspired and authoritative), clears or fails this bar on its own
per-question canonical evidence. The whole canon is examined for every claim.

### Hard rules

1. **Apparatus + interlinear + concordance settle. Nothing else does.**
2. **Concordance traversal is mandatory on every question, every tier.**
   `evidence.concordance_lemmas_traversed: []` is a hard validation failure.
3. **Counter-witness is encouraged for diagnostic completeness** on every question,
   so the reader sees how each major lineage reads the same text. Missing
   counter-witness flags `counter-witness-missing` for research-quality tracking
   only. It does NOT shift `affirms`, `cult_marker_if_denied`, `would_die_for`,
   or `confidence`. Lexical clarity in Scripture, not lineage agreement, drives
   every verdict field.
4. **Selection-bias check is mandatory.** A `scripture[]` array with all
   `supports="for"` AND `complicating_texts_searched=true` AND `flags` containing
   `no-complicating-texts-after-search` is honest; the same array without that flag
   is a smell.
5. **Question-stem hygiene.** If `question.statement` names heretics, asserts the
   verdict, or uses Reformed-confessional vocabulary as if neutral, work the
   *neutralized form* and record the original in `evidence.stem_audit`.
6. **NO confessions in the baseline as authority.** WCF, 1689 LBC, Brethren Archive,
   Westminster Standards, Heidelberg, Belgic, Savoy, all recorded as
   `counter_witness[]` entries with `tradition` tagged appropriately, never as the
   voice settling a verdict.
7. **NO Brethren teaching notes in baseline derivation.** The `source-docs/` and
   `parsed/` directories are respondent material, not baseline input. Do NOT call
   the retrieval CLI from a baseline subagent.
8. **NO Reformed-aligned commentary sites as authority.** carm.org, equip.org,
   gotquestions.org, monergism.com, ligonier.org, thegospelcoalition.org are
   forbidden. They share the formation-under-examination's substrate.

You (the orchestrator) act as a brain. You spawn agents, you don't research. You
only intervene when:

- An agent reports the apparatus reading and the counter-witness panel diverge sharply.
- An agent returns `affirms=null` AND `would_die_for=true` (gospel-stake question with uncertain verdict).
- ≥5 agents flag the same cross-cutting issue.
- An agent flags `stem-pre-loaded-verdict`, the question itself needs a phase-3 rewrite.

Otherwise, run autonomously.

---

## User context (carry into every subagent prompt)

- **Owner**: Ebenezer Isaac.
- **Owner's formation**: Plymouth Brethren-adjacent (India). **This formation is the
  position under examination, not the rubric.** The whole point is to test whether
  the Brethren reading survives primary-source scrutiny. Do not calibrate to
  Brethren or Reformed-Protestant orthodoxy. Calibrate to apparatus + interlinear +
  concordance. Counter-witness traditions are recorded as diagnostic information
  for the reader; they do not adjudicate.
- **Faith stage**: Stage 3 (which denomination is right). Calibrating discernment,
  not scoring churches.
- **Authority hierarchy**: Critical Apparatus → Interlinear → Formal translation →
  Dynamic translation → Application. Confessions are NOT a tier; they are an
  information layer recorded as `counter_witness[]`. See
  [AUTHORITY_HIERARCHY.md](../docs/AUTHORITY_HIERARCHY.md).
- **Anonymization rule**: only "Ebenezer" may appear in any output. Every other
  personal name must be `[REDACTED]` in any quoted excerpt.
- **Discernment principle**: gospel-stake errors (`would_die_for=true` cases)
  break fellowship absolutely; methodological or preference differences MUST
  NOT outweigh demonstrable Christian fruit. Standing is inferred from the
  answer's boolean pattern, not from a pre-assigned tier on the question.

---

## Inputs

| Path | What it is | How subagents use it |
|---|---|---|
| `questions.json` | 231 questions under `.questions` | Source of truth; shape locked in [QUESTION_SCHEMA.md](../docs/QUESTION_SCHEMA.md) |
| Neo4j (concordance graph) | TAHOT + TAGNT + OSHB + OpenBible + TSK ingested | Spider-map traversal via Cypher; see [CONCORDANCE.md](../docs/CONCORDANCE.md) |
| `docs/ANSWER_SCHEMA.md` | Locked answer + evidence shape | Subagents emit JSON conforming to this exactly |

`source-docs/`, `parsed/`, `retrieval/` are **NOT inputs to baseline derivation.**

---

## Outputs

1. **`baseline.json`**: envelope per [ANSWER_SCHEMA.md](../docs/ANSWER_SCHEMA.md):
   ```json
   {
     "$schema_version": "1.0",
     "viewpoint": "inferred-from-sources",
     "generated_at": "<ISO date>",
     "answers": [ <Answer×231> ]
   }
   ```
   Each Answer is exactly the 13 fields in ANSWER_SCHEMA.md. No extra fields.

2. **`evidence/<id>.json`**: one file per question, audit trail per
   ANSWER_SCHEMA.md `evidence` shape. This directory IS the evidence record.

3. **`baseline-report.md`**: human-readable run summary:
   - `affirms` distribution (true / false / null counts).
   - Top flag categories with counts.
   - Per-standing breakdown of `affirms` and `engagement_score` distributions
     (standing inferred from each answer's boolean pattern per ANSWER_SCHEMA.md).
   - List of `confidence=low` questions where `would_die_for=true` for
     trusted-elder review priority.
   - Counter-witness coverage stats (gospel-stake questions with ≥1 vs missing).
   - Concordance traversal stats (avg lemmas traversed per question, distribution).

4. **`baseline-conflicts.md`**: manual-review report listing every question where
   `apparatus-vs-counter-witness-conflict`, `confession-tradition-divergence` (kin
   confessions disagree), `stem-pre-loaded-verdict`, or `counter-witness-missing`
   fired. Includes relevant excerpts. Ebenezer resolves manually.

5. **`stem-audit.md`**: every `stem-pre-loaded-verdict` flag, original stem,
   neutralized form, and notes. Used to revise `questions.json` in phase 3
   separately.

PDF rendering is not part of this run; runs separately via
[tools/evidence_to_pdf.py](../tools/evidence_to_pdf.py) after the orchestrator
completes.

---

## Per-question subagent template

Spawn ONE subagent per question. Each writes to `evidence/<id>.json`. **Default
model: Opus 4.7.** The synthesis step (apparatus + concordance + counter-witness
+ hermeneutic lens) genuinely benefits from Opus reasoning quality on:
1. **Synthesis when evidence conflicts** (apparatus says X, concordance shows
   complicating texts, counter-witness traditions diverge, Sonnet picks the
   obvious answer; Opus surfaces the tension in `notes` and `competing_lens_verdicts`).
2. **K2 cult-marker bar enforcement** (Sonnet rubber-stamps "essentials I expect
   to be cult-grade" like Trinity; Opus actually checks whether canonical
   demonstration clears, surfacing single-passage or lexically-ambiguous
   doctrines that should NOT carry `cult_marker_if_denied=true` regardless of
   how the agent's intuition frames them).
3. **Brethren-on-trial discipline** (Sonnet drifts back toward Brethren-comfortable
   readings under stress; Opus holds the line when the lexical evidence cuts
   against the formation).

The project produces a baseline referenced indefinitely; "cannot afford to
re-run" tilts toward Opus on the first pass even at the cost of more rate-limit
windows.

**Execution model: Claude Max subscription, Opus 4.7.** Opus has tighter 5-hour
rolling-window rate limits than Sonnet. Plan for the full 231-question run to
span **multiple days** rather than hours. The resume gate makes interruptions
safe; just re-invoke the orchestrator and it skips already-completed evidence
files.

Concurrency cap on Opus: **2-3 active subagents at a time** (NOT 5). Idle
10-15 minutes between every ~15 completions to let the rate-limit bucket
recover. If a rate-limit error fires, back off **30 minutes** before retrying
that single id (longer than Sonnet's 15).

### Subagent task prompt

```
You are deriving a tradition-neutral lexical-philological baseline answer for ONE
question. The owner is formed in Plymouth Brethren-adjacent tradition; THAT
FORMATION IS ON TRIAL, NOT THE RUBRIC. Calibrate to apparatus + interlinear +
concordance. Counter-witness traditions are recorded as diagnostic information
for the reader showing how each lineage reads the same lexical text; they do
NOT vote on `affirms`, `cult_marker_if_denied`, `would_die_for`, or `confidence`.
Do NOT calibrate to Brethren or Reformed-Protestant orthodoxy.

This answer is a SEED for community-questionnaire input. Be honest about
uncertainty so trusted-elder reviewers know what to scrutinize.

## Authority order (strict)

1. Critical apparatus (BHS, NA28/UBS5): the only authority that settles a verdict.
   Cite footnote IDs / variant readings where retrievable.
2. Interlinear (Hebrew/Greek lemma + morphology): closest accessible representation
   when the apparatus is paywalled. Use STEPBible (https://www.stepbible.org),
   BibleHub interlinear (https://biblehub.com/interlinear/), OSHB
   (https://hb.openscriptures.org).
3. Concordance (mandatory traversal, all tiers): Strong's lemma → all-occurrences
   spider-map via Neo4j Cypher. See CONCORDANCE.md.
4. Hermeneutic classification (mandatory): primary method, frameworks in play,
   figures of speech, genre per scripture citation. See HERMENEUTICS.md.
5. Counter-witness traditions (encouraged for diagnostic completeness on every
   question): patristic, Catholic, Lutheran, Anglican, Anabaptist, Methodist,
   Pentecostal, Reformed, Eastern Orthodox primary sources. Web fetch primary
   URLs only. They are recorded for the reader's information; they do not vote
   on any verdict field.

Confessions never override apparatus + interlinear. Defendant teaching notes
(source-docs/, parsed/) are NOT in this run.

## Anonymization (relaxed for the baseline pipeline)

The strict redaction rule applies to `parsed/` (private sermon corpus), which
this pipeline DOES NOT consult. The baseline pipeline only touches public
sources. Use real names freely:

- **External published authors** (Athanasius, Augustine, Aquinas, Calvin, Wesley,
  Lossky, Bavinck, Berkhof, etc.): RETAIN. They are the citation chain.
- **Public confession authors / institutions** (Westminster Assembly, Council
  of Nicaea, Catechism of the Catholic Church, Mennonite Confession of
  Dordrecht): RETAIN.
- **Public-record heresy / cult founders** (Joseph Smith, Charles Russell,
  Ellen White, William Branham, Felix Manalo, Sun Myung Moon, etc.): RETAIN
  where discussed in `notes`. They are public figures.
- **Public denominations and movements** (Unitarian Universalists, Christadelphians,
  Mormons, Jehovah's Witnesses, Iglesia ni Cristo, Oneness Pentecostals, etc.):
  RETAIN.
- **Private-corpus contributors** (Ebenezer's personal teachers from `parsed/`):
  REDACT if they appear (they shouldn't, the baseline pipeline doesn't read
  parsed/ at all).

Do NOT over-redact. "[REDACTED]'s abridgement of the 39 Articles" should be
"Wesley's abridgement". "[REDACTED]-Universalists" should be "Unitarian
Universalists". The point of the rule is privacy for Ebenezer's private
contributors, not pseudonymizing public theological history.

## Question
<paste the full question object from questions.json>

## Method (in order, DO NOT SKIP STEPS)

### Step 1: Stem audit (FIRST)

Read `question.statement`. Flag if any of:
- It names specific heretics or "cult-grade" carriers as part of the statement
  (verdict embedded in the prompt).
- It asserts the answer rather than posing the proposition.
- It uses Reformed-confessional vocabulary as if neutral (e.g. "sola fide",
  "cult-grade", "heterodox" inside the statement).

If flagged: populate `evidence.stem_audit`:
- verdict_preloaded: true
- neutralized_form: "<rewritten as a neutral proposition or interrogative>"
- notes: "<which clause was loaded>"
Then work the NEUTRALIZED form. Add flag `stem-pre-loaded-verdict`.
Otherwise: verdict_preloaded: false, neutralized_form: null.

### Step 2: Apparatus + interlinear pass

For each `scripture_anchors` entry:
- Read in context (one chapter minimum).
- For each load-bearing Hebrew/Greek term, fetch the interlinear. Cite lemma +
  transliteration + Strong's number + lexical force in one line.
- If a critical-apparatus footnote bears on the question (NET Bible translator
  notes, STEPBible apparatus, ccat.sas.upenn.edu Tov readings), cite it.
  If paywalled, flag `apparatus-paywalled`; do not block.
- Identify each citation's `genre` (narrative, epistle, prophecy, wisdom,
  apocalyptic, gospel, law, psalm, parable) and `figures` ([] if literal).
- Note per anchor: "for" | "against" | "complicates" | "neutral".

### Step 3: Concordance traversal (MANDATORY, every tier)

For every doctrinally salient Strong's lemma identified in Step 2, run:

  MATCH (l:Lemma {strongs: $strongs})<-[:HAS_LEMMA]-(t:Token)-[:OCCURS_IN]->(v:Verse)
  RETURN v.verse_osis, count(t) ORDER BY v.book_osis, v.chapter, v.verse

Inspect the occurrence list. Identify uses of the same lemma in passages NOT
in `scripture_anchors` that complicate or qualify the verdict. Add at least one
to `scripture[]` if any are doctrinally relevant.

For at least one anchor verse, also run the full spider-map (Pattern C in
CONCORDANCE.md), verses sharing ≥1 lemma + cross-references. Surface
canonical-context verses missed by the seed anchors.

Record EVERY Strong's number you fed into the spider-map in
`evidence.concordance_lemmas_traversed[]`. An empty array is a hard
validation failure regardless of tier.

If Neo4j is unavailable, fall back to BibleHub's concordance
(https://biblehub.com/strongs/<g_or_h>/<number>.htm) and flag
`concordance-via-biblehub-fallback`.

### Step 4: Hermeneutic classification (MANDATORY)

Populate `evidence.hermeneutics`:
- primary_method: grammatico-historical (default), redemptive-historical,
  quadriga, patristic-typological, or accommodation
- frameworks_in_play: any of covenant_theology, dispensationalism,
  new_covenant_theology, progressive_covenantalism, historic_premillennialism
  that produce different verdicts on this question
- analogia_scripturae_invoked: bool (true if the verdict rests on Scripture
  interpreting Scripture via concordance)
- progressive_revelation_factor: bool
- competing_lens_verdicts[]: mandatory if frameworks_in_play.length > 1
  (tier-gating removed; tier abolished from questions.json)
- notes: short narrative on hermeneutic commitments required

If the verdict requires dispensational hermeneutics (pre-trib rapture,
Israel and church distinction, literal millennium tied to ethnic Israel), add
flag `dispensational-lens-required`. The flag notes for the reader that this
verdict requires a non-default hermeneutic; it does NOT demote the verdict.
Verdict stands or falls on apparatus plus interlinear plus concordance.

### Step 5: Complicating-text search (MANDATORY)

Independent of `scripture_anchors`. Ask: "What passages might complicate the
verdict if the formation's reading is wrong?" Examples:
- Omnipotence/immutability/omniscience/impassibility/sovereignty ⇒
  Gen 6:6 (anthropopathism), Ex 32:14, 1 Sam 15:11, Jonah 3:10, Jer 18:8
- Eternal security ⇒ Heb 6:4-6, 10:26-31, 2 Pet 2:20-22
- Cessation of sign gifts ⇒ Acts 21:9, 1 Cor 14, Joel 2 / Acts 2 telos
- Baptism mode ⇒ household baptisms (Acts 16:33, 1 Cor 1:16) on credo side;
  pour/sprinkle imagery (Ezek 36:25, Heb 10:22) on paedo side

Set complicating_texts_searched: true regardless of whether any were found.
If none applicable after dedicated search, add flag
`no-complicating-texts-after-search`.

For omnipotence-class questions (catalogued in tools/verify_catalogs.json
H5), at least one anthropomorphic / anthropopathic citation MUST appear in
scripture[] with figures including 'anthropomorphism' or 'anthropopathism'.
Otherwise add flag `anthropomorphic-passages-omitted` and lower confidence.

### Step 6: Counter-witness pass (encouraged for diagnostic completeness)

Pull at least ONE primary-source statement from each of as many tracked
lineages as possible. Counter-witness is RESEARCH AID and DIAGNOSTIC
information for the reader, showing how each lineage reads the same lexical
text. It does NOT vote on `affirms`, `cult_marker_if_denied`, `would_die_for`,
or `confidence`. Encouraged on every question for completeness; missing
counter-witness flags `counter-witness-missing` for research-quality tracking
only. Required entry points:

- Patristic (Eastern Orthodox lineage): https://ccel.org/fathers (Schaff
  Ante-Nicene / Nicene & Post-Nicene Fathers, NPNF Series 1 & 2)
- Catholic magisterial: https://www.vatican.va/archive/ENG0015/_INDEX.HTM
  (Catechism of the Catholic Church); Dei Verbum at
  https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/
  vat-ii_const_19651118_dei-verbum_en.html
- Lutheran: https://bookofconcord.org (Augsburg, Apology, Smalcald, Treatise,
  Small/Large Catechism, Formula of Concord)
- Anglican: https://www.churchofengland.org/prayer-and-worship/worship-texts-and
  -resources/book-common-prayer/articles-religion (39 Articles)
- Reformed: confessional standards (Westminster Confession, Heidelberg, Belgic,
  Savoy), recorded as `tradition: "reformed"`
- Methodist: https://www.umc.org/en/content/articles-of-religion
- Anabaptist: Schleitheim Confession 1527, https://courses.washington.edu/
  hist112/SCHLEITHEIM%20CONFESSION%20OF%20FAITH.htm
- Continuationist/Pentecostal: https://ag.org/Beliefs/Statement-of-Fundamental
  -Truths (AG Fundamental Truths)
- Eastern Orthodox: https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine
  -scripture (OCA Orthodox Faith)

For each primary source consulted, record under `evidence.counter_witness[]`:
tradition, anchor, verified (true if you read primary text), stance
(affirms|denies|complicates), key_phrase (≤200 chars).

If zero counter-witness can be surfaced in good faith on any tier, flag
`counter-witness-missing` for research-quality tracking. Confidence is NOT
lowered; it reflects how clearly Scripture answers the question, not how
much primary-source corroboration the agent could reach.

### Step 7: Web pass, primary repositories only

Allowed sources only:
- BibleHub interlinear/strongs/concordance (biblehub.com)
- STEPBible (stepbible.org)
- OSHB / WLC (hb.openscriptures.org)
- ccel.org (Schaff Patristics)
- vatican.va (Catholic magisterial)
- bookofconcord.org (Lutheran primary)
- churchofengland.org (39 Articles)
- ag.org (AG Fundamental Truths)
- umc.org (Methodist Articles)
- oca.org (Orthodox)
- bookofconcord.org and equivalents
- openbible.info (cross-references)

FORBIDDEN as authority:
- carm.org, equip.org (Reformed-orthodox polemics, same substrate)
- gotquestions.org
- monergism.com, ligonier.org, thegospelcoalition.org as authority (these are
  Reformed commentary, not primary; only allowed if quoting a primary source
  they reproduce, in which case cite the primary source URL directly).
- brethrenarchive.org as authority in baseline (it would be defendant material;
  excluded from baseline derivation entirely).

Record under `evidence.web[]`: url, category (primary_repository | magisterial
| patristic_archive | tradition_primary | interlinear | critical_apparatus),
stance, quote (≤200 chars).

### Step 8: Lay summary (MANDATORY, reader-facing, TWO separate paragraphs)

After the technical work, write TWO plain-English paragraphs in
`evidence.lay_summary`. The reader is a layperson. The two paragraphs are
deliberately separated to keep Scripture-based reasoning from being conflated
with denominational landscape. Each is capped at 500 words; each must be at
least 100 chars; both are MANDATORY; the validator enforces all of this.

#### `lay_summary.reasoning` (Scripture-based verdict justification)

Plain English. Required structure:

1. **State the verdict** in everyday language (no Greek, no Strong's, no
   theological jargon).
2. **The strongest reason FOR it** from Scripture, named-verse plain words.
3. **The strongest counterargument** from Scripture's own complicating texts,
   named-verse plain words (e.g., "Critics point to Mark 13:32 where Jesus
   says he doesn't know the hour, or to Acts 21:9 where Philip's daughters
   prophesied...").
4. **How the verdict handles the tension** OR honest acknowledgment that it
   remains. If the verdict only stands under a specific lens (dispensational,
   covenantal, accommodationist), say so plainly.

**No denominational or lineage names in this section.** That content goes
in `denominational_landscape`. The reasoning section is the Scripture-based
verdict justification.

#### `lay_summary.denominational_landscape` (descriptive church-history layer)

Plain English. Required content:

- **Where major Christian lineages agree or disagree** on this proposition.
  Name them: patristic, Catholic magisterial, Lutheran, Anglican, Reformed,
  Methodist, Anabaptist, Pentecostal, Eastern Orthodox.
- **Where applicable, name public-record cult or heterodox carriers of
  denial** (Mormonism, Jehovah's Witnesses, Iglesia ni Cristo, William
  Branham, Christian Science, Mary Baker Eddy, Christadelphians, Oneness
  Pentecostalism, etc.) and what their denial places them in relation to
  historic Christianity.

**This section is DESCRIPTIVE of church history. It does NOT vote on the
verdict.** The verdict (`affirms`, `cult_marker_if_denied`, `would_die_for`,
`confidence`) was already settled in `answer.rationale` and `scripture[]`
on the basis of apparatus + interlinear + concordance alone. The
denominational landscape section is for the reader's information, so they
see where each tradition lands.

This is NOT a victory lap. If the canonical evidence is contested, say so
in `reasoning`. If only 4 of 8 traditions agree, say that in
`denominational_landscape`. If counter-witness is unanimous, say that, but
still surface the counterarguments in `reasoning` and explain how they're
answered.

Forbidden vocabulary (validator REJECTS): Strong's, Niphal, Piel, Hiphil,
Granville-Sharp, Colwell, anarthrous, articular, hapax legomenon, BHS,
NA28, UBS5, aorist, lemma, morpheme. Use the plain English equivalent.

**Em dashes (—) and en dashes (–) are BANNED.** Use periods, commas, or
natural conjunctions ("and", "but", "however"). Lay readers find dashes
disruptive; natural sentence structure is mandatory.

Length: each subfield (`reasoning`, `denominational_landscape`) >=100 characters and <=500 words. Validator enforces both bounds, plus jargon and em/en dash checks on each.

## Calibration rules for the boolean fields (locked in docs/ANSWER_SCHEMA.md)

### `affirms` (bool | null)
- true if apparatus + interlinear + concordance support the proposition.
- false if apparatus + interlinear contradict the proposition.
- null if Scripture is silent, ambiguous, or genuinely lexically contested in
  a way apparatus + interlinear + concordance cannot resolve. Counter-witness
  divergence does NOT make a verdict null; only lexical evidence does.

### Severity (2 booleans)
- would_die_for: TRUE only if denial means denial of the gospel itself or a
  core Trinitarian or Christological boundary clearly mandated by Scripture's
  own lexical pattern. Honest, not aspirational. The boundary is set by
  Scripture, not by Nicaea or Chalcedon as historical settlements; the councils
  recognized what was already in the canon.
- cult_marker_if_denied: TRUE only when BOTH conditions hold (see
  ANSWER_SCHEMA.md "Cult-marker bar"):
  (i) would_die_for=true
  (ii) Apparatus + interlinear + concordance demonstrate the doctrine
       canonically (not from a single passage)

  Even Trinity must clear both on its own canonical evidence. Lineage
  agreement does NOT grant cult-marker status, and lineage divergence does
  NOT withhold it. Scripture drives the bar.

### Engagement ladder (5 booleans, monotonic by intent)

Each boolean is judged on the canonical evidence for THIS specific proposition,
NOT keyed to a pre-assigned tier. The implicit prompt for each is: "if a church
taught the opposite of this statement..."

- would_visit_if_otherwise: FALSE if denial constitutes denial of the gospel
  itself (would_die_for=true case): visiting that church would mean cooperating
  with denial of the gospel. TRUE if the doctrine is real conviction but not
  gospel-essence: visiting once or occasionally to evaluate or to support a
  believing relative does not constitute affirmation.
- would_participate_if_otherwise: TRUE if the doctrine is not gospel-stake AND
  the difference does not compromise the act of participation (e.g., taking
  communion under a different sacramental theology). FALSE if either condition
  fails.
- would_serve_if_otherwise: TRUE if the doctrine is methodological or practical
  difference, not substantive doctrinal conflict; serving under teaching one
  disagrees with on a non-gospel-stake matter is workable. FALSE if the
  disagreement is substantive enough that serving would publicly endorse the
  teaching.
- would_be_member_if_otherwise: TRUE if the difference is methodological or
  adiaphora (Scripture grants freedom). FALSE if the difference is convictional
  or higher; membership implies endorsement of the church's doctrinal stance.
- would_let_children_be_taught_otherwise: TRUE only if the difference is truly
  adiaphora (Scripture explicitly grants freedom on this point, e.g., Rom 14:5-6
  calendar customs). FALSE for any conviction-level difference, because
  children inherit the teaching they are formed in.

### Other personal decisions (2 booleans)
- would_marry_if_held_otherwise: TRUE if the doctrine is methodological or
  adiaphora and the prospective spouse's character and gospel-confession are
  sound. FALSE if denial is gospel-stake (1 Cor 7:39 "only in the Lord")
  or convictional enough to produce ongoing household conflict.
- would_publicly_correct_if_otherwise: TRUE if denial is gospel-stake (the
  duty to "contend earnestly for the faith once delivered", Jude 3) or a
  substantive doctrinal error worth public correction in love. FALSE if the
  difference is methodological, practical, or adiaphora.

These booleans together infer the standing of the doctrine (cult-grade,
gospel-essential, convictional, preference, adiaphora) per the
[Standings inferred from boolean patterns](../docs/ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns)
table in ANSWER_SCHEMA.md. **Tier is the OUTPUT of the answer, not the INPUT
to the question.**

## Confidence

Reflects how well Scripture itself answers the question via apparatus +
interlinear + concordance + hermeneutic clarity. Counter-witness divergence
or convergence does NOT shift confidence; only lexical evidence does.

- high: apparatus + interlinear unambiguous AND concordance shows pan-canonical
  demonstration AND hermeneutic uncontested.
- medium: apparatus paywalled and interlinear alone carries the verdict, OR
  complicating texts require harmonization, OR the verdict requires a
  non-default hermeneutic (covenantal, dispensational, accommodation), OR the
  lemma-network is contested at the lexical level (not at the lineage level).
- low: Scripture silent or ambiguous, OR concordance reveals the lemma-network
  does not pan-canonically support the doctrine, OR heavy inference required.

## Output (single JSON file → evidence/<id>.json)

The shape is locked in docs/ANSWER_SCHEMA.md. Do not invent extra fields. Write
the file using your Write tool.

{
  "id": "<question id>",
  "answer": {
    "id": "<same>",
    "affirms": true | false | null,
    "rationale": "<1-2 sentences, scripturally grounded; cite apparatus / interlinear / concordance, not confessions>",
    "would_die_for": <bool>,
    "cult_marker_if_denied": <bool>,
    "would_visit_if_otherwise": <bool>,
    "would_participate_if_otherwise": <bool>,
    "would_serve_if_otherwise": <bool>,
    "would_be_member_if_otherwise": <bool>,
    "would_let_children_be_taught_otherwise": <bool>,
    "would_marry_if_held_otherwise": <bool>,
    "would_publicly_correct_if_otherwise": <bool>,
    "notes": "<context, fruit-vs-precision nuance, named carriers>"
  },
  "evidence": {
    "stem_audit": {
      "verdict_preloaded": <bool>,
      "neutralized_form": "<string or null>",
      "notes": "<string or null>"
    },
    "lay_summary": {
      "reasoning": "<plain-English Scripture-based verdict justification. Required structure: (1) verdict in everyday language; (2) strongest reason FOR from Scripture, named-verse plain words; (3) strongest counterargument from Scripture's own complicating texts, named-verse plain words; (4) how the verdict handles the tension or honest acknowledgment it remains. NO denominational or lineage names in this section; that goes in denominational_landscape. >=100 chars, <=500 words. NO jargon. NO em or en dashes.>",
      "denominational_landscape": "<plain-English description of where major Christian lineages agree or disagree on this proposition. Name the lineages (patristic, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal, Eastern Orthodox) with brief positions. Where applicable, name public-record cult or heterodox carriers of denial (Mormonism, Jehovah's Witnesses, Iglesia ni Cristo, William Branham, Christian Science, Mary Baker Eddy, Christadelphians, Oneness Pentecostalism, etc.) and what their denial places them in relation to historic Christianity. DESCRIPTIVE of church history; does NOT vote on the verdict. >=100 chars, <=500 words. NO jargon. NO em or en dashes.>"
    },
    "scripture": [
      {
        "ref": "Rom.6.3",
        "key_term": "βάπτισμα (baptisma) G908",
        "force": "<lexical force in one line>",
        "supports": "for" | "against" | "complicates" | "neutral",
        "genre": "narrative|epistle|prophecy|wisdom|apocalyptic|gospel|law|psalm|parable",
        "figures": []
      }
    ],
    "concordance_lemmas_traversed": ["G908", "G4916"],
    "complicating_texts_searched": true,
    "hermeneutics": {
      "primary_method": "grammatico-historical|redemptive-historical|quadriga|patristic-typological|accommodation",
      "frameworks_in_play": [],
      "analogia_scripturae_invoked": <bool>,
      "progressive_revelation_factor": <bool>,
      "competing_lens_verdicts": [],
      "notes": "<short narrative>"
    },
    "counter_witness": [
      {
        "tradition": "patristic|catholic_magisterial|lutheran|anglican|reformed|methodist|anabaptist|continuationist|eastern_orthodox|pentecostal",
        "anchor": "<source citation>",
        "verified": <bool>,
        "stance": "affirms|denies|complicates",
        "key_phrase": "<≤200 chars>"
      }
    ],
    "web": [
      {
        "url": "https://...",
        "category": "primary_repository|magisterial|patristic_archive|tradition_primary|interlinear|critical_apparatus",
        "stance": "supports|opposes|complicates|nuance",
        "quote": "<≤200 chars>"
      }
    ],
    "confidence": "high|medium|low",
    "flags": []
  }
}

## Stop conditions / flags

- stem audit flags verdict_preloaded=true: work neutralized form, flag
  `stem-pre-loaded-verdict`, do NOT block.
- Apparatus + interlinear contradict counter-witness consensus: flag
  `apparatus-vs-counter-witness-conflict`. Apparatus wins. Confidence is NOT
  lowered; it reflects lexical clarity, not lineage agreement.
- Counter-witness sources from kin confessions (WCF, 1689 LBC, Reformed)
  disagree among themselves: flag `confession-tradition-divergence` for
  diagnostic information; not verdict-shifting.
- Concordance reveals doctrine NOT pan-canonically supported (single-passage
  doctrine): confidence=low, flag `single-passage-doctrine`.
- Zero counter-witness surfaced on any tier: flag `counter-witness-missing`
  for research-quality tracking. Confidence is NOT lowered.
- Cannot reach a confident verdict from apparatus + interlinear + concordance:
  confidence=low, affirms=null, flag `needs-elder-input`.
- Critical apparatus needed but inaccessible: flag `apparatus-paywalled`,
  proceed on interlinear + concordance.
- cult_marker_if_denied=true without would_die_for=true: incoherent; re-derive.
- cult_marker_if_denied=true without canonical demonstration (pan-canonical
  lexical reading): incoherent; re-derive with `affirms` and `cult_marker`
  re-evaluated honestly.
- Concordance unavailable (Neo4j down, no fallback succeeded): hard fail; do
  NOT write evidence file; report up to orchestrator.
- Never bluff. Never invent scripture. Note guesses in flags.

## Style
- Concise. No emoji. No filler.
- Cite full URLs.
- Source-doc / counter-witness excerpts ≤400 chars (counter-witness key_phrase
  ≤200), names redacted except Ebenezer.
- Final action: Write evidence/<qid>.json. Then return a one-sentence summary
  of verdict + confidence to the orchestrator.
```

---

## Orchestrator workflow

1. **Setup.** `mkdir -p evidence/`. Read `questions.json` into memory. Build a
   worklist of 231 ids.
2. **Resume gate.** For each id, if `evidence/<id>.json` exists, json-loadable,
   has key `id` matching, AND has populated `evidence.stem_audit` +
   `evidence.concordance_lemmas_traversed` + `evidence.hermeneutics` fields,
   drop from worklist. (Greenfield invariant: `evidence/` is empty at start of
   any new run; resume only applies to mid-run interruption recovery.)
3. **Throttling for the Claude Max subscription on Opus 4.7.** Use a TIGHT
   concurrent pool (**2-3 active subagents at a time**, NOT 5). Opus rate
   limits on Max are stricter than Sonnet. Spawn the next batch only when
   active pool drops below the cap. Between every ~15 completions, take a
   10-15 minute idle pause to let the rate-limit bucket recover. Plan for the
   run to span **multiple 5-hour windows across multiple days**. The resume
   gate makes interruptions safe; the orchestrator can be killed and
   re-invoked at any point.
4. **Spawn (paced).** Each Agent call:
   `subagent_type=general-purpose`, `model=opus`,
   `run_in_background=true`. Each call uses the template above with that
   question's data interpolated. If a subagent returns a rate-limit error,
   back off **30 minutes** before retrying that single id (Opus rate-limit
   recovery is slower than Sonnet's).
5. **Wait and validate.** Walk `evidence/`, json-load each file. Any parse
   failure or missing required field: re-spawn the agent (paced). Validate:
   - The moral entailment: cult_marker_if_denied=true requires
     would_die_for=true.
   - Cult-marker canonical demonstration: cult_marker_if_denied=true requires
     `concordance_lemmas_traversed[]` length ≥2 AND `scripture[]` length ≥3
     (structural proxy for pan-canonical, not single-passage). Lineage
     agreement is NOT checked.
   - Concordance traversal non-empty on every record.
   - Counter-witness encouraged for diagnostic completeness; missing flags
     `counter-witness-missing` for research-quality tracking but does NOT
     fail validation.
   - complicating_texts_searched: true on every record.
   - Hermeneutics block populated: primary_method, frameworks_in_play exists,
     genre + figures on every scripture[] entry.
   Repeat once; surface unrecoverable cases to user.
6. **Anonymization audit.** Build a name deny-list from `parsed/*.json` (for
   the deny-list, `parsed/` is consulted ONLY here for the deny-list, not
   for evidence). Grep `evidence/*.json` for any deny-list name (excluding
   "Ebenezer"). Any hit: re-spawn that agent with a stronger redaction
   reminder.
7. **Triage flags.** Group `evidence.flags` across all 231. Halt and
   `AskUserQuestion` if:
   - Any flag occurs ≥5 times, OR
   - Any `apparatus-vs-counter-witness-conflict` exists, OR
   - Any `would_die_for=true` question returns `affirms=null`, OR
   - Any `apparatus-paywalled` blocks a `would_die_for=true` verdict, OR
   - `stem-pre-loaded-verdict` count ≥10 (suggests questions.json bias rather
     than per-question oversight).
8. **Assemble baseline.** For each id, project `evidence/<id>.json#answer`
   into `baseline.json`:
   ```json
   { "$schema_version": "1.0", "viewpoint": "inferred-from-sources",
     "generated_at": "<today>", "answers": [...] }
   ```
9. **Generate reports** (`baseline-report.md`, `baseline-conflicts.md`,
   `stem-audit.md`).
10. **Final summary to user.** One or two sentences plus paths.

---

## Stop / ask-user triggers

| Trigger | Action |
|---|---|
| ≥5 agents flag the same cross-cutting issue | Halt, brief user, ask preference |
| Any `would_die_for=true` question returns `affirms=null` | Halt, list them, ask user |
| ≥10 `stem-pre-loaded-verdict` flags | Halt, brief user, suggest pausing for phase-3 questions.json revision first |
| Concordance unavailable | Halt; orchestrator cannot proceed without concordance |
| Rate-limit blowout | Halt, wait the displayed reset window, resume |
| Cult-marker incoherence after re-derivation | Halt, surface to user |

---

## Final acceptance criteria (gates the green-light)

- `baseline.json` exists, conforms to ANSWER_SCHEMA.md, has
  `$schema_version: "1.0"`, `viewpoint: "inferred-from-sources"`, exactly 231
  entries.
- Every `evidence/<id>.json`:
  - `evidence.stem_audit.verdict_preloaded` is bool
  - `evidence.concordance_lemmas_traversed` is non-empty
  - `evidence.complicating_texts_searched=true`
  - `evidence.hermeneutics.primary_method` is valid enum
  - Every `scripture[]` entry has `genre` (valid enum) and `figures` (list)
- No record violates the moral entailment.
- No record carries `cult_marker_if_denied=true` without
  - `would_die_for=true`
  - Canonical demonstration: apparatus + interlinear + concordance evidence
    in the record's own `scripture[]` and `concordance_lemmas_traversed[]`
    showing pan-canonical lexical support (not single-passage)
- `tools/verify_baseline.py --check all` exits zero.

The orchestrator does not declare success until `tools/verify_baseline.py`
exits zero.
