# Question Schema (`questions.json`)

> Locked envelope and field shape. The 231 question entries are scheduled for a separate phase-3 reframe pass (verdict-pre-loading audit + overlap disambiguation); the schema here defines what that reframe must conform to.

The question bank is universal. Every respondent (inferred-baseline run, trusted-elder collaborators, the project owner) answers the same 231 questions. Schemas for the answer files live in [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md). The methodology that produces the inferred baseline is in [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md).

---

## Top-level envelope

```json
{
  "$schema_version": "2.0",
  "formation_under_examination": "Plymouth Brethren-adjacent: classical Reformed Protestant orthodoxy plus Brethren distinctives",
  "judging_panel": ["critical_apparatus", "interlinear", "concordance"],
  "research_panel": ["counter_witness_traditions"],
  "location_context": "evaluating churches across denominations",
  "generated_at": "<ISO date>",
  "description": "<string>",
  "category_index": ["Bibliology", "Theology Proper", "..."],
  "field_definitions": { ... },
  "stats": { ... },
  "questions": [ <Question>, ... ]
}
```

### Envelope fields

- **`formation_under_examination`**: records the doctrinal formation Ebenezer is testing. **Not the rubric.** The whole point of the project is to test whether this formation's reading survives primary-source scrutiny.
- **`judging_panel`**: the rubric. Critical apparatus + interlinear + concordance. These three settle every verdict. Counter-witness traditions and confessions are NOT in the panel.
- **`research_panel`**: counter-witness traditions consulted as diagnostic information. They are recorded in `counter_witness[]` for every question so the reader sees how each major lineage reads the same lexical text. They do NOT vote on any verdict field.

See [AUTHORITY_HIERARCHY.md](AUTHORITY_HIERARCHY.md) for the authority tier scale (which is independent of the panel) and [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md) for how each panel member is consulted.

---

## Question record (10 fields)

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable kebab-case slug. Prefix `doc-` for doctrine, `prc-` for practice, `cult-` for cult marker, `het-` for heterodoxy marker. |
| `category` | string | One of `category_index` (e.g. "Bibliology", "Christology") |
| `subcategory` | string | Optional finer grouping; null if not applicable. |
| `kind` | enum | `doctrine` \| `practice` |
| `statement` | string | The proposition under examination. **Phase-3 reframe target**: must be a neutral interrogative-equivalent proposition, not a verdict assertion. See `field_definitions.statement` for current and target guidance. |
| `scripture_anchors` | string[] | OSIS-normalized seed references. Inferred-baseline subagents extend this via concordance traversal; the anchors are not a closed list. |
| `confessional_anchors` | string[] | Recorded as **informational research aids** during the inferred run, NOT as authority. Subagents read confessional anchors to characterize how each tradition reads the passage; they do not vote on the verdict. See [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md). |
| ~~`tier`~~ | (removed) | The `tier` field has been **abolished from the question bank**. Pre-assigning a tier was a verdict-pre-load. Standing (cult-grade / gospel-essential / convictional / preference / adiaphora) is now **inferred from the answer's boolean pattern** per [ANSWER_SCHEMA.md "Standings inferred from boolean patterns"](ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns). The subagent judges each verdict boolean independently per question on canonical evidence; standing emerges from the resulting pattern. |
| `historical_consensus` | enum | `unanimous_lineages` \| `divided_lineages` \| `minority_lineages` \| `outside_majority_lineages` \| `outside_historic_christianity`. **Descriptive metadata about church history, not a verdict-shaper.** Records how the major lineages have actually confessed the doctrine across history. The terms are descriptive (which lineages affirm) rather than normative (whether the doctrine is true); normative judgment belongs to apparatus + interlinear + concordance, recorded in `evidence/<id>.json`. |
| `brethren_distinctive` | bool | True if the position is a Plymouth Brethren distinctive. Marker for what counts as a *defendant claim*, useful for downstream analysis (e.g., flagging when a verdict aligns suspiciously with brethren-distinctive positions). |

---

## Field-level guidance (canonical, lives in `questions.json` `field_definitions`)

### `statement`, neutral form (phase-3 target)

The `statement` field is the proposition the inferred-baseline run tests. Two failure modes the phase-3 rewrite must eliminate:

**Verdict pre-loading.** The current corpus contains statements like *"Additions (Book of Mormon, Ellen G. White's writings, Branham's tape ministry, Watch Tower publications…) are cult-grade error."* The verdict is in the proposition; the inferred-baseline subagent can only confirm or contradict the prefab conclusion. Phase-3 target: rewrite to *"No revelation given after the apostolic age binds the conscience or stands on par with Scripture; the canon is closed and sufficient."*, the named carriers are evidence the subagent surfaces in `notes`, not part of the proposition.

