"""Attack vector L12: source strings lowercased / case-mutated.

A lazy adapter that applies ``.lower()`` to Hebrew and Greek lemmas
before emission. Hebrew has no case, but Greek does, and SBL transl-
iteration conventions encode case-sensitive distinctions (Theos vs
theos, Christos vs christos). The verifier's character-preservation
check (Phase C per-adapter assertion against the fixture slice) must
catch this.

For Z purposes, the stub passes the shallow checks but the Z driver
adversarial harness inspects ``emit_records()`` against
``EXPECTED_VERBATIM`` and fails when stored output differs from the
expected case.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")


EXPECTED_VERBATIM = {
    "G2316": "Θεός",
    "G5547": "Χριστός",
    "G2424": "Ἰησοῦς",
}


def emit_records() -> list[dict[str, object]]:
    raw = [
        ("G2316", "Θεός", "God"),
        ("G5547", "Χριστός", "Christ"),
        ("G2424", "Ἰησοῦς", "Jesus"),
        ("G2962", "Κύριος", "Lord"),
        ("G3056", "Λόγος", "Word"),
        ("G4151", "Πνεῦμα", "Spirit"),
    ]
    return [
        {"lemma": lemma.lower(), "gloss": gloss, "ref": "JOHN 1:1",
         "strong": strong}
        for strong, lemma, gloss in raw
    ]


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "JOHN 1:1"} for i in range(8)
    ] + [
        {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"G{i}"} for i in range(8)
    ]
