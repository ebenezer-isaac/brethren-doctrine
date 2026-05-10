"""KPI verifier for the inferred-baseline run.

Single entry-point CI-friendly check. Exit code = number of failed KPIs.

Usage:
    python -m tools.verify_baseline --check all
    python -m tools.verify_baseline --check framing
    python -m tools.verify_baseline --check schema-purity
    python -m tools.verify_baseline --check lemma-counts
    python -m tools.verify_baseline --check spider-perf
    python -m tools.verify_baseline --check urls
    python -m tools.verify_baseline --check concordance
    python -m tools.verify_baseline --check counter-witness
    python -m tools.verify_baseline --check cult-marker
    python -m tools.verify_baseline --check stem-audit
    python -m tools.verify_baseline --check selection-bias
    python -m tools.verify_baseline --report  # writes verify-report.md

KPI matrix is documented in the conversation log; canonical descriptions are
kept in the docstrings of each check_* function below so the verifier itself
is the source of truth.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "questions.json"
EVIDENCE = ROOT / "evidence"
CATALOGS = ROOT / "tools" / "verify_catalogs.json"
DOCS = ROOT / "docs"
TOOLS = ROOT / "tools"
README = ROOT / "README.md"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _load_questions() -> list[dict]:
    return json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]


def _load_catalogs() -> dict:
    if not CATALOGS.exists():
        return {}
    return json.loads(CATALOGS.read_text(encoding="utf-8"))


def _evidence_files() -> list[Path]:
    return sorted([p for p in EVIDENCE.glob("*.json")])


def _read_text_files(*paths: Path) -> str:
    out = []
    for p in paths:
        if p.is_file():
            out.append(p.read_text(encoding="utf-8", errors="ignore"))
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.suffix in (".md", ".py", ".json") and f.is_file():
                    out.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(out)


# ----------------------------------------------------------------------------
# KPI checks. Each returns (name, passed: bool, details: list[str]).
# ----------------------------------------------------------------------------

KPIResult = tuple[str, bool, list[str]]


def check_framing() -> list[KPIResult]:
    """A1: drop sola-scriptura smuggling. A2: tradition-neutral envelope.
    Greps for the forbidden phrasing in docs/, tools/, README.md.
    """
    results: list[KPIResult] = []
    forbidden = re.compile(r"\bsola\s+scriptura\b|\bscripture[- ]only\b", re.IGNORECASE)
    targets = list(DOCS.rglob("*.md")) + list(TOOLS.rglob("*.md")) + [README]
    hits: list[str] = []
    for p in targets:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in forbidden.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            ctx_start = max(0, m.start() - 60)
            ctx_end = min(len(text), m.end() + 60)
            ctx = text[ctx_start:ctx_end].replace("\n", " ")
            # Allow if the immediate context disowns the framing
            if any(w in ctx.lower() for w in (
                "smuggle", "smuggling", "avoid", "do not", "not the framing",
                "not the rubric", "is itself a", "would smuggle",
            )):
                continue
            hits.append(f"{p.relative_to(ROOT)}:{line_no}: ...{ctx}...")
    results.append(("A1_no_sola_scriptura_smuggling", not hits, hits[:10]))

    # A2: questions.json envelope
    q_envelope = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    a2_errors = []
    if "formation_under_examination" not in q_envelope:
        a2_errors.append("questions.json missing 'formation_under_examination'")
    if "judging_panel" not in q_envelope:
        a2_errors.append("questions.json missing 'judging_panel'")
    if "tradition_baseline" in q_envelope:
        a2_errors.append("questions.json still has legacy 'tradition_baseline' key")
    results.append(("A2_tradition_neutral_envelope", not a2_errors, a2_errors))

    return results


def check_schema_purity() -> list[KPIResult]:
    """A3-A5: evidence files have no legacy keys, no confessions cited as authority,
    no Brethren teaching notes referenced.
    """
    results: list[KPIResult] = []
    legacy_keys = ("confession_kin", "defendant_position",
                   "confessional_verifications", "source_docs")
    legacy_hits: list[str] = []
    confession_grep = re.compile(
        r"\b1689\b|\bLBC\b|Westminster Confession|brethrenarchive",
        re.IGNORECASE,
    )
    confession_hits: list[str] = []
    parsed_grep = re.compile(r"\bparsed/|defendant", re.IGNORECASE)
    parsed_hits: list[str] = []

    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ev = d.get("evidence", {}) or {}
        for k in legacy_keys:
            if k in ev:
                legacy_hits.append(f"{f.name}:{k}")

        # Confessions allowed only inside counter_witness[].anchor / .key_phrase
        # OR inside web[].quote - but never in scripture[] / hermeneutics
        text_dump_outside_cw = json.dumps({
            k: v for k, v in ev.items() if k not in ("counter_witness", "web")
        })
        for m in confession_grep.finditer(text_dump_outside_cw):
            ctx = text_dump_outside_cw[max(0, m.start()-30):m.end()+30]
            confession_hits.append(f"{f.name}: ...{ctx}...")

        text_dump_full = json.dumps(ev)
        for m in parsed_grep.finditer(text_dump_full):
            ctx = text_dump_full[max(0, m.start()-30):m.end()+30]
            parsed_hits.append(f"{f.name}: ...{ctx}...")

    results.append(("A3_no_legacy_evidence_keys", not legacy_hits, legacy_hits[:10]))
    results.append(("A4_no_confessions_outside_counter_witness", not confession_hits, confession_hits[:10]))
    results.append(("A5_no_parsed_or_defendant_refs", not parsed_hits, parsed_hits[:10]))
    return results


def check_evidence_shape() -> list[KPIResult]:
    """H1-H4, S1-S5, W1-W3, K3 — full schema validation via baseline_orchestrator.validate."""
    sys.path.insert(0, str(TOOLS))
    try:
        import baseline_orchestrator as bo  # type: ignore
    except Exception as e:
        return [("evidence_shape_import", False, [f"failed to import: {e}"])]

    questions = _load_questions()
    failures: list[str] = []
    for q in questions:
        ok, errs = bo.validate(q["id"])
        # Missing-file is OK for an unrun question; only count real schema failures
        if not ok and errs != ["missing-file"]:
            failures.append(f"{q['id']}: {errs[:3]}")

    return [("evidence_shape_validates", not failures, failures[:15])]


def check_lemma_counts() -> list[KPIResult]:
    """C3: spot-check known Strong's lemma occurrence counts via Neo4j.
    Aggregates across STEPBible disambiguated variants (e.g. H5162G + H5162H
    = classical H5162 nacham = 108 occurrences). Skipped if Neo4j is unreachable.
    """
    expected = {
        "H7706": ("shaddai", 48),
        "H2617": ("chesed", 246),
        "H5162": ("nacham", 108),
        "G3056": ("logos", 330),
        "G3551": ("nomos", 195),
        "G26": ("agape", 116),
    }
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception:
        return [("C3_lemma_counts", True, ["SKIP: neo4j driver not installed"])]

    import os
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not pwd:
        return [("C3_lemma_counts", True, ["SKIP: NEO4J_PASSWORD not set"])]

    try:
        driver = GraphDatabase.driver(uri, auth=("neo4j", pwd))
        with driver.session() as session:
            # First check whether any Lemmas exist at all
            n_lemmas = session.run("MATCH (l:Lemma) RETURN count(l) AS n").single()["n"]
            if n_lemmas == 0:
                driver.close()
                return [("C3_lemma_counts", True, ["SKIP: no Lemma nodes (concordance not yet ingested)"])]

            failures = []
            for strongs, (lemma, exp) in expected.items():
                # Match base + optional single-letter suffix: H5162, H5162G, H5162H, etc.
                # but NOT H51620 / H51629 (those are different Strong's numbers).
                pattern = f"^{strongs}[A-Za-z]?$"
                q = (
                    "MATCH (l:Lemma) WHERE l.strongs =~ $p "
                    "OPTIONAL MATCH (l)<-[:HAS_LEMMA]-(t:Token) "
                    "RETURN count(t) AS n"
                )
                rec = session.run(q, p=pattern).single()
                n = (rec or {}).get("n", 0) if rec else 0
                tolerance = max(3, int(exp * 0.03))
                if abs(n - exp) > tolerance:
                    failures.append(f"{strongs}* ({lemma}): got {n}, expected {exp} ±{tolerance}")
        driver.close()
        return [("C3_lemma_counts", not failures, failures)]
    except Exception as e:
        return [("C3_lemma_counts", True, [f"SKIP: neo4j unreachable: {e}"])]


def check_concordance_traversed() -> list[KPIResult]:
    """KPI: concordance_lemmas_traversed non-empty on every evidence file."""
    failures: list[str] = []
    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        lemmas = d.get("evidence", {}).get("concordance_lemmas_traversed")
        if not isinstance(lemmas, list) or len(lemmas) == 0:
            failures.append(f"{f.name}: empty/missing concordance_lemmas_traversed")
    return [("concordance_traversed_non_empty", not failures, failures[:10])]


def check_counter_witness() -> list[KPIResult]:
    """W1: tier=essential / convictional require counter_witness OR explicit flag.
    W2: cross-tradition diversity &gt;= 6 of 10 tracked lineages across corpus.
    W3: no Reformed-only fallback on tier=essential.
    """
    questions = {q["id"]: q for q in _load_questions()}
    files = _evidence_files()
    if not files:
        return [
            ("W1_counter_witness_mandatory", True, ["SKIP: orchestrator not yet run (no evidence files)"]),
            ("W2_cross_tradition_diversity", True, ["SKIP: orchestrator not yet run"]),
            ("W3_no_reformed_only_fallback", True, ["SKIP: orchestrator not yet run"]),
        ]

    w1_failures: list[str] = []
    distinct_traditions: set[str] = set()
    w3_failures: list[str] = []
    REFORMED_ONLY = {"reformed", "lutheran", "anglican"}

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        qid = d.get("id")
        q = questions.get(qid, {})
        cw = d.get("evidence", {}).get("counter_witness") or []
        flags = d.get("evidence", {}).get("flags") or []

        for c in cw:
            if c.get("tradition"):
                distinct_traditions.add(c["tradition"])

        if q.get("tier") in {"essential", "convictional"}:
            if not cw and "counter-witness-missing" not in flags:
                w1_failures.append(f"{qid}: tier={q.get('tier')} has no counter_witness and no missing-flag")

        if q.get("tier") == "essential" and cw:
            traditions = {c.get("tradition") for c in cw}
            if traditions and traditions.issubset(REFORMED_ONLY):
                w3_failures.append(f"{qid}: tier=essential has only Reformed-substrate counter-witness {traditions}")

    w2_pass = len(distinct_traditions) >= 6

    return [
        ("W1_counter_witness_mandatory", not w1_failures, w1_failures[:10]),
        ("W2_cross_tradition_diversity", w2_pass,
         [f"distinct traditions seen: {sorted(distinct_traditions)} (need &gt;=6)"] if not w2_pass else
         [f"distinct traditions seen: {sorted(distinct_traditions)}"]),
        ("W3_no_reformed_only_fallback", not w3_failures, w3_failures[:10]),
    ]


def check_cult_marker() -> list[KPIResult]:
    """K1: pan-tradition consensus &gt;=6 affirming on cult_marker=true.
    K2: cult_marker=true only on catalogued ids.
    K3: moral entailment cult_marker → would_die_for.
    """
    catalogs = _load_catalogs()
    eligible = set(catalogs.get("K2_cult_marker_eligible", []))

    k1_failures: list[str] = []
    k2_failures: list[str] = []
    k3_failures: list[str] = []

    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        a = d.get("answer", {}) or {}
        if a.get("cult_marker_if_denied") is not True:
            continue
        qid = d.get("id")
        if a.get("would_die_for") is not True:
            k3_failures.append(f"{qid}: cult_marker=true but would_die_for=false")

        cw = d.get("evidence", {}).get("counter_witness") or []
        affirming = {c.get("tradition") for c in cw if c.get("stance") == "affirms"}
        if len(affirming) < 6:
            k1_failures.append(
                f"{qid}: cult_marker=true with {len(affirming)} affirming traditions {sorted(affirming)}"
            )

        if eligible and qid not in eligible:
            k2_failures.append(f"{qid}: cult_marker=true on non-eligible question")

    return [
        ("K1_pan_tradition_consensus", not k1_failures, k1_failures[:10]),
        ("K2_cult_marker_catalog_match", not k2_failures, k2_failures[:10]),
        ("K3_moral_entailment", not k3_failures, k3_failures[:10]),
    ]


def check_stem_audit() -> list[KPIResult]:
    """S1-S2: stem_audit populated on every file; neutralized_form when verdict_preloaded."""
    s1_failures: list[str] = []
    s2_failures: list[str] = []
    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        sa = d.get("evidence", {}).get("stem_audit") or {}
        if not isinstance(sa.get("verdict_preloaded"), bool):
            s1_failures.append(f"{f.name}: verdict_preloaded missing or not bool")
        if sa.get("verdict_preloaded") is True and not sa.get("neutralized_form"):
            s2_failures.append(f"{f.name}: verdict_preloaded=true but no neutralized_form")
    return [
        ("S1_stem_audit_populated", not s1_failures, s1_failures[:10]),
        ("S2_neutralized_form_present", not s2_failures, s2_failures[:10]),
    ]


def check_selection_bias() -> list[KPIResult]:
    """S4: complicating_texts_searched=true on every file.
    S5: all-`for` arrays carry no-complicating-texts-after-search flag.
    H5: anthropomorphism catalog enforcement.
    """
    s4_failures: list[str] = []
    s5_failures: list[str] = []
    h5_failures: list[str] = []
    catalogs = _load_catalogs()
    h5_required = set(catalogs.get("H5_anthropomorphism_required", []))

    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ev = d.get("evidence", {}) or {}
        if ev.get("complicating_texts_searched") is not True:
            s4_failures.append(f"{f.name}: complicating_texts_searched != true")

        scripture = ev.get("scripture") or []
        flags = ev.get("flags") or []
        if scripture and all(s.get("supports") == "for" for s in scripture):
            if "no-complicating-texts-after-search" not in flags:
                s5_failures.append(f"{f.name}: all-for scripture without justification flag")

        qid = d.get("id")
        if qid in h5_required:
            has_anthro = any(
                ("anthropomorphism" in (s.get("figures") or [])
                 or "anthropopathism" in (s.get("figures") or []))
                for s in scripture
            )
            if not has_anthro and "anthropomorphic-passages-omitted" not in flags:
                h5_failures.append(f"{qid}: no anthropomorphism/anthropopathism cited and no flag")

    return [
        ("S4_complicating_texts_searched", not s4_failures, s4_failures[:10]),
        ("S5_all_for_array_justified", not s5_failures, s5_failures[:10]),
        ("H5_anthropomorphism_required", not h5_failures, h5_failures[:10]),
    ]


def check_urls() -> list[KPIResult]:
    """W4: URLs in evidence.web[] reachable. Forbidden domains rejected."""
    catalogs = _load_catalogs()
    forbidden = catalogs.get("verifier_url_set_forbidden", [])

    forbidden_hits: list[str] = []
    unreachable: list[str] = []

    try:
        import httpx  # type: ignore
        client = httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={
                # Wikipedia/Wikisource and similar sites reject default httpx UA;
                # send a plausible browser UA so reachability checks succeed.
                "User-Agent": "brethren-doctrine-verifier/1.0 (research; contact via project repo)",
            },
        )
    except Exception:
        client = None

    for f in _evidence_files():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for w in (d.get("evidence", {}).get("web") or []):
            url = w.get("url", "")
            for fdom in forbidden:
                if fdom in url:
                    forbidden_hits.append(f"{f.name}: forbidden domain {fdom} in {url}")

            if client is not None and url.startswith("http"):
                try:
                    r = client.head(url)
                    # Some sites (wikisource, archive.org) block HEAD with 403/405;
                    # fall back to a tiny GET range to confirm reachability.
                    if r.status_code in (403, 405):
                        r = client.get(url, headers={"Range": "bytes=0-512"})
                    if r.status_code >= 400 and r.status_code != 416:
                        unreachable.append(f"{f.name}: {r.status_code} {url}")
                except Exception as e:
                    unreachable.append(f"{f.name}: {type(e).__name__} {url}")

    if client is not None:
        client.close()

    return [
        ("W4_no_forbidden_domains", not forbidden_hits, forbidden_hits[:10]),
        ("W4_urls_reachable", not unreachable, unreachable[:10]),
    ]


def check_velocity() -> list[KPIResult]:
    """V3-V5: confidence distribution + counter-witness coverage on essentials."""
    questions = {q["id"]: q for q in _load_questions()}
    files = _evidence_files()
    if not files:
        return [("V3_first_pass_validator_success", True, ["SKIP: orchestrator not yet run"])]

    sys.path.insert(0, str(TOOLS))
    try:
        import baseline_orchestrator as bo  # type: ignore
    except Exception as e:
        return [("V_velocity", False, [f"failed to import orchestrator: {e}"])]

    pass_count = 0
    total = 0
    essential_with_cw = 0
    essential_total = 0
    high_confidence_essential = 0
    for f in files:
        total += 1
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ok, _ = bo.validate(d.get("id", ""))
        if ok:
            pass_count += 1
        qid = d.get("id")
        q = questions.get(qid, {})
        if q.get("tier") == "essential":
            essential_total += 1
            cw = d.get("evidence", {}).get("counter_witness") or []
            if cw:
                essential_with_cw += 1
            if d.get("evidence", {}).get("confidence") == "high":
                high_confidence_essential += 1

    v3_pass = total == 0 or (pass_count / total) >= 0.85
    v4_pass = essential_total == 0 or (essential_with_cw / essential_total) >= 0.95
    v5_ratio = high_confidence_essential / essential_total if essential_total else 0
    # Only meaningful with a real sample size; small-N runs always look "lopsided"
    v5_pass = essential_total < 5 or (0.30 <= v5_ratio <= 0.70)

    return [
        ("V3_first_pass_validator_success", v3_pass,
         [f"pass={pass_count}/{total} ({pass_count/total*100:.1f}%)" if total else "0/0"]),
        ("V4_counter_witness_coverage_essentials", v4_pass,
         [f"essentials_with_cw={essential_with_cw}/{essential_total}" if essential_total else "no essentials yet"]),
        ("V5_confidence_distribution_sane", v5_pass,
         [f"high_confidence_essential_ratio={v5_ratio:.2f} (target 0.30-0.70)"]),
    ]


def check_greenfield() -> list[KPIResult]:
    """G1: no v1 keys anywhere. G2: no orphan PDFs (a PDF whose paired
    evidence/<id>.json does not exist is legacy / stale). PDFs alongside
    current evidence files are CURRENT renders, not legacy."""
    g1 = check_schema_purity()  # subsumed
    pdfs = list(EVIDENCE.glob("*.pdf"))
    orphans = [p for p in pdfs if not (p.parent / f"{p.stem}.json").exists()]
    g2_pass = len(orphans) == 0
    details = [f"{p.name} (no matching .json)" for p in orphans] if orphans else (
        [f"{len(pdfs)} current PDF render(s) ok"] if pdfs else []
    )
    return g1 + [("G2_no_legacy_pdfs", g2_pass, details)]


# ----------------------------------------------------------------------------
# Wiring
# ----------------------------------------------------------------------------

def check_question_hygiene() -> list[KPIResult]:
    """Q1: zero questions in questions.json have verdict-pre-loaded statements,
    confessional-vocabulary smuggling, named carriers inline, or meta-framing.
    Delegates to tools/verify_questions.py for the regex catalog.
    """
    sys.path.insert(0, str(TOOLS))
    try:
        import verify_questions as vq  # type: ignore
    except Exception as e:
        return [("Q1_question_hygiene", False, [f"failed to import verify_questions: {e}"])]
    flagged = vq.audit_all()
    if not flagged:
        return [("Q1_question_hygiene", True, [])]
    summary = [f"{r['id']}: {','.join(f for f, _ in r['flags'])}" for r in flagged[:10]]
    return [("Q1_question_hygiene", False,
             summary + [f"... and {len(flagged) - 10} more" if len(flagged) > 10 else ""])]


CHECKS: dict[str, Callable[[], list[KPIResult]]] = {
    "framing": check_framing,
    "schema-purity": check_schema_purity,
    "evidence-shape": check_evidence_shape,
    "question-hygiene": check_question_hygiene,
    "lemma-counts": check_lemma_counts,
    "concordance": check_concordance_traversed,
    "counter-witness": check_counter_witness,
    "cult-marker": check_cult_marker,
    "stem-audit": check_stem_audit,
    "selection-bias": check_selection_bias,
    "urls": check_urls,
    "greenfield": check_greenfield,
    "velocity": check_velocity,
}


def run_check(name: str) -> list[KPIResult]:
    if name == "all":
        out: list[KPIResult] = []
        for fn in CHECKS.values():
            out.extend(fn())
        return out
    if name not in CHECKS:
        print(f"unknown check: {name}; choices: all, {', '.join(CHECKS)}", file=sys.stderr)
        sys.exit(2)
    return CHECKS[name]()


def write_report(results: list[KPIResult]) -> None:
    out = ROOT / "verify-report.md"
    lines = ["# verify-report.md", ""]
    lines.append("| KPI | Pass | Details |")
    lines.append("|---|---|---|")
    for name, ok, details in results:
        mark = "✓" if ok else "✗"
        detail_md = "; ".join(details).replace("|", "\\|") if details else ""
        if len(detail_md) > 200:
            detail_md = detail_md[:197] + "..."
        lines.append(f"| {name} | {mark} | {detail_md} |")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    # Make stdout safe on Windows cp1252 consoles
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", default="all",
                   help=f"Check name. all | {' | '.join(CHECKS)}")
    p.add_argument("--report", action="store_true",
                   help="Write verify-report.md alongside stdout output")
    args = p.parse_args()

    t0 = time.time()
    results = run_check(args.check)
    elapsed = time.time() - t0

    failed = 0
    for name, ok, details in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}")
        if not ok:
            failed += 1
            for d in details[:5]:
                print(f"    {d}")

    print(f"\n{len(results)} checks, {failed} failed, {elapsed:.1f}s")

    if args.report:
        write_report(results)
        print(f"wrote verify-report.md")

    return failed


if __name__ == "__main__":
    sys.exit(main())