**Confessional vocabulary as if neutral.** Statements that smuggle Reformed-confessional vocabulary (*"sola fide"*, *"forensic"*, *"cult-grade"*, *"heterodox"*) into the proposition itself. These bias the verdict because the vocabulary already implies the framework that makes the verdict obvious. Phase-3 target: state the proposition in tradition-neutral terms; let the subagent's evidence decide whether the framework's vocabulary applies.

**Overlap.** Some current questions test the same proposition under different angles (e.g., separate questions on `doc-substitutionary-atonement` and `doc-penal-substitution`, or `doc-scripture-inerrancy` and `doc-scripture-infallibility`), forcing subagents to give vague answers to avoid conflating with the adjacent question. Phase-3 target: either merge into one question or sharpen each statement so the distinction is mechanical.

### `scripture_anchors`

OSIS-normalized seed references. The inferred-baseline subagent extends these via concordance traversal, every Strong's lemma in the seed verses is spider-mapped to the entire canon. The `scripture_anchors` list is a starting point for retrieval, not a closed list of "the passages this doctrine rests on."

### `confessional_anchors`

Records the confessions that historically address this proposition. Subagents check the named confession to characterize how it reads the passage (recorded under `evidence.counter_witness[]` with the appropriate `tradition` tag). The confession is NOT authoritative for the verdict; it is research data showing how a particular tradition reads the same text.

### `tier` (abolished)

The `tier` field on questions has been removed. Pre-assigning a tier at the question level was a verdict-pre-load: it told the subagent how to weight the question before evidence was read. Under the revised methodology, **standing emerges from the answer's boolean pattern**, not from a pre-set tier on the question.

Each subagent judges every verdict boolean (`would_die_for`, `cult_marker_if_denied`, the five engagement-ladder booleans, the two personal-decision booleans) independently per question on its own canonical evidence. The resulting pattern projects to a standing (cult-grade, gospel-essential, convictional, preference, adiaphora) per [ANSWER_SCHEMA.md "Standings inferred from boolean patterns"](ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns).

Scripture itself signals where doctrines sit: Galatians 1:8-9 anathema language, 1 Corinthians 15:1-4 first-importance framing, 1 John 4:1-3 spirit-of-antichrist test, 2 John 7-11 do-not-receive instruction, and Romans 14 weak-and-strong territory are the canonical markers. The subagent recognizes these signals per question; the orchestrator does not pre-classify.

### `brethren_distinctive`

True if the position is distinctive to Plymouth Brethren tradition (as opposed to broadly held by orthodox Christianity). Used during the inferred-baseline run to flag when a verdict aligns with a brethren-distinctive, not as a disqualifier, but as a sign the verdict requires extra counter-witness scrutiny. The 231-question corpus currently has ~40 entries marked brethren_distinctive=true.

---

## Standing (inferred from answer, not pre-assigned to question)

Standing emerges from the answer's boolean pattern. The five recognized standings are documented in [ANSWER_SCHEMA.md "Standings inferred from boolean patterns"](ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns):

| Standing | Inferred when |
|---|---|
| `cult-grade` | `cult_marker_if_denied=true` (and `would_die_for=true` by entailment) |
| `gospel-essential` | `would_die_for=true`, `cult_marker_if_denied=false` |
| `convictional` | `would_die_for=false`, `would_be_member=false`, `would_visit=true` |
| `preference` / `important` | `would_be_member=true` |
| `adiaphora` | all severity and engagement-ladder booleans permissive |

Scripture's own signals (Galatians 1:8-9 anathema, 1 Corinthians 15:1-4 first-importance, 1 John 4:1-3 spirit-of-antichrist, 2 John 7-11 do-not-receive, Romans 14 weak-and-strong) are recognized by the subagent per question. The orchestrator does not pre-classify.

---

## Locked rules

1. **Envelope keys are stable.** `formation_under_examination`, `judging_panel`, `research_panel`, `category_index`, `field_definitions`, `stats`, `questions`. Renaming requires migration across this doc, the validator, and the renderer. The `tier_definitions` envelope key and the `tier` field on questions have been abolished; standing is inferred from the answer's boolean pattern.
2. **Field names within `questions[]` are stable.** Renaming requires coordinated migration across all artifacts.
3. **Adding a question** requires stubbing it in every existing answer file (`baseline.json`, `responses/*.json`, `consolidated.json`).
4. **Removing a question** is destructive. Only do this if the question itself is malformed.
5. **Phase-3 statement reframes** rewrite `statement` text but MUST preserve the `id` (so existing answer-file entries continue to key correctly).
6. **Public-release scope**: `questions.json` is publishable.
