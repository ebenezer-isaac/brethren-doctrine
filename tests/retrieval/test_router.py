"""Tests for retrieval.router."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from retrieval.router import RoutingDecision, classify_intent


def test_verse_ref_routes_to_scripture_lookup() -> None:
    d = classify_intent("What does John 1:1 say about logos")
    assert d.intent == "scripture_lookup"
    assert d.primary_store == "lexical"


def test_strong_code_routes_to_scripture_lookup() -> None:
    d = classify_intent("Show me occurrences of G2316")
    assert d.intent == "scripture_lookup"
    assert d.primary_store == "lexical"


def test_doctrine_of_routes_to_doctrinal_verdict() -> None:
    d = classify_intent("What is the doctrine of penal substitution")
    assert d.intent == "doctrinal_verdict"
    assert d.primary_store == "lexical"
    assert "cultural" in d.also_query
    assert d.expand_graph is True


def test_what_does_teach_routes_to_cultural_overlay() -> None:
    d = classify_intent("What does the Reformed church teach about baptism")
    assert d.intent == "cultural_overlay"
    assert d.primary_store == "cultural"


def test_comparative_routes_to_comparative_with_expand() -> None:
    d = classify_intent("Compare Catholic and Reformed views on the Eucharist")
    assert d.intent == "comparative"
    assert d.expand_graph is True
    assert d.also_query == ["cultural"]


def test_variant_keyword_routes_to_variant_inspect() -> None:
    d = classify_intent("Show variant readings for 1 John 5:7")
    assert d.intent == "variant_inspect"
    assert d.primary_store == "lexical"


def test_codex_keyword_routes_to_variant_inspect() -> None:
    d = classify_intent("Compare Codex Sinaiticus and Vaticanus for Mark 16")
    assert d.intent == "variant_inspect"


def test_versification_routes_to_versification() -> None:
    d = classify_intent("Psalm 51:1 Hebrew vs English numbering")
    assert d.intent == "versification"
    assert d.primary_store == "lexical"


def test_denomination_name_only_routes_to_cultural_overlay() -> None:
    d = classify_intent("Wesleyan position on sanctification")
    assert d.intent == "cultural_overlay"
    assert d.primary_store == "cultural"


def test_general_query_routes_to_general() -> None:
    d = classify_intent("Why is forgiveness important")
    assert d.intent == "general"
    assert d.primary_store == "lexical"
    assert "cultural" in d.also_query


def test_empty_string_routes_to_general() -> None:
    d = classify_intent("")
    assert d.intent == "general"


def test_non_string_input_safe() -> None:
    d = classify_intent("   ")
    assert d.intent == "general"


def test_default_uses_reranker_and_k_10() -> None:
    d = classify_intent("John 3:16")
    assert d.use_reranker is True
    assert d.k == 10


def test_doctrine_of_takes_precedence_over_verse_ref() -> None:
    d = classify_intent("Doctrine of the Trinity in John 1:1")
    assert d.intent == "doctrinal_verdict"


def test_variant_takes_precedence_over_doctrine_of() -> None:
    d = classify_intent("Variant readings for the doctrine of baptism")
    assert d.intent == "variant_inspect"


def test_extra_forbid_on_routing_decision() -> None:
    with pytest.raises(ValidationError):
        RoutingDecision.model_validate(
            {
                "intent": "general",
                "primary_store": "lexical",
                "bogus": True,
            }
        )
