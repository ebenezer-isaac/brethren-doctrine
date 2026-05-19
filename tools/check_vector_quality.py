"""Phase E.2 vector-quality gate for the lexical Qdrant collection.

Implements the RESEED_PLAN section E.2 invariants (P-EFH spec gap G2).
RESEED_PLAN E.2 (as amended 2026-05-19, see PHASE_D_DECISIONS_LOG entry
"E.2 norm-variance floor replaced by direction-dispersion") states:

    count(DISTINCT sha256(vec)) / count(*) >= 0.999  (was 0.99).
    Duplicate vector groups allowed only if all members share gloss
    exactly.

    Direction-dispersion non-degeneracy: over a random sample of
    disjoint vector pairs, mean pairwise cosine similarity must be
    <= 0.95 AND the population stdev of pairwise cosine similarity
    must be >= 1e-4 (rejects "all vectors point the same direction").

DEFECT HISTORY. The original E.2 second invariant was a vector-norm
variance floor, ``stdev([norm(v) for v in sample]) >= 0.001``. The
embedding model is voyage-4-large, which returns L2-UNIT-NORMALIZED
vectors by construction (every stored norm is approximately 1.0; an
independent live audit measured norm population stdev approximately
3.97e-08 over lex_col, mean approximately 1.0, and a fresh 512-point
re-measure here gave stdev 4.108e-08). The collection correctly uses
COSINE distance, for which the vector norm is irrelevant by design.
A "norm stdev >= 0.001" test is therefore mathematically impossible
to pass for ANY unit-normalized embedding model and was the wrong
degeneracy proxy. It is replaced (not merely deleted) by a model-
appropriate direction-dispersion test that genuinely detects "all
vectors point the same direction" for unit vectors. The embeddings
were NOT altered (de-normalizing faithful vectors would degrade
COSINE retrieval); the GATE/SPEC was wrong, like the earlier
openbible catalog-arithmetic defect. See
docs/AUDIT_phase_e_vector_quality.md and the dated decisions entry.

This script asserts BOTH invariants against the lexical Qdrant
collection ``lex_col``. The connection is read from the same source the
embedding code uses: ``Settings.qdrant_lexical_url`` (env
``QDRANT_LEXICAL_URL``, see ``ingest/lexical/_common.py`` and
``embeddings/embed_lexical.py``). Vectors are stored under the named
vector ``dense`` (see ``embeddings/embed_lexical.py``); the payload
carries a ``gloss`` field.

Distinct-vector ratio with the gloss exception
----------------------------------------------
Let ``N = count(*)``. Group points by ``sha256`` of the canonicalised
vector. A group of size ``k`` is *exempt* from counting as duplicates
ONLY when every member of that group shares the exact same ``gloss``
string. The effective distinct count is::

    distinct_effective = (number of distinct vector hashes)
                          + sum over each non-exempt duplicate group of
                            (k - 1)   # the surplus copies are penalised

Equivalently: a point is a *penalised duplicate* iff its vector hash is
shared by >= 2 points AND not all points in that hash group share an
identical gloss. The ratio asserted is::

    (N - penalised_duplicates) / N >= 0.999

A group whose members all share one gloss contributes zero penalised
duplicates (the faithful E.2 exception: legitimately identical glosses
may legitimately collide in vector space).

Direction-dispersion non-degeneracy
-----------------------------------
voyage-4-large vectors are unit-normalized, so vector MAGNITUDE carries
no information and a magnitude-variance test is meaningless. Degeneracy
for a unit-normalized, COSINE-distance store means DIRECTION collapse:
every vector pointing (nearly) the same way. We detect that directly.

Over the collected sample (all points when small, capped by
``--sample``), the points are split into disjoint consecutive pairs and
the cosine similarity of each pair is computed. A genuinely degenerate
store (constant or near-collinear direction) yields mean pairwise
cosine approximately 1.0 with pairwise-cosine stdev approximately 0; a
healthy store yields a mean well below 1.0 with a substantial spread.
Empirically measured on the live lex_col: mean pairwise cosine
approximately 0.483, stdev approximately 0.125; on a synthetic
constant-direction store: mean 1.0, stdev 0.0; on a near-collinear
store (float jitter only): mean 1.0, stdev approximately 1.8e-11.

Two conditions must BOTH hold to pass (either failing flags
degeneracy):

* mean pairwise cosine ``<= 0.95``  (live approximately 0.483;
  degenerate approximately 1.0). Conservative ceiling with a wide
  margin: even substantially more clustered but still healthy
  embeddings stay well under 0.95, while collinear collapse pins it
  to approximately 1.0.
* population stdev of pairwise cosine ``>= 1e-4``  (live approximately
  0.125; degenerate 0.0 to approximately 1.8e-11). The floor sits
  roughly three orders of magnitude above the degenerate value and
  three orders of magnitude below the healthy value, so it cannot be
  tripped by a healthy store nor passed by a collapsed one.

Pairing uses a fixed seed so the verdict is deterministic for a given
scrolled set; the metric is order-insensitive in expectation.

The script is strictly read-only: it issues only ``scroll`` /
``count`` against Qdrant and never writes. It exits non-zero with a
precise message when either invariant is violated (fault-finding, not a
rubber stamp).

Usage::

    python tools/check_vector_quality.py [--collection lex_col]
                                         [--sample N] [--self-test]

Exit codes:

* 0  both E.2 invariants hold
* 1  an invariant is violated (message names which and by how much)
* 2  argument / connection error
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import struct
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable


COLLECTION_DEFAULT = "lex_col"
VECTOR_NAME = "dense"
DISTINCT_RATIO_FLOOR = 0.999
# Direction-dispersion non-degeneracy thresholds (replace the prior
# norm-variance floor, invalid for unit-normalized voyage-4-large; see
# the module docstring and PHASE_D_DECISIONS_LOG 2026-05-19).
COSINE_MEAN_CEIL = 0.95
COSINE_STDEV_FLOOR = 1e-4
PAIR_SEED = 0x1EAF
SAMPLE_DEFAULT = 20000
SCROLL_PAGE = 256


@dataclass(frozen=True)
class _Point:
    """A minimal projection of a Qdrant point used by the gate."""

    vector: tuple[float, ...]
    gloss: str


@dataclass(frozen=True)
class Verdict:
    ok: bool
    total: int
    penalised_duplicates: int
    distinct_ratio: float
    cosine_mean: float
    cosine_stdev: float
    detail: str = ""


# ---------- vector canonicalisation ----------

def vector_sha256(vec: Iterable[float]) -> str:
    """Stable content hash of a vector.

    Each component is packed as an IEEE-754 big-endian double. NaN is
    normalised to a single canonical quiet-NaN bit pattern so that two
    NaN-bearing vectors hash equal (defensive: real embeddings never
    carry NaN, but a degenerate store might). Negative zero is folded
    to positive zero so ``-0.0`` and ``0.0`` do not split a group.
    """
    h = hashlib.sha256()
    for component in vec:
        f = float(component)
        if f != f:  # NaN
            packed = struct.pack(">Q", 0x7FF8000000000000)
        elif f == 0.0:
            packed = struct.pack(">d", 0.0)
        else:
            packed = struct.pack(">d", f)
        h.update(packed)
    return h.hexdigest()


def l2_norm(vec: Iterable[float]) -> float:
    return math.sqrt(sum(float(c) * float(c) for c in vec))


def population_stdev(values: list[float]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(var)


def pairwise_cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity of two vectors.

    Defensive against a zero (degenerate) vector: a zero vector has no
    direction, so a pair touching one is treated as maximally collapsed
    (similarity 1.0) rather than raising. Real voyage-4-large vectors
    are unit-norm so the denominator is approximately 1.0.
    """
    na = l2_norm(a)
    nb = l2_norm(b)
    if na == 0.0 or nb == 0.0:
        return 1.0
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    return dot / (na * nb)


