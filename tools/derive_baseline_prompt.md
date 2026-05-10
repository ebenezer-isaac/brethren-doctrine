# Handover Prompt for Deriving the Source-Inferred `baseline.json`

> Paste this entire document into a fresh Claude Code session at the project root
> (`e:\projects-working-dir\brethren-doctrine`). The receiving model is the
> **orchestrator**; it spawns one subagent per question via `tools/baseline_orchestrator.py`.

---

## Mission

Derive a **tradition-neutral lexical-philological baseline** for the 221 questions in
[questions.json](../questions.json), producing `baseline.json` and per-question
audit trails in `evidence/<id>.json`. The baseline is the original-language exegetical
floor that all eight major lineages (Eastern Orthodox, Catholic, Lutheran, Anglican,
Reformed, Methodist, Anabaptist, Pentecostal) can audit, prior to any single
tradition's confessional commitment.

Each verdict is settled by **apparatus + interlinear + concordance**. Counter-witness
traditions are consulted as **research aids** to verify the lexical reading isn't
idiosyncratic — they corroborate, they do not vote on the verdict. Confessions
(Reformed-Baptist, Reformed paedobaptist, Catholic, Orthodox, Lutheran, Anglican,
Anabaptist) are NOT in the baseline; they are recorded as `counter_witness[]` entries
showing how each tradition reads the lexical text.

Brethren-adjacent teaching notes (`source-docs/`, `parsed/`) are **not consulted at
all** during baseline derivation. They are respondent material that lives in
`responses/<id>.json` files contributed by the specific church or elder who affirms
them — including Ebenezer himself when he fills out his own questionnaire.

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
| 3 | **Counter-witness** | Patristic, Catholic magisterial, Lutheran, Anglican, Anabaptist, Methodist, Pentecostal, Reformed, Eastern Orthodox primary sources via web fetch (see Method Step 6) | Corroborates that the lexical reading isn't idiosyncratic. Mandatory ≥1 for any tier=essential or tier=convictional verdict. Does NOT settle the verdict. |

### The bar (corrected)

`apparatus + interlinear + concordance` settle every verdict. Confessions never
override Scripture. Counter-witness corroborates the lexical reading; it does not vote.

**Cult-marker bar requires three conditions, all canonical:**

1. **Moral entailment**: `would_die_for=true`.
2. **Canonical demonstration**: apparatus + interlinear yield an unambiguous lexical
   reading affirming the doctrine, AND concordance demonstrates the doctrine across
   the canon (not from a single passage). The Bible itself does the work.
3. **Pan-tradition corroboration**: `counter_witness[]` contains entries from ≥6
   distinct lineages, ALL with `stance: "affirms"`. Tracked lineages: Eastern
   Orthodox patristic, Catholic magisterial, Lutheran, Anglican, Reformed, Methodist,
   Anabaptist, Pentecostal/charismatic.

**Even Trinity is not exempt.** Each question — including the Nicene-Chalcedonian
foundations (Trinity, full deity+humanity of Christ, bodily resurrection, Scripture
as inspired-authoritative) — clears or fails this bar on its own per-question
evidence. The whole canon is examined for every claim.

### Hard rules

1. **Apparatus + interlinear + concordance settle. Nothing else does.**
2. **Concordance traversal is mandatory on every question, every tier.**
   `evidence.concordance_lemmas_traversed: []` is a hard validation failure.
3. **Counter-witness is mandatory** for any tier=essential or tier=convictional
   verdict. Missing → flag `counter-witness-missing`, confidence drops a tier.
4. **Selection-bias check is mandatory.** A `scripture[]` array with all
   `supports="for"` AND `complicating_texts_searched=true` AND `flags` containing
   `no-complicating-texts-after-search` is honest; the same array without that flag
   is a smell.
5. **Question-stem hygiene.** If `question.statement` names heretics, asserts the
   verdict, or uses Reformed-confessional vocabulary as if neutral, work the
   *neutralized form* and record the original in `evidence.stem_audit`.
6. **NO confessions in the baseline as authority.** WCF, 1689 LBC, Brethren Archive,
   Westminster Standards, Heidelberg, Belgic, Savoy — all recorded as
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
- An agent reports `affirms=null` (uncertain) on a tier=essential question.
- ≥5 agents flag the same cross-cutting issue.
- An agent flags `stem-pre-loaded-verdict` — the question itself needs a phase-3 rewrite.

Otherwise, run autonomously.

---

## User context (carry into every subagent prompt)

