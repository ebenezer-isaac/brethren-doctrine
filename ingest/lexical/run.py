"""Pipeline 1 lexical ingest CLI.

Dispatches per-dataset adapters in dependency order. Each adapter is
idempotent (MERGE-based) so re-runs are safe.

This CLI does NOT perform count verification. The single authoritative
per-source count gate is ``tools/expected_counts.json`` enforced by the
Phase D.4 count-gate auditor via the acceptance Cyphers in
``docs/implementation_phases/phase_02_lexical_ingest.md``. run.py only
dispatches adapters and prints each adapter's returned JSON counts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingest.lexical._common import Settings
from ingest.lexical.bhsa import ingest_bhsa
from ingest.lexical.coptic_scriptorium import ingest_coptic_scriptorium
from ingest.lexical.etcbc_parallels import ingest_etcbc_parallels
from ingest.lexical.etcbc_phono import ingest_etcbc_phono
from ingest.lexical.macula_greek import ingest_macula_greek
from ingest.lexical.macula_hebrew import ingest_macula_hebrew
from ingest.lexical.morphgnt import ingest_morphgnt
from ingest.lexical.open_cbgm_3_john import ingest_open_cbgm_3_john
from ingest.lexical.openbible import ingest_openbible
from ingest.lexical.oshb import ingest_oshb
from ingest.lexical.peshitta import ingest_peshitta
from ingest.lexical.stepbible_morph_codes import ingest_stepbible_morph_codes
from ingest.lexical.stepbible_proper_nouns import ingest_stepbible_proper_nouns
from ingest.lexical.stepbible_tagnt import ingest_stepbible_tagnt
from ingest.lexical.stepbible_tahot import ingest_stepbible_tahot
from ingest.lexical.stepbible_tbesg import ingest_stepbible_tbesg
from ingest.lexical.stepbible_tbesh import ingest_stepbible_tbesh
from ingest.lexical.stepbible_tflsj import ingest_stepbible_tflsj
from ingest.lexical.stepbible_ttesv import ingest_stepbible_ttesv
from ingest.lexical.stepbible_tvtms import ingest_stepbible_tvtms
from ingest.lexical.theographic import ingest_theographic
from ingest.lexical.tsk import ingest_tsk
from ingest.lexical.vulgate_clementine import ingest_vulgate_clementine

DATA_ROOT = Path("data/private")
STEPBIBLE_ROOT = DATA_ROOT / "stepbible"
STEPBIBLE_TAGGED_BIBLES_ROOT = STEPBIBLE_ROOT / "Tagged-Bibles"
OPEN_CBGM_ROOT = Path("tmp/poc/cbgm")

DATASETS = [
    "oshb",
    "macula_hebrew",
    "bhsa",
    "etcbc_phono",
    "etcbc_parallels",
    "macula_greek",
    "morphgnt",
    "stepbible_morph_codes",
    "stepbible_ttesv",
    "stepbible_tbesh",
    "stepbible_tbesg",
    "stepbible_tahot",
    "stepbible_tagnt",
    "stepbible_tflsj",
    "stepbible_proper_nouns",
    "stepbible_tvtms",
    "peshitta",
    "coptic_scriptorium",
    "vulgate_clementine",
    "open_cbgm_3_john",
    "openbible",
    "tsk",
    "theographic",
]


def _run_one(name: str, settings: Settings) -> dict[str, int]:
    if name == "oshb":
        return ingest_oshb(DATA_ROOT / "oshb", settings)
    if name == "macula_hebrew":
        return ingest_macula_hebrew(DATA_ROOT / "macula-hebrew", settings)
    if name == "bhsa":
        return ingest_bhsa(settings)
    if name == "etcbc_phono":
        return ingest_etcbc_phono(settings)
    if name == "etcbc_parallels":
        return ingest_etcbc_parallels(settings)
    if name == "morphgnt":
        return ingest_morphgnt(DATA_ROOT / "morphgnt", settings)
    if name == "macula_greek":
        return ingest_macula_greek(DATA_ROOT / "macula-greek", settings)
    if name == "stepbible_morph_codes":
        return ingest_stepbible_morph_codes(STEPBIBLE_ROOT, settings)
    if name == "stepbible_tahot":
        return ingest_stepbible_tahot(STEPBIBLE_ROOT, settings)
    if name == "stepbible_tagnt":
        return ingest_stepbible_tagnt(STEPBIBLE_ROOT, settings)
    if name == "stepbible_ttesv":
        return ingest_stepbible_ttesv(STEPBIBLE_TAGGED_BIBLES_ROOT, settings)
    if name == "stepbible_tbesh":
        return ingest_stepbible_tbesh(STEPBIBLE_ROOT, settings)
    if name == "stepbible_tbesg":
        return ingest_stepbible_tbesg(STEPBIBLE_ROOT, settings)
    if name == "stepbible_tflsj":
        return ingest_stepbible_tflsj(STEPBIBLE_ROOT / "Lexicons", settings)
    if name == "stepbible_proper_nouns":
        return ingest_stepbible_proper_nouns(STEPBIBLE_ROOT, settings)
    if name == "stepbible_tvtms":
        return ingest_stepbible_tvtms(STEPBIBLE_ROOT, settings)
    if name == "peshitta":
        return ingest_peshitta(DATA_ROOT / "peshitta", settings)
    if name == "coptic_scriptorium":
        return ingest_coptic_scriptorium(DATA_ROOT / "coptic", settings)
    if name == "vulgate_clementine":
        return ingest_vulgate_clementine(DATA_ROOT / "vulgate", settings)
    if name == "open_cbgm_3_john":
        return ingest_open_cbgm_3_john(OPEN_CBGM_ROOT, settings)
    if name == "openbible":
        return ingest_openbible(DATA_ROOT / "openbible", settings)
    if name == "tsk":
        return ingest_tsk(DATA_ROOT / "tskxref.txt", settings)
    if name == "theographic":
        return ingest_theographic(DATA_ROOT / "theographic", settings)
    raise ValueError(f"unknown dataset: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="all", help="all | comma-separated list")
    parser.add_argument(
        "--list",
        action="store_true",
        help="print every wired dataset name and exit without ingesting",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="skip ingest; validate counts only via Neo4j queries",
    )
    args = parser.parse_args()

    if args.list:
        for name in DATASETS:
            print(name)
        return 0

    if args.dataset == "all":
        chosen = DATASETS
    else:
        chosen = [s.strip() for s in args.dataset.split(",") if s.strip()]

    settings = Settings()  # type: ignore[call-arg]

    if args.verify_only:
        from neo4j import GraphDatabase, Session

        def _count(session: Session, cypher: str) -> int:
            rec = session.run(cypher).single()
            return int(rec["n"]) if rec is not None else 0

        driver = GraphDatabase.driver(
            settings.neo4j_lexical_uri,
            auth=(settings.neo4j_lexical_user, settings.neo4j_lexical_password),
        )
        try:
            with driver.session() as session:
                counts = {
                    "macula_hebrew_words": _count(
                        session, "MATCH (w:Word {source:'macula-hebrew'}) RETURN count(w) AS n"
                    ),
                    "macula_greek_sblgnt_words": _count(
                        session,
                        "MATCH (w:Word {source:'macula-greek-sblgnt'}) RETURN count(w) AS n",
                    ),
                    "morphgnt_words": _count(
                        session, "MATCH (w:Word {source:'morphgnt-sblgnt'}) RETURN count(w) AS n"
                    ),
                    "lemmas": _count(session, "MATCH (l:Lemma) RETURN count(l) AS n"),
                    "verses": _count(session, "MATCH (v:Verse) RETURN count(v) AS n"),
                    "openbible_crossrefs": _count(
                        session,
                        "MATCH ()-[r:CROSS_REF {source:'openbible'}]->() RETURN count(r) AS n",
                    ),
                    "tsk_crossrefs": _count(
                        session, "MATCH ()-[r:CROSS_REF {source:'tsk'}]->() RETURN count(r) AS n"
                    ),
                    "people": _count(session, "MATCH (p:Person) RETURN count(p) AS n"),
                    "places": _count(session, "MATCH (p:Place) RETURN count(p) AS n"),
                }
            print(json.dumps(counts, indent=2))
        finally:
            driver.close()
        return 0

    all_counts: dict[str, dict[str, int]] = {}
    for name in chosen:
        print(f"=== {name} ===")
        counts = _run_one(name, settings)
        all_counts[name] = counts
        print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
