# Evidence Schema v3.0

Pipeline 2 output schema. One file per doctrinal proposition in `questions.json`. Filename pattern: `evidence/<question_id>.json`.

The Pydantic v2 model lives at `pipeline2/evidence_schema.py` with `extra="forbid"` at every level. The post-processor that computes `lexical_score` lives at `pipeline2/score_calc.py` and is a pure function.

## Schema versions

- v3.0 (current): lean schema, lexical-only, no counter-witness, no personal-decision booleans, no denominational landscape in lay_summary.
- v2.0 (archived 2026-05-12): mixed lexical and cultural fields in one document. The 111 evidence files at the prior session's commit `12921bb` use v2.0. They are archived; the new Pipeline 2 produces v3.0.
- v1.0 (deleted 2026-05-10): pre-greenfield schema.

## Top-level shape

```json
{
  "$schema_version": "3.0",
  "id": "doc-trinity",
  "question_id": "doc-trinity",
  "generated_at": "2026-05-12T18:00:00Z",
  "pipeline_version": "v1",
  "model": "claude-opus-4-7",

  "verdict": { ... },
  "lexical_evidence": { ... },
  "variants": { ... },
  "hermeneutics": { ... },
  "stem_audit": { ... },
  "lay_summary": "...",
  "citations": [ ... ],
  "license_audit": { ... },
  "flags": []
}
```

## Identity fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `$schema_version` | string | yes | Must equal `"3.0"` |
| `id` | string | yes | Echoes `question_id`; kept for legacy tooling |
| `question_id` | string | yes | Must match a `questions[].id` in `questions.json` |
| `generated_at` | ISO 8601 UTC string | yes | When Pipeline 2 emitted this file |
| `pipeline_version` | string | yes | Currently `"v1"` |
| `model` | string | yes | Model slug, e.g. `"claude-opus-4-7"` |

Pydantic validator: `id == question_id`.

## verdict block