- **Owner**: Ebenezer Isaac.
- **Owner's formation**: Plymouth Brethren-adjacent (India). **This formation is the
  position under examination, not the rubric.** The whole point is to test whether
  the Brethren reading survives primary-source scrutiny. Do not calibrate to
  Brethren or Reformed-Protestant orthodoxy. Calibrate to apparatus + interlinear +
  concordance, with counter-witness corroborating that the lexical reading is
  cross-tradition, not idiosyncratic.
- **Faith stage**: Stage 3 (which denomination is right). Calibrating discernment,
  not scoring churches.
- **Authority hierarchy**: Critical Apparatus → Interlinear → Formal translation →
  Dynamic translation → Application. Confessions are NOT a tier; they are an
  information layer recorded as `counter_witness[]`. See
  [AUTHORITY_HIERARCHY.md](../docs/AUTHORITY_HIERARCHY.md).
- **Anonymization rule**: only "Ebenezer" may appear in any output. Every other
  personal name must be `[REDACTED]` in any quoted excerpt.
- **Discernment principle**: tier=essential errors break fellowship absolutely;
  tier=preference differences MUST NOT outweigh demonstrable Christian fruit.

---

## Inputs

| Path | What it is | How subagents use it |
|---|---|---|
| `questions.json` | 221 questions under `.questions` | Source of truth; shape locked in [QUESTION_SCHEMA.md](../docs/QUESTION_SCHEMA.md) |
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
     "answers": [ <Answer×221> ]
   }
   ```
   Each Answer is exactly the 13 fields in ANSWER_SCHEMA.md. No extra fields.

2. **`evidence/<id>.json`**: one file per question, audit trail per
   ANSWER_SCHEMA.md `evidence` shape. This directory IS the evidence record.

3. **`baseline-report.md`**: human-readable run summary:
   - `affirms` distribution (true / false / null counts).
   - Top flag categories with counts.
   - Per-tier breakdown of `affirms` and `engagement_score` distributions.
   - List of `confidence=low` questions on tier=essential / tier=convictional for
     trusted-elder review priority.
   - Counter-witness coverage stats (essentials/convictionals with ≥1 vs missing).
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
   complicating texts, counter-witness traditions diverge — Sonnet picks the
   obvious answer; Opus surfaces the tension in `notes` and `competing_lens_verdicts`).
2. **K2 cult-marker bar enforcement** (Sonnet rubber-stamps "essentials I expect
   to be cult-grade" like Trinity; Opus actually checks whether the ≥6-tradition
   consensus rule clears, and downgrades to `would_die_for=true,
   cult_marker=false` when only Reformed-substrate consensus is present).
3. **Brethren-on-trial discipline** (Sonnet drifts back toward Brethren-comfortable
   readings under stress; Opus holds the line when the lexical evidence cuts
   against the formation).

The project produces a baseline referenced indefinitely; "cannot afford to
re-run" tilts toward Opus on the first pass even at the cost of more rate-limit
windows.

**Execution model: Claude Max subscription, Opus 4.7.** Opus has tighter 5-hour
rolling-window rate limits than Sonnet. Plan for the full 221-question run to
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
concordance, with counter-witness traditions corroborating that the lexical
reading is cross-tradition. Do NOT calibrate to Brethren or Reformed-Protestant
orthodoxy.

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
5. Counter-witness traditions (mandatory for tier=essential / convictional):
   patristic, Catholic, Lutheran, Anglican, Anabaptist, Methodist, Pentecostal,
   Reformed, Eastern Orthodox primary sources. Web fetch primary URLs only.

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
  REDACT if they appear (they shouldn't — the baseline pipeline doesn't read
  parsed/ at all).

Do NOT over-redact. "[REDACTED]'s abridgement of the 39 Articles" should be
"Wesley's abridgement". "[REDACTED]-Universalists" should be "Unitarian
Universalists". The point of the rule is privacy for Ebenezer's private
contributors, not pseudonymizing public theological history.

## Question
<paste the full question object from questions.json>

## Method (in order — DO NOT SKIP STEPS)

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
CONCORDANCE.md) — verses sharing ≥1 lemma + cross-references. Surface
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
- competing_lens_verdicts[]: mandatory if frameworks_in_play.length > 1 AND
  tier in {essential, convictional}
- notes: short narrative on hermeneutic commitments required

If the verdict requires dispensational hermeneutics (pre-trib rapture,
Israel/church distinction, literal millennium tied to ethnic Israel), add
flag `dispensational-lens-required`. Verdict can stand — but as a Brethren
distinctive, not as cross-tradition consensus.

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

### Step 6: Counter-witness pass (MANDATORY for tier=essential / convictional)

Pull at least ONE primary-source statement from each of as many tracked
lineages as possible. Required entry points:

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
  Savoy) — recorded as `tradition: "reformed"`
- Methodist: https://www.umc.org/en/content/articles-of-religion
- Anabaptist: Schleitheim Confession 1527 — https://courses.washington.edu/
  hist112/SCHLEITHEIM%20CONFESSION%20OF%20FAITH.htm
- Continuationist/Pentecostal: https://ag.org/Beliefs/Statement-of-Fundamental
  -Truths (AG Fundamental Truths)
- Eastern Orthodox: https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine
  -scripture (OCA Orthodox Faith)

For each primary source consulted, record under `evidence.counter_witness[]`:
tradition, anchor, verified (true if you read primary text), stance
(affirms|denies|complicates), key_phrase (≤200 chars).

If tier=essential or tier=convictional and zero counter-witness can be
surfaced in good faith, flag `counter-witness-missing` and lower confidence
to medium.

For tier=preference / adiaphora: counter-witness encouraged but not required.

### Step 7: Web pass — primary repositories only

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

### Step 8: Lay summary (MANDATORY — reader-facing reasoning)

After the technical work, write a 4-8 sentence plain-English explanation in
`evidence.lay_summary`. The reader is a layperson trying to understand WHAT
the verdict is and WHY — including counterarguments. Required structure:

1. **State the verdict** in everyday language (no Greek, no Strong's, no
   theological jargon).
2. **The strongest reason FOR it** from Scripture, in plain words.
3. **The strongest counterargument or complicating texts that critics cite**,
   named explicitly (e.g., "Critics like Unitarians and Jehovah's Witnesses
   point to Mark 13:32 where Jesus says he doesn't know the hour…").
4. **How the verdict handles the tension** OR honest acknowledgment that it
   remains. If the verdict only stands under a specific lens (dispensational,
   covenantal, accommodationist), say so plainly.
5. **Where major Christian traditions agree or disagree** — name the lineages.

This is NOT a victory lap. If the canonical evidence is contested, say so.
If only 4 of 8 traditions agree, that's a `would_die_for=true,
cult_marker_if_denied=false` case and the lay_summary must say "Christians
disagree about this." If counter-witness is unanimous and apparatus is
unambiguous, say that — but still surface the counterarguments and explain
how they're answered.

Forbidden vocabulary (validator REJECTS): Strong's, Niphal, Piel, Hiphil,
Granville-Sharp, Colwell, anarthrous, articular, hapax legomenon, BHS,
NA28, UBS5, aorist, lemma, morpheme. Use the plain English equivalent.

**Em dashes (—) and en dashes (–) are BANNED.** Use periods, commas, or
natural conjunctions ("and", "but", "however"). Lay readers find dashes
disruptive; natural sentence structure is mandatory.

Length: 200-2000 characters. Validator enforces.

## Calibration rules for the boolean fields (locked in docs/ANSWER_SCHEMA.md)

### `affirms` (bool | null)
- true if apparatus + interlinear + concordance support the proposition AND
  counter-witness does not decisively refute the lexical reading.
- false if apparatus + interlinear contradict the proposition.
- null if Scripture is silent, ambiguous, or contested across traditions in a
  way the lexical reading alone does not resolve.

### Severity (2 booleans)
- would_die_for: TRUE only if denial means denial of the gospel itself or a
  core Trinitarian/Christological boundary clearly mandated by Scripture.
  Honest, not aspirational.
- cult_marker_if_denied: TRUE only when ALL THREE conditions hold (see
  ANSWER_SCHEMA.md "Cult-marker bar"):
  (i) would_die_for=true
  (ii) Apparatus + interlinear + concordance demonstrate the doctrine
       canonically (not from a single passage)
  (iii) counter_witness[] has ≥6 distinct lineages, all with stance="affirms"

  Even Trinity must clear all three on its own evidence. Pan-tradition
  consensus alone does not grant cult-marker status; it corroborates the
  lexical reading.

### Engagement ladder (5 booleans, monotonic by intent)
- would_visit_if_otherwise: TRUE for tier=convictional and below; FALSE for
  tier=essential.
- would_participate_if_otherwise: TRUE for tier=important and below.
- would_serve_if_otherwise: TRUE for tier=preference and below.
- would_be_member_if_otherwise: TRUE for tier=preference and adiaphora.
- would_let_children_be_taught_otherwise: TRUE for tier=adiaphora only.

### Other personal decisions (2 booleans)
- would_marry_if_held_otherwise: TRUE for tier=preference; usually FALSE for
  tier=essential.
- would_publicly_correct_if_otherwise: TRUE for tier=essential.

## Confidence

Reflects how well Scripture itself answers the question via apparatus +
interlinear + concordance + hermeneutic clarity.

- high: apparatus + interlinear unambiguous AND concordance shows pan-canonical
  demonstration AND hermeneutic uncontested AND ≥3 distinct counter-witness
  traditions corroborate.
- medium: lexical reading clear but counter-witness divided, OR apparatus
  paywalled and interlinear alone, OR complicating texts require harmonization,
  OR verdict requires non-default hermeneutic.
- low: Scripture silent/ambiguous, OR counter-witness sharply divided on the
  same lexical reading, OR concordance reveals lemma-network does not
  pan-canonically support the doctrine, OR heavy inference required.

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
    "complicating_texts_searched": <bool>,
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
- Apparatus + interlinear contradict counter-witness consensus: confidence=
  medium, flag `apparatus-vs-counter-witness-conflict`. Apparatus wins.
- Counter-witness sources from kin confessions (WCF, 1689 LBC, Reformed)
  disagree among themselves: flag `confession-tradition-divergence` (recorded
  as intramural debate, not verdict-shifter).
- Concordance reveals doctrine NOT pan-canonically supported (single-passage
  doctrine): confidence=low, flag `single-passage-doctrine`.
- Tier=essential or tier=convictional with zero counter-witness sources: flag
  `counter-witness-missing`, lower confidence to medium.
- Cannot reach a confident verdict from apparatus + interlinear + concordance:
  confidence=low, affirms=null, flag `needs-elder-input`.
- Critical apparatus needed but inaccessible: flag `apparatus-paywalled`,
  proceed on interlinear + concordance + counter-witness.
- cult_marker_if_denied=true without would_die_for=true: incoherent; re-derive.
- cult_marker_if_denied=true without ≥6 affirming counter-witness lineages:
  flag `cult-marker-substrate-only`, downgrade to would_die_for=true,
  cult_marker=false.
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
   worklist of 221 ids.
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
   - Cult-marker pan-tradition consensus: cult_marker_if_denied=true requires
     ≥6 distinct counter_witness traditions all with stance="affirms".
   - Concordance traversal non-empty on every record.
   - For tier=essential / tier=convictional: counter_witness[] non-empty OR
     flags contains `counter-witness-missing`.
   - complicating_texts_searched: true on every record.
   - Hermeneutics block populated: primary_method, frameworks_in_play exists,
     genre + figures on every scripture[] entry.
   Repeat once; surface unrecoverable cases to user.
6. **Anonymization audit.** Build a name deny-list from `parsed/*.json` (for
   the deny-list — `parsed/` is consulted ONLY here for the deny-list, not
   for evidence). Grep `evidence/*.json` for any deny-list name (excluding
   "Ebenezer"). Any hit: re-spawn that agent with a stronger redaction
   reminder.
7. **Triage flags.** Group `evidence.flags` across all 221. Halt and
   `AskUserQuestion` if:
   - Any flag occurs ≥5 times, OR
   - Any `apparatus-vs-counter-witness-conflict` exists, OR
   - Any tier=essential question returns `affirms=null`, OR
   - Any `apparatus-paywalled` blocks a tier=essential verdict, OR
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
| Any `apparatus-vs-counter-witness-conflict` | Halt, show both, ask which prevails (apparatus wins by default) |
| Any tier=essential question returns `affirms=null` | Halt, list them, ask user |
| ≥10 `stem-pre-loaded-verdict` flags | Halt, brief user, suggest pausing for phase-3 questions.json revision first |
| Concordance unavailable | Halt; orchestrator cannot proceed without concordance |
| Rate-limit blowout | Halt, wait the displayed reset window, resume |
| Cult-marker incoherence after re-derivation | Halt, surface to user |

---

## Final acceptance criteria (gates the green-light)

- `baseline.json` exists, conforms to ANSWER_SCHEMA.md, has
  `$schema_version: "1.0"`, `viewpoint: "inferred-from-sources"`, exactly 221
  entries.
- Every `evidence/<id>.json`:
  - `evidence.stem_audit.verdict_preloaded` is bool
  - `evidence.concordance_lemmas_traversed` is non-empty
  - `evidence.complicating_texts_searched=true`
  - `evidence.hermeneutics.primary_method` is valid enum
  - Every `scripture[]` entry has `genre` (valid enum) and `figures` (list)
  - For tier=essential / tier=convictional: `counter_witness[].length ≥ 1`
    OR `flags` includes `counter-witness-missing`
- No record violates the moral entailment.
- No record carries `cult_marker_if_denied=true` without
  - `would_die_for=true`
  - `counter_witness[]` containing ≥6 distinct traditions, all
    `stance="affirms"`
- `tools/verify_baseline.py --check all` exits zero.

The orchestrator does not declare success until `tools/verify_baseline.py`
exits zero.