def direction_dispersion(
    vectors: list[tuple[float, ...]], *, seed: int = PAIR_SEED
) -> tuple[float, float, int]:
    """Mean and population stdev of cosine over disjoint random pairs.

    Returns ``(mean, stdev, n_pairs)``. Pairing is a deterministic
    seeded shuffle then consecutive disjoint pairing, so the statistic
    is reproducible for a given scrolled set. With < 2 vectors no pair
    exists and a fully-collapsed signal ``(1.0, 0.0, 0)`` is returned so
    a tiny or empty store cannot silently pass the non-degeneracy gate.
    """
    n = len(vectors)
    if n < 2:
        return 1.0, 0.0, 0
    order = list(range(n))
    random.Random(seed).shuffle(order)
    sims: list[float] = []
    for i in range(0, n - 1, 2):
        sims.append(
            pairwise_cosine(vectors[order[i]], vectors[order[i + 1]])
        )
    mean = sum(sims) / len(sims)
    var = sum((s - mean) ** 2 for s in sims) / len(sims)
    return mean, math.sqrt(var), len(sims)


# ---------- core invariant evaluation ----------

def evaluate(points: list[_Point]) -> Verdict:
    """Apply the two E.2 invariants to an in-memory point list.

    Pure and O(n) in the number of points (plus O(d) per vector for the
    hash / norm, unavoidable). No I/O.
    """
    total = len(points)
    if total == 0:
        return Verdict(
            ok=False,
            total=0,
            penalised_duplicates=0,
            distinct_ratio=0.0,
            cosine_mean=1.0,
            cosine_stdev=0.0,
            detail="collection is empty; E.2 cannot be satisfied",
        )

    # Group point indices by vector hash in one pass.
    by_hash: dict[str, list[int]] = {}
    for idx, p in enumerate(points):
        by_hash.setdefault(vector_sha256(p.vector), []).append(idx)

    penalised = 0
    offending_hash: str | None = None
    for vhash, members in by_hash.items():
        if len(members) < 2:
            continue
        glosses = {points[i].gloss for i in members}
        if len(glosses) == 1:
            # E.2 exception: identical-gloss collision is permitted.
            continue
        penalised += len(members) - 1
        if offending_hash is None:
            offending_hash = vhash

    distinct_ratio = (total - penalised) / total
    cos_mean, cos_stdev, n_pairs = direction_dispersion(
        [p.vector for p in points]
    )

    problems: list[str] = []
    if distinct_ratio < DISTINCT_RATIO_FLOOR:
        problems.append(
            "distinct-vector ratio "
            f"{distinct_ratio:.6f} < {DISTINCT_RATIO_FLOOR} "
            f"({penalised} penalised duplicate(s) of {total}; first "
            f"offending vector sha256={(offending_hash or '-')[:12]}; "
            "duplicates are exempt only when every member of the "
            "vector group shares an identical gloss)"
        )
    if n_pairs == 0:
        problems.append(
            "fewer than 2 vectors: direction-dispersion "
            "non-degeneracy cannot be evaluated"
        )
    else:
        if cos_mean > COSINE_MEAN_CEIL:
            problems.append(
                "mean pairwise cosine "
                f"{cos_mean:.6f} > {COSINE_MEAN_CEIL} over {n_pairs} "
                "pair(s) (vectors point nearly the same direction / "
                "degenerate; unit-norm collinear collapse pins this to "
                "approximately 1.0)"
            )
        if cos_stdev < COSINE_STDEV_FLOOR:
            problems.append(
                "pairwise-cosine stdev "
                f"{cos_stdev:.6g} < {COSINE_STDEV_FLOOR} over {n_pairs} "
                "pair(s) (direction spread collapsed; a healthy store "
                "spreads cosine widely, a collinear store collapses it "
                "to approximately 0)"
            )

    return Verdict(
        ok=not problems,
        total=total,
        penalised_duplicates=penalised,
        distinct_ratio=distinct_ratio,
        cosine_mean=cos_mean,
        cosine_stdev=cos_stdev,
        detail="; ".join(problems),
    )


