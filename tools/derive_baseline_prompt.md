# Handover Prompt for Deriving the Source-Inferred `baseline.json`

> Paste this entire document into a fresh Claude Code session at the project root
> (`e:\projects-working-dir\brethren-doctrine`). The receiving model is the
> **orchestrator**; it spawns one Sonnet subagent per question.

---

## Mission

Derive a **source-inferred seed answer set** for the 222 questions in
[questions.json](../questions.json), producing `baseline.json`. This is **not**
Ebenezer's personal stance. It is autofill drudge-work for a community
questionnaire round.

The collaboration model: a small set of **trusted churches and elders that
Ebenezer personally knows** will fill out the same 222-question shape (and
Ebenezer fills out his own). The seed exists so they engage with substantive
disagreements instead of blank forms. The downstream use of the eventual
consolidated baseline is to evaluate **potential churches Ebenezer might
visit or join**. That's the evaluation direction. Trusted-elder collaborators
are upstream; potential-church evaluation targets are downstream.

The output is **provisional**. The eventual canonical answer file is
`consolidated.json`, produced after collating responses with the inferred
seed and final research. See [docs/QUESTION_SCHEMA.md](../docs/QUESTION_SCHEMA.md)
for the question bank shape and [docs/ANSWER_SCHEMA.md](../docs/ANSWER_SCHEMA.md)
for the answer record shape (13 fields, boolean-pattern design).

Each verdict must be backed by, in this priority order:

1. **Critical apparatus**: BHS / NA28 / UBS5 footnotes where retrievable
   (paywalled in many cases; flag if inaccessible). The bedrock per the
   project's authority hierarchy.
2. **Interlinear**: Hebrew/Greek lexical force via Bible Hub Interlinear,
   STEPBible, or OSHB. The closest accessible representation when the apparatus
   itself is paywalled.
3. **Ebenezer's source documents**: accessed via the Tier 2 hybrid retrieval
   pipeline (see "Source-doc lookup" below). These represent the user's lived
   teaching tradition and carry weight.
4. **Confessional anchors** (only if `confessional_anchors` is non-empty):
   one quick verification that the named confession actually says what the
   anchor implies.
5. **Web sources** (MINIMAL, tertiary, used only when 1 through 4 leave a gap):
   to identify named cult/heterodox carriers for tier=essential questions; never
   as a primary doctrinal authority. Critical-apparatus-grade evidence does NOT
   come from blogs.

You (the orchestrator) act as a **brain**. You spawn agents, you don't research.
You only intervene when:

- An agent reports contradiction between source-docs and the apparatus / interlinear.
- An agent reports `affirms=null` (uncertain) on a tier=essential question.
- ≥5 agents flag the same cross-cutting issue.

Otherwise, run autonomously.

---

## User context (carry into every subagent prompt)

- **Owner**: Ebenezer Isaac.
- **Tradition baseline**: Plymouth Brethren-adjacent. Classical Reformed
  Protestant orthodoxy plus Brethren distinctives.
- **Faith stage**: Stage 3. Calibrating discernment, not scoring churches.
- **Authority hierarchy**: Critical Apparatus (source of truth) → Interlinear
  → Formal translation → Dynamic translation → Application. Web/orthodox
  sources are tertiary; never lean on them extensively.
- **Anonymization rule**: only "Ebenezer" may appear in any output. Every other
  personal name in source-docs must be `[REDACTED]` in quoted excerpts. The
  orchestrator runs a deny-list audit at the end (step 6).
- **Discernment principle**: tier=essential errors break fellowship absolutely;
  tier=preference differences MUST NOT outweigh demonstrable Christian fruit.

---

## Inputs

| Path | What it is | How subagents use it |
|---|---|---|
| `questions.json` | 222 questions under `.questions` | Source of truth; shape locked in [QUESTION_SCHEMA.md](../docs/QUESTION_SCHEMA.md) |
| `parsed/` | Sermon JSONs (already ingested into Qdrant) | Indirect access via the retrieval CLI, not grep |
| `retrieval/` | Hybrid retrieval pipeline (Tier 2, live) | Direct access; see "Source-doc lookup" |
| `docs/ANSWER_SCHEMA.md` | Locked 13-field answer shape and evidence shape | Subagents emit JSON conforming to this exactly |

