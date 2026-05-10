# Answer Schema for `baseline.json` / `responses/<id>.json` / `consolidated.json`

> Locked. All three answer files share the exact 13-field answer shape; they differ only in the envelope's `viewpoint` field.

The question bank these answer-records key against is documented in [QUESTION_SCHEMA.md](QUESTION_SCHEMA.md). The methodology that produces `baseline.json` + `evidence/*.json` is documented in [../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md). The interpretive hermeneutic recorded per verdict is documented in [HERMENEUTICS.md](HERMENEUTICS.md). The concordance spider-map that backs `analogia scripturae` is documented in [CONCORDANCE.md](CONCORDANCE.md).

---

## Design philosophy

**Booleans only on the answer side.** Minimum cognitive load for trusted-elder respondents and clean aggregation for downstream analysis. No enums for severity, no enums for engagement. The standing (cult-grade / gospel-essential / convictional / preference / adiaphora) is **inferred from the boolean pattern**, not stored as a separate enum.

**Slugs are the labels.** Each boolean's field name reads naturally as a checkbox label. A respondent looking at the questionnaire reads the question's `statement`, then ticks each label that matches their stance.

**Evidence is the audit trail for the inferred-baseline only.** Trusted-elder responses do not carry evidence files. Evidence is what the inferred-baseline subagents produce; respondent files just record positions.

**Tradition-neutral lexical-philological floor.** The `evidence/*.json` shape records: what the original-language text says, what hermeneutic the verdict requires, what the canon-wide concordance shows, and how each major tradition reads the same passage. Confessions and Brethren teaching notes are NOT in the baseline evidence. They live in `responses/<id>.json` files contributed by specific churches and elders.

---

## Top-level envelope

```json
{
  "$schema_version": "1.0",
  "viewpoint": "inferred-from-sources" | "individual:<respondent_id>" | "consolidated",
  "respondent_id": "<string, omitted for inferred-from-sources and consolidated>",
  "generated_at": "<ISO date>",
  "answers": [ <Answer>, ... ]
}
```

---

## Answer record (13 fields, locked)

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
| `rationale` |  | Free-form 1-2 sentence justification. For inferred-baseline: cite apparatus / interlinear, not confessions. |

### Severity (2 booleans)

| Field | Label |
|---|---|
| `would_die_for` | Would die for if challenged |
| `cult_marker_if_denied` | Cult marker if denied |

**Moral entailment** (validated at parse time): `cult_marker_if_denied=true` ⇒ `would_die_for=true`. A respondent cannot consistently classify a group as cult-grade without willingness to die for the truth they deny.

### Engagement ladder (5 booleans, monotonic by intent)

The implicit prompt for each is: *"if a church taught the opposite of this statement…"*

| Field | Label |
|---|---|
| `would_visit_if_otherwise` | Would visit if otherwise |
| `would_participate_if_otherwise` | Would participate if otherwise |
| `would_serve_if_otherwise` | Would serve if otherwise |
| `would_be_member_if_otherwise` | Would be member if otherwise |
| `would_let_children_be_taught_otherwise` | Would let children be taught otherwise |

Letting children be taught is a stronger commitment than personal membership; membership implies serving capacity; etc.

### Other personal decisions (2 booleans)

| Field | Label |
|---|---|
| `would_marry_if_held_otherwise` | Would marry if held otherwise |
| `would_publicly_correct_if_otherwise` | Would publicly correct if otherwise |

Both orthogonal to severity.

### Free-form (1 field)

| Field | Notes |
|---|---|
| `notes` | Free-form context, fruit-vs-precision nuance, named carriers, qualifications |

---

## Standings inferred from boolean patterns

| Pattern | Standing |
|---|---|
| `cult_marker_if_denied=true` (and `would_die_for=true` by entailment) | **Cult-grade**. Denying body is classifiable as a cult |
| `would_die_for=true`, `cult_marker_if_denied=false` | **Gospel-essential** but not cult-classifying (most Reformed Solas land here under the new bar) |
| `would_die_for=false`, `would_be_member=false`, `would_visit=true` | **Convictional** |
| `would_be_member=true` | **Preference / important** |
| All severity & ladder permissive | **Adiaphora** |

