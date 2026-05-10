"""Verdict ingestion: baseline.json + evidence/*.json -> Neo4j.

Bridges the orchestrator output into the concordance graph so the MCP server
(Tier 3) can query verdicts alongside the lemma index and cross-references.

Run order (post-orchestrator, idempotent MERGE):
    python -m ingest.adapters.verdict_loader load-questions
    python -m ingest.adapters.verdict_loader load-evidence
    python -m ingest.adapters.verdict_loader load-baseline       # collated answers from baseline.json
    python -m ingest.adapters.verdict_loader load-all

Schema (extends concordance):
    (:Question {id, category, subcategory, kind, statement, tier,
                historical_consensus, brethren_distinctive,
                scripture_anchors, confessional_anchors})
    (:Verdict {question_id, viewpoint, affirms, rationale, confidence, notes,
               would_die_for, cult_marker_if_denied, ...all 9 thresholds...,
               primary_method, frameworks_in_play, analogia_scripturae_invoked,
               progressive_revelation_factor, stem_verdict_preloaded})
    (:ScriptureCitation {citation_id, ref, key_term, force, supports, genre, figures})
    (:CounterWitness    {witness_id, tradition, anchor, verified, stance, key_phrase})
    (:Framework         {name})
    (:CompetingLens     {lens_id, lens, verdict, note})
    (:Flag              {name})

    (:Question)-[:HAS_VERDICT]->(:Verdict)
    (:Verdict)-[:CITES]->(:ScriptureCitation)-[:REFS]->(:Verse)
    (:Verdict)-[:TRAVERSED_LEMMA]->(:Lemma)
    (:Verdict)-[:CONSULTS]->(:CounterWitness)
    (:Verdict)-[:USES_FRAMEWORK]->(:Framework)
    (:Verdict)-[:CONSIDERED_LENS]->(:CompetingLens)
    (:Verdict)-[:FLAGGED]->(:Flag)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_FILE = ROOT / "questions.json"
BASELINE_FILE = ROOT / "baseline.json"
EVIDENCE_DIR = ROOT / "evidence"
RESPONSES_DIR = ROOT / "responses"
CONSOLIDATED_FILE = ROOT / "consolidated.json"


def _driver():
    from neo4j import GraphDatabase  # type: ignore
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not pwd:
        raise RuntimeError("NEO4J_PASSWORD env var required")
    return GraphDatabase.driver(uri, auth=("neo4j", pwd))


def apply_constraints(driver) -> None:
    """Idempotent constraint creation for the verdict-graph layer."""
    cypher = [
        "CREATE CONSTRAINT question_id_uq IF NOT EXISTS "
        "FOR (q:Question) REQUIRE q.id IS UNIQUE",
        "CREATE CONSTRAINT verdict_id_uq IF NOT EXISTS "
        "FOR (v:Verdict) REQUIRE (v.question_id, v.viewpoint) IS UNIQUE",
        "CREATE CONSTRAINT framework_name_uq IF NOT EXISTS "
        "FOR (f:Framework) REQUIRE f.name IS UNIQUE",
        "CREATE CONSTRAINT flag_name_uq IF NOT EXISTS "
        "FOR (f:Flag) REQUIRE f.name IS UNIQUE",
        "CREATE INDEX question_tier IF NOT EXISTS "
        "FOR (q:Question) ON (q.tier)",
        "CREATE INDEX question_category IF NOT EXISTS "
        "FOR (q:Question) ON (q.category)",
        "CREATE INDEX verdict_confidence IF NOT EXISTS "
        "FOR (v:Verdict) ON (v.confidence)",
    ]
    with driver.session() as s:
        for c in cypher:
            s.run(c)


# ----------------------------------------------------------------------------
# Question loader
# ----------------------------------------------------------------------------

UPSERT_QUESTION = """
MERGE (q:Question {id: $id})
SET q.category = $category, q.subcategory = $subcategory,
    q.kind = $kind, q.statement = $statement, q.tier = $tier,
    q.historical_consensus = $historical_consensus,
    q.brethren_distinctive = $brethren_distinctive,
    q.scripture_anchors = $scripture_anchors,
    q.confessional_anchors = $confessional_anchors,
    q.updated_at = datetime()