---

## Source-doc lookup (subagents call this, do NOT grep)

Tier 2 retrieval is live. From a subagent shell:

```bash
uv run python -m retrieval.cli "<query>" --k 8 --json-only
```

Returns a JSON envelope with `answer_context[]` where each item has:
`chunk_id`, `score`, `source_doc`, `authority_level` (1-4), `chunk_type`,
`themes`, `scripture_refs`, `text`, `citations`, `graph_context`.

**Subagents must use this for source-doc evidence.** Grep over [parsed/](../parsed/)
is forbidden; it bypasses the authority-tagged hybrid index.

Suggested queries per subagent (run 2 to 4, take union, dedupe by `chunk_id`):
- The question's `statement` paraphrased to a natural search query.
- Each major scripture anchor as its own query (e.g. `"Romans 6:1-4 baptism"`).
- One query for any named carriers (e.g. `"Watchtower JW deity of Christ"`).

---

## Outputs

1. **`baseline.json`**: envelope per [ANSWER_SCHEMA.md](../docs/ANSWER_SCHEMA.md):
   ```json
   {
     "$schema_version": "1.0",
     "viewpoint": "inferred-from-sources",
     "generated_at": "<ISO date>",
     "answers": [ <Answer×222> ]
   }
   ```
   Each Answer is exactly the 13 fields in ANSWER_SCHEMA.md. No extra fields.

2. **`evidence/<id>.json`**: one file per question, audit trail per
   ANSWER_SCHEMA.md `evidence` shape. This directory IS the evidence record.

3. **`baseline-report.md`**: human-readable run summary:
   - `affirms` distribution (true / false / null counts).
   - Top flag categories with counts.
   - Per-tier breakdown of `affirms` and `engagement_score` distributions.
   - List of `confidence=low` questions on tier=essential / tier=convictional
     for trusted-elder review priority.

4. **`baseline-conflicts.md`**: manual-review report listing every question
   where `confession-conflict`, `source-doc-vs-scripture-conflict`, or
   `source-doc-vs-orthodox-conflict` was flagged. Includes both anchor
   positions, the relevant source-doc excerpts, and the subagent's verdict.
   Ebenezer resolves these by hand later.

PDF rendering is not part of this run. Both renderers were deleted under
the greenfield policy and will be rewritten fresh against the new 13-field
shape when needed.

---

## Per-question Sonnet subagent template

Spawn ONE Sonnet subagent per question. Each writes to `evidence/<id>.json`.

**Execution model: Claude Max subscription, not API.** Rate limits are 5-hour
rolling windows on the subscription, not per-call cost. The user is fine with
the run taking many hours or days. The constraint is "do not exhaust a 5-hour
window in 20 minutes." See "Throttling" under the orchestrator workflow.

### Subagent task prompt