---

## Aggregate metrics (derivable, not stored)

| Metric | Formula | Range |
|---|---|---|
| `engagement_score` | sum(visit, participate, serve, be_member, let_children_be_taught) | 0–5 |
| `essentialness_score` | sum(would_die_for, cult_marker_if_denied) | 0–2 |
| `personal_lock_score` | sum(would_marry, would_publicly_correct) | 0–2 |

---

## Evidence record (`evidence/<question_id>.json`)

Produced during the inferred-baseline run only. One file per question. The file IS the audit trail and the public-release artifact.

```json
{
  "id": "<matches Question.id>",
  "answer": { <Answer>, ... },
  "evidence": {
    "stem_audit": {
      "verdict_preloaded": <bool>,
      "neutralized_form": "<string or null>",
      "notes": "<string or null>"
    },

    "lay_summary": "<4-8 sentences in plain English. No Greek/Hebrew, no Strong's numbers, no theological jargon (Niphal, Granville-Sharp, Colwell, hapax legomenon, anarthrous, etc.). Required structure: (1) state the verdict in everyday language; (2) the strongest reason FOR it from Scripture; (3) the strongest counterargument or complicating texts that critics cite, named explicitly; (4) how the verdict handles the tension OR honest acknowledgment that the tension remains; (5) where major Christian traditions agree or disagree. The reader is a layperson; the goal is faithful reasoning, NOT triumphalism. If the verdict is contested or only stands under a specific lens, say so plainly. Names of historical figures, denominations, and public movements (Athanasius, Catholic Church, Mormonism, Unitarian Universalists, Joseph Smith, etc.) are allowed.>",

    "scripture": [
      {
        "ref": "Rom.6.3-4",
        "key_term": "βάπτισμα (baptisma) G908",
        "force": "the rite of baptism; from βαπτίζω 'to dip/submerge'; Paul links the rite to burial-with-Christ via συνετάφημεν (G4916, aorist passive)",
        "supports": "for" | "against" | "complicates" | "neutral",
        "genre": "epistle",
        "figures": ["typology"]
      }
    ],

    "concordance_lemmas_traversed": ["G908", "G4916", "G4982"],
    "complicating_texts_searched": true,

    "hermeneutics": {
      "primary_method": "grammatico-historical",
      "frameworks_in_play": ["covenant_theology", "new_covenant_theology"],
      "analogia_scripturae_invoked": true,
      "progressive_revelation_factor": false,
      "competing_lens_verdicts": [
        {
          "lens": "covenantal",
          "verdict": "complicates",
          "note": "Reads household-baptism passages (Acts 16:33, 1 Cor 1:16) as covenantal extension to children"
        }
      ],
      "notes": "Verdict rests on lexical force of βαπτίζω + Pauline burial-resurrection imagery; complicates under covenantal household reading"
    },

    "counter_witness": [
      {
        "tradition": "patristic",
        "anchor": "Didache 7",
        "verified": true,
        "stance": "complicates",
        "key_phrase": "If thou hast not living water...pour water thrice on the head"
      },
      {
        "tradition": "catholic_magisterial",
        "anchor": "Catechism of the Catholic Church §1239",
        "verified": true,
        "stance": "complicates",
        "key_phrase": "Baptism is performed in the most expressive way by triple immersion in the baptismal water...however, from ancient times it has also been able to be conferred by pouring"
      }
    ],

    "web": [
      {
        "url": "https://biblehub.com/interlinear/romans/6-4.htm",
        "category": "interlinear",
        "stance": "supports",
        "quote": "συνετάφημεν aor pass — 'we were buried with him'"
      }
    ],

    "confidence": "high" | "medium" | "low",
    "flags": ["<one short string per flag>"]
  }
}
```

### Field roles

