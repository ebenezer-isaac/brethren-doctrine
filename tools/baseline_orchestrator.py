"""Helper utilities for the inferred-baseline run.

Two responsibilities:
1. Build per-question subagent prompts (strings to pass to the Agent tool).
2. Validate evidence/<id>.json output against the locked schema.

Methodology lives in tools/derive_baseline_prompt.md and is mirrored here in
PROMPT_TEMPLATE so the runtime injection stays in sync. Schema lives in
docs/ANSWER_SCHEMA.md, docs/HERMENEUTICS.md, docs/CONCORDANCE.md.

Model-agnostic: the orchestrator passes --model {sonnet,opus} on the CLI;
the prompt template itself does not depend on model choice.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "questions.json"
EVIDENCE = ROOT / "evidence"

ANSWER_FIELDS = (
    "id",
    "affirms",
    "rationale",
    "would_die_for",
    "cult_marker_if_denied",
    "would_visit_if_otherwise",
    "would_participate_if_otherwise",
    "would_serve_if_otherwise",
    "would_be_member_if_otherwise",
    "would_let_children_be_taught_otherwise",
    "would_marry_if_held_otherwise",
    "would_publicly_correct_if_otherwise",
    "notes",
)

EVIDENCE_REQUIRED_FIELDS = (
    "stem_audit",
    "lay_summary",
    "scripture",
    "concordance_lemmas_traversed",
    "complicating_texts_searched",
    "hermeneutics",
    "counter_witness",
    "web",
    "confidence",
    "flags",
)

# lay_summary is now an OBJECT with two reader-facing paragraphs:
#   - reasoning: Scripture-based verdict justification (lexical evidence, complicating
#     texts, how the verdict handles the tension)
#   - denominational_landscape: where major Christian lineages agree or disagree on the
#     proposition, with named lineages and named carriers of denial where applicable
# Each section: <=500 words, >=100 chars, plain English, no jargon, no em/en dashes.
LAY_SUMMARY_SUBFIELDS = ("reasoning", "denominational_landscape")
LAY_SUMMARY_MIN_CHARS = 100
LAY_SUMMARY_MAX_WORDS = 500
# Specialist vocabulary that should NOT appear in the reader-facing summary.
LAY_SUMMARY_JARGON_TOKENS = (
    "Strong's", "Niphal", "Piel", "Hiphil", "Granville-Sharp", "Granville Sharp",
    "Colwell", "anarthrous", "articular", "hapax legomenon", "hapax",
    "lemma", "morpheme", "septuagint", "BHS", "NA28", "UBS5",
    "preterite", "aorist", "Niph",
)
# Em dash and en dash are banned in lay_summary (per user directive). Use
# periods, commas, or natural conjunctions instead.
LAY_SUMMARY_BANNED_DASHES = ("—", "–")  # em dash, en dash

LEGACY_EVIDENCE_KEYS = (
    "confessional_verifications",
    "source_docs",
    "defendant_position",
    "confession_kin",
)

VALID_GENRES = {
    "narrative", "epistle", "prophecy", "wisdom", "apocalyptic",
    "gospel", "law", "psalm", "parable",
}

VALID_FIGURES = {
    "anthropomorphism", "anthropopathism", "metaphor", "simile",
    "hyperbole", "metonymy", "synecdoche", "irony", "personification",
    "chiasm", "merism", "idiom", "typology", "apocalyptic-symbolism",
    "parallelism", "parable", "phenomenological-language",
}

VALID_PRIMARY_METHODS = {
    "grammatico-historical", "redemptive-historical", "quadriga",
    "patristic-typological", "accommodation",
}

VALID_TRADITIONS = {
    "patristic", "catholic_magisterial", "lutheran", "anglican",
    "reformed", "methodist", "anabaptist", "continuationist",
    "eastern_orthodox", "pentecostal",
}

VALID_SUPPORTS = {"for", "against", "complicates", "neutral"}
VALID_STANCES = {"affirms", "denies", "complicates"}
VALID_WEB_CATEGORIES = {
    "primary_repository", "magisterial", "patristic_archive",
    "tradition_primary", "interlinear", "critical_apparatus",
}
VALID_WEB_STANCES = {"supports", "opposes", "complicates", "nuance"}
VALID_CONFIDENCE = {"high", "medium", "low"}

# Cult-marker bar requires canonical demonstration (pan-canonical lexical reading,
# not single-passage). Validator enforces minimum structural breadth as a proxy
# for "not single-passage": at least 2 distinct concordance lemmas traversed and
# at least 3 scripture[] anchors. Lineage agreement does NOT factor in.
CULT_MARKER_MIN_LEMMAS = 2
CULT_MARKER_MIN_ANCHORS = 3


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]


def question_by_id(qid: str) -> dict | None:
    for q in load_questions():
        if q["id"] == qid:
            return q
    return None


def worklist() -> list[str]:
    """Question ids that don't yet have a complete evidence file."""
    EVIDENCE.mkdir(exist_ok=True)
    todo = []
    for q in load_questions():
        qid = q["id"]
        ok, _ = validate(qid)
        if not ok:
            todo.append(qid)
    return todo


