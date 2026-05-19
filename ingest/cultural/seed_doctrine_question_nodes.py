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

# Explicit, exhaustive category -> fine-doctrine-slug map.
#
# Keyed on the slugified `category` field as it actually occurs across every one
# of the 231 questions in questions.json (26 distinct categories: 21 whose slug
# is already an exact FINE_SLUGS member, plus 5 whose slug differs only because
# the source category drops the connective "and"). The prior heuristic resolved
# the 5 via a 5-char `[:5]` prefix scan over FINE_SLUGS and fell back to
# `next(iter(FINE_SLUGS))` on a miss. FINE_SLUGS is a frozenset, whose iteration
# order is NOT stable across Python processes, so both the prefix scan and the
# iter() fallback could resolve the SAME category to DIFFERENT slugs between two
# byte-identical reseeds (e.g. prefix `chris` -> {christology, christian-ethics};
# `worsh` -> {worship-structure, worship-style}), flipping UNDER_QUESTION edge
# targets and breaking the Phase-G idempotency triangle, while the silent
# fallback could mis-attach a future category. This map makes resolution
# deterministic and explicit; an unmapped category RAISES (never arbitrary
# attach). Behaviour for the current 231 is byte-identical to what the G-AUDIT-2
# audit verified, now deterministic and fail-loud.
_CATEGORY_SLUG_TO_FINE: dict[str, str] = {
    # 21 categories whose slug is already an exact FINE_SLUGS member.
    "angelology": "angelology",
    "anthropology": "anthropology",
    "bibliology": "bibliology",
    "christian-ethics": "christian-ethics",
    "christology": "christology",
    "church-discipline": "church-discipline",
    "cult-marker": "cult-marker",
    "demonology": "demonology",
    "ecclesiology": "ecclesiology",
    "engagement-with-world": "engagement-with-world",
    "eschatology": "eschatology",
    "hamartiology": "hamartiology",
    "heterodoxy-marker": "heterodoxy-marker",
    "inter-church-relations": "inter-church-relations",
    "pneumatology": "pneumatology",
    "sacraments": "sacraments",
    "soteriology": "soteriology",
    "spiritual-gifts": "spiritual-gifts",
    "theology-proper": "theology-proper",
    "worship-structure": "worship-structure",
    "worship-style": "worship-style",
    # 5 categories the prior heuristic resolved via the 5-char prefix, now
    # made explicit (source category omits the connective "and").
    "calendar-customs": "calendar-and-customs",
    "family-discipleship": "family-and-discipleship",
    "leadership-polity": "leadership-and-polity",
    "marriage-sexuality": "marriage-and-sexuality",
    "money-stewardship": "money-and-stewardship",
}

# Every mapped target must be a real fine slug; fail at import time otherwise.
assert set(_CATEGORY_SLUG_TO_FINE.values()) <= FINE_SLUGS, (
    "_CATEGORY_SLUG_TO_FINE targets must all be members of FINE_SLUGS"
)


def _slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return s or "unknown"


def _resolve_fine_slug(category: str) -> str:
    """Resolve a question category to its fine doctrine slug, deterministically.

    Looks the slugified category up in the explicit, exhaustive
    `_CATEGORY_SLUG_TO_FINE` map. Raises `KeyError` (fail-loud, never an
    arbitrary attach) when the category is not in the map, so a newly
    introduced category cannot silently mis-attach an UNDER_QUESTION edge to
    an order-dependent doctrine.
    """
    slug = _slugify(category)
    try:
        return _CATEGORY_SLUG_TO_FINE[slug]
    except KeyError:
        known = ", ".join(sorted(_CATEGORY_SLUG_TO_FINE))
        raise KeyError(
            f"Unmapped question category {category!r} (slugified {slug!r}); "
            f"add it to _CATEGORY_SLUG_TO_FINE with its correct fine doctrine "
            f"slug. Known category slugs: {known}"
        ) from None


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
                slug = _resolve_fine_slug(q["category"])
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
