"""Intent classifier for natural-language queries.

Rule-based. No LLM. Decides which store(s) to query, whether to graph-expand,
and whether to invoke the reranker. Tools that already know their target
(evidence_inspect, license_audit) bypass this layer.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Intent = Literal[
    "scripture_lookup",
    "doctrinal_verdict",
    "cultural_overlay",
    "comparative",
    "variant_inspect",
    "versification",
    "general",
]

Store = Literal["lexical", "cultural"]

_VERSE_REF_REGEX = re.compile(r"\b[1-3]?\s?[A-Z][a-z]+\s+\d+:\d+\b")
_STRONG_REGEX = re.compile(r"\b[HG]\d{3,5}\b")
_DOCTRINE_OF_REGEX = re.compile(r"\bdoctrine of\b", re.IGNORECASE)
_WHAT_DOES_TEACH_REGEX = re.compile(
    r"\bwhat does (the )?(\w+|reformed|catholic|lutheran|orthodox|anglican|methodist|anabaptist|"
    r"pentecostal|brethren) (church |tradition )?teach\b",
    re.IGNORECASE,
)
_DENOMINATION_NAMES = re.compile(
    r"\b(reformed|catholic|lutheran|orthodox|anglican|methodist|anabaptist|pentecostal|"
    r"brethren|wesleyan|baptist|presbyterian)\b",
    re.IGNORECASE,
)
_COMPARATIVE_REGEX = re.compile(
    r"\b(compare|vs\.?|versus|difference between|how does \w+ differ)\b",
    re.IGNORECASE,
)
_VARIANT_REGEX = re.compile(
    r"\b(variant|original reading|manuscript|codex|sinaiticus|vaticanus|byzantine|alexandrian|"
    r"textus receptus|apparatus|comma johanneum)\b",
    re.IGNORECASE,
)
_VERSIFICATION_REGEX = re.compile(
    r"\b(versification|hebrew vs english|english vs hebrew|verse numbering|chapter division|"
    r"psalm \d+:\d+ hebrew)\b",
    re.IGNORECASE,
)


class RoutingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Intent
    primary_store: Store
    also_query: list[Store] = Field(default_factory=list)
    expand_graph: bool = False
    use_reranker: bool = True
    k: int = 10


def classify_intent(query: str) -> RoutingDecision:
    if not isinstance(query, str) or not query.strip():
        return RoutingDecision(intent="general", primary_store="lexical", also_query=["cultural"])

    if _VARIANT_REGEX.search(query):
        return RoutingDecision(intent="variant_inspect", primary_store="lexical")
    if _VERSIFICATION_REGEX.search(query):
        return RoutingDecision(intent="versification", primary_store="lexical")
    if _COMPARATIVE_REGEX.search(query):
        return RoutingDecision(
            intent="comparative",
            primary_store="lexical",
            also_query=["cultural"],
            expand_graph=True,
        )
    if _DOCTRINE_OF_REGEX.search(query):
        return RoutingDecision(
            intent="doctrinal_verdict",
            primary_store="lexical",
            also_query=["cultural"],
            expand_graph=True,
        )
    if _WHAT_DOES_TEACH_REGEX.search(query):
        return RoutingDecision(intent="cultural_overlay", primary_store="cultural")
    if _VERSE_REF_REGEX.search(query) or _STRONG_REGEX.search(query):
        return RoutingDecision(intent="scripture_lookup", primary_store="lexical")
    if _DENOMINATION_NAMES.search(query):
        return RoutingDecision(intent="cultural_overlay", primary_store="cultural")
    return RoutingDecision(
        intent="general",
        primary_store="lexical",
        also_query=["cultural"],
    )