PROMPT_TEMPLATE = """\
You are deriving a tradition-neutral lexical-philological baseline answer for ONE
question. The owner is formed in Plymouth Brethren-adjacent tradition; THAT
FORMATION IS ON TRIAL, NOT THE RUBRIC. Calibrate to apparatus + interlinear +
concordance. Counter-witness traditions are recorded as diagnostic information
for the reader showing how each lineage reads the same lexical text; they do
NOT vote on `affirms`, `cult_marker_if_denied`, `would_die_for`, or `confidence`.
Do NOT calibrate to Brethren or Reformed-Protestant orthodoxy.

This answer is a SEED for community-questionnaire input. Be honest about
uncertainty so trusted-elder reviewers know what to scrutinize.

## Authority order (strict)
1. Critical apparatus (BHS, NA28/UBS5): the only authority that settles a verdict.
2. Interlinear (Hebrew/Greek lemma + morphology): use STEPBible (https://www.stepbible.org),
   BibleHub interlinear (https://biblehub.com/interlinear/), OSHB (https://hb.openscriptures.org).
3. Concordance (mandatory traversal, all tiers): Strong's lemma → all-occurrences spider-map.
4. Hermeneutic classification (mandatory): primary method, frameworks, figures, genre.
5. Counter-witness traditions (encouraged for diagnostic completeness on every
   question): patristic, Catholic, Lutheran, Anglican, Anabaptist, Methodist,
   Pentecostal, Reformed, Eastern Orthodox primary sources via web fetch.
   Recorded for the reader's information; they do NOT vote on any verdict field.

Confessions never override apparatus + interlinear. Defendant teaching notes
(source-docs/, parsed/) are NOT in this run.

## Anonymization (relaxed for the baseline pipeline)

The strict redaction rule applies to `parsed/` (private sermon corpus), which
this pipeline does NOT consult. Use real names freely:
- External published authors (Athanasius, Augustine, Aquinas, Calvin, Wesley, etc.): RETAIN.
- Public confession authors / institutions (Westminster Assembly, Council of
  Nicaea, CCC, Mennonite Confession of Dordrecht): RETAIN.
- Public-record heresy / cult founders (Joseph Smith, Charles Russell, Ellen
  White, William Branham, Felix Manalo, Sun Myung Moon, etc.): RETAIN where
  discussed in `notes`. Public figures.
- Public denominations and movements (Unitarian Universalists, Christadelphians,
  Mormons, JWs, Iglesia ni Cristo, Oneness Pentecostals, etc.): RETAIN.
- Private-corpus contributors (Ebenezer's personal teachers from `parsed/`):
  REDACT if they appear (they shouldn't, baseline doesn't consult parsed/).

Do NOT over-redact. "Wesley's abridgement of the 39 Articles" stays; do not
write "[REDACTED]'s abridgement". "Unitarian Universalists" stays; do not
write "[REDACTED]-Universalists".

## Question (your only question)
{question_json}

## Method (in order, DO NOT SKIP STEPS)

### Step 1: Stem audit (FIRST)
Read `question.statement`. Flag if it names heretics, asserts the verdict, or uses
Reformed-confessional vocabulary as if neutral.
Populate `evidence.stem_audit.verdict_preloaded` (bool), `neutralized_form`
(string|null), `notes` (string|null). If pre-loaded, work the neutralized form and
add flag `stem-pre-loaded-verdict`.

### Step 2: Apparatus + interlinear pass
For each `scripture_anchors` entry:
- Read in context (one chapter minimum).
- For each load-bearing Hebrew/Greek term, fetch interlinear. Cite lemma +
  transliteration + Strong's number + lexical force in one line.
- Cite critical-apparatus footnotes where retrievable (NET Bible translator notes,
  STEPBible apparatus). Flag `apparatus-paywalled` if inaccessible.
- Identify `genre` and `figures` per citation.
- Note: "for" | "against" | "complicates" | "neutral".

### Step 3: Concordance traversal (MANDATORY, every tier)
For every doctrinally salient Strong's lemma in Step 2, run a spider-map query
(via Neo4j Cypher or BibleHub fallback https://biblehub.com/strongs/<g_or_h>/<n>.htm)
to find every occurrence in the canon. Identify uses NOT in `scripture_anchors`
that complicate or qualify the verdict. Add at least one to scripture[] if any
are doctrinally relevant.

For at least one anchor verse, run the full spider-map (verses sharing ≥1 lemma +
cross-references). Surface canonical-context verses missed by the seed anchors.

Record EVERY Strong's number traversed in `evidence.concordance_lemmas_traversed[]`.
EMPTY ARRAY IS A HARD VALIDATION FAILURE.

### Step 4: Hermeneutic classification (MANDATORY)
Populate `evidence.hermeneutics`:
- primary_method (grammatico-historical default)
- frameworks_in_play (covenant_theology, dispensationalism, new_covenant_theology,
  progressive_covenantalism, historic_premillennialism, list those producing
  different verdicts on this question)
- analogia_scripturae_invoked (bool)
- progressive_revelation_factor (bool)
- competing_lens_verdicts[] (mandatory if frameworks_in_play.length > 1;
  tier abolished from questions.json so no tier-gating)
- notes (short narrative)

If verdict requires dispensational hermeneutics, add flag `dispensational-lens-required`.

### Step 5: Complicating-text search (MANDATORY)
Independent of `scripture_anchors`. Ask: "What passages might complicate the
verdict if the formation's reading is wrong?"
- Omnipotence/immutability/omniscience/impassibility/sovereignty ⇒ Gen 6:6, Ex 32:14,
  1 Sam 15:11, Jonah 3:10, Jer 18:8 (anthropopathism).
- Eternal security ⇒ Heb 6:4-6, 10:26-31, 2 Pet 2:20-22.
- Cessation ⇒ Acts 21:9, 1 Cor 14, Joel 2/Acts 2 telos.
- Baptism mode ⇒ Acts 16:33, 1 Cor 1:16; Ezek 36:25, Heb 10:22.

Set `complicating_texts_searched: true` regardless. If none applicable after
dedicated search, add flag `no-complicating-texts-after-search`.

For omnipotence-class questions (catalogued in tools/verify_catalogs.json H5):
at least one anthropomorphic / anthropopathic citation MUST appear in scripture[]
with figures including 'anthropomorphism' or 'anthropopathism'. Otherwise add flag
`anthropomorphic-passages-omitted`.

### Step 6: Counter-witness pass (encouraged for diagnostic completeness)
Pull at least ONE primary-source statement from each of as many tracked lineages
as possible. Counter-witness is research aid for the reader; it does NOT vote
on `affirms`, `cult_marker_if_denied`, `would_die_for`, or `confidence`.
Allowed entry points (use these URLs only):
- Patristic: https://ccel.org/fathers (Schaff NPNF Series 1 & 2)
- Catholic magisterial: https://www.vatican.va/archive/ENG0015/_INDEX.HTM (CCC);
  Dei Verbum at https://www.vatican.va/archive/hist_councils/ii_vatican_council/
  documents/vat-ii_const_19651118_dei-verbum_en.html
- Lutheran: https://bookofconcord.org
- Anglican: https://www.churchofengland.org/prayer-and-worship/worship-texts-and
  -resources/book-common-prayer/articles-religion (39 Articles)
- Reformed: WCF, Heidelberg, Belgic, Savoy
- Methodist: https://www.umc.org/en/content/articles-of-religion
- Anabaptist: Schleitheim 1527 https://courses.washington.edu/hist112/
  SCHLEITHEIM%20CONFESSION%20OF%20FAITH.htm
- Pentecostal: https://ag.org/Beliefs/Statement-of-Fundamental-Truths
- Eastern Orthodox: https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture

Record `tradition`, `anchor`, `verified` (bool), `stance`, `key_phrase` (≤200 chars).

If zero counter-witness can be surfaced in good faith on any question, flag
`counter-witness-missing` for research-quality tracking. Confidence is NOT
lowered; it reflects lexical clarity, not lineage coverage.

### Step 7: Web pass, primary repositories only
ALLOWED: biblehub.com, stepbible.org, hb.openscriptures.org, ccel.org, vatican.va,
bookofconcord.org, churchofengland.org, ag.org, umc.org, oca.org, openbible.info.

FORBIDDEN as authority: carm.org, equip.org, gotquestions.org, monergism.com,
ligonier.org, thegospelcoalition.org, brethrenarchive.org.

Record url, category, stance, quote (≤200 chars).

### Step 8: Lay summary (MANDATORY, reader-facing reasoning)

After the technical work, write a 4-8 sentence plain-English explanation in
`evidence.lay_summary`. The reader is a layperson trying to understand what
the verdict is and WHY, including counterarguments. Required structure:
1. State the verdict in everyday language (no Greek, no Strong's, no jargon).
2. The strongest reason FOR it from Scripture, in plain words.
3. The strongest counterargument or complicating texts that critics cite,
   named explicitly (e.g., "Critics like Unitarians and Jehovah's Witnesses
   point to Mark 13:32 where Jesus says he doesn't know the hour…").
4. How the verdict handles the tension OR honest acknowledgment that it
   remains. If the verdict only stands under a specific lens, say so plainly.
5. Where major Christian traditions agree or disagree.

This is NOT a victory lap. Surface contested cases honestly. If only 4 of 8
traditions agree, the lay_summary must say "Christians disagree about this."

Forbidden vocabulary (validator REJECTS): Strong's, Niphal, Piel, Hiphil,
Granville-Sharp, Colwell, anarthrous, articular, hapax legomenon, BHS, NA28,
UBS5, aorist, lemma, morpheme. Use plain English equivalents.

Em dashes (long dash) and en dashes are BANNED. Use periods, commas, or
natural conjunctions like "and", "but", "however". Natural language only.

Length: 200-2000 characters. Validator enforces.

## Cult-marker bar (TWO conditions, both canonical)
cult_marker_if_denied=true requires:
1. would_die_for=true (entailment). Denial constitutes denial of the gospel
   itself or a core Trinitarian or Christological boundary clearly mandated
   by Scripture's own lexical pattern.
2. Apparatus + interlinear + concordance demonstrate the doctrine canonically
   (pan-canonical lexical reading, not from a single passage).

Lineage agreement does NOT grant or withhold cult-marker status. Counter-witness
is recorded for diagnostic completeness; it does not vote. Even Trinity clears
or fails on its own canonical evidence.

The Brethren-on-trial discipline is preserved through canonical demonstration:
most Brethren distinctives lack unambiguous pan-canonical lexical support and
will fail condition 2 honestly.

## Confidence (lexical clarity, not lineage agreement)
- high: apparatus + interlinear unambiguous AND concordance pan-canonical AND
  hermeneutic uncontested.
- medium: apparatus paywalled and interlinear alone carries the verdict OR
  complicating texts require harmonization OR verdict requires non-default
  hermeneutic OR lemma-network is contested at the lexical level.
- low: Scripture silent or ambiguous OR concordance shows no pan-canonical
  demonstration OR heavy inference required.

Counter-witness divergence or convergence does NOT shift confidence.

## Output (single JSON file → evidence/{qid}.json)

The shape is locked in docs/ANSWER_SCHEMA.md. Do not invent extra fields.

{{
  "id": "{qid}",
  "answer": {{
    "id": "{qid}",
    "affirms": true | false | null,
    "rationale": "<1-2 sentences, scripturally grounded; cite apparatus / interlinear / concordance>",
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
  }},
  "evidence": {{
    "stem_audit": {{
      "verdict_preloaded": <bool>,
      "neutralized_form": "<string or null>",
      "notes": "<string or null>"
    }},
    "lay_summary": {{
      "reasoning": "<plain-English Scripture-based verdict justification. Required structure: (1) verdict in everyday language; (2) strongest reason FOR from Scripture, named-verse plain words; (3) strongest counterargument from Scripture's own complicating texts, named-verse plain words; (4) how the verdict handles the tension or honest acknowledgment it remains. NO denominational or lineage names in this section; that goes in denominational_landscape. >=100 chars, <=500 words. NO jargon (Strong's, Niphal, Piel, Hiphil, Granville-Sharp, Colwell, anarthrous, articular, hapax legomenon, lemma, morpheme, BHS, NA28, UBS5, aorist, septuagint, preterite). NO em or en dashes.>",
      "denominational_landscape": "<plain-English description of where major Christian lineages agree or disagree on this proposition. Name the lineages (patristic, Catholic, Lutheran, Anglican, Reformed, Methodist, Anabaptist, Pentecostal, Eastern Orthodox) with brief positions. Where applicable, name public-record cult or heterodox carriers of denial (Mormonism, Jehovah's Witnesses, Iglesia ni Cristo, William Branham, Christian Science, Mary Baker Eddy, Christadelphians, etc.) and what their denial places them in relation to historic Christianity. This section is DESCRIPTIVE of church history; it does NOT vote on the verdict. >=100 chars, <=500 words. NO jargon. NO em or en dashes.>"
    }},
    "scripture": [
      {{"ref": "Rom.6.3", "key_term": "βάπτισμα (baptisma) G908",
        "force": "<lexical force in one line>",
        "supports": "for|against|complicates|neutral",
        "genre": "narrative|epistle|prophecy|wisdom|apocalyptic|gospel|law|psalm|parable",
        "figures": []}}
    ],
    "concordance_lemmas_traversed": ["G908", "G4916"],
    "complicating_texts_searched": true,
    "hermeneutics": {{
      "primary_method": "grammatico-historical|redemptive-historical|quadriga|patristic-typological|accommodation",
      "frameworks_in_play": [],
      "analogia_scripturae_invoked": <bool>,
      "progressive_revelation_factor": <bool>,
      "competing_lens_verdicts": [],
      "notes": "<short narrative>"
    }},
    "counter_witness": [
      {{"tradition": "patristic|catholic_magisterial|lutheran|anglican|reformed|methodist|anabaptist|continuationist|eastern_orthodox|pentecostal",
        "anchor": "<source citation>", "verified": <bool>,
        "stance": "affirms|denies|complicates",
        "key_phrase": "<≤200 chars>"}}
    ],
    "web": [
      {{"url": "https://...",
        "category": "primary_repository|magisterial|patristic_archive|tradition_primary|interlinear|critical_apparatus",
        "stance": "supports|opposes|complicates|nuance",
        "quote": "<≤200 chars>"}}
    ],
    "confidence": "high|medium|low",
    "flags": []
  }}
}}

Write to: evidence/{qid}.json (relative to repo root).

## Stop conditions / flags
- stem_audit.verdict_preloaded=true → flag `stem-pre-loaded-verdict`, work neutralized.
- Apparatus + interlinear contradict counter-witness consensus → flag
  `apparatus-vs-counter-witness-conflict`. Apparatus wins. Confidence is NOT
  lowered; lineage divergence is diagnostic, not confidence-shifting.
- Counter-witness sources from kin confessions disagree → flag
  `confession-tradition-divergence` for diagnostic information.
- Concordance reveals doctrine NOT pan-canonically supported → confidence=low,
  flag `single-passage-doctrine`.
- Zero counter-witness on any tier → flag `counter-witness-missing` for
  research-quality tracking. Confidence is NOT lowered.
- Cannot reach confident verdict from apparatus + interlinear + concordance →
  confidence=low, affirms=null, flag `needs-elder-input`.
- cult_marker_if_denied=true without canonical demonstration (single-passage
  or lexically ambiguous) → incoherent; re-derive with `affirms` and
  `cult_marker` re-evaluated honestly.
- Concordance unavailable (Neo4j down, no fallback) → hard fail; report up.
- Never bluff. Never invent scripture. Note guesses in flags.

## Style
- Concise. No emoji. No filler.
- Cite full URLs.
- Counter-witness key_phrase / web quote ≤200 chars.
- Final action: Write evidence/{qid}.json. Then return a one-sentence summary
  of verdict + confidence to the orchestrator.
"""