# ---------- Qdrant client protocol + adapter ----------

@runtime_checkable
class _QdrantLike(Protocol):
    def scroll(
        self,
        collection_name: str,
        *,
        limit: int,
        offset: Any = None,
        with_payload: bool = True,
        with_vectors: bool = True,
    ) -> tuple[list[Any], Any]: ...


def _record_vector(rec: Any) -> tuple[float, ...]:
    """Extract the ``dense`` vector from a scrolled record.

    Handles both the named-vector dict form ``{"dense": [...]}`` (how
    ``embed_lexical.py`` upserts) and the bare-list form.
    """
    vec = getattr(rec, "vector", None)
    if isinstance(vec, dict):
        comp = vec.get(VECTOR_NAME)
        if comp is None:
            raise KeyError(
                f"point {getattr(rec, 'id', '?')} has no named vector "
                f"{VECTOR_NAME!r}; present: {sorted(vec)}"
            )
        return tuple(float(x) for x in comp)
    if vec is None:
        raise KeyError(
            f"point {getattr(rec, 'id', '?')} carries no vector "
            "(scroll requested with_vectors=True)"
        )
    return tuple(float(x) for x in vec)


def _record_gloss(rec: Any) -> str:
    payload = getattr(rec, "payload", None) or {}
    return str(payload.get("gloss", ""))