"""


def load_questions() -> int:
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"missing: {QUESTIONS_FILE}")
    raw = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    questions = raw["questions"]

    drv = _driver()
    apply_constraints(drv)
    n = 0
    with drv.session() as session:
        for q in questions:
            session.run(
                UPSERT_QUESTION,
                id=q["id"],
                category=q.get("category"),
                subcategory=q.get("subcategory"),
                kind=q.get("kind"),
                statement=q.get("statement"),
                tier=q.get("tier"),
                historical_consensus=q.get("historical_consensus"),
                brethren_distinctive=bool(q.get("brethren_distinctive")),
                scripture_anchors=q.get("scripture_anchors") or [],
                confessional_anchors=q.get("confessional_anchors") or [],
            )
            n += 1
    drv.close()
    print(f"questions: {n} upserted", file=sys.stderr)
    return n


# ----------------------------------------------------------------------------
# Evidence loader (one evidence/*.json per question)
# ----------------------------------------------------------------------------

UPSERT_VERDICT_AND_EVIDENCE = """
// Question + Verdict identity
MERGE (q:Question {id: $question_id})
MERGE (v:Verdict {question_id: $question_id, viewpoint: $viewpoint})
SET v += $verdict_props, v.updated_at = datetime()
MERGE (q)-[:HAS_VERDICT {viewpoint: $viewpoint}]->(v)

// Wipe existing evidence-graph children for this verdict before rebuilding
// (safer than diffing; the file is the source of truth)
WITH v
OPTIONAL MATCH (v)-[r1:CITES]->(sc:ScriptureCitation)
WITH v, collect(sc) AS old_citations, collect(r1) AS rels1
FOREACH(rel IN rels1 | DELETE rel)
FOREACH(n IN old_citations | DETACH DELETE n)
WITH v
OPTIONAL MATCH (v)-[r2:CONSULTS]->(cw:CounterWitness)
WITH v, collect(cw) AS old_witnesses, collect(r2) AS rels2
FOREACH(rel IN rels2 | DELETE rel)
FOREACH(n IN old_witnesses | DETACH DELETE n)
WITH v
OPTIONAL MATCH (v)-[r3:CONSIDERED_LENS]->(cl:CompetingLens)
WITH v, collect(cl) AS old_lenses, collect(r3) AS rels3
FOREACH(rel IN rels3 | DELETE rel)
FOREACH(n IN old_lenses | DETACH DELETE n)
WITH v
OPTIONAL MATCH (v)-[r4:TRAVERSED_LEMMA]->(:Lemma)
FOREACH(rel IN collect(r4) | DELETE rel)
WITH v
OPTIONAL MATCH (v)-[r5:USES_FRAMEWORK]->(:Framework)
FOREACH(rel IN collect(r5) | DELETE rel)
WITH v
OPTIONAL MATCH (v)-[r6:FLAGGED]->(:Flag)
FOREACH(rel IN collect(r6) | DELETE rel)

// Scripture citations -> link to Verse
WITH v
UNWIND $scripture AS sc
  CREATE (s:ScriptureCitation {
    citation_id: $question_id + '|' + $viewpoint + '|' + sc.idx,
    ref: sc.ref, key_term: sc.key_term, force: sc.force,
    supports: sc.supports, genre: sc.genre, figures: sc.figures
  })
  MERGE (v)-[:CITES]->(s)
  MERGE (target:Verse {verse_osis: sc.ref_osis})
  MERGE (s)-[:REFS]->(target)

// Concordance lemma traversal
WITH v
UNWIND $lemmas_traversed AS strongs
  MATCH (l:Lemma {strongs: strongs})
  MERGE (v)-[:TRAVERSED_LEMMA]->(l)

// Counter-witness
WITH v
UNWIND $counter_witness AS cw
  CREATE (w:CounterWitness {
    witness_id: $question_id + '|' + $viewpoint + '|' + cw.idx,
    tradition: cw.tradition, anchor: cw.anchor,
    verified: cw.verified, stance: cw.stance, key_phrase: cw.key_phrase
  })
  MERGE (v)-[:CONSULTS]->(w)