```json
{
  "verdict": {
    "affirms": true | false | null | "disputed",
    "lexical_score": null,
    "confidence": "high | medium | low",
    "variant_robust": <bool>,
    "pan_canonical": <bool>,
    "rationale": "<2-5 sentence dense rationale>"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `affirms` | enum: `true`, `false`, `null`, `"disputed"` | yes | Four-state per architecture decision |
| `lexical_score` | float 0.0-1.0 or null | no | **Always null at LLM emission time.** Post-processor fills it |
| `confidence` | enum: `"high"`, `"medium"`, `"low"` | yes | Reflects lexical clarity, not lineage agreement |
| `variant_robust` | bool | yes | Verdict survives all plausible variant readings |
| `pan_canonical` | bool | yes | Anchor lemmas span multiple canon sections |
| `rationale` | string | yes | 2-5 sentences citing key lemmas and verse refs |

### `affirms` semantics

- `true` — lexical pattern across the canon supports the proposition.
- `false` — lexical pattern contradicts it.
- `null` — lexical evidence is genuinely insufficient (sparse anchor lemmas, narrow textual base).
- `"disputed"` — lexical pattern is materially contested across the canon (e.g., paedobaptism, women in eldership) such that multiple defensible readings exist.

### `confidence` semantics

- `high` — dense anchor_lemmas, `pan_canonical: true`, complicating_texts addressed, `variant_robust: true`.
- `medium` — some of the above with gaps.
- `low` — sparse lemma evidence OR complicating texts unresolved OR verdict variant-sensitive.

## lexical_evidence block

```json
{
  "lexical_evidence": {
    "anchor_lemmas": [
      {
        "strong": "H3068",
        "lemma": "YHWH",
        "transliteration": "yhwh",
        "occurrences_in_canon": 6828,
        "in_anchors": true
      }
    ],
    "concordance_traversed": ["H3068", "H430", "H259", "G2316", "G3056"],
    "scripture": [ ... ],
    "cross_refs_invoked": [ ... ],
    "complicating_texts": [ ... ]
  }
}
```

### anchor_lemmas

The canonical lemmas the verdict rests on. Drives `pan_canonical` and `anchor_lemma_factor` in the score formula.

```json
{
  "strong": "<canonical Strong's; H#### or G####>",
  "lemma": "<UTF-8 lemma>",
  "transliteration": "<Latin transliteration>",
  "occurrences_in_canon": <int>,
  "in_anchors": <bool>
}
```

Validator: `strong` matches regex `^[HG]\d{4}[A-Z]?$`.

### concordance_traversed

Flat list of all Strong's codes the subagent examined while deriving the verdict (broader than anchor_lemmas; includes semantic-domain neighbors). Drives `concordance_breadth_factor`.

### scripture

The verses cited as evidence. Each entry:

```json
{
  "ref": "Deut.6.4",
  "key_terms": [{"strong": "H3068", "lemma": "YHWH"}],
  "force": "<dense description of what this verse contributes>",
  "supports": "for | complicates | neutral",
  "genre": "law | narrative | wisdom | prophecy | gospel | epistle | apocalyptic",
  "figures": ["metaphor", "simile", "personification", "chiasm", "merism", "idiom", "hyperbole"],
  "macula_anchor": "OT.Deut.06.004.001-005 (optional)"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `ref` | OSIS BCV string | yes | e.g. `John.1.1` |
| `key_terms` | array | yes | At least 1 entry |
| `force` | string | yes | Dense lexical reasoning |
| `supports` | enum | yes | `for`, `complicates`, `neutral` |
| `genre` | enum | yes | One of 7 |
| `figures` | array | yes | Empty array if no figures |
| `macula_anchor` | string | no | Token-level pointer for reproducibility |

### cross_refs_invoked

Cross-references the subagent followed during concordance walking.

```json
{
  "from": "Deut.6.4",
  "to": "Mark.12.29",
  "source": "openbible | tsk",
  "votes": 130
}
```

### complicating_texts

Verses that could be read against the verdict. Each must be addressed.

```json
{
  "ref": "Mark.13.32",
  "addressed": true,
  "resolution": "communicatio idiomatum: the Son in assumed human nature does not access divine omniscience for that disclosure"
}
```

`complicating_resolved_factor` in the score is the fraction of `complicating_texts[]` with `addressed: true`.

## variants block

```json
{
  "variants": {
    "verdict_variant_sensitive": <bool>,
    "variant_units_examined": [
      {
        "ref": "1John.5.7",
        "variant_id": "comma_johanneum",
        "verdict_impact": "none | minor | material",
        "note": "Verdict holds without the comma."
      }
    ],
    "ecm_status": "ecm-published | ecm-shadow | n/a",
    "note": "<optional overall note>"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `verdict_variant_sensitive` | bool | yes | True if any contested variant materially affects the verdict |
| `variant_units_examined` | array | yes | Empty array if no variants in play |
| `ecm_status` | enum | yes | `ecm-published` if Layer 1 has ECM data for the cited books; `ecm-shadow` if NA28-apparatus-only; `n/a` for OT-only doctrines |
| `note` | string or null | no | Overall variant-coverage note |

In v1 (CBGM deferred), `ecm_status` is typically `n/a` or `ecm-shadow`; `variant_units_examined` is typically empty.

## hermeneutics block

```json
{
  "hermeneutics": {
    "primary_method": "grammatico-historical | redemptive-historical | quadriga | patristic-typological | accommodation",
    "frameworks_in_play": ["covenant_theology", "dispensationalism", "new_covenant_theology", "progressive_covenantalism", "historic_premillennialism"],
    "analogia_scripturae": <bool>,
    "progressive_revelation": <bool>,
    "competing_lens_verdicts": [],
    "notes": "<>"
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `primary_method` | enum (5 values) | yes | Default `grammatico-historical` |
| `frameworks_in_play` | array | yes | Empty if no framework is contested |
| `analogia_scripturae` | bool | yes | Was scripture-interprets-scripture invoked |
| `progressive_revelation` | bool | yes | Does the verdict use progressive revelation reasoning |
| `competing_lens_verdicts` | array | yes | Empty if no competing lens produces a different verdict |
| `notes` | string | yes | Explanation |

If multiple frameworks produce different verdicts (e.g., covenant theology vs dispensationalism on a millennium question), `competing_lens_verdicts` records each:

```json
{
  "framework": "covenant_theology",
  "verdict": "affirms",
  "rationale": "<>"
}
```

## stem_audit block

```json
{
  "stem_audit": {
    "verdict_preloaded": <bool>,
    "neutralized_form": "<string or null>",
    "notes": "<>"
  }
}
```

Flags whether `questions.json[].statement` smuggles a verdict. Examples:
- "Scripture is the sole and final authority" smuggles `sola scriptura` (Reformed framing).
- "Believer's baptism is the New Testament pattern" assumes the verdict.

If `verdict_preloaded: true`, `neutralized_form` provides a tradition-neutral rephrasing. The verdict is still derived on the original stem; the neutralized form is a flag for human review.

## lay_summary

A single string field, 100-500 words, plain language, lexical reasoning only.

Constraints:
- No em-dashes (—) or en-dashes (–).
- No "the historic Christian position is..." framing (that's cultural overlay).
- No "Reformed teach X; Catholics teach Y" (that's cultural overlay).
- Plain prose that explains what the lexical pattern says.

Validator: `100 <= word_count <= 500`; rejects em-dash and en-dash characters.

## citations array

Sources actually cited in the verdict. Each entry:

```json
{
  "type": "morphology | syntax | cross_ref | variant | interlinear | lexicon",
  "source": "<source slug from docs/LICENSE_TAGGING.md>",
  "license": "<license slug>",
  "redistribute": <bool>,
  "ref": "<verse ref or lemma id>"
}
```

Allowed `source` slugs (from `docs/LICENSE_TAGGING.md`):
- `MACULA-Greek`, `MACULA-Hebrew`, `MACULA-Hebrew-marble-sdbh`, `MACULA-Greek-louw-nida`
- `STEPBible-TAHOT`, `STEPBible-TAGNT`, `STEPBible-TVTMS`, `STEPBible-TBESH`, `STEPBible-TBESG`, `STEPBible-TFLSJ`
- `OSHB-morphology`
- `MorphGNT-morphology`
- `SBLGNT-text`, `Nestle1904-text`
- `ETCBC-BHSA`, `ETCBC-Peshitta`, `ETCBC-syrnt`, `ETCBC-DSS`
- `OpenBible-cross-refs`, `TSK`
- `Theographic-Bible-Metadata`
- `INTF-NTVMR`, `open-cbgm-3-john-sample`
- `BibleHub-interlinear` (cross-validation only, snippet-cite only)

TTESV (STEPBible Tagged ESV) is **deliberately excluded** from the allowed citation slugs even though it is registered in `docs/LICENSE_TAGGING.md`. Reason: TTESV is a CC-BY-NC tagged translation output, not a lexical primary source. Pipeline 2 cites lexical primaries (apparatus, interlinear, concordance) only. TTESV is ingested into the lexical store (Phase 02) for translation alignment but is not promotable to verdict citations.

Forbidden source slugs: any confession, magisterial document, denominational commentary, or Reformed-aligned commentary site. Pipeline 2 cannot see these (cultural store air-gap), and the schema validator rejects them.

## license_audit block

```json
{
  "license_audit": {
    "sources_used": [
      {"source": "MACULA-Greek", "license": "CC-BY-4.0", "redistribute": true},
      {"source": "ETCBC-BHSA", "license": "CC-BY-NC-4.0", "redistribute": false}
    ],
    "evidence_safe_to_publish": false,
    "non_redistributable_reason": "Cites BHSA syntactic features under CC-BY-NC-4.0."
  }
}
```

Derivation:
```
evidence_safe_to_publish = all(check_redistribute(license=src.license, mode="bulk", ...)["allowed"] for src in sources_used)
```

If `evidence_safe_to_publish: false`, the orchestrator records the question id in `evidence/_non_redistributable.txt`.

## flags array

Free-form list of slug-style flags. Standard slugs:
- `ecm-shadow` — variant data is NA28-apparatus-shadow, not ECM-published
- `concordance-thin` — anchor_lemmas count is below a threshold (e.g., < 3)
- `variant-sensitive` — `verdict_variant_sensitive: true`
- `lexically-disputed` — verdict is `"disputed"` rather than true/false/null
- `cross-tradition-divergent` — set by Pipeline 3 synthesis, not Pipeline 2 (verdict diverges from majority cultural-overlay stance; informational only, does not change verdict)
- `complicating-unresolved` — at least one complicating text has `addressed: false`

## Pipeline 2 prompt contract

The lean prompt that Pipeline 2 subagents follow lives at `docs/phase_prompts/pipeline2_verdict.md`. It specifies:
- Hard constraints (no cultural sources, no LLM-written score, no personal-decision booleans).
- Input schema (lexical_context_bundle).
- Output schema (this document).
- Verdict guidance per `affirms` and `confidence` values.
- Stem audit guidance.
- Citation discipline.
- Acceptance criteria.

## Post-processor: lexical_score

Pure deterministic function at `pipeline2/score_calc.py`. Weights sum to 1.0:

```
lexical_score = (
    0.25 * pan_canonical_factor +
    0.20 * anchor_lemma_factor +
    0.15 * complicating_resolved_factor +
    0.15 * cross_ref_density_factor +
    0.15 * variant_robust_factor +
    0.10 * concordance_breadth_factor
)
```

Factor formulas:
- `pan_canonical_factor` = 1.0 if `pan_canonical: true` else 0.3
- `anchor_lemma_factor` = `min(len(anchor_lemmas), 8) / 8`
- `complicating_resolved_factor` = `addressed_count / max(len(complicating_texts), 1)`; 1.0 if `complicating_texts` is empty
- `cross_ref_density_factor` = `min(len(cross_refs_invoked), 12) / 12`
- `variant_robust_factor` = 1.0 if `variant_robust: true` else 0.5
- `concordance_breadth_factor` = `min(len(concordance_traversed), 10) / 10`

All factors are in [0, 1]; final score is in [0, 1]. The function reads sets and counts only; it is order-invariant by construction. Triangle test (H11 in PoC) verifies this.

## Triangle test

Pipeline 2 outputs are subject to a triangle test:

1. Run Pipeline 2 on `question_id=X` once, save as `evidence/X.json`.
2. Run again on same inputs, save to `tmp/triangle/X_run2.json`.
3. Compute `lexical_score` for both via score_calc.
4. Verify:
   - Schema validation passes for both.
   - `verdict.affirms` matches.
   - `lexical_score` differs by ≤ 0.01 (epsilon-stable).
   - Order-permutation of inputs produces the same score.

Verified architecturally in H11; live verification pending Max-plan subagent run.

## Migration notes (v2.0 → v3.0)

The 111 v2.0 evidence files at commit `12921bb` are archived (per user decision to re-derive from scratch). The migration path is not implemented; v2.0 files are read-only history.

Key differences if a future migration is wanted:

| v2.0 | v3.0 |
|---|---|
| `answer.would_die_for`, `cult_marker_if_denied`, engagement-ladder | Removed. Move to `responses/<respondent>.json`. |
| `counter_witness[]` | Removed. Cultural store handles this. |
| `web[]` with tradition-primary URLs | Removed. Cultural store handles this. |
| `lay_summary.reasoning` + `denominational_landscape` | Collapsed to single `lay_summary` (lexical only). |
| `answer.affirms` (tri-state) | `verdict.affirms` (four-state: adds `"disputed"`). |
| No `lexical_score` | Added (deterministic post-processor). |
| No `variants` block | Added. |
| No `license_audit` block | Added (mandatory). |
| No explicit `citations[]` with license | Added (mandatory). |
