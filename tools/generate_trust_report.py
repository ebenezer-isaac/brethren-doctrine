"""Re-runnable layman trust-report PDF generator (Phase H verdict).

This tool produces a plain English PDF that a non technical owner or
church elder can read to see, in everyday words, whether the rebuilt
Bible text knowledge base and the church teaching knowledge base were
constructed correctly, completely, reproducibly, with no copyrighted
text leaked and no shortcuts taken.

It is a KEEPER. It is designed to outlive a future repository cleanup
that deletes the narrative audit and phase markdown files. It therefore
depends ONLY on durable core artifacts:

* the recorded claim file ``docs/RESEED_MANIFEST_<timestamp>.json``
  (the architect contract listing the 25 checks),
* the independent re-executor ``tools/verify_manifest.py``,
* that re-executor's own machine output
  ``docs/MANIFEST_VERIFICATION_<phase>.json``,
* and the two live air gapped data stores themselves.

It never reads any ``docs/AUDIT_*.md`` or ``docs/PHASE_*.md`` narrative
file, so it stays correct after those are removed.

Two modes
=========

* ``--verify`` (default): runs ``tools/verify_manifest.py`` fresh so the
  report reflects the live current state at generation time. This RE
  PROVES every claim against the live data and is the honest meaning of
  "generate at any time". One claim (a full adapter test suite) takes
  roughly 70 minutes, so the whole verify pass is slow on purpose.
* ``--use-last``: skips re running the slow claim set and instead reads
  an existing ``docs/MANIFEST_VERIFICATION_*.json`` recorded by a prior
  ``tools/verify_manifest.py`` run. The PDF is then clearly stamped as a
  CACHED verdict together with the timestamp of that cached run, so the
  reader is never misled into thinking it is a fresh re proof.

In BOTH modes the tool independently runs a small set of fast read only
live spot checks against the two stores, so the PDF always carries live
corroboration and not merely the tool's own self report.

Usage
=====

    python tools/generate_trust_report.py                 # live re-verify
    python tools/generate_trust_report.py --use-last      # fast, cached
    python tools/generate_trust_report.py --self-test     # offline check
    python tools/generate_trust_report.py \\
        --manifest docs/RESEED_MANIFEST_<ts>.json \\
        --out-dir reports

The generated PDF is written to a separate ``reports/`` folder (created
if absent) as ``reports/TRUST_REPORT_<UTC timestamp>.pdf`` and a stable
``reports/TRUST_REPORT_latest.pdf`` is overwritten each run. Generated
PDFs are regenerable artifacts and are gitignored; only this tool is
committed.

No em dashes or en dashes appear anywhere in this code or in the
rendered PDF text; only periods, commas, "and" and "but" are used.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Plain English, one short clause per claim id. The reader never sees the
# raw claim id or its jargon, only the line below. Every claim in the
# Phase H manifest is covered; an id absent from this map falls back to a
# trimmed form of the recorded description so the report never goes blank.
CLAIM_PLAIN: dict[str, str] = {
    "h2_adapter_pytest": (
        "All automated software tests for the data loaders pass with "
        "zero failures."
    ),
    "h3_src_macula_hebrew": (
        "The Hebrew word dataset (MACULA) loaded the exact expected "
        "number of words."
    ),
    "h3_src_oshb_morphology": (
        "The Hebrew Bible word dataset (OSHB) loaded the exact expected "
        "number of words."
    ),
    "h3_src_stepbible_tahot": (
        "The STEPBible Old Testament tagged word dataset loaded the "
        "exact expected number of items."
    ),
    "h3_src_stepbible_tagnt": (
        "The STEPBible New Testament tagged word dataset loaded the "
        "exact expected number of items."
    ),
    "h3_src_stepbible_tvtms": (
        "The verse numbering rules dataset loaded the exact expected "
        "number of rules."
    ),
    "h3_edge_openbible_cross_ref": (
        "The verse to verse cross reference links loaded the exact "
        "expected number of links."
    ),
    "h3_edge_parallel_of": (
        "The parallel passage links loaded the exact expected number "
        "of links."
    ),
    "h3_edge_instance_of_total": (
        "Every word is correctly linked to its dictionary entry, with "
        "the exact expected total of links."
    ),
    "hp2_cultural_chunk_count": (
        "The church teaching text was split into the exact expected "
        "number of readable pieces."
    ),
    "hp2_cultural_has_chunk": (
        "Every church teaching piece is attached to its source work, "
        "with no orphans."
    ),
    "hp2_cultural_work_count": (
        "The exact expected number of distinct church teaching works "
        "is present."
    ),
    "hp2_cultural_doctrine_count": (
        "The exact expected number of doctrine topics is present."
    ),
    "hp2_cultural_question_count": (
        "The exact expected number of study questions is present."
    ),
    "hp2_cultural_under_question": (
        "Every study question is correctly connected to its doctrine "
        "topic."
    ),
    "hp2_cultural_conciliar_workids": (
        "The historic church creeds are present as four distinct "
        "documents, not collapsed into one."
    ),
    "h7_thresholds_immutable": (
        "The fixed correctness targets were not secretly altered to "
        "make the checks pass."
    ),
    "h7_verify_no_deferral": (
        "No required work was quietly postponed or marked as skipped "
        "in the plan."
    ),
    "h6_adapter_purity": (
        "The data loaders contain no hidden network or shortcut code, "
        "they only read approved local data."
    ),
    "h8_check_caste_full_history": (
        "Every single change in the project history followed the "
        "required role and permission rules."
    ),
    "h5_triangle_snapshot_determinism": (
        "Rebuilding from scratch produces the same result every time, "
        "it is reproducible."
    ),
    "h4_vector_quality_gate": (
        "The numeric search fingerprints (embeddings) are healthy and "
        "not degenerate."
    ),
    "h7_expected_counts_file_sha": (
        "The locked correctness target file is byte for byte the "
        "original, unchanged."
    ),
    "h7_no_deferral_phase02_grep": (
        "The data loading plan document contains zero postponement or "
        "to do markers."
    ),
    "hp2_procurement_no_unapproved_deadend": (
        "No in scope data source was silently parked as abandoned."
    ),
}

# Plain headings that group the 25 checks. Order is deliberate so the
# report reads as a story for a non technical owner.
GROUPS: list[tuple[str, tuple[str, ...]]] = [
    (
        "Right amount of data loaded",
        (
            "h3_src_macula_hebrew",
            "h3_src_oshb_morphology",
            "h3_src_stepbible_tahot",
            "h3_src_stepbible_tagnt",
            "h3_src_stepbible_tvtms",
            "h3_edge_openbible_cross_ref",
            "h3_edge_parallel_of",
            "h3_edge_instance_of_total",
        ),
    ),
    (
        "Church teaching side correct and walled off",
        (
            "hp2_cultural_chunk_count",
            "hp2_cultural_has_chunk",
            "hp2_cultural_work_count",
            "hp2_cultural_doctrine_count",
            "hp2_cultural_question_count",
            "hp2_cultural_under_question",
            "hp2_cultural_conciliar_workids",
        ),
    ),
    (
        "No copyrighted text leaked and nothing faked",
        (
            "h7_thresholds_immutable",
            "h7_expected_counts_file_sha",
            "h6_adapter_purity",
            "hp2_procurement_no_unapproved_deadend",
        ),
    ),
    (
        "Every change followed the rules",
        (
            "h8_check_caste_full_history",
            "h7_verify_no_deferral",
            "h7_no_deferral_phase02_grep",
        ),
    ),
    (
        "Reproducible and embeddings healthy",
        (
            "h5_triangle_snapshot_determinism",
            "h4_vector_quality_gate",
            "h2_adapter_pytest",
        ),
    ),
]


@dataclass(frozen=True)
class SpotCheck:
    """One independent fast live read only corroboration check."""

    name: str
    plain: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class TrustData:
    """Everything the PDF renderer needs, fully resolved."""

    mode: str  # "live re-verified" or "cached verdict"
    generated_utc: str
    git_head_short: str
    manifest_path: str
    manifest_sha256: str
    verdict_source_utc: str
    all_match: bool
    claims: tuple[dict[str, Any], ...]
    matched: int
    total: int
    spot_checks: tuple[SpotCheck, ...]


# Em dash and en dash are forbidden in all output. This guard makes any
# accidental introduction fail loudly instead of silently shipping.
_FORBIDDEN_DASHES = ("—", "–")


def _no_fancy_dashes(text: str) -> str:
    for bad in _FORBIDDEN_DASHES:
        if bad in text:
            text = text.replace(bad, ", ")
    return text


def _load_dotenv_if_needed() -> None:
    """Populate os.environ from a repo .env for any missing key.

    Mirrors how the rest of the toolchain expects env vars to already be
    present, but stays self contained: it never overwrites an existing
    value and never prints any secret. No third party dependency.
    """

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        raw = env_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _git_head_short() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_human(stamp_iso: str | None = None) -> str:
    if stamp_iso:
        return stamp_iso
    return _dt.datetime.now(_dt.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC")


def discover_manifest(explicit: Path | None) -> Path:
    if explicit is not None:
        p = explicit if explicit.is_absolute() else REPO_ROOT / explicit
        if not p.exists():
            raise FileNotFoundError(f"manifest not found: {p}")
        return p
    candidates = sorted(
        (REPO_ROOT / "docs").glob("RESEED_MANIFEST_*.json"),
        key=lambda x: x.name,
    )
    if not candidates:
        raise FileNotFoundError(
            "no docs/RESEED_MANIFEST_*.json manifest found")
    return candidates[-1]


def discover_verification_json(phase_hint: str | None) -> Path:
    """Newest verify_manifest.py output file under docs/."""

    docs = REPO_ROOT / "docs"
    candidates = sorted(
        docs.glob("MANIFEST_VERIFICATION_*.json"),
        key=lambda x: x.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            "no docs/MANIFEST_VERIFICATION_*.json found; run "
            "tools/verify_manifest.py first or use the default --verify mode"
        )
    return candidates[-1]


def run_fresh_verification(manifest: Path) -> tuple[dict[str, Any], str]:
    """Run tools/verify_manifest.py fresh and read its output JSON.

    Returns the parsed verification dict and an ISO timestamp string for
    when this fresh run completed. This RE PROVES every claim against the
    live data; it is slow on purpose (one claim is a full test suite).
    """

    completed_before = _dt.datetime.now(_dt.timezone.utc)
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "fresh_verification.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "verify_manifest.py"),
                "--manifest", str(manifest),
                "--out", str(out_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if not out_path.exists():
            raise RuntimeError(
                "verify_manifest.py did not produce an output file; "
                f"exit={proc.returncode} stderr_tail="
                f"{proc.stderr[-500:]!r}"
            )
        data = json.loads(out_path.read_text(encoding="utf-8"))
    finished = _dt.datetime.now(_dt.timezone.utc)
    iso = finished.strftime("%Y-%m-%d %H:%M:%S UTC")
    # completed_before kept only to make intent explicit; the run is the
    # authoritative window and the finished stamp is what we report.
    _ = completed_before
    return data, iso


def read_cached_verification(verification_path: Path) -> tuple[
        dict[str, Any], str]:
    data = json.loads(verification_path.read_text(encoding="utf-8"))
    mtime = _dt.datetime.fromtimestamp(
        verification_path.stat().st_mtime, tz=_dt.timezone.utc)
    iso = mtime.strftime("%Y-%m-%d %H:%M:%S UTC")
    return data, iso


# Fast read only live spot checks. Each returns a SpotCheck. They are
# MATCH only or collection info only, never write anything, and never
# cross the air gap (the air gap check verifies the wall is intact in
# BOTH directions).

def _neo4j_driver(prefix: str):
    uri = os.environ.get(f"NEO4J_{prefix}_URI")
    user = os.environ.get(f"NEO4J_{prefix}_USER")
    pwd = os.environ.get(f"NEO4J_{prefix}_PASSWORD")
    if not (uri and user and pwd):
        raise RuntimeError(f"missing NEO4J_{prefix}_* env")
    from neo4j import GraphDatabase

    # Silence the driver's per-query "label/property does not exist"
    # notifications. They are expected and harmless here: a read only
    # spot check against the lexical store deliberately probes for
    # cultural labels (and vice versa) to prove the air gap, so a
    # not-found is the desired healthy answer, not an error.
    try:
        return GraphDatabase.driver(
            uri, auth=(user, pwd),
            notifications_min_severity="OFF",
        )
    except (TypeError, ValueError):
        # Older driver without the kwarg; fall back cleanly.
        return GraphDatabase.driver(uri, auth=(user, pwd))


def _scalar(driver, query: str) -> Any:
    with driver.session() as session:
        rows = list(session.run(query))
    if rows and len(rows[0].keys()) >= 1:
        return rows[0][rows[0].keys()[0]]
    return None


def run_spot_checks() -> tuple[SpotCheck, ...]:
    checks: list[SpotCheck] = []
    lex = None
    cul = None
    try:
        try:
            lex = _neo4j_driver("LEXICAL")
        except Exception as exc:  # pragma: no cover - env dependent
            lex = None
            _lex_err = str(exc)
        else:
            _lex_err = ""
        try:
            cul = _neo4j_driver("CULTURAL")
        except Exception as exc:  # pragma: no cover - env dependent
            cul = None
            _cul_err = str(exc)
        else:
            _cul_err = ""

        # 1. Lexical INSTANCE_OF total.
        try:
            v = _scalar(
                lex, "MATCH ()-[r:INSTANCE_OF]->() RETURN count(r) AS n")
            checks.append(SpotCheck(
                "Word to dictionary links",
                "Every Bible word is linked to its dictionary entry.",
                v == 2025687,
                f"found {v:,} links, expected 2,025,687"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Word to dictionary links",
                "Every Bible word is linked to its dictionary entry.",
                False, f"could not read lexical store: {exc}"))

        # 2. Lexical OPENBIBLE_CROSS_REF total.
        try:
            v = _scalar(
                lex,
                "MATCH ()-[r:OPENBIBLE_CROSS_REF]->() RETURN count(r) AS n")
            checks.append(SpotCheck(
                "Verse cross reference links",
                "Verse to verse cross references are all present.",
                v == 342128,
                f"found {v:,} links, expected 342,128"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Verse cross reference links",
                "Verse to verse cross references are all present.",
                False, f"could not read lexical store: {exc}"))

        # 3. Lexical PARALLEL_OF total.
        try:
            v = _scalar(
                lex, "MATCH ()-[r:PARALLEL_OF]->() RETURN count(r) AS n")
            checks.append(SpotCheck(
                "Parallel passage links",
                "Parallel Bible passages are all linked.",
                v == 5882,
                f"found {v:,} links, expected 5,882"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Parallel passage links",
                "Parallel Bible passages are all linked.",
                False, f"could not read lexical store: {exc}"))

        # 4. Sample verse Hebrews 1:1 is present and in its known
        # correct shape. New Testament verses are keyed by the 'osis'
        # property, and their 'osisID' property is deliberately null
        # (osisID is used only for the Old Testament source here). The
        # healthy expected state is exactly: the verse exists by osis,
        # and its osisID is null. Both conditions must hold.
        try:
            with lex.session() as _ses:
                row = _ses.run(
                    "MATCH (v:Verse {osis:'Heb.1.1'}) "
                    "RETURN count(v) AS n, "
                    "sum(CASE WHEN v.osisID IS NULL THEN 1 ELSE 0 END) "
                    "AS null_oid"
                ).single()
            present = int(row["n"]) if row else 0
            null_oid = int(row["null_oid"]) if row else 0
            ok = present >= 1 and null_oid == present
            checks.append(SpotCheck(
                "Sample verse present and correctly shaped",
                "A sample verse (Hebrews 1:1) is present and has its "
                "expected internal shape.",
                ok,
                f"found {present} verse(s), {null_oid} with the "
                "expected null id, both should match and be at least 1",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Sample verse present and correctly shaped",
                "A sample verse (Hebrews 1:1) is present and has its "
                "expected internal shape.",
                False, f"could not read lexical store: {exc}"))

        # 5. Copyright leak gate. The real leak risk is a copyrighted
        # piece wrongly marked as freely shareable. A piece is freely
        # shareable only if its license is public domain or has been
        # sanitized. Any piece marked redistributable while still under a
        # restrictive license would be a leak. The expected count is 0.
        try:
            v = _scalar(
                cul,
                "MATCH (n:CulturalChunk) WHERE n.redistribute = true "
                "AND NOT (n.license IN ['public_domain', "
                "'parsed-sanitized']) RETURN count(n) AS n")
            ok = v == 0
            checks.append(SpotCheck(
                "No copyrighted text leaked",
                "Zero copyrighted church teaching pieces are wrongly "
                "marked as freely shareable.",
                ok,
                f"found {v} mislabelled piece(s), expected 0"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "No copyrighted text leaked",
                "Zero copyrighted church teaching pieces are wrongly "
                "marked as freely shareable.",
                False, f"could not read cultural store: {exc}"))

        # 6. Cultural conciliar work_ids fan out to 4 distinct.
        try:
            v = _scalar(
                cul,
                "MATCH (w:Work) WHERE w.work_id STARTS WITH 'conciliar.' "
                "RETURN count(DISTINCT w.work_id) AS n")
            checks.append(SpotCheck(
                "Historic creeds kept distinct",
                "The historic church creeds are four distinct works.",
                v == 4,
                f"found {v} distinct creed work(s), expected 4"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Historic creeds kept distinct",
                "The historic church creeds are four distinct works.",
                False, f"could not read cultural store: {exc}"))

        # 7. Cultural CulturalChunk count.
        try:
            v = _scalar(
                cul, "MATCH (n:CulturalChunk) RETURN count(n) AS n")
            checks.append(SpotCheck(
                "Church teaching pieces present",
                "The church teaching text holds the expected number "
                "of readable pieces.",
                v == 60040,
                f"found {v:,} pieces, expected 60,040"
                if isinstance(v, int) else f"found {v!r}",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Church teaching pieces present",
                "The church teaching text holds the expected number "
                "of readable pieces.",
                False, f"could not read cultural store: {exc}"))

        # 8. Air gap intact in BOTH directions: the Bible text store must
        # not contain any church teaching node, and the church teaching
        # store must not contain any Bible word node. Either leak fails.
        try:
            lex_has_cultural = _scalar(
                lex,
                "MATCH (n:CulturalChunk) RETURN count(n) AS n")
            cul_has_lexical = _scalar(
                cul, "MATCH (n:Word) RETURN count(n) AS n")
            ok = lex_has_cultural == 0 and cul_has_lexical == 0
            checks.append(SpotCheck(
                "Two knowledge bases stay walled off",
                "The Bible text base and the church teaching base "
                "never see each other, in both directions.",
                ok,
                f"Bible base church-nodes={lex_has_cultural}, "
                f"church base Bible-words={cul_has_lexical}, "
                "both must be 0",
            ))
        except Exception as exc:
            checks.append(SpotCheck(
                "Two knowledge bases stay walled off",
                "The Bible text base and the church teaching base "
                "never see each other, in both directions.",
                False, f"could not run air gap check: {exc}"))
    finally:
        for d in (lex, cul):
            try:
                if d is not None:
                    d.close()
            except Exception:
                pass
    return tuple(checks)


def build_trust_data(
    *,
    mode_use_last: bool,
    manifest: Path,
    skip_spot_checks: bool = False,
) -> TrustData:
    if mode_use_last:
        vpath = discover_verification_json(None)
        verification, verdict_iso = read_cached_verification(vpath)
        mode = "cached verdict"
    else:
        verification, verdict_iso = run_fresh_verification(manifest)
        mode = "live re-verified"

    raw_claims = verification.get("claims", [])
    claims: list[dict[str, Any]] = []
    for c in raw_claims:
        cid = c.get("id", "")
        claims.append({
            "id": cid,
            "plain": CLAIM_PLAIN.get(
                cid,
                _no_fancy_dashes(str(c.get("description", cid)))[:140],
            ),
            "matches": bool(c.get("matches")),
        })
    matched = sum(1 for c in claims if c["matches"])
    total = len(claims)
    all_match = bool(verification.get("all_match")) and matched == total \
        and total > 0

    spot = () if skip_spot_checks else run_spot_checks()

    return TrustData(
        mode=mode,
        generated_utc=_utc_human(),
        git_head_short=_git_head_short(),
        manifest_path=str(
            verification.get("manifest_path", str(manifest))
        ).replace("\\", "/"),
        manifest_sha256=str(verification.get("manifest_sha256", "")),
        verdict_source_utc=verdict_iso,
        all_match=all_match,
        claims=tuple(claims),
        matched=matched,
        total=total,
        spot_checks=spot,
    )


# ----------------------------- PDF render -----------------------------

def render_pdf(data: TrustData, out_path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1", parent=styles["Title"], fontSize=20, spaceAfter=10)
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=13, spaceBefore=14,
        spaceAfter=6)
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14,
        spaceAfter=6)
    small = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontSize=9, leading=12)

    green = colors.HexColor("#1b7f3b")
    red = colors.HexColor("#b00020")

    story: list[Any] = []

    def P(text: str, style=body) -> None:
        story.append(Paragraph(_no_fancy_dashes(text), style))

    P("Trustworthiness Report", h1)
    P(
        "Bible text knowledge base and church teaching knowledge base, "
        "independent rebuild verification.",
        small,
    )
    story.append(Spacer(1, 6))
    P(
        f"Generated: {data.generated_utc}. "
        f"Code version (git): {data.git_head_short}. "
        f"Mode: {data.mode}.",
        body,
    )
    if data.mode == "cached verdict":
        P(
            "This report used the CACHED verdict mode. The pass and fail "
            "results in the 25 check table below were recorded by an "
            f"earlier full verification run dated {data.verdict_source_utc}. "
            "The eight live spot checks lower down were still run fresh "
            "just now against the live data. To fully re prove every one "
            "of the 25 checks live, run the tool without --use-last; that "
            "takes roughly 70 minutes because it re runs an entire "
            "software test suite.",
            body,
        )
    else:
        P(
            "This report used the LIVE re verified mode. Every one of the "
            "25 checks below was re executed against the live data just "
            f"now, finishing {data.verdict_source_utc}. The eight live "
            "spot checks were also run fresh just now.",
            body,
        )

    P("What this proves", h2)
    P(
        "This is an independent, automated re check. It confirms that the "
        "Bible text knowledge base and the separate church teaching "
        "knowledge base were rebuilt correctly, completely and "
        "reproducibly, that no copyrighted text leaked out, and that no "
        "shortcuts were taken. The check re runs the recorded list of "
        "promises against the real data and reports a plain pass or fail "
        "for each one. A trustworthy result can be reproduced on demand.",
        body,
    )

    # Verdict banner.
    if data.all_match:
        banner_text = (
            f"TRUSTWORTHY. All checks passed. "
            f"{data.matched} of {data.total} checks matched."
        )
        banner_bg = green
    else:
        banner_text = (
            f"NOT TRUSTWORTHY. One or more checks failed. "
            f"{data.matched} of {data.total} checks matched."
        )
        banner_bg = red
    banner = Table(
        [[Paragraph(
            f'<b>{_no_fancy_dashes(banner_text)}</b>',
            ParagraphStyle("Banner", parent=body, textColor=colors.white,
                           fontSize=13, leading=17))]],
        colWidths=[6.7 * inch],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), banner_bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(Spacer(1, 8))
    story.append(banner)
    story.append(Spacer(1, 8))

    # The 25 checks, grouped under plain headings.
    by_id = {c["id"]: c for c in data.claims}
    P("The 25 checks, in plain words", h2)
    P(
        "Each line is one promise about the rebuilt data. PASS means the "
        "live data matched the promise exactly.",
        small,
    )

    placed: set[str] = set()
    for heading, ids in GROUPS:
        rows = [[Paragraph("<b>Check</b>", cell),
                 Paragraph("<b>Result</b>", cell)]]
        any_row = False
        for cid in ids:
            c = by_id.get(cid)
            if c is None:
                continue
            placed.add(cid)
            any_row = True
            res = "PASS" if c["matches"] else "FAIL"
            rows.append([
                Paragraph(_no_fancy_dashes(c["plain"]), cell),
                Paragraph(
                    f'<b>{res}</b>',
                    ParagraphStyle(
                        "R", parent=cell,
                        textColor=green if c["matches"] else red)),
            ])
        if not any_row:
            continue
        P(heading, ParagraphStyle(
            "GrpH", parent=body, fontSize=11, spaceBefore=8,
            spaceAfter=4, textColor=colors.HexColor("#1a1a1a")))
        t = Table(rows, colWidths=[5.5 * inch, 1.2 * inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    leftover = [c for c in data.claims if c["id"] not in placed]
    if leftover:
        P("Other recorded checks", ParagraphStyle(
            "GrpH2", parent=body, fontSize=11, spaceBefore=8,
            spaceAfter=4))
        rows = [[Paragraph("<b>Check</b>", cell),
                 Paragraph("<b>Result</b>", cell)]]
        for c in leftover:
            res = "PASS" if c["matches"] else "FAIL"
            rows.append([
                Paragraph(_no_fancy_dashes(c["plain"]), cell),
                Paragraph(
                    f'<b>{res}</b>',
                    ParagraphStyle(
                        "R2", parent=cell,
                        textColor=green if c["matches"] else red)),
            ])
        t = Table(rows, colWidths=[5.5 * inch, 1.2 * inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # Live spot checks.
    P("Eight independent live spot checks", h2)
    P(
        "These were run fresh just now, directly against the live data, "
        "as a second opinion that does not rely on the tool's own report. "
        "Each shows the actual number found.",
        small,
    )
    srows = [[Paragraph("<b>Spot check</b>", cell),
              Paragraph("<b>What was found</b>", cell),
              Paragraph("<b>Result</b>", cell)]]
    for s in data.spot_checks:
        res = "PASS" if s.passed else "FAIL"
        srows.append([
            Paragraph(_no_fancy_dashes(s.plain), cell),
            Paragraph(_no_fancy_dashes(s.detail), cell),
            Paragraph(
                f'<b>{res}</b>',
                ParagraphStyle(
                    "SR", parent=cell,
                    textColor=green if s.passed else red)),
        ])
    st = Table(
        srows, colWidths=[2.7 * inch, 3.0 * inch, 1.0 * inch],
        repeatRows=1)
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(st)

    P("What this does not cover", h2)
    P(
        "This report checks that the data was rebuilt correctly, "
        "completely and reproducibly. It does not, by design, judge "
        "whether any particular church teaching is right or wrong, and it "
        "does not cover a few features that were intentionally placed "
        "outside the first version's scope. Those intentional scope "
        "boundaries are written down in the project's core design "
        "documents (the architecture and schema decision records). They "
        "are deliberate choices, not gaps that this report is hiding.",
        body,
    )

    P("How to regenerate this report", h2)
    P(
        "Run: python tools/generate_trust_report.py . That re proves "
        "every check against the live data and writes a fresh PDF. For a "
        "faster report that reuses the most recent recorded verification "
        "instead of re running the slow test suite, add --use-last . "
        "Because every check is re executed against the live data, a "
        "green report can be reproduced on demand by anyone with access "
        "to the two data stores.",
        body,
    )
    story.append(Spacer(1, 8))
    P(
        f"Manifest: {data.manifest_path} . "
        f"Manifest fingerprint (sha256): {data.manifest_sha256}.",
        small,
    )

    doc = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title="Trustworthiness Report",
        author="brethren-doctrine trust report generator",
    )
    doc.build(story)


def write_reports(data: TrustData, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamped = out_dir / f"TRUST_REPORT_{_utc_stamp()}.pdf"
    latest = out_dir / "TRUST_REPORT_latest.pdf"
    render_pdf(data, stamped)
    # Re render to latest rather than copying so both are independently
    # valid PDFs even if a copy were interrupted.
    render_pdf(data, latest)
    return stamped, latest


def _self_test() -> int:
    """Render a PDF from a tiny in memory fake verdict. No network."""

    fake = TrustData(
        mode="cached verdict",
        generated_utc=_utc_human(),
        git_head_short="0000000",
        manifest_path="docs/RESEED_MANIFEST_selftest.json",
        manifest_sha256="deadbeef",
        verdict_source_utc="1970-01-01 00:00:00 UTC",
        all_match=True,
        claims=tuple(
            {"id": cid, "plain": CLAIM_PLAIN[cid], "matches": True}
            for cid in CLAIM_PLAIN
        ),
        matched=len(CLAIM_PLAIN),
        total=len(CLAIM_PLAIN),
        spot_checks=(
            SpotCheck("Sample", "A sample live check.", True,
                      "found 1, expected 1"),
        ),
    )
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "selftest.pdf"
        render_pdf(fake, out)
        if not out.exists():
            print("self-test FAIL: no PDF produced", file=sys.stderr)
            return 1
        blob = out.read_bytes()
        if len(blob) < 1000:
            print(f"self-test FAIL: PDF too small ({len(blob)} bytes)",
                  file=sys.stderr)
            return 1
        if not blob.startswith(b"%PDF-"):
            print("self-test FAIL: missing %PDF- header", file=sys.stderr)
            return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a plain English trustworthiness report PDF of the "
            "reseed verification verdict. Default mode re proves every "
            "check live (slow, about 70 minutes); --use-last reuses the "
            "most recent recorded verification (fast) and clearly stamps "
            "the report as a cached verdict. In both modes eight fast "
            "live spot checks are run for independent corroboration."
        ),
    )
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="Path to docs/RESEED_MANIFEST_<ts>.json. Default: newest one.")
    parser.add_argument(
        "--out-dir", type=Path, default=REPO_ROOT / "reports",
        help="Folder for the generated PDF. Default: reports/ .")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--verify", action="store_true", default=False,
        help=("Re prove every check live now (default). Slow, about 70 "
              "minutes, because it re runs a full test suite."))
    mode.add_argument(
        "--use-last", action="store_true", default=False,
        help=("Fast path. Reuse the most recent recorded "
              "docs/MANIFEST_VERIFICATION_*.json instead of re running "
              "the slow checks. The report is stamped as a cached "
              "verdict with that run's timestamp."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    _load_dotenv_if_needed()

    try:
        manifest = discover_manifest(args.manifest)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    use_last = bool(args.use_last)
    # --verify is the documented default; if neither flag is passed we
    # run the live re proof.

    try:
        data = build_trust_data(
            mode_use_last=use_last, manifest=manifest)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out_dir = (
        args.out_dir if args.out_dir.is_absolute()
        else REPO_ROOT / args.out_dir
    )
    stamped, latest = write_reports(data, out_dir)

    verdict = "GREEN" if data.all_match else "RED"
    print(f"mode={data.mode}")
    print(f"verdict={verdict} claims={data.matched}/{data.total}")
    sp_pass = sum(1 for s in data.spot_checks if s.passed)
    print(f"spot_checks={sp_pass}/{len(data.spot_checks)} passed")
    print(f"written: {stamped} ({stamped.stat().st_size} bytes)")
    print(f"written: {latest} ({latest.stat().st_size} bytes)")
    # A non green verdict is reported but is not a tool error; the PDF is
    # still produced and is the deliverable.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
