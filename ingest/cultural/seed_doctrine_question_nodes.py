"""Seed :Doctrine and :Question nodes plus UNDER_QUESTION edges in cultural Neo4j.

Reads questions.json (231 question entries) and ingest.doctrine_taxonomy.FINE_SLUGS
(26 doctrine fine slugs). Creates one :Question node per question and one :Doctrine
node per fine slug. For each question, derives doctrine_fine from its category
(slugified) and writes a :Doctrine-[:UNDER_QUESTION]->:Question edge.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ingest.cultural._common import Settings, get_cultural_driver
from ingest.doctrine_taxonomy import FINE_SLUGS, FINE_TO_COARSE


def _slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return s or "unknown"


def _load_questions(questions_path: Path) -> list[dict[str, str]]:
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    raw_list = data["questions"] if isinstance(data, dict) and "questions" in data else data
    if not isinstance(raw_list, list):
        return []
    out: list[dict[str, str]] = []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        qid = entry.get("id") or entry.get("question_id")
        if not qid:
            continue
        out.append(
            {
                "id": str(qid),
                "category": str(entry.get("category", "")),
                "text": str(entry.get("text", "") or entry.get("prompt", "")),
            }
        )
    return out


def seed(questions_path: Path = Path("questions.json")) -> dict[str, int]:
    settings = Settings()  # type: ignore[call-arg]
    questions = _load_questions(questions_path)
    driver = get_cultural_driver(settings)
    counts = {"Doctrine": 0, "Question": 0, "UNDER_QUESTION": 0}
    try:
        with driver.session() as session:
            doctrine_rows = [
                {"slug": slug, "coarse": FINE_TO_COARSE.get(slug, slug), "fine": slug}
                for slug in sorted(FINE_SLUGS)
            ]
            session.run(
                "UNWIND $rows AS row "
                "MERGE (d:Doctrine {slug: row.slug}) "
                "SET d.coarse = row.coarse, d.fine = row.fine",
                rows=doctrine_rows,
            ).consume()
            counts["Doctrine"] = len(doctrine_rows)

            session.run(
                "UNWIND $rows AS row "
                "MERGE (q:Question {id: row.id}) "
                "SET q.category = row.category, q.text = row.text",
                rows=questions,
            ).consume()
            counts["Question"] = len(questions)

            edge_rows = []
            for q in questions:
                slug = _slugify(q["category"])
                if slug not in FINE_SLUGS:
                    fallback = next(
                        (s for s in FINE_SLUGS if s.startswith(slug[:5])),
                        next(iter(FINE_SLUGS)),
                    )
                    slug = fallback
                edge_rows.append({"slug": slug, "qid": q["id"]})
            session.run(
                "UNWIND $rows AS row "
                "MATCH (d:Doctrine {slug: row.slug}), (q:Question {id: row.qid}) "
                "MERGE (d)-[:UNDER_QUESTION]->(q)",
                rows=edge_rows,
            ).consume()
            counts["UNDER_QUESTION"] = len(edge_rows)
    finally:
        driver.close()
    return counts


if __name__ == "__main__":
    import sys

    result = seed()
    print(json.dumps(result, indent=2))
    sys.exit(0)
