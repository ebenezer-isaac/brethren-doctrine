# Hermeneutics

> Methodology pillar #2 (after concordance). Makes interpretive commitments visible per question, so verdicts that depend on a particular reading lens are auditable rather than smuggled.

A clear lexical reading of Hebrew or Greek does not, by itself, settle a doctrinal question. The same passage produces different verdicts under different hermeneutical frameworks, and a verdict that's only true under one framework is not the same as a verdict that holds across orthodox interpretive lenses.

The trial structure ([../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md)) tells subagents what each information layer does. Hermeneutics tells subagents *how* a passage may legitimately be read and forces them to surface the lens behind any verdict.

---

## Why this exists in the schema

Two failure modes hermeneutics catches that concordance alone cannot:

**Lens-dependent verdicts hidden under "lexical clarity."** Two subagents reading the same `scripture[]` array can produce opposite verdicts if one reads `Daniel 9` dispensationally and the other reads it covenantally, and neither has lied about the lexical force of any single word. The lens is doing work that the lexical force isn't. Without recording the lens, this is invisible.

**Figure-of-speech omissions.** Anthropomorphism, anthropopathism, and hyperbole are textbook sources of bias: passages like Gen 6:6, Ex 32:14, 1 Sam 15:11, Jonah 3:10 read literally produce an open-theist God; read accommodationally they preserve immutability. A subagent that omits these passages from a `scripture[]` array on omnipotence/immutability/omniscience questions is not lying, it is hiding the hermeneutical commitment. Forcing `figures: ["anthropomorphism"]` or `figures: ["anthropopathism"]` on each such citation makes the commitment visible.

Making hermeneutics first-class evidence exposes both failures.

---

## Primary methods

The subagent picks one as the primary method behind the verdict.

| Method | What it privileges | Default home |
|---|---|---|
| `grammatico-historical` | Original grammar, syntax, semantic range, immediate historical setting. (`literal-grammatical` is a synonym; do not record it as a separate method.) Founded by Ernesti (1707-1781), consolidated by Hengstenberg/Delitzsch/Keil. | Reformed, Lutheran, evangelical mainstream, the default |
| `redemptive-historical` | Whole-Bible storyline; OT read in light of Christ's accomplishment. Geerhardus Vos (1862-1949). | Confessional Reformed (OPC, URC), New Covenant Theology |
| `quadriga` | Four senses (literal, allegorical, tropological, anagogical); literal sense primary for doctrine. Origen → Cassian → Aquinas (ST I.1.10). | Catholic |
| `patristic-typological` | Scripture read in/through the Church's liturgical-patristic mind; OT events as forward-pointing types fulfilled in Christ + Church. | Eastern Orthodox |
| `accommodation` | Anthropomorphic / phenomenal language as God's accommodation to human capacity. Origen ("baby-talk"), Calvin ("lisps"). A *principle* often layered onto another method, not a standalone school. | Cross-tradition |

Most verdicts default to `grammatico-historical`. Subagents must record the primary method explicitly anyway, so when the verdict requires a non-default method (typological, redemptive-historical, etc.) it is visible.

---

## Frameworks that produce different verdicts

Major contested interpretive frameworks. Each produces consistently different verdicts on a defined set of questions.

| Framework | Core commitment | Where verdicts diverge |
|---|---|---|
| **Covenant theology** | One covenant of grace across Testaments; church = true Israel | Baptism mode/recipients, sacraments, ecclesiology, eschatology |
| **Dispensationalism** | Distinct dispensations; sharp Israel/church distinction; literal future for ethnic Israel. **Brethren-distinctive** (Darby originated the system). | Eschatology (pre-trib rapture, millennium), OT prophecy fulfillment, ecclesiology |
| **New Covenant Theology** | One people of God but no covenant of grace; Mosaic law abrogated | Sabbath, tithing, OT moral law continuity |
| **Progressive covenantalism** | Mediating between covenant and dispensational systems | Israel/church relationship, kingdom ethics |
| **Historic premillennialism** | Christ returns before the millennium, but no separate Israel/church future | Eschatology specifically |

When a question's verdict diverges across these frameworks, subagents MUST record `competing_lens_verdicts[]` with at least the lenses in play. This is how dispensationalism, a Brethren distinctive, becomes auditable rather than smuggled.

---

## Figures of speech

Identifying figures is non-optional for any passage where the literal reading would produce nonsense or absurdity.

