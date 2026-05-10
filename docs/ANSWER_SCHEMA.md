# Answer Schema for `baseline.json` / `responses/<id>.json` / `consolidated.json`

> Locked as of 2026-05-10. All three answer files share this exact 13-field shape; they differ only in the envelope's `viewpoint` field.

The question bank that these answer-records key against is documented in [QUESTION_SCHEMA.md](QUESTION_SCHEMA.md).

---

## Design philosophy

**Booleans only.** Minimum cognitive load for trusted-elder respondents and clean aggregation for downstream analysis. No enums for severity, no enums for engagement. The standing (cult-grade / gospel-essential / convictional / preference / adiaphora) is **inferred from the boolean pattern**, not stored as a separate enum.

**Slugs are the labels.** Each boolean's field name reads naturally as a checkbox label. A respondent looking at the questionnaire reads the question's `statement`, then ticks each label that matches their stance. No verbose question wordings to wade through.

---

## Top-level envelope

```json
{
  "$schema_version": "1.0",
  "viewpoint": "inferred-from-sources" | "individual:<respondent_id>" | "consolidated",
  "respondent_id": "<string, omitted for inferred-from-sources>",
  "generated_at": "<ISO date>",
  "answers": [ <Answer>, ... ]
}
```

---

## Answer record (13 fields)

```json
{
  "id": "<matches Question.id>",
  "affirms": true | false | null,
  "rationale": "<1-2 sentences scripturally grounded>",

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
}
```

---

## Field semantics

### Identity & rationale (3 fields)

| Field | Label | Notes |
|---|---|---|
| `id` |  | Matches a `Question.id` |
| `affirms` | Affirm | `true` = affirms the statement; `false` = denies; `null` = no committed answer (covers both intentional-open and uncertain) |
| `rationale` |  | Free-form 1-2 sentence justification |

### Severity (2 booleans)

Each respondent reads the `statement` and ticks if true:

| Field | Label |
|---|---|
| `would_die_for` | Would die for |
| `cult_marker_if_denied` | Cult marker if denied |

**Moral entailment**: `cult_marker_if_denied → would_die_for`. A respondent cannot consistently classify a group as cult-grade without willingness to die for the truth they deny. Validate at parse time.

### Engagement ladder (5 booleans, monotonic by intent)

The implicit prompt for each is: *"if a church taught the opposite of this statement…"*

| Field | Label |
|---|---|
| `would_visit_if_otherwise` | Would visit if otherwise |
| `would_participate_if_otherwise` | Would participate if otherwise |
| `would_serve_if_otherwise` | Would serve if otherwise |
| `would_be_member_if_otherwise` | Would be member if otherwise |
| `would_let_children_be_taught_otherwise` | Would let children be taught otherwise |

The 5 rungs are monotonic by intent: letting children be taught is a stronger commitment than personal membership; membership implies serving capacity; etc.

### Other personal decisions (2 booleans)

| Field | Label |
|---|---|
| `would_marry_if_held_otherwise` | Would marry if held otherwise |
| `would_publicly_correct_if_otherwise` | Would publicly correct if otherwise |

Both orthogonal to severity. Different respondents legitimately diverge on marriage compatibility and public-correction style at the same severity level.

### Free-form (1 field)

| Field | Notes |
|---|---|
| `notes` | Free-form context, fruit-vs-precision nuance, named carriers, qualifications |

---

## Standings inferred from boolean patterns

No separate enum needed. The boolean pattern IS the classification:

| Pattern | Standing |
|---|---|
| `cult_marker_if_denied=true` (and `would_die_for=true` by entailment) | **Cult-grade**. Denying body is classifiable as a cult |
| `would_die_for=true`, `cult_marker_if_denied=false` | **Gospel-essential** but not cult-classifying (sola fide, inerrancy, virgin birth) |
| `would_die_for=false`, `would_be_member_if_otherwise=false`, `would_visit_if_otherwise=true` | **Convictional**. Membership-breaking but visit/participate possible |
| `would_be_member_if_otherwise=true` | **Preference / important**. Full membership compatible |
| All severity & ladder booleans permissive | **Adiaphora** |

---

## Aggregate metrics (derivable, not stored)

| Metric | Formula | Range |
|---|---|---|
| `engagement_score` | sum(visit, participate, serve, be_member, let_children_be_taught) | 0–5 |
| `essentialness_score` | sum(would_die_for, cult_marker_if_denied) | 0–2 |
| `personal_lock_score` | sum(would_marry_if_held_otherwise, would_publicly_correct_if_otherwise) | 0–2 |

Use these for cross-respondent aggregation during consolidation, for charting confidence/disagreement across the trusted-elder cohort, and for thresholding downstream evaluations.

---

## Evidence record (`evidence/<question_id>.json`)

Produced during the inferred-baseline run only (NOT for trusted-elder responses). One file per question. The file IS the audit trail.

```json
{
  "id": "<matches Question.id>",
  "answer": { <Answer>, ... },
  "evidence": {
    "scripture": [
      {
        "ref": "John 1:1",
        "key_term": "λόγος (logos)",
        "force": "the divine self-expression, applied as a divine name in v.1c",
        "supports": true
      }
    ],
    "confessional_verifications": [
      { "anchor": "WCF 1.4", "verified": true, "key_phrase": "..." }
    ],
    "source_docs": [
      {
        "chunk_id": "baptism_and_communion_17",
        "authority_level": 3,
        "score": 0.91,
        "excerpt": "<=400 chars, names [REDACTED]>",
        "implies": "affirm" | "deny" | "open" | "silent"
      }
    ],
    "web": [
      { "url": "...", "stance": "supports" | "opposes" | "nuance", "quote": "<=200 chars" }
    ],
    "confidence": "high" | "medium" | "low",
    "flags": ["<one short string per flag>"]
  }
}
```

`confidence` is the most important field for downstream trusted-elder review:
- `high`: scripture/interlinear clearly supports AND source-docs align
- `medium`: scripture clear but source-docs silent or partially divergent, OR the question is contested within orthodox tradition
- `low`: scripture silent or contested AND source-docs unhelpful, OR verdict required heavy inference. Trusted elders should scrutinize these first.

**Anonymization**: every personal name except "Ebenezer" must be `[REDACTED]` in `source_docs.excerpt` and anywhere else.

---

## Locked rules

1. **Field names are stable.** Renaming requires coordinated migration across this doc, the migration script, the renderer, every existing answer file, and the [personal_beliefs_baseline](../) memory.
2. **The 13-field shape is identical** across `baseline.json`, `responses/*.json`, and `consolidated.json`. Differences live only in the envelope.
3. **`evidence/*.json` is per-question, produced only during the inferred-baseline run.** Trusted-elder responses don't carry evidence files.
4. **`viewpoint` values** are the only allowed envelope discriminators: `inferred-from-sources` | `individual:<id>` | `consolidated`.
5. **Public-release scope**: `baseline.json`, `consolidated.json`, `evidence/` may be published. `responses/*.json` are private (gitignored).
6. **Slug-as-label**: the questionnaire UI / PDF uses the field slug (with underscores replaced by spaces) as the checkbox label. No verbose question text. Brevity is a feature.
