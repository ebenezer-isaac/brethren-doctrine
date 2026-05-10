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

Standing (cult-grade, gospel-essential, convictional, preference, adiaphora) is **inferred from the answer's boolean pattern, not pre-assigned to the question**. The question bank carries no `tier` field; each subagent judges each boolean per-question on canonical evidence, and the resulting pattern projects to a standing per this table.

| Pattern | Standing |
|---|---|
| `cult_marker_if_denied=true` (and `would_die_for=true` by entailment) | **Cult-grade**. Denying body is classifiable as a cult |
| `would_die_for=true`, `cult_marker_if_denied=false` | **Gospel-essential** but not cult-classifying. Reformed Solas as worded land here, since their stems carry theory-specific vocabulary that the lexical anchors do not unambiguously license. |
| `would_die_for=false`, `would_be_member=false`, `would_visit=true` | **Convictional** |
| `would_be_member=true` | **Preference / important** |
| All severity & ladder permissive | **Adiaphora** |

---

## Aggregate metrics (derivable, not stored)

| Metric | Formula | Range |
|---|---|---|
| `engagement_score` | sum(visit, participate, serve, be_member, let_children_be_taught) | 0-5 |
| `essentialness_score` | sum(would_die_for, cult_marker_if_denied) | 0-2 |
| `personal_lock_score` | sum(would_marry, would_publicly_correct) | 0-2 |

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

    "lay_summary": {
      "reasoning": "<plain-English Scripture-based verdict justification. Required structure: (1) verdict in everyday language; (2) strongest reason FOR from Scripture, named-verse plain words; (3) strongest counterargument from Scripture's own complicating texts, named-verse plain words; (4) how the verdict handles the tension or honest acknowledgment it remains. NO denominational or lineage names in this section; that goes in denominational_landscape. >=100 chars, <=500 words. NO jargon. NO em or en dashes.>",
      "denominational_landscape": "<plain-English description of where major Christian lineages agree or disagree on this proposition. Name the lineages (patristic, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal, Eastern Orthodox) with brief positions. Where applicable, name public-record cult or heterodox carriers of denial (Mormonism, Jehovah's Witnesses, Iglesia ni Cristo, William Branham, Christian Science, Mary Baker Eddy, etc.) and what their denial places them in relation to historic Christianity. DESCRIPTIVE of church history; does NOT vote on the verdict. >=100 chars, <=500 words. NO jargon. NO em or en dashes.>"
    },

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
        "quote": "συνετάφημεν aor pass, 'we were buried with him'"
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
| `lay_summary` | **Reader-facing, TWO separate paragraphs** | Nested object with two required string fields: `reasoning` (Scripture-based verdict justification: verdict in everyday words, strongest reason FOR from Scripture, strongest counterargument from Scripture's own complicating texts, how the verdict handles the tension; NO denominational names) and `denominational_landscape` (descriptive church-history layer: where major Christian lineages agree or disagree, with named lineages and named carriers of denial where applicable; DOES NOT vote on the verdict). Each subfield is plain English, >=100 chars, <=500 words, no jargon, no em or en dashes. The split is deliberate: keeps the verdict-justifying Scripture reasoning visually distinct from the denominational landscape so a reader can see the verdict math and the church-history context separately. Validator enforces both bounds and both jargon/dash checks. |
| `scripture[]` | **Judge** | Apparatus + interlinear citations. The only voice that settles a verdict. `supports` is a 4-state enum: `for` / `against` / `complicates` / `neutral`, `complicates` and `neutral` are first-class signals, not bugs. |
| `scripture[].genre` | **Judge, genre rule** | Forces the subagent to acknowledge what kind of text the citation is (narrative ≠ prescription, wisdom ≠ promise, apocalyptic ≠ calendar). See [HERMENEUTICS.md](HERMENEUTICS.md). |
| `scripture[].figures` | **Judge, figure of speech** | Forces explicit acknowledgment of anthropomorphism, hyperbole, metonymy, etc. Empty `[]` means literal/propositional. Non-empty means the verdict involves figurative reading. |
| `concordance_lemmas_traversed` | **Mandatory, all tiers** | List of Strong's numbers the subagent ran spider-map queries against during the analogia-scripturae step. **An empty list is a hard validation failure on every tier.** Every question goes through the canon-wide lemma index. See [CONCORDANCE.md](CONCORDANCE.md). |
| `complicating_texts_searched` | Hygiene | Mandatory `true` after the dedicated complicating-text pass. A `scripture[]` array with all `supports="for"` AND `complicating_texts_searched=true` AND `flags` containing `no-complicating-texts-after-search` is honest; the same array without that flag is a smell. |
| `hermeneutics` | **Visible interpretive commitment** | Records the primary method, frameworks in play, whether `analogia scripturae` was invoked, whether progressive revelation factored, and competing-lens verdicts. Forces the subagent to surface the lens behind any verdict. See [HERMENEUTICS.md](HERMENEUTICS.md). |
| `counter_witness[]` | **Diagnostic information for the reader, not a verdict-shaper** | Primary-source statements from major lineages (patristic / catholic / lutheran / anglican / reformed / methodist / anabaptist / pentecostal / eastern_orthodox / continuationist) recorded so the reader sees how each lineage reads the same lexical text. **Does NOT vote on `affirms`, `cult_marker_if_denied`, `would_die_for`, or `confidence`.** Encouraged for diagnostic completeness on every question; missing counter-witness flags `counter-witness-missing` for research-quality tracking only. |
| `web[]` | Primary-source repositories only | BibleHub, STEPBible, OSHB, ccel.org, vatican.va, bookofconcord.org, oca.org, churchofengland.org, ag.org, umc.org, schleitheim primary, openbible.info. Reformed-aligned commentary sites (carm, equip, gotquestions, monergism, ligonier, gospelcoalition) are **forbidden as authority**, they share the formation-under-examination's substrate. The `category` field disambiguates the source type. |

### Confidence

`confidence` reflects how well **Scripture itself** answers the question, given the canonical evidence (apparatus + interlinear + concordance + hermeneutic clarity). Counter-witness convergence and divergence are diagnostic information about lineage history; they do NOT shift confidence. Only lexical evidence does.

- `high`: apparatus + interlinear give an unambiguous lexical reading, concordance shows pan-canonical demonstration of the doctrine, and hermeneutic method is uncontested.
- `medium`: apparatus is paywalled and interlinear alone carries the verdict, OR complicating texts exist and require harmonization, OR the verdict requires a non-default hermeneutic method (covenantal, dispensational, accommodation), OR the lemma-network is contested at the lexical level.
- `low`: Scripture is silent or ambiguous, OR concordance reveals the lemma-network does not pan-canonically support the doctrine, OR the verdict required heavy inference. Trusted elders should scrutinize these first.

### Cult-marker bar

`cult_marker_if_denied=true` requires **TWO** conditions, both canonical:

1. **Moral entailment**: `would_die_for=true`. Denial constitutes denial of the gospel itself or a core Trinitarian or Christological boundary clearly mandated by Scripture's own lexical pattern.
2. **Canonical demonstration from Scripture**: apparatus + interlinear yield an unambiguous lexical reading affirming the doctrine, AND concordance demonstrates the doctrine across the canon (not from a single passage). The Bible itself does the work.

**Lineage agreement does NOT grant or withhold cult-marker status.** If apparatus + interlinear + concordance unambiguously affirm a doctrine and denial constitutes denial of the gospel, the cult-marker stands regardless of which historical traditions confess it in those exact terms. Conversely, unanimous lineage agreement on a doctrine that lacks unambiguous canonical demonstration does NOT clear the bar.

**The Brethren-on-trial discipline is preserved through canonical demonstration.** Most Brethren distinctives (eldership polity, weekly breaking of bread, baptism mode, dispensational hermeneutics) lack unambiguous pan-canonical lexical support and will fail condition 2 honestly. The discipline is the canon itself, not ecumenical vote-counting.

**Even Trinity is not exempt.** Each question, including the four Nicene-Chalcedonian convergent doctrines (Trinity, full deity and humanity of Christ, bodily resurrection, Scripture as inspired and authoritative), clears or fails this bar on its own per-question canonical evidence.

A position lexically settled by Scripture and gospel-implicating clears the bar regardless of how many lineages happen to confess it. What matters is canonical demonstration. If condition 2 fails (single-passage doctrine, lexically ambiguous, or contested at the lemma-network level), the verdict cannot carry `cult_marker_if_denied=true` regardless of what any tradition affirms.

### Anonymization (relaxed for the baseline pipeline)

The strict "only Ebenezer's name allowed" rule applies to **the published `parsed/` corpus** (sermon notes ingested via `ingest-sermons`), where private-corpus contributors must remain anonymous in public-release artifacts. See [ANONYMIZATION.md](ANONYMIZATION.md).

The **inferred-baseline pipeline does not consult `parsed/`**, it only consults critical apparatus, interlinear, concordance, and counter-witness primary sources. Names appearing in this pipeline's output are public-record figures:

- **External published authors** (Athanasius, Augustine, Calvin, Wesley, Aquinas, Lossky, etc.), **RETAIN**. They are the citation chain.
- **Public confession authors / institutions** (Westminster Assembly, Council of Nicaea, CCC, Mennonite Confession of Dordrecht), **RETAIN**.
- **Public-record heresy / cult founders** (Joseph Smith, Charles Russell, Ellen White, William Branham, Felix Manalo, Sun Myung Moon, etc.), **RETAIN** where discussed in `notes`. They are public figures and the baseline's job is to characterize their teaching against Scripture.
- **Public denominations and movements** (Unitarian Universalists, Christadelphians, Mormons, Jehovah's Witnesses, Iglesia ni Cristo, Oneness Pentecostals, Branhamites, etc.), **RETAIN**.
- **Private-corpus contributors** (Ebenezer's personal teachers from `parsed/`), **REDACT** if they appear (they shouldn't, since baseline doesn't consult parsed/).

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