```
You are deriving the source-inferred baseline answer for ONE question in a
Plymouth Brethren-adjacent doctrinal taxonomy. This answer is a SEED for
community-questionnaire input from churches and elders Ebenezer personally
knows and trusts. It is not a personal stance. Be honest about uncertainty
so trusted-elder reviewers know what to scrutinize.

## Owner profile (calibrate to this)
- Plymouth Brethren-adjacent, classical Reformed Protestant orthodoxy.
- Authority: Critical Apparatus (source of truth) > Interlinear > Formal >
  Dynamic > Application. Tradition does not override Scripture. Web sources
  are TERTIARY.
- Goal: calibrated thresholds for visit/participate/serve/member/marry/
  let-children-be-taught/correct, used downstream to evaluate potential
  churches Ebenezer is considering.

## Anonymization
Only "Ebenezer" may appear. Redact every other personal name as [REDACTED] in
quoted excerpts.

## Question
<paste the full question object from questions.json>

## Method (in priority order)

1. **Apparatus / Interlinear pass.** For each `scripture_anchors` entry:
   - Read in context (one chapter minimum).
   - Where doctrine rests on a Hebrew/Greek term, fetch the interlinear
     (https://biblehub.com/interlinear/...). Cite lemma + transliteration +
     lexical force in one line.
   - If a critical-apparatus footnote is retrievable (e.g. via NET Bible
     translator notes, STEPBible apparatus data) and bears on the question,
     cite it. If paywalled or inaccessible, do NOT block; note in flags.
   - Note per anchor: supports / requires harmonization / contested.

2. **Source-doc pass.** Run the retrieval CLI 2 to 4 times with different
   queries derived from this question. Example:
       uv run python -m retrieval.cli "<query>" --k 8 --json-only
   Take the union of top hits, dedupe by chunk_id, read the `text` field.
   Note `authority_level` (4=interlinear-derived, 3=SOF, lower=sermon).
   This is the user's lived teaching tradition; weight it accordingly.

3. **Confessional pass.** If `confessional_anchors` is non-empty, verify each
   distinct anchor against the locked confession set:
   - Westminster Confession of Faith (1646)
   - 1689 London Baptist Confession of Faith
   - Apostles' Creed
   - Nicene Creed
   - Athanasian Creed
   ONE web search per distinct anchor to confirm the named confession actually
   says what the anchor implies. If unverified after one search, flag with
   "anchor-unverified"; do not block.

   **When confessions disagree on a question** (the canonical case is WCF and
   1689 LBC on baptism / ecclesiology / sacraments): record both anchor
   positions in `evidence.confessional_verifications`, raise a
   `confession-conflict` flag, and EXTEND the source-doc pass to surface what
   Ebenezer's teaching notes say on the contested point. Do NOT pick a side;
   the orchestrator collates conflicts into `baseline-conflicts.md`.

4. **Web pass, MINIMAL.** Only invoke when 1 through 3 above leave a real gap:
   - One search to identify named carriers (cults / heterodox movements) for
     tier=essential or tier=convictional questions where the verdict is
     `cult_marker_if_denied=true`.
   - One search for orthodox-position confirmation if scripture and source-docs
     are silent or unclear.
   Do NOT do a "broad orthodox consensus survey." Critical-apparatus-grade
   evidence does not come from blogs. Use trusted starts only when needed:
   monergism.com, ligonier.org, thegospelcoalition.org (Reformed),
   brethrenarchive.org (Brethren), carm.org / equip.org (cult ID).
   Got Questions: do not cite as authority.

## Calibration rules for the boolean fields

The 13-field answer shape (locked in docs/ANSWER_SCHEMA.md):

### `affirms` (bool | null)
- `true` if sources support the positive statement in `question.statement`.
- `false` if sources contradict the statement (rare for orthodox questions).
- `null` if sources are silent, contested, or insufficient. Use sparingly;
  null is the "uncertain / open" signal for trusted-elder review.

### Severity (2 booleans)
- `would_die_for`: TRUE only if denial means denial of the gospel itself or
  core Trinitarian/Christological boundary. Honest, not aspirational. Expect
  ~30 to 60 of 222 entries true.
- `cult_marker_if_denied`: TRUE only for classical cult-grade errors: denial
  of Trinity, full deity/humanity of Christ, bodily resurrection, sola fide,
  Scripture-level new revelation, salvation by works alone.
- **Moral entailment**: `cult_marker_if_denied=true` REQUIRES `would_die_for=true`.
  Setting cult-grade without die-for is incoherent. Validate before emitting.

### Engagement ladder (5 booleans, monotonic by intent)
Each is "would I be in this environment if it taught the OPPOSITE of the
statement?" Higher rungs imply lower ones.
- `would_visit_if_otherwise`: TRUE for tier=convictional and below; FALSE for tier=essential.
- `would_participate_if_otherwise`: TRUE for tier=important and below; FALSE for convictional and above.
- `would_serve_if_otherwise`: TRUE for tier=preference and below.
- `would_be_member_if_otherwise`: TRUE for tier=preference and adiaphora only.
- `would_let_children_be_taught_otherwise`: TRUE for tier=adiaphora only. Children's formation deserves the strictest filter.

### Other personal decisions (2 booleans)
- `would_marry_if_held_otherwise`: TRUE for tier=preference; usually FALSE for
  tier=essential; case by case for convictional/important.
- `would_publicly_correct_if_otherwise`: TRUE for tier=essential and any
  position framed as a public error to challenge. FALSE for adiaphora/preference.

## Confidence (the most important field for trusted-elder review)

Set `evidence.confidence` transparently:
- **`high`**: scripture/interlinear clearly supports AND source-docs align AND
  the verdict is unambiguous within Reformed-Protestant orthodoxy.
- **`medium`**: scripture is clear but source-docs are silent or partially
  divergent, OR the question is contested within orthodox tradition (e.g.
  baptism mode, communion frequency, eschatology details).
- **`low`**: scripture is silent or contested AND source-docs unhelpful, OR
  the verdict required heavy inference. Trusted elders should scrutinize
  these first.

## Output (single JSON object → evidence/<id>.json)

The shape is locked in docs/ANSWER_SCHEMA.md. Do not invent extra fields.

{
  "id": "<question id>",
  "answer": {
    "id": "<same>",
    "affirms": true | false | null,
    "rationale": "<1-2 sentences, scripturally grounded>",
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
    "scripture": [
      {"ref": "John 1:1", "key_term": "λόγος (logos)",
       "force": "divine self-expression, applied as a divine name in v.1c",
       "supports": true}
    ],
    "confessional_verifications": [
      {"anchor": "WCF 1.4", "verified": true, "key_phrase": "..."}
    ],
    "source_docs": [
      {"chunk_id": "baptism_and_communion_17", "authority_level": 3,
       "score": 0.91, "excerpt": "<=400 chars, names [REDACTED]>",
       "implies": "affirm|deny|open|silent"}
    ],
    "web": [
      {"url": "...", "stance": "supports|opposes|nuance", "quote": "<=200 chars"}
    ],
    "confidence": "high|medium|low",
    "flags": ["<one short string per flag>"]
  }
}

## Stop conditions

- Cannot verify a confessional anchor in 1 search: flag, do not block.
- Source-docs CONTRADICT apparatus/interlinear: confidence=medium, flag
  "source-doc-vs-scripture-conflict".
- Source-docs CONTRADICT orthodox-Reformed consensus: confidence=medium, flag
  "source-doc-vs-orthodox-conflict".
- Confessions disagree: flag "confession-conflict" (do not pick a side).
- Cannot reach a confident verdict: confidence=low, affirms=null, flag
  "needs-elder-input".
- Critical apparatus needed but inaccessible: flag "apparatus-paywalled",
  proceed on interlinear plus source-docs.
- `cult_marker_if_denied=true` without `would_die_for=true`: reject as
  incoherent; re-derive.
- Never bluff. Never invent scripture. Note guesses in flags.

## Style
- Concise. No emoji. No filler.
- Cite full URLs.
- Source-doc excerpts ≤400 chars, names redacted except Ebenezer.
```