Bullinger's *Figures of Speech Used in the Bible* (1898) catalogues 217 figures and remains a useful cross-reference (https://archive.org/details/figuresofspeechu00bull). Modern consensus textbooks: Klein/Blomberg/Hubbard, *Introduction to Biblical Interpretation* (3rd ed.); Osborne, *The Hermeneutical Spiral*.

Operational subset for doctrinal interpretation:

| Figure | Recognition cue | Doctrinal stake |
|---|---|---|
| `anthropomorphism` | Human bodily attribution to God ("hand of the LORD", "eyes of the LORD") | Transcendence vs immanence; impassibility |
| `anthropopathism` | Human emotional attribution to God ("the LORD repented", "God grieved") | Immutability, omniscience (Open Theism reads literally) |
| `metaphor` | Implied comparison ("I am the door", "the kingdom is like…") | Christology, ecclesiology, ontology of speech-acts |
| `simile` | Explicit comparison with "like" / "as" | Often signals where literal reading would mislead |
| `hyperbole` | Deliberate exaggeration for rhetorical effect ("if your eye causes you to sin, pluck it out") | Sermon on the Mount ethics, asceticism |
| `metonymy` | Substitution by association ("the cup" for the contents) | Eucharistic theology |
| `synecdoche` | Part for whole or whole for part ("daily bread" for sustenance) | Lord's Prayer, covenant promises |
| `irony` | Stated meaning opposite to intended (Job's "no doubt you are the people") | Wisdom-literature interpretation |
| `personification` | Abstract things treated as persons (Wisdom in Prov 8) | Wisdom Christology debates |
| `chiasm` | A-B-B'-A' / A-B-C-B'-A' literary structure | Determines what the central pivot of a passage is |
| `merism` | Two opposites for totality ("heaven and earth" = creation) | Cosmological readings |
| `idiom` | Culturally locked phrasing not transparent to literal reading | Translation choices, doctrinal misreadings |
| `typology` | OT person/event/institution as forward-pointing pattern | Christ-pattern in Adam, Melchizedek, Moses; Israel/church |
| `apocalyptic-symbolism` | Numbered, beastly, cosmic imagery in apocalyptic genre | Revelation, Daniel; rapture, millennium |
| `parallelism` | Hebrew poetic restatement (synonymous, antithetic, synthetic) | Psalms, prophets, counts ONE thought, not two |
| `parable` | Extended comparison, single point | Synoptic teachings; reading as allegory inflates points |

**Anthropomorphism / anthropopathism deserve special attention**, they are the largest source of selection-bias smell on divine-attributes questions. The validator (`tools/verify_baseline.py`) checks (per the H5 catalog) that omnipotence/immutability/omniscience/impassibility/sovereignty questions carry at least one such citation. Omitting them carries flag `anthropomorphic-passages-omitted`.

---

## Genre rules

The genre of the passage determines what kind of reading is even legitimate. Reading apocalyptic as a calendar produces date-setting cults; reading wisdom as promise produces health-and-wealth theology.

| Genre | Reading rules |
|---|---|
| `narrative` | Description ≠ prescription. What characters do or experience is not automatically normative. Look for authorial commentary and apostolic generalization. |
| `epistle` | Direct teaching; closest to propositional. Watch occasional vs general; identify the problem the letter addresses. |
| `prophecy` | Near and far horizons; conditional vs unconditional; covenant context; apocalyptic vs classical-prophetic style. |
| `wisdom` | Generalizations not promises (Proverbs); existential laments not theology proper (Ecclesiastes, Job dialogues). |
| `apocalyptic` | Symbolic, cosmic, often numbered. Identify the symbols' functions before assigning referents. |
| `gospel` | Theological biography. Each evangelist's emphases shape what's recorded; harmonization possible but not always required. |
| `law` | Casuistic vs apodictic; Mosaic vs Noahic; ceremonial / civil / moral distinctions (themselves contested across covenant theology). |
| `psalm` | Inspired prayers, not always teaching. Distinguish what is *modeled* from what is *taught*. |
| `parable` | Single main point; secondary details serve the point, not independent doctrines. |

Every `scripture[]` citation MUST carry its genre. A verdict resting on a wisdom-genre passage read as a doctrinal promise carries flag `genre-mismatch`.

---

## Cross-passage principles

**Analogia scripturae** (Scripture interprets Scripture): obscure passages are read in light of clear ones. The clear passages on a doctrine are the controlling ones. *In the evidence schema*: when a verdict invokes this principle, `analogia_scripturae_invoked: true` and the controlling passages should appear in `scripture[]`. The concordance spider-map is what makes this principle mechanical instead of editorial, see [CONCORDANCE.md](CONCORDANCE.md).

**Analogia fidei** (the analogy of faith): individual passages read in light of the whole-canon doctrinal coherence. **Dangerous because it can become "read every passage to confirm what I already believe."** *In the evidence schema*: this principle is NOT recorded as a separate boolean field, because it leaks easily into formation-confirmation. If a verdict requires invoking it, the subagent must say so in `notes` and explain *which* doctrinal whole is doing the controlling work.

**Progressive revelation**: later revelation clarifies earlier (e.g., NT clarifies OT typology). *In the evidence schema*: `progressive_revelation_factor: true` when the verdict requires later revelation to settle an earlier passage's meaning.

---

## What gets recorded per question

The `evidence.hermeneutics` block on every `evidence/<id>.json`:

```json
"hermeneutics": {
  "primary_method": "grammatico-historical",
  "frameworks_in_play": ["covenant_theology", "dispensationalism"],
  "analogia_scripturae_invoked": true,
  "progressive_revelation_factor": false,
  "competing_lens_verdicts": [
    {
      "lens": "covenantal",
      "verdict": "denies",
      "note": "Reads Heb 8:13 as continuity of one covenant of grace, not new dispensation"
    },
    {
      "lens": "dispensational",
      "verdict": "affirms",
      "note": "Reads sharp discontinuity; church age is parenthetical to Israel program"
    }
  ],
  "notes": "Verdict requires a position on Israel/church relationship. Inferred-baseline records both lenses to allow trusted-elder review."
}
```

And on each `scripture[]` entry:

```json
{
  "ref": "Genesis 6:6",
  "key_term": "וַיִּנָּחֶם (vayyinnachem), Niphal of nacham, H5162",
  "force": "...",
  "supports": "complicates",
  "genre": "narrative",
  "figures": ["anthropopathism"]
}
```

`figures` is an array because some passages combine figures (e.g., apocalyptic-symbolism + hyperbole). Empty `[]` if the passage is straight literal/propositional with no figure operative.

---

## Hard rules for subagents

1. **Default `primary_method` is `grammatico-historical`.** A verdict resting on a non-default method must be defensible from the apparatus / interlinear AND must record the method explicitly.
2. **Anthropomorphism / anthropopathism passages on omnipotence, immutability, omniscience, impassibility, sovereignty questions are NOT optional.** The H5 catalog in `tools/verify_catalogs.json` lists the question ids; the validator enforces at least one such citation per catalogued question. Omission produces `flags: ["anthropomorphic-passages-omitted"]`. The flag is a research-quality marker; it does not lower confidence by itself, since confidence reflects lexical clarity rather than completeness of figure tagging.
3. **Dispensational verdicts are flagged.** Any verdict that requires dispensational hermeneutics gets `flags: ["dispensational-lens-required"]` and `frameworks_in_play` must list `dispensationalism`. The flag notes for the reader that the verdict requires a non-default hermeneutic; it does not demote the verdict. Verdict stands or falls on apparatus, interlinear, and concordance. Catalogued in H6.
4. **Genre mismatch is flagged.** A verdict that treats a wisdom-genre passage as a doctrinal promise, or apocalyptic as calendar, or narrative as prescription, gets `flags: ["genre-mismatch"]` with a note.
5. **`competing_lens_verdicts` is mandatory** for any question where `frameworks_in_play.length > 1`. (Tier-gating removed; tier abolished from questions.json. The frameworks-in-play count alone triggers the mandate.)

---

## Where this is enforced

- **Evidence schema** ([ANSWER_SCHEMA.md](ANSWER_SCHEMA.md)): the `hermeneutics` block and the `genre` / `figures` fields on `scripture[]` are part of the locked shape.
- **Subagent prompt** ([../tools/derive_baseline_prompt.md](../tools/derive_baseline_prompt.md)): the hermeneutic-classification step makes the recording mandatory.
- **Runtime template** ([../tools/baseline_orchestrator.py](../tools/baseline_orchestrator.py)): the `PROMPT_TEMPLATE` interpolated for each subagent invocation carries the same step + schema.
- **Validator** ([../tools/baseline_orchestrator.py](../tools/baseline_orchestrator.py) `validate()` and [../tools/verify_baseline.py](../tools/verify_baseline.py)): rejects evidence files missing the `hermeneutics` block, missing `genre` / `figures` on any `scripture[]` entry, or violating the hard rules above.
