# Question Schema (`questions.json`)

> Locked envelope and field shape. The 221 question entries are scheduled for a separate phase-3 reframe pass (verdict-pre-loading audit + overlap disambiguation); the schema here defines what that reframe must conform to.

The question bank is universal. Every respondent (inferred-baseline run, trusted-elder collaborators, the project owner) answers the same 221 questions. Schemas for the answer files live in [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md). The methodology that produces the inferred baseline is in [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md).

---

## Top-level envelope

```json
{
  "$schema_version": "2.0",
  "formation_under_examination": "Plymouth Brethren-adjacent: classical Reformed Protestant orthodoxy plus Brethren distinctives",
  "judging_panel": ["critical_apparatus", "interlinear", "concordance", "counter_witness_traditions"],
  "location_context": "evaluating churches across denominations",
  "generated_at": "<ISO date>",
  "description": "<string>",
  "tier_definitions": {
    "essential":     "<see Tier definitions below>",
    "convictional":  "...",
    "important":     "...",
    "preference":    "...",
    "adiaphora":     "..."
  },
  "category_index": ["Bibliology", "Theology Proper", "..."],
  "field_definitions": { ... },
  "stats": { ... },
  "questions": [ <Question>, ... ]
}
```

### Envelope fields

- **`formation_under_examination`**: records the doctrinal formation Ebenezer is testing. **Not the rubric.** The whole point of the project is to test whether this formation's reading survives primary-source scrutiny.
- **`judging_panel`**: the rubric. Critical apparatus + interlinear + concordance + counter-witness traditions. Confessions (Reformed or otherwise) are NOT in the panel; they are an information layer.

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
| `tier` | enum | `essential` \| `convictional` \| `important` \| `preference` \| `adiaphora`. Severity assessment derived from cross-tradition consensus on the doctrinal stake, not from any single tradition. |
| `historical_consensus` | enum | `orthodox` \| `divided` \| `minority` \| `heterodox` \| `heretical`. **"Orthodox" means cross-tradition consensus** (patristic + magisterial + Lutheran + Anglican + Reformed + Methodist + Anabaptist + Pentecostal converge), not Reformed-Baptist consensus. |
| `brethren_distinctive` | bool | True if the position is a Plymouth Brethren distinctive. Marker for what counts as a *defendant claim* — useful for downstream analysis (e.g., flagging when a verdict aligns suspiciously with brethren-distinctive positions). |

---

## Field-level guidance (canonical, lives in `questions.json` `field_definitions`)

### `statement` — neutral form (phase-3 target)

The `statement` field is the proposition the inferred-baseline run tests. Two failure modes the phase-3 rewrite must eliminate:

**Verdict pre-loading.** The current corpus contains statements like *"Additions (Book of Mormon, Ellen G. White's writings, Branham's tape ministry, Watch Tower publications…) are cult-grade error."* The verdict is in the proposition; the inferred-baseline subagent can only confirm or contradict the prefab conclusion. Phase-3 target: rewrite to *"No revelation given after the apostolic age binds the conscience or stands on par with Scripture; the canon is closed and sufficient."* — the named carriers are evidence the subagent surfaces in `notes`, not part of the proposition.

**Confessional vocabulary as if neutral.** Statements that smuggle Reformed-confessional vocabulary (*"sola fide"*, *"forensic"*, *"cult-grade"*, *"heterodox"*) into the proposition itself. These bias the verdict because the vocabulary already implies the framework that makes the verdict obvious. Phase-3 target: state the proposition in tradition-neutral terms; let the subagent's evidence decide whether the framework's vocabulary applies.

**Overlap.** Some current questions test the same proposition under different angles (e.g., separate questions on `doc-substitutionary-atonement` and `doc-penal-substitution`, or `doc-scripture-inerrancy` and `doc-scripture-infallibility`), forcing subagents to give vague answers to avoid conflating with the adjacent question. Phase-3 target: either merge into one question or sharpen each statement so the distinction is mechanical.

### `scripture_anchors`

OSIS-normalized seed references. The inferred-baseline subagent extends these via concordance traversal — every Strong's lemma in the seed verses is spider-mapped to the entire canon. The `scripture_anchors` list is a starting point for retrieval, not a closed list of "the passages this doctrine rests on."

### `confessional_anchors`

Records the confessions that historically address this proposition. Subagents check the named confession to characterize how it reads the passage (recorded under `evidence.counter_witness[]` with the appropriate `tradition` tag). The confession is NOT authoritative for the verdict; it is research data showing how a particular tradition reads the same text.

### `tier`

Severity assessment. Tier is derived from the doctrinal stake under cross-tradition consensus, NOT from any single tradition's calibration:
- **`essential`** = Nicene-Chalcedonian-Apostolic foundations: Trinity, full deity+humanity of Christ, bodily resurrection, Scripture as inspired-authoritative. Doctrines all 8 lineages converge on. Denial = false gospel.
- **`convictional`** = Clear from apparatus + concordance, but with legitimate intramural dispute across the 8 lineages (e.g., justification theory, baptism mode/recipients, sacramental count, cessationism).
- **`important`** = Matters significantly but does not break fellowship. Multiple traditions disagree without breaking communion.
- **`preference`** = Methodological or practical. Worship style, communion frequency, calendar customs.
- **`adiaphora`** = Truly indifferent. Freedom of conscience.

### `brethren_distinctive`

True if the position is distinctive to Plymouth Brethren tradition (as opposed to broadly held by orthodox Christianity). Used during the inferred-baseline run to flag when a verdict aligns with a brethren-distinctive — not as a disqualifier, but as a sign the verdict requires extra counter-witness scrutiny. The 221-question corpus currently has ~40 entries marked brethren_distinctive=true.

---

## Tier definitions

| Tier | Meaning |
|---|---|
| `essential` | Core gospel and Trinitarian-Chalcedonian boundaries. Denial means false gospel or cult-grade error. Always teach to children, always correct, never become member where denied. |
| `convictional` | Clear scriptural conviction that nonetheless has legitimate intramural dispute across orthodox traditions. Membership-level threshold. Would not compromise on doctrine, but visit/participate is usually fine where denied. |
| `important` | Matters significantly but does not break fellowship. Reservations about membership, but not absolute. Marry across is usually fine. |
| `preference` | Methodological or practical. Membership across is fine. Worship style, communion frequency, calendar customs. |
| `adiaphora` | Truly indifferent. Freedom of conscience. All thresholds permissive. |

Tier on the question side is the **canonical** severity assessment. Per-respondent severity is captured indirectly through the boolean pattern in their answer file. See [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns).

---

## Locked rules

1. **Envelope keys are stable.** `formation_under_examination`, `judging_panel`, `tier_definitions`, `category_index`, `field_definitions`, `stats`, `questions` — renaming requires migration across this doc, the validator, and the renderer.
2. **Field names within `questions[]` are stable.** Renaming requires coordinated migration across all artifacts.
3. **Adding a question** requires stubbing it in every existing answer file (`baseline.json`, `responses/*.json`, `consolidated.json`).
4. **Removing a question** is destructive. Only do this if the question itself is malformed; otherwise leave it and mark `tier=adiaphora`.
5. **Phase-3 statement reframes** rewrite `statement` text but MUST preserve the `id` (so existing answer-file entries continue to key correctly).
6. **Public-release scope**: `questions.json` is publishable.