def collect_points(
    client: _QdrantLike, collection: str, *, sample: int
) -> list[_Point]:
    """Scroll up to ``sample`` points (read-only) into memory.

    ``sample <= 0`` means "all points". Scroll order is Qdrant's
    internal order; for variance/dup statistics order is irrelevant.
    """
    out: list[_Point] = []
    offset: Any = None
    while True:
        remaining = SCROLL_PAGE if sample <= 0 else min(SCROLL_PAGE, sample - len(out))
        if remaining <= 0:
            break
        records, offset = client.scroll(
            collection_name=collection,
            limit=remaining,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        for rec in records:
            out.append(_Point(vector=_record_vector(rec), gloss=_record_gloss(rec)))
        if offset is None or not records:
            break
    return out


def _default_client() -> tuple[_QdrantLike, str]:
    """Build the real Qdrant client from the configured local store.

    Uses ``Settings.qdrant_lexical_url`` (the same source the embedding
    code reads) and falls back to the ``QDRANT_LEXICAL_URL`` env var so
    the tool runs even before a ``.env`` is loaded into the process.
    """
    url: str | None
    try:
        from ingest.lexical._common import Settings

        url = Settings().qdrant_lexical_url  # type: ignore[call-arg]
    except Exception:
        url = os.environ.get("QDRANT_LEXICAL_URL")
    if not url:
        raise RuntimeError(
            "QDRANT_LEXICAL_URL is not configured (Settings.qdrant_lexical_url "
            "/ env QDRANT_LEXICAL_URL); cannot reach the lexical Qdrant"
        )
    from qdrant_client import QdrantClient

    return QdrantClient(url=url), url


# ---------- self-test ----------

class _FakeRecord:
    def __init__(self, vector: Any, payload: dict[str, Any]) -> None:
        self.vector = vector
        self.payload = payload
        self.id = id(self)


class _FakeQdrant:
    """Deterministic in-memory scroll-only stand-in for QdrantClient."""

    def __init__(self, records: list[_FakeRecord]) -> None:
        self._records = records

    def scroll(
        self,
        collection_name: str,
        *,
        limit: int,
        offset: Any = None,
        with_payload: bool = True,
        with_vectors: bool = True,
    ) -> tuple[list[_FakeRecord], Any]:
        start = int(offset or 0)
        page = self._records[start : start + limit]
        nxt = start + limit
        return page, (nxt if nxt < len(self._records) else None)


def _mk(vec: list[float], gloss: str) -> _FakeRecord:
    return _FakeRecord({VECTOR_NAME: vec}, {"gloss": gloss})


def _unit(seed: int, dim: int = 16) -> list[float]:
    """A pseudo-random unit-norm vector (mimics voyage-4-large output)."""
    rng = random.Random(seed)
    v = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _self_test() -> int:
    # --- PASS case: many distinct UNIT vectors with healthy direction
    # spread (each norm approximately 1.0, mimicking voyage-4-large),
    # plus an identical-gloss collinear duplicate pair which is exempt
    # and must NOT penalise. A well-dispersed random unit sample has
    # mean pairwise cosine near 0 and a wide spread, so it must pass
    # the direction-dispersion non-degeneracy gate.
    healthy = [_mk(_unit(i), f"w{i}") for i in range(200)]
    healthy += [_mk(_unit(9001), "twin"), _mk(_unit(9001), "twin")]
    pts = collect_points(_FakeQdrant(healthy), "lex_col", sample=0)
    v_pass = evaluate(pts)
    if not v_pass.ok:
        print(
            f"self-test FAIL: healthy collection rejected: {v_pass.detail}",
            file=sys.stderr,
        )
        return 1
    if v_pass.penalised_duplicates != 0:
        print(
            "self-test FAIL: identical-gloss duplicate was penalised "
            f"({v_pass.penalised_duplicates})",
            file=sys.stderr,
        )
        return 1

    # --- FAIL case 1: duplicate vectors with DIFFERENT gloss ---
    dup_bad = [_mk([1.0, 1.0, 1.0], f"g{i}") for i in range(10)]
    dup_bad += [_mk([9.0, 0.0, 0.0], "x"), _mk([9.0, 0.0, 0.0], "y")]
    v_dup = evaluate(collect_points(_FakeQdrant(dup_bad), "lex_col", sample=0))
    if v_dup.ok:
        print(
            "self-test FAIL: differing-gloss duplicate vectors accepted "
            f"(ratio={v_dup.distinct_ratio})",
            file=sys.stderr,
        )
        return 1
    if "distinct-vector ratio" not in v_dup.detail:
        print(
            f"self-test FAIL: wrong failure reason for dup case: {v_dup.detail}",
            file=sys.stderr,
        )
        return 1

    # --- FAIL case 2: degenerate constant-direction store. 2000
    # vectors all pointing the SAME direction but each scaled by a
    # DISTINCT positive factor, so every sha256 is distinct (distinct-
    # ratio passes at 1.0) yet every pairwise cosine is exactly 1.0:
    # mean cosine 1.0 > 0.95 and stdev 0.0 < 1e-4. The direction-
    # dispersion gate MUST reject this (the genuine collapse signal a
    # unit-norm-only store would otherwise hide). This is the case the
    # removed norm-variance floor was meant to catch but, for a unit-
    # normalized model, never could.
    collinear = [
        _mk([float(i + 1), 0.0, 0.0], f"u{i}") for i in range(2000)
    ]
    v_col = evaluate(collect_points(_FakeQdrant(collinear), "lex_col", sample=0))
    if v_col.ok:
        print(
            "self-test FAIL: constant-direction vectors accepted "
            f"(cos_mean={v_col.cosine_mean} cos_stdev={v_col.cosine_stdev})",
            file=sys.stderr,
        )
        return 1
    if "cosine" not in v_col.detail:
        print(
            f"self-test FAIL: wrong failure reason for collinear case: "
            f"{v_col.detail}",
            file=sys.stderr,
        )
        return 1

    # --- FAIL case 2b: near-collinear unit vectors (a fixed direction
    # plus float-scale jitter only). Each is unit-norm and distinct, so
    # the OLD norm-variance floor would have passed it; the new gate
    # must still reject because mean cosine stays approximately 1.0 and
    # the spread collapses below the 1e-4 floor.
    base = _unit(7, dim=16)
    near = []
    for i in range(2000):
        rng = random.Random(1000 + i)
        v = [b + rng.uniform(-1e-7, 1e-7) for b in base]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        near.append(_mk([x / n for x in v], f"n{i}"))
    v_near = evaluate(collect_points(_FakeQdrant(near), "lex_col", sample=0))
    if v_near.ok:
        print(
            "self-test FAIL: near-collinear unit vectors accepted "
            f"(cos_mean={v_near.cosine_mean} cos_stdev={v_near.cosine_stdev})",
            file=sys.stderr,
        )
        return 1
    if "cosine" not in v_near.detail:
        print(
            "self-test FAIL: wrong failure reason for near-collinear "
            f"case: {v_near.detail}",
            file=sys.stderr,
        )
        return 1

    # --- FAIL case 3: empty collection ---
    v_empty = evaluate(collect_points(_FakeQdrant([]), "lex_col", sample=0))
    if v_empty.ok:
        print("self-test FAIL: empty collection accepted", file=sys.stderr)
        return 1

    # --- threshold-edge: exactly one penalised dup in 1000 -> ratio
    # 0.999, the inclusive floor, must PASS. The 998 non-dup vectors
    # are well-dispersed unit vectors so the direction-dispersion gate
    # is satisfied and ONLY the distinct-ratio edge is exercised. The
    # final pair shares one vector with DIFFERING gloss ("p" vs "q")
    # so it is one penalised duplicate (not gloss-exempt).
    edge = [_mk(_unit(5000 + i), f"e{i}") for i in range(998)]
    edge += [_mk(_unit(123456), "p"), _mk(_unit(123456), "q")]
    v_edge = evaluate(collect_points(_FakeQdrant(edge), "lex_col", sample=0))
    if not v_edge.ok:
        print(
            "self-test FAIL: ratio exactly at 0.999 floor rejected "
            f"({v_edge.distinct_ratio:.6f}: {v_edge.detail})",
            file=sys.stderr,
        )
        return 1

    print(
        "self-test OK "
        f"(pass ratio={v_pass.distinct_ratio:.6f} "
        f"cos_mean={v_pass.cosine_mean:.4f} cos_stdev={v_pass.cosine_stdev:.4f}; "
        f"dup-fail ratio={v_dup.distinct_ratio:.6f}; "
        f"constant-dir-fail cos_mean={v_col.cosine_mean:.4f} "
        f"cos_stdev={v_col.cosine_stdev:.3g}; "
        f"near-collinear-fail cos_mean={v_near.cosine_mean:.4f} "
        f"cos_stdev={v_near.cosine_stdev:.3g}; "
        f"edge ratio={v_edge.distinct_ratio:.6f})"
    )
    return 0


# ---------- entrypoint ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase E.2 vector-quality gate for the lexical Qdrant "
            "collection (RESEED_PLAN E.2: distinct-ratio >= 0.999 with "
            "the identical-gloss duplicate exception, and direction-"
            "dispersion non-degeneracy: mean pairwise cosine <= 0.95 "
            "AND pairwise-cosine stdev >= 1e-4). Read-only; non-zero "
            "exit on violation."
        )
    )
    parser.add_argument(
        "--collection", default=COLLECTION_DEFAULT,
        help=f"Qdrant collection name (default: {COLLECTION_DEFAULT}).",
    )
    parser.add_argument(
        "--sample", type=int, default=SAMPLE_DEFAULT,
        help=(
            "Max points to scroll for the direction-dispersion "
            "sample; <= 0 means scan the whole collection. The "
            "distinct-ratio is computed over the same scrolled set."
        ),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        client, url = _default_client()
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    try:
        points = collect_points(client, args.collection, sample=args.sample)
    except Exception as exc:  # noqa: BLE001 - surface store errors loudly
        print(
            f"FAIL: cannot scroll {args.collection!r} at {url}: {exc}",
            file=sys.stderr,
        )
        return 2

    verdict = evaluate(points)
    if verdict.ok:
        print(
            f"OK: {args.collection} n={verdict.total} "
            f"distinct_ratio={verdict.distinct_ratio:.6f} "
            f"(>= {DISTINCT_RATIO_FLOOR}) "
            f"cosine_mean={verdict.cosine_mean:.6f} "
            f"(<= {COSINE_MEAN_CEIL}) "
            f"cosine_stdev={verdict.cosine_stdev:.6g} "
            f"(>= {COSINE_STDEV_FLOOR})"
        )
        return 0
    print(f"FAIL: E.2 violated: {verdict.detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
