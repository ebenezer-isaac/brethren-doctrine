"""Pipeline 1 lexical ingest CLI.

Dispatches per-dataset adapters in dependency order. Each adapter is
idempotent (MERGE-based) so re-runs are safe.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingest.lexical._common import Settings, assert_counts_match
from ingest.lexical.bhsa import ingest_bhsa
from ingest.lexical.macula_greek import ingest_macula_greek
from ingest.lexical.macula_hebrew import ingest_macula_hebrew
from ingest.lexical.morphgnt import ingest_morphgnt
from ingest.lexical.openbible import ingest_openbible
from ingest.lexical.oshb import ingest_oshb
from ingest.lexical.stepbible import ingest_stepbible
from ingest.lexical.theographic import ingest_theographic
from ingest.lexical.tsk import ingest_tsk

DATA_ROOT = Path("data/private")

DATASETS = [
    "oshb",
    "macula_hebrew",
    "bhsa",
    "morphgnt",
    "macula_greek",
    "stepbible",
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
    if name == "morphgnt":
        return ingest_morphgnt(DATA_ROOT / "morphgnt", settings)
    if name == "macula_greek":
        return ingest_macula_greek(DATA_ROOT / "macula-greek", settings)
    if name == "stepbible":
        return ingest_stepbible(DATA_ROOT / "stepbible", settings)
    if name == "openbible":
        return ingest_openbible(DATA_ROOT / "openbible", settings)
    if name == "tsk":
        return ingest_tsk(DATA_ROOT / "tskxref.txt", settings)
    if name == "theographic":
        return ingest_theographic(DATA_ROOT / "theographic", settings)
    raise ValueError(f"unknown dataset: {name}")


EXPECTED_COUNTS: dict[str, dict[str, tuple[int, int]]] = {
    "macula_hebrew": {"Word": (300000, 320000)},
    "macula_greek": {"Word": (130000, 145000)},
    "morphgnt": {"Word": (130000, 145000)},
    "openbible": {"CrossRef": (340000, 350000)},
    "tsk": {"CrossRef": (380000, 400000)},
    "theographic": {"Person": (3000, 3100), "Place": (1500, 1700)},
}


def _verify(name: str, counts: dict[str, int]) -> bool:
    expected = EXPECTED_COUNTS.get(name)
    if not expected:
        return True
    try:
        assert_counts_match(counts, expected)
        return True
    except AssertionError as e:
        print(f"VERIFY FAIL [{name}]: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="all", help="all | comma-separated list")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="skip ingest; validate counts only via Neo4j queries",
    )
    args = parser.parse_args()

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
        _verify(name, counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
