"""Deterministic post-processor for verdict.lexical_score.

Pure function. No I/O, no clock, no random. Reads only counts and booleans from
the Evidence model, so it is order-invariant by construction. Triangle test
H11 verifies this in tests.
"""

from __future__ import annotations

from pipeline2.evidence_schema import Evidence

WEIGHT_PAN_CANONICAL = 0.25
WEIGHT_ANCHOR_LEMMA = 0.20
WEIGHT_COMPLICATING = 0.15
WEIGHT_CROSS_REF = 0.15
WEIGHT_VARIANT_ROBUST = 0.15
WEIGHT_CONCORDANCE = 0.10

PAN_CANONICAL_FLOOR = 0.3
VARIANT_ROBUST_FLOOR = 0.5

ANCHOR_LEMMA_CAP = 8
CROSS_REF_CAP = 12
CONCORDANCE_CAP = 10

SCORE_PRECISION = 6


def compute_lexical_score(evidence: Evidence) -> float:
    pan_canonical_factor = 1.0 if evidence.verdict.pan_canonical else PAN_CANONICAL_FLOOR
    anchor_lemma_factor = (
        min(len(evidence.lexical_evidence.anchor_lemmas), ANCHOR_LEMMA_CAP) / ANCHOR_LEMMA_CAP
    )
    complicating = evidence.lexical_evidence.complicating_texts
    if not complicating:
        complicating_resolved_factor = 1.0
    else:
        addressed = sum(1 for c in complicating if c.addressed)
        complicating_resolved_factor = addressed / len(complicating)
    cross_ref_density_factor = (
        min(len(evidence.lexical_evidence.cross_refs_invoked), CROSS_REF_CAP) / CROSS_REF_CAP
    )
    variant_robust_factor = 1.0 if evidence.verdict.variant_robust else VARIANT_ROBUST_FLOOR
    concordance_breadth_factor = (
        min(len(evidence.lexical_evidence.concordance_traversed), CONCORDANCE_CAP) / CONCORDANCE_CAP
    )

    score = (
        WEIGHT_PAN_CANONICAL * pan_canonical_factor
        + WEIGHT_ANCHOR_LEMMA * anchor_lemma_factor
        + WEIGHT_COMPLICATING * complicating_resolved_factor
        + WEIGHT_CROSS_REF * cross_ref_density_factor
        + WEIGHT_VARIANT_ROBUST * variant_robust_factor
        + WEIGHT_CONCORDANCE * concordance_breadth_factor
    )
    return round(score, SCORE_PRECISION)
