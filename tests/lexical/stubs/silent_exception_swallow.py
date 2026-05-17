"""Attack vector L13: bulk records swallowed by bare except.

A lazy adapter that wraps per-record parsing in ``try/except: pass`` and
silently drops 80% of source rows. ``emit_records()`` therefore returns
far fewer records than the expected count from the source file. The
verifier must reject via a count-floor check derived from the source
file (Phase C ``tools/derive_expected_counts.py`` Tier-A exact match,
or Tier-B ratio).

For Z purposes the stub exposes ``EXPECTED_RECORD_COUNT`` so the
adversarial test can assert the verifier flags an 80% shortfall.
"""

from __future__ import annotations


REQUIRED_FIELDS = ("lemma", "gloss", "ref")
EXPECTED_RECORD_COUNT = 50


def _full_input() -> list[tuple[str, str, str, str]]:
    return [
        (f"H{1000 + i}", f"lex_{i}", f"gloss_{i}", f"GEN 1:{(i % 10) + 1}")
        for i in range(EXPECTED_RECORD_COUNT)
    ]


def emit_records() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for i, (strong, lemma, gloss, ref) in enumerate(_full_input()):
        try:
            if i % 5 != 0:
                raise ValueError("simulated parse failure")
            out.append({"lemma": lemma, "gloss": gloss, "ref": ref, "strong": strong})
        except ValueError:
            pass
    return out


def emit_edges() -> list[dict[str, str]]:
    return [
        {"type": "IN_VERSE", "src": f"w{i}", "dst": "GEN 1:1"} for i in range(6)
    ] + [
        {"type": "INSTANCE_OF", "src": f"w{i}", "dst": f"H{i}"} for i in range(6)
    ]
