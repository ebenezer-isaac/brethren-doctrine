"""Stage 0 intent routing. Cheap regex-driven classifier.

Per docs/TIER_2_SPEC.md §5 Stage 0. Returns weights for hybrid fusion plus a
flag for whether to run graph-side expansion. Graph traversal lands in M4-M6;
this stage just sets the flag the orchestrator reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# OSIS-ish book code patterns. Covers the common short forms in our corpus
# ("Matt 28:18", "1 Cor 11:23", "Rom 6:1-4", "Acts 8") plus full-name forms.
_OSIS_BOOKS = (
    r"Gen|Exod|Exo|Lev|Num|Deut|Josh|Judg|Ruth|"
    r"1\s?Sam|2\s?Sam|1\s?Kings|2\s?Kings|1\s?Chron|2\s?Chron|"
    r"Ezra|Neh|Esth|Job|Ps|Pss|Psalm|Prov|Eccl|Song|"
    r"Isa|Isaiah|Jer|Jeremiah|Lam|Ezek|Ezekiel|Dan|Daniel|"
    r"Hos|Hosea|Joel|Amos|Obad|Jonah|Mic|Micah|Nah|Hab|Zeph|Hag|Zech|Mal|"
    r"Matt|Matthew|Mark|Luke|John|Acts|Rom|Romans|"
    r"1\s?Cor|2\s?Cor|Gal|Eph|Phil|Col|"
    r"1\s?Thess|2\s?Thess|1\s?Tim|2\s?Tim|Titus|Phlm|Philem|"
    r"Heb|Jas|James|1\s?Pet|2\s?Pet|1\s?John|2\s?John|3\s?John|Jude|Rev"
)
SCRIPTURE_RE = re.compile(rf"\b(?:{_OSIS_BOOKS})\.?\s*\d+(?::\d+(?:[-,]\d+)?)?", re.IGNORECASE)

# Theologian / movement names that meaningfully shift retrieval toward exact-name
# matching. Kept narrow on purpose; broader name lists were rejected as noisy
# (false positives like "John" the gospel collide with the apostle name).
NAMED_FIGURE_RE = re.compile(
    r"\b(?:Calvin|Luther|Augustine|Aquinas|Wesley|Spurgeon|Piper|Ryrie|"
    r"Edwards|Owen|Tozer|Chafer|Darby|Mackintosh|Newton|Whitefield)\b",
    re.IGNORECASE,
)
COMPARATIVE_TOKENS = ("vs", "versus", "differ", "differs", "disagree", "disagrees", "compare", "contrast")


@dataclass(frozen=True)
class Routing:
    bm25_w: float
    dense_w: float
    use_graph: bool
    intent: str  # one of: scripture, named_figure, comparative, general


def route(query: str) -> Routing:
    q = query.strip()
    if SCRIPTURE_RE.search(q):
        return Routing(bm25_w=0.7, dense_w=0.3, use_graph=True, intent="scripture")
    if NAMED_FIGURE_RE.search(q):
        return Routing(bm25_w=0.6, dense_w=0.4, use_graph=True, intent="named_figure")
    lower = q.lower()
    if any(re.search(rf"\b{tok}\b", lower) for tok in COMPARATIVE_TOKENS):
        return Routing(bm25_w=0.3, dense_w=0.7, use_graph=True, intent="comparative")
    return Routing(bm25_w=0.5, dense_w=0.5, use_graph=False, intent="general")