| Field | Role | What it does |
|---|---|---|
| `stem_audit` | Hygiene | Records whether `question.statement` pre-loaded a verdict. If `verdict_preloaded=true`, the subagent worked the `neutralized_form` and the original belongs in `stem-audit.md` for `questions.json` revision. |
| `lay_summary` | **Reader-facing reasoning** | 4-8 sentences in plain English. Required structure: (1) the verdict, (2) strongest evidence for it, (3) strongest counterargument / complicating texts that critics cite, named explicitly, (4) how the tension resolves or whether it remains, (5) where major Christian traditions agree or disagree. **NOT a victory-lap; honest reasoning including the cases where the verdict is contested or only stands under a specific lens.** First thing a non-specialist sees in the rendered PDF. Validator enforces 200-2000 char length and warns on specialist-vocabulary leak. |
| `scripture[]` | **Judge** | Apparatus + interlinear citations. The only voice that settles a verdict. `supports` is a 4-state enum: `for` / `against` / `complicates` / `neutral` — `complicates` and `neutral` are first-class signals, not bugs. |
| `scripture[].genre` | **Judge — genre rule** | Forces the subagent to acknowledge what kind of text the citation is (narrative ≠ prescription, wisdom ≠ promise, apocalyptic ≠ calendar). See [HERMENEUTICS.md](HERMENEUTICS.md). |
| `scripture[].figures` | **Judge — figure of speech** | Forces explicit acknowledgment of anthropomorphism, hyperbole, metonymy, etc. Empty `[]` means literal/propositional. Non-empty means the verdict involves figurative reading. |
| `concordance_lemmas_traversed` | **Mandatory, all tiers** | List of Strong's numbers the subagent ran spider-map queries against during the analogia-scripturae step. **An empty list is a hard validation failure on every tier.** Every question goes through the canon-wide lemma index. See [CONCORDANCE.md](CONCORDANCE.md). |
| `complicating_texts_searched` | Hygiene | Mandatory `true` after the dedicated complicating-text pass. A `scripture[]` array with all `supports="for"` AND `complicating_texts_searched=true` AND `flags` containing `no-complicating-texts-after-search` is honest; the same array without that flag is a smell. |
| `hermeneutics` | **Visible interpretive commitment** | Records the primary method, frameworks in play, whether `analogia scripturae` was invoked, whether progressive revelation factored, and competing-lens verdicts. Forces the subagent to surface the lens behind any verdict. See [HERMENEUTICS.md](HERMENEUTICS.md). |
| `counter_witness[]` | **Mandatory test, research aid only** | Primary-source statements from major lineages (patristic / catholic / lutheran / anglican / reformed / methodist / anabaptist / pentecostal / eastern_orthodox / continuationist) consulted to verify the lexical reading isn't idiosyncratic. **Does NOT settle a verdict.** Apparatus + interlinear settle; counter-witness corroborates. |
| `web[]` | Primary-source repositories only | BibleHub, STEPBible, OSHB, ccel.org, vatican.va, bookofconcord.org, oca.org, churchofengland.org, ag.org, umc.org, schleitheim primary, openbible.info. Reformed-aligned commentary sites (carm, equip, gotquestions, monergism, ligonier, gospelcoalition) are **forbidden as authority** — they share the formation-under-examination's substrate. The `category` field disambiguates the source type. |

### Confidence

`confidence` reflects how well **Scripture itself** answers the question, given the canonical evidence (apparatus + interlinear + concordance + hermeneutic clarity). Counter-witness convergence corroborates; counter-witness disagreement does not, by itself, lower confidence in a clear lexical reading.

- `high`: apparatus + interlinear give an unambiguous lexical reading, concordance shows pan-canonical demonstration of the doctrine, hermeneutic method is uncontested, AND ≥3 distinct counter-witness traditions corroborate.
- `medium`: lexical reading is clear but counter-witness is divided across major traditions, OR apparatus is paywalled and interlinear alone carries the verdict, OR complicating texts exist and require harmonization, OR the verdict requires a non-default hermeneutic method.
- `low`: Scripture is silent / ambiguous, OR counter-witness traditions disagree sharply on the same lexical reading, OR the verdict required heavy inference, OR concordance reveals the lemma-network does not pan-canonically support the doctrine. Trusted elders should scrutinize these first.

### Cult-marker bar (corrected)

`cult_marker_if_denied=true` requires **THREE** conditions, all canonical:

