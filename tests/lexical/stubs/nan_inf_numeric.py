"""Attack vector L9: numeric fields contain NaN / Inf.

A lazy adapter that emits records whose required numeric fields are
``float("nan")`` or ``float("inf")``. The verifier (Phase C
``verify_adapter_*.py`` referencing
``tools/predicates_by_type.cypher::$pred_float``) must reject these as
non-finite.

The Phase Z adversarial driver (``tools/verify_adapter_template.py``)
detects this via ``required_field_empty`` because the per-type predicate
treats NaN/Inf as empty. See ``RESEED_PLAN`` Z.1 item 5.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref", "confidence")


def emit_records() -> list[dict[str, object]]:
    return [
        {"lemma": "rēšîṯ", "gloss": "beginning", "ref": "GEN 1:1",
         "strong": "H7225", "confidence": float("nan")},
        {"lemma": "bārāʾ", "gloss": "create", "ref": "GEN 1:1",
         "strong": "H1254", "confidence": float("inf")},
        {"lemma": "ʾĕlōhîm", "gloss": "God", "ref": "GEN 1:1",
         "strong": "H430", "confidence": float("-inf")},
        {"lemma": "ʾēṯ", "gloss": "[obj]", "ref": "GEN 1:1",
         "strong": "H853", "confidence": float("nan")},
        {"lemma": "šāmayim", "gloss": "heavens", "ref": "GEN 1:1",
         "strong": "H8064", "confidence": float("nan")},
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
    ] + [
        {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"H{i}"} for i in range(6)
    ]
