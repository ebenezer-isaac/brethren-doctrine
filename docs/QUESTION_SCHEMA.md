# Question Schema (`questions.json`)

> Locked as of 2026-05-10. Adding or removing a question requires updating every existing answer file with a stub entry. Renaming a field requires coordinated migration across this doc, the migration script, the renderer, and the [personal_beliefs_baseline](../) memory.

The question bank is universal. Every respondent (inferred-baseline run, trusted-elder collaborators, the project owner) answers the same 222 questions. Schemas for the answer files live in [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md).

---

## Top-level envelope

```json
{
  "$schema_version": "2.0",
  "tradition_baseline": "Plymouth Brethren-adjacent: classical Reformed Protestant orthodoxy plus Brethren distinctives",
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
  "questions": [ <Question>, ... ]
}
```

---

## Question record (10 fields)

| Field | Type | Notes |
|---|---|---|
| `id` | string | slug, unique, stable across schema versions |
| `category` | string | one of `category_index` (e.g. "Bibliology", "Christology") |
| `subcategory` | string | free-form within category |
| `kind` | enum | `doctrine` \| `practice` |
| `statement` | string | the affirmable proposition; drives `affirms` semantics on the answer side |
| `scripture_anchors` | string[] | e.g. `["Romans 6:3-4", "Acts 2:38"]`. OSIS-normalized |
| `confessional_anchors` | string[] | e.g. `["WCF 28.4", "1689 LBC 29"]`. Cross-checked against the [locked confession set](../tools/derive_baseline_prompt.md) during the inferred run |
| `tier` | enum | `essential` \| `convictional` \| `important` \| `preference` \| `adiaphora`. Canonical Brethren-baseline severity |
| `historical_consensus` | enum | `orthodox` \| `divided` \| `minority` \| `heterodox` \| `heretical` |
| `brethren_distinctive` | bool | true if the position is a Plymouth Brethren distinctive |

---

## Tier definitions

| Tier | Meaning |
|---|---|
| `essential` | Core gospel and Trinitarian boundaries. Denial means false gospel or cult-grade error. Always teach to children, always correct, never become member where denied. |
| `convictional` | Clear scriptural conviction. Membership-level threshold. Would not compromise on doctrine, but visit/participate is usually fine where denied. |
| `important` | Matters significantly but does not break fellowship. Reservations about membership, but not absolute. Marry across is usually fine. |
| `preference` | Methodological or practical. Membership across is fine. Worship style, communion frequency, calendar customs. |
| `adiaphora` | Truly indifferent. Freedom of conscience. All thresholds permissive. |

Tier on the question side is the **canonical** severity assessment. Per-respondent severity is captured indirectly through the boolean pattern in their answer file. See [ANSWER_SCHEMA.md](ANSWER_SCHEMA.md#standings-inferred-from-boolean-patterns).

---

## Locked rules

1. **Field names are stable.** Renaming requires coordinated migration across all artifacts.
2. **Adding a question** requires stubbing it in every existing answer file (`baseline.json`, `responses/*.json`, `consolidated.json`).
3. **Removing a question** is destructive. Only do this if the question itself is malformed; otherwise leave it and mark `tier=adiaphora`.
4. **Public-release scope**: `questions.json` is publishable.