1. **Moral entailment**: `would_die_for=true`.
2. **Canonical demonstration from Scripture**: apparatus + interlinear yield an unambiguous lexical reading affirming the doctrine, AND concordance demonstrates the doctrine across the canon (not from a single passage). The Bible itself does the work.
3. **Pan-tradition corroboration**: `counter_witness[]` contains entries from **≥6 distinct lineages**, ALL with `stance: "affirms"`. Tracked lineages: Eastern Orthodox patristic, Catholic magisterial, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal/charismatic.

**Even Trinity is not exempt.** Each question — including the four Nicene-Chalcedonian convergent doctrines (Trinity, full deity+humanity of Christ, bodily resurrection, Scripture as inspired-authoritative) — clears or fails this bar on its own per-question evidence. Cross-tradition agreement is corroborating evidence the lexical reading isn't idiosyncratic; it does not, by itself, grant cult-marker status.

A position rejected only by Reformed-Baptist confessions (the formation-under-examination's substrate) does NOT clear the bar; it carries `flags: ["cult-marker-on-substrate-only"]` and is downgraded to `would_die_for=true, cult_marker=false`.

A position rejected by some major lineages but not others (e.g., Reformed-distinctive forensic justification, Catholic/Orthodox baptismal regeneration, Reformed-Baptist denial of paedobaptism) **fails condition 3** and is gospel-essential at most, not cult-grade.

### Anonymization (relaxed for the baseline pipeline)

The strict "only Ebenezer's name allowed" rule applies to **the published `parsed/` corpus** (sermon notes ingested via `ingest-sermons`), where private-corpus contributors must remain anonymous in public-release artifacts. See [ANONYMIZATION.md](ANONYMIZATION.md).

The **inferred-baseline pipeline does not consult `parsed/`** — it only consults critical apparatus, interlinear, concordance, and counter-witness primary sources. Names appearing in this pipeline's output are public-record figures:

- **External published authors** (Athanasius, Augustine, Calvin, Wesley, Aquinas, Lossky, etc.) — **RETAIN**. They are the citation chain.
- **Public confession authors / institutions** (Westminster Assembly, Council of Nicaea, CCC, Mennonite Confession of Dordrecht) — **RETAIN**.
- **Public-record heresy / cult founders** (Joseph Smith, Charles Russell, Ellen White, William Branham, Felix Manalo, Sun Myung Moon, etc.) — **RETAIN** where discussed in `notes`. They are public figures and the baseline's job is to characterize their teaching against Scripture.
- **Public denominations and movements** (Unitarian Universalists, Christadelphians, Mormons, Jehovah's Witnesses, Iglesia ni Cristo, Oneness Pentecostals, Branhamites, etc.) — **RETAIN**.
- **Private-corpus contributors** (Ebenezer's personal teachers from `parsed/`) — **REDACT** if they appear (they shouldn't, since baseline doesn't consult parsed/).

In short: the inferred-baseline pipeline can use real names freely. Over-redaction (e.g., redacting "Wesley's abridgement of the 39 Articles" or "Unitarian Universalists") is a calibration miss the prompt should not cause.

---

## Locked rules

1. **Field names are stable.** Renaming requires coordinated migration across this doc, the validator in `tools/baseline_orchestrator.py`, the renderer in `tools/evidence_to_pdf.py`, every existing answer file, and the project memory.
2. **The 13-field answer shape is identical** across `baseline.json`, `responses/*.json`, and `consolidated.json`. Differences live only in the envelope.
3. **`evidence/*.json` is per-question, produced only during the inferred-baseline run.** Trusted-elder responses don't carry evidence files.
4. **Evidence schema is greenfield.** No legacy fields (`confession_kin`, `defendant_position`, `confessional_verifications`, `source_docs`, `web` without `category`) are accepted; the validator rejects them.
5. **`viewpoint` values** are the only allowed envelope discriminators: `inferred-from-sources` | `individual:<id>` | `consolidated`.
6. **Public-release scope**: `baseline.json`, `consolidated.json`, `evidence/` may be published. `responses/*.json` are private (gitignored).
7. **Slug-as-label**: the questionnaire UI / PDF uses the field slug (with underscores replaced by spaces) as the checkbox label. No verbose question text. Brevity is a feature.