---

## Orchestrator workflow

1. **Setup.** `mkdir evidence/`. Read `questions.json` into memory. Build a
   worklist of 222 ids.
2. **Resume gate.** For each id, if `evidence/<id>.json` exists AND
   `json.load` succeeds AND has key `id` matching, drop from worklist.
3. **Throttling for the Claude Max subscription.** Use a small concurrent pool
   (3 to 5 active subagents at a time, NOT 25). Do not flood the 5-hour
   window. Spawn the next batch only when the active pool drops below the cap.
   Between every ~30 completions, take a 10-minute idle pause to let the
   rate-limit bucket recover. Plan for the run to span multiple 5-hour
   windows (potentially across days). The resume gate makes interruptions
   safe; the orchestrator can be re-invoked at any point and will skip already-
   completed evidence files.
4. **Spawn (paced).** Each Agent call: `subagent_type=general-purpose`,
   `model=sonnet`, `run_in_background=true`. Each call uses the template
   above with that question's data interpolated. If a subagent returns a
   rate-limit error, back off 15 minutes before retrying that single id.
5. **Wait and validate.** Walk `evidence/`, `json.load` each file. Any parse
   failure or missing required field: re-spawn that single agent (paced).
   Validate the moral entailment: any record with
   `cult_marker_if_denied=true` AND `would_die_for=false` is incoherent and
   must be re-spawned. Repeat once; surface unrecoverable cases to user.