def build_prompt(qid: str) -> str:
    q = question_by_id(qid)
    if q is None:
        raise KeyError(qid)
    return PROMPT_TEMPLATE.format(
        qid=qid, question_json=json.dumps(q, indent=2, ensure_ascii=False)
    )


def _required_dispensational_flags() -> set[str]:
    """Question ids where dispensational-lens-required flag is mandatory if affirms=true.

    Loaded from tools/verify_catalogs.json H6.
    """
    catalog_path = ROOT / "tools" / "verify_catalogs.json"
    if not catalog_path.exists():
        return set()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return set(catalog.get("H6_dispensational_lens_required", []))


def _required_anthropomorphism() -> set[str]:
    """Question ids that must carry an anthropomorphism/anthropopathism citation.

    Loaded from tools/verify_catalogs.json H5.
    """
    catalog_path = ROOT / "tools" / "verify_catalogs.json"
    if not catalog_path.exists():
        return set()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return set(catalog.get("H5_anthropomorphism_required", []))


def _cult_marker_eligible() -> set[str]:
    catalog_path = ROOT / "tools" / "verify_catalogs.json"
    if not catalog_path.exists():
        return set()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return set(catalog.get("K2_cult_marker_eligible", []))


def validate(qid: str) -> tuple[bool, list[str]]:
    """Validate evidence/<qid>.json against the locked schema.

    Returns (ok, errors). ok=True only when errors is empty.
    """
    f = EVIDENCE / f"{qid}.json"
    if not f.exists():
        return False, ["missing-file"]
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"parse-error:{e}"]

    errs: list[str] = []

    # Top-level shape
    if d.get("id") != qid:
        errs.append("id-mismatch")

    # Answer (13 fields)
    a = d.get("answer", {}) or {}
    for k in ANSWER_FIELDS:
        if k not in a:
            errs.append(f"missing-answer.{k}")
    if a.get("cult_marker_if_denied") is True and a.get("would_die_for") is not True:
        errs.append("entailment-violation:cult_marker_without_die_for")
    if a.get("cult_marker_if_denied") is True and a.get("affirms") is not True:
        errs.append("entailment-violation:cult_marker_without_affirms_true")

    # Evidence shape
    if "evidence" not in d:
        errs.append("missing-evidence")
        return (not errs), errs
    ev = d["evidence"]

    # Reject any legacy keys
    for k in LEGACY_EVIDENCE_KEYS:
        if k in ev:
            errs.append(f"legacy-evidence-key:{k}")

    # Required evidence fields
    for k in EVIDENCE_REQUIRED_FIELDS:
        if k not in ev:
            errs.append(f"missing-evidence.{k}")

    # stem_audit shape
    sa = ev.get("stem_audit", {}) or {}
    if "verdict_preloaded" not in sa or not isinstance(sa.get("verdict_preloaded"), bool):
        errs.append("evidence.stem_audit.verdict_preloaded-bad")
    if sa.get("verdict_preloaded") is True and not sa.get("neutralized_form"):
        errs.append("evidence.stem_audit.neutralized_form-missing")

    # lay_summary: required nested object with two paragraphs.
    # Each paragraph: >=100 chars, <=500 words, no jargon, no em/en dashes.
    lay = ev.get("lay_summary")
    if not isinstance(lay, dict):
        errs.append("evidence.lay_summary-not-object")
    else:
        for sub in LAY_SUMMARY_SUBFIELDS:
            text = lay.get(sub)
            if not isinstance(text, str):
                errs.append(f"evidence.lay_summary.{sub}-missing-or-not-string")
                continue
            n_chars = len(text)
            n_words = len(text.split())
            if n_chars < LAY_SUMMARY_MIN_CHARS:
                errs.append(f"evidence.lay_summary.{sub}-too-short:{n_chars}<{LAY_SUMMARY_MIN_CHARS}-chars")
            if n_words > LAY_SUMMARY_MAX_WORDS:
                errs.append(f"evidence.lay_summary.{sub}-too-long:{n_words}>{LAY_SUMMARY_MAX_WORDS}-words")
            text_lower = text.lower()
            leaks = [
                t for t in LAY_SUMMARY_JARGON_TOKENS
                if re.search(rf"\b{re.escape(t.lower())}\b", text_lower)
            ]
            if leaks:
                errs.append(f"evidence.lay_summary.{sub}-jargon-leak:{','.join(leaks)}")
            if any(d in text for d in LAY_SUMMARY_BANNED_DASHES):
                errs.append(f"evidence.lay_summary.{sub}-em-dash-banned:use-periods-or-commas")

    # scripture[] entries
    scripture = ev.get("scripture") or []
    if not isinstance(scripture, list) or len(scripture) == 0:
        errs.append("evidence.scripture-empty")
    else:
        for i, s in enumerate(scripture):
            if not isinstance(s, dict):
                errs.append(f"evidence.scripture[{i}]-not-object")
                continue
            for k in ("ref", "key_term", "force", "supports", "genre", "figures"):
                if k not in s:
                    errs.append(f"evidence.scripture[{i}].{k}-missing")
            if s.get("supports") not in VALID_SUPPORTS:
                errs.append(f"evidence.scripture[{i}].supports-invalid")
            if s.get("genre") not in VALID_GENRES:
                errs.append(f"evidence.scripture[{i}].genre-invalid")
            figs = s.get("figures")
            if not isinstance(figs, list):
                errs.append(f"evidence.scripture[{i}].figures-not-list")
            else:
                for fig in figs:
                    if fig not in VALID_FIGURES:
                        errs.append(f"evidence.scripture[{i}].figures.{fig}-invalid")

    # concordance_lemmas_traversed (mandatory non-empty)
    lemmas = ev.get("concordance_lemmas_traversed")
    if not isinstance(lemmas, list) or len(lemmas) == 0:
        errs.append("evidence.concordance_lemmas_traversed-empty")
    else:
        for lem in lemmas:
            if not (isinstance(lem, str) and (lem.startswith("G") or lem.startswith("H"))):
                errs.append(f"evidence.concordance_lemmas_traversed.{lem}-not-strongs")

    # complicating_texts_searched mandatory true
    if ev.get("complicating_texts_searched") is not True:
        errs.append("evidence.complicating_texts_searched-not-true")

    # hermeneutics block
    h = ev.get("hermeneutics", {}) or {}
    if h.get("primary_method") not in VALID_PRIMARY_METHODS:
        errs.append("evidence.hermeneutics.primary_method-invalid")
    if not isinstance(h.get("frameworks_in_play"), list):
        errs.append("evidence.hermeneutics.frameworks_in_play-not-list")
    if not isinstance(h.get("analogia_scripturae_invoked"), bool):
        errs.append("evidence.hermeneutics.analogia_scripturae_invoked-not-bool")
    if not isinstance(h.get("progressive_revelation_factor"), bool):
        errs.append("evidence.hermeneutics.progressive_revelation_factor-not-bool")

    # counter_witness presence-or-flag check, universal (tier abolished).
    cw = ev.get("counter_witness") or []
    if (not cw) and "counter-witness-missing" not in (ev.get("flags") or []):
        errs.append("counter-witness-missing-without-flag")
    for i, c in enumerate(cw):
        if not isinstance(c, dict):
            errs.append(f"evidence.counter_witness[{i}]-not-object")
            continue
        if c.get("tradition") not in VALID_TRADITIONS:
            errs.append(f"evidence.counter_witness[{i}].tradition-invalid")
        if c.get("stance") not in VALID_STANCES:
            errs.append(f"evidence.counter_witness[{i}].stance-invalid")

    # web entries
    for i, w in enumerate(ev.get("web") or []):
        if not isinstance(w, dict):
            errs.append(f"evidence.web[{i}]-not-object")
            continue
        if w.get("category") not in VALID_WEB_CATEGORIES:
            errs.append(f"evidence.web[{i}].category-invalid")
        if w.get("stance") not in VALID_WEB_STANCES:
            errs.append(f"evidence.web[{i}].stance-invalid")

    # confidence + flags
    if ev.get("confidence") not in VALID_CONFIDENCE:
        errs.append("evidence.confidence-invalid")
    if not isinstance(ev.get("flags"), list):
        errs.append("evidence.flags-not-list")

    # Cult-marker canonical-demonstration check (lexical breadth proxy for
    # "pan-canonical, not single-passage"). Lineage agreement is NOT checked;
    # under the revised rule, Scripture's lexical clarity drives the bar.
    if a.get("cult_marker_if_denied") is True:
        n_lemmas = len(ev.get("concordance_lemmas_traversed", []) or [])
        n_anchors = len(ev.get("scripture", []) or [])
        if n_lemmas < CULT_MARKER_MIN_LEMMAS:
            errs.append(
                f"cult-marker-without-canonical-demonstration:lemmas-{n_lemmas}-need-{CULT_MARKER_MIN_LEMMAS}"
            )
        if n_anchors < CULT_MARKER_MIN_ANCHORS:
            errs.append(
                f"cult-marker-without-canonical-demonstration:anchors-{n_anchors}-need-{CULT_MARKER_MIN_ANCHORS}"
            )

    # Cult-marker eligibility (catalog allow-list)
    if a.get("cult_marker_if_denied") is True:
        eligible = _cult_marker_eligible()
        if eligible and qid not in eligible:
            errs.append("cult-marker-on-non-eligible-question")

    # H5 anthropomorphism check
    h5 = _required_anthropomorphism()
    if qid in h5:
        has_anthro = any(
            ("anthropomorphism" in (s.get("figures") or [])
             or "anthropopathism" in (s.get("figures") or []))
            for s in scripture
        )
        if not has_anthro and "anthropomorphic-passages-omitted" not in (ev.get("flags") or []):
            errs.append("anthropomorphism-required-not-cited")

    # H6 dispensational flag
    h6 = _required_dispensational_flags()
    if qid in h6 and a.get("affirms") is True:
        if "dispensational-lens-required" not in (ev.get("flags") or []):
            errs.append("dispensational-lens-flag-missing")

    return (not errs), errs


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("worklist", help="List question ids without complete evidence")
    pp = sub.add_parser("prompt", help="Print the prompt for a question id")
    pp.add_argument("qid")
    pv = sub.add_parser("validate", help="Validate one evidence file")
    pv.add_argument("qid")
    sub.add_parser("validate-all", help="Validate every evidence file")

    p.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        default="opus",
        help="Model used for subagent invocations. DEFAULT: opus. The synthesis step "
             "(apparatus + concordance + counter-witness + hermeneutic) genuinely "
             "benefits from Opus reasoning quality; the project produces a baseline "
             "referenced indefinitely, so 'cannot afford to re-run' tilts toward "
             "Opus on the first pass even at the cost of more rate-limit windows.",
    )

    args = p.parse_args()

    if args.cmd == "worklist":
        wl = worklist()
        print(f"{len(wl)} todo (model={args.model})")
        for x in wl[:30]:
            print(" ", x)
        if len(wl) > 30:
            print(f"  ...and {len(wl)-30} more")
        return 0
    if args.cmd == "prompt":
        print(build_prompt(args.qid))
        return 0
    if args.cmd == "validate":
        ok, errs = validate(args.qid)
        print("OK" if ok else f"FAIL: {errs}")
        return 0 if ok else 1
    if args.cmd == "validate-all":
        bad: list[tuple[str, list[str]]] = []
        questions = load_questions()
        for q in questions:
            ok, errs = validate(q["id"])
            if not ok:
                bad.append((q["id"], errs))
        print(f"{len(bad)} invalid of {len(questions)}")
        for qid, errs in bad[:30]:
            print(" ", qid, errs)
        return 0 if not bad else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