// Frameworks in play
WITH v
UNWIND $frameworks AS fname
  MERGE (f:Framework {name: fname})
  MERGE (v)-[:USES_FRAMEWORK]->(f)

// Competing-lens verdicts
WITH v
UNWIND $competing_lenses AS cl
  CREATE (lens:CompetingLens {
    lens_id: $question_id + '|' + $viewpoint + '|' + cl.idx,
    lens: cl.lens, verdict: cl.verdict, note: cl.note
  })
  MERGE (v)-[:CONSIDERED_LENS]->(lens)

// Flags
WITH v
UNWIND $flags AS fname
  MERGE (fl:Flag {name: fname})
  MERGE (v)-[:FLAGGED]->(fl)
"""


def _normalize_osis(ref: str) -> str:
    """Best-effort: pass through OSIS as-is. Evidence files use OSIS already."""
    return ref.split("-")[0].split(",")[0].strip()


def _verdict_props(answer: dict, evidence: dict) -> dict:
    h = (evidence or {}).get("hermeneutics", {}) or {}
    sa = (evidence or {}).get("stem_audit", {}) or {}
    return {
        "affirms": answer.get("affirms"),
        "rationale": answer.get("rationale"),
        "notes": answer.get("notes"),
        "would_die_for": answer.get("would_die_for"),
        "cult_marker_if_denied": answer.get("cult_marker_if_denied"),
        "would_visit_if_otherwise": answer.get("would_visit_if_otherwise"),
        "would_participate_if_otherwise": answer.get("would_participate_if_otherwise"),
        "would_serve_if_otherwise": answer.get("would_serve_if_otherwise"),
        "would_be_member_if_otherwise": answer.get("would_be_member_if_otherwise"),
        "would_let_children_be_taught_otherwise": answer.get("would_let_children_be_taught_otherwise"),
        "would_marry_if_held_otherwise": answer.get("would_marry_if_held_otherwise"),
        "would_publicly_correct_if_otherwise": answer.get("would_publicly_correct_if_otherwise"),
        "confidence": (evidence or {}).get("confidence"),
        "primary_method": h.get("primary_method"),
        "frameworks_in_play": h.get("frameworks_in_play") or [],
        "analogia_scripturae_invoked": h.get("analogia_scripturae_invoked"),
        "progressive_revelation_factor": h.get("progressive_revelation_factor"),
        "stem_verdict_preloaded": sa.get("verdict_preloaded"),
        "stem_neutralized_form": sa.get("neutralized_form"),
    }


def _scripture_records(scripture: list[dict]) -> list[dict]:
    out = []
    for i, s in enumerate(scripture or []):
        ref = s.get("ref") or ""
        out.append({
            "idx": str(i),
            "ref": ref,
            "ref_osis": _normalize_osis(ref),
            "key_term": s.get("key_term"),
            "force": s.get("force"),
            "supports": s.get("supports"),
            "genre": s.get("genre"),
            "figures": s.get("figures") or [],
        })
    return out


def _counter_witness_records(cw_list: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cw_list or []):
        out.append({
            "idx": str(i),
            "tradition": c.get("tradition"),
            "anchor": c.get("anchor"),
            "verified": bool(c.get("verified")),
            "stance": c.get("stance"),
            "key_phrase": c.get("key_phrase"),
        })
    return out


def _competing_lens_records(cl_list: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cl_list or []):
        out.append({
            "idx": str(i),
            "lens": c.get("lens"),
            "verdict": c.get("verdict"),
            "note": c.get("note"),
        })
    return out


def load_evidence(viewpoint: str = "inferred-from-sources") -> int:
    """Walk evidence/*.json and upsert each as a (Question)-[:HAS_VERDICT]->(Verdict)
    plus child evidence-graph nodes."""
    files = sorted(EVIDENCE_DIR.glob("*.json"))
    if not files:
        print(f"no evidence files under {EVIDENCE_DIR}", file=sys.stderr)
        return 0

    drv = _driver()
    apply_constraints(drv)
    n = 0
    with drv.session() as session:
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"skip {f.name}: parse-error {e}", file=sys.stderr)
                continue
            qid = data.get("id")
            if not qid:
                continue
            answer = data.get("answer", {}) or {}
            evidence = data.get("evidence", {}) or {}
            h = evidence.get("hermeneutics", {}) or {}
            session.run(
                UPSERT_VERDICT_AND_EVIDENCE,
                question_id=qid,
                viewpoint=viewpoint,
                verdict_props=_verdict_props(answer, evidence),
                scripture=_scripture_records(evidence.get("scripture") or []),
                lemmas_traversed=evidence.get("concordance_lemmas_traversed") or [],
                counter_witness=_counter_witness_records(evidence.get("counter_witness") or []),
                frameworks=h.get("frameworks_in_play") or [],
                competing_lenses=_competing_lens_records(h.get("competing_lens_verdicts") or []),
                flags=evidence.get("flags") or [],
            )
            n += 1
            if n % 25 == 0:
                print(f"  ...{n} verdicts upserted", file=sys.stderr)
    drv.close()
    print(f"evidence: {n} verdicts upserted (viewpoint={viewpoint})", file=sys.stderr)
    return n


# ----------------------------------------------------------------------------
# baseline.json loader (collated 13-field answers; redundant with evidence
# load if evidence/*.json is complete, but useful for ingest order independence)
# ----------------------------------------------------------------------------

UPSERT_VERDICT_FROM_BASELINE = """
MERGE (q:Question {id: $question_id})
MERGE (v:Verdict {question_id: $question_id, viewpoint: $viewpoint})
SET v += $verdict_props, v.updated_at = datetime()
MERGE (q)-[:HAS_VERDICT {viewpoint: $viewpoint}]->(v)
"""


def load_baseline(file: Path | None = None, viewpoint_override: str | None = None) -> int:
    file = file or BASELINE_FILE
    if not file.exists():
        print(f"missing: {file}", file=sys.stderr)
        return 0
    raw = json.loads(file.read_text(encoding="utf-8"))
    viewpoint = viewpoint_override or raw.get("viewpoint", "inferred-from-sources")
    answers = raw.get("answers") or []

    drv = _driver()
    apply_constraints(drv)
    n = 0
    with drv.session() as session:
        for a in answers:
            qid = a.get("id")
            if not qid:
                continue
            session.run(
                UPSERT_VERDICT_FROM_BASELINE,
                question_id=qid,
                viewpoint=viewpoint,
                verdict_props={
                    k: a.get(k) for k in (
                        "affirms", "rationale", "notes",
                        "would_die_for", "cult_marker_if_denied",
                        "would_visit_if_otherwise", "would_participate_if_otherwise",
                        "would_serve_if_otherwise", "would_be_member_if_otherwise",
                        "would_let_children_be_taught_otherwise",
                        "would_marry_if_held_otherwise",
                        "would_publicly_correct_if_otherwise",
                    )
                },
            )
            n += 1
    drv.close()
    print(f"baseline: {n} verdicts upserted (viewpoint={viewpoint})", file=sys.stderr)
    return n


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load-questions", help="Load 221 Question nodes from questions.json")
    e = sub.add_parser("load-evidence", help="Load Verdict + evidence graph from evidence/*.json")
    e.add_argument("--viewpoint", default="inferred-from-sources")
    b = sub.add_parser("load-baseline", help="Load Verdict nodes from baseline.json (collated)")
    b.add_argument("--file", type=Path, default=None)
    b.add_argument("--viewpoint", default=None)
    sub.add_parser("load-all", help="load-questions + load-evidence + load-baseline")

    args = p.parse_args()
    if args.cmd == "load-questions":
        load_questions()
    elif args.cmd == "load-evidence":
        load_evidence(viewpoint=args.viewpoint)
    elif args.cmd == "load-baseline":
        load_baseline(file=args.file, viewpoint_override=args.viewpoint)
    elif args.cmd == "load-all":
        load_questions()
        load_evidence()
        load_baseline()
    return 0


if __name__ == "__main__":
    sys.exit(main())