6. **Anonymization audit.** Build a name deny-list from `parsed/*.json`
   (extract proper nouns from source-doc filenames plus a one-pass scan for
   capitalized two-word strings in parsed JSON). Grep `evidence/*.json` for
   any deny-list name (excluding "Ebenezer"). Any hit: re-spawn that agent
   with a stronger redaction reminder (paced).
7. **Triage flags.** Group `evidence.flags` across all 222. Halt and
   `AskUserQuestion` if:
   - Any flag occurs ≥5 times, OR
   - Any `source-doc-vs-scripture-conflict` exists, OR
   - Any `needs-elder-input` on a tier=essential question, OR
   - Any `apparatus-paywalled` blocks a tier=essential verdict.
8. **Assemble baseline.** For each id, project `evidence/<id>.json#answer`
   into `baseline.json`:
   ```json
   { "$schema_version": "1.0", "viewpoint": "inferred-from-sources",
     "generated_at": "<today>", "answers": [...] }
   ```
   The `evidence` sub-object stays in `evidence/<id>.json` only.
9. **Generate reports.**
   - `baseline-report.md`: affirms-distribution (true/false/null counts), top
     flags, per-tier engagement-score distribution, prioritized list of
     `confidence=low` tier=essential and tier=convictional questions for
     trusted-elder review.
   - `baseline-conflicts.md`: every `confession-conflict`,
     `source-doc-vs-scripture-conflict`, and `source-doc-vs-orthodox-conflict`,
     with both positions and the relevant source-doc excerpts. Ebenezer
     resolves manually.
10. **Final summary to user.** One or two sentences plus paths to
    `baseline.json`, `baseline-report.md`, and `baseline-conflicts.md`.
    Do NOT touch any renderer (none currently exist; deferred work).

---

## Stop / ask-user triggers

| Trigger | Action |
|---|---|
| ≥5 agents flag the same cross-cutting issue | Halt, brief user, ask preference |
| Any source-doc-vs-scripture-conflict | Halt, show both quotes, ask which prevails |
| Any tier=essential question returns `affirms=null` | Halt, list them, ask user |
| Rate-limit blowout (multiple back-to-back rate-limit errors) | Halt, wait the displayed reset window, resume |
| Cult-marker incoherence after re-derivation | Halt, surface to user |

---

## Token / rate-limit note

Sonnet, not Opus. Each subagent reads only its own question (not full
questions.json). Owner profile block stays tight. Web pass is deliberately
minimal per the authority-hierarchy reframe; this also reduces cost and
latency. The constraint is rate limits, not API dollars; pace the run.

---

## Style constraints (orchestrator output to user)

- Concise. No emoji. State decisions, not deliberation.
- For user questions: focused 2 to 4 option choices via `AskUserQuestion`.
- End-of-run summary: one or two sentences plus paths to the report files.

---

## Final acceptance criteria

- `baseline.json` exists, conforms to [docs/ANSWER_SCHEMA.md](../docs/ANSWER_SCHEMA.md),
  has `viewpoint: "inferred-from-sources"` and exactly 222 entries under
  `.answers`. Every entry has the locked 13 fields, no extras.
- Every `evidence/<id>.json` has at least one scripture citation OR one
  source-doc hit OR one web source (web alone permitted only if scripture
  is silent and source-docs are empty; flag this).
- No record violates the moral entailment
  (`cult_marker_if_denied=true` ⇒ `would_die_for=true`).
- `baseline-report.md` summarizes affirms/confidence distribution, flags, and
  prioritizes `confidence=low` essential/convictional questions for elder review.
- `baseline-conflicts.md` lists every conflict requiring manual resolution,
  with both positions and the relevant source-doc excerpts.
- No PDF rendering performed. Renderers were deleted; fresh ones come later.
