"""Phase E.2 vector-quality gate for the lexical Qdrant collection.

Implements the RESEED_PLAN section E.2 invariants (P-EFH spec gap G2).
RESEED_PLAN E.2 states verbatim:

    count(DISTINCT sha256(vec)) / count(*) >= 0.999  (was 0.99).
    Duplicate vector groups allowed only if all members share gloss
    exactly.

    Vector norm variance floor:
    stdev([norm(v) for v in sample]) >= 0.001
    (rejects "all vectors approximately the same direction").

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

Norm variance floor
--------------------
Over a sample of points (all points when the collection is small,
capped by ``--sample`` otherwise, scanned in scroll order which is
deterministic per Qdrant segment layout) compute the L2 norm of every
``dense`` vector and require the population standard deviation to be
``>= 0.001``. A degenerate store where every vector points the same
direction (or is the zero vector) collapses this stdev to ~0 and is
rejected.

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
import struct
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable


COLLECTION_DEFAULT = "lex_col"
VECTOR_NAME = "dense"
DISTINCT_RATIO_FLOOR = 0.999
NORM_STDEV_FLOOR = 0.001
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
    norm_stdev: float
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
            norm_stdev=0.0,
            detail="collection is empty; E.2 cannot be satisfied",
        )

    # Group point indices by vector hash in one pass.
    by_hash: dict[str, list[int]] = {}
    norms: list[float] = []
    for idx, p in enumerate(points):
        by_hash.setdefault(vector_sha256(p.vector), []).append(idx)
        norms.append(l2_norm(p.vector))

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
    norm_stdev = population_stdev(norms)

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
    if norm_stdev < NORM_STDEV_FLOOR:
        problems.append(
            "vector L2-norm stdev "
            f"{norm_stdev:.6g} < {NORM_STDEV_FLOOR} "
            "(vectors are near-collinear / degenerate)"
        )

    return Verdict(
        ok=not problems,
        total=total,
        penalised_duplicates=penalised,
        distinct_ratio=distinct_ratio,
        norm_stdev=norm_stdev,
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


def _self_test() -> int:
    # --- PASS case: all distinct, healthy norm spread ---
    healthy = [
        _mk([1.0, 0.0, 0.0], "alpha"),
        _mk([0.0, 2.0, 0.0], "beta"),
        _mk([0.0, 0.0, 3.0], "gamma"),
        _mk([0.5, 0.5, 4.0], "delta"),
        # A legitimately-collinear-gloss duplicate pair: SAME vector,
        # SAME gloss -> exempt, must NOT penalise.
        _mk([7.0, 7.0, 7.0], "twin"),
        _mk([7.0, 7.0, 7.0], "twin"),
    ]
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

    # --- FAIL case 2: all vectors collinear (norm stdev collapses) ---
    # 2000 identical-direction vectors, EACH with a unique gloss so the
    # distinct-ratio invariant passes and ONLY the variance floor fires.
    collinear = [_mk([1.0, 0.0, 0.0], f"u{i}") for i in range(2000)]
    v_col = evaluate(collect_points(_FakeQdrant(collinear), "lex_col", sample=0))
    if v_col.ok:
        print(
            "self-test FAIL: collinear/zero-variance vectors accepted "
            f"(stdev={v_col.norm_stdev})",
            file=sys.stderr,
        )
        return 1
    if "norm stdev" not in v_col.detail:
        print(
            f"self-test FAIL: wrong failure reason for collinear case: "
            f"{v_col.detail}",
            file=sys.stderr,
        )
        return 1

    # --- FAIL case 3: empty collection ---
    v_empty = evaluate(collect_points(_FakeQdrant([]), "lex_col", sample=0))
    if v_empty.ok:
        print("self-test FAIL: empty collection accepted", file=sys.stderr)
        return 1

    # --- threshold-edge: exactly one penalised dup in 1000 -> ratio
    # 0.999 which is the inclusive floor and must PASS ---
    edge = [_mk([float(i), 1.0, 0.0], f"e{i}") for i in range(998)]
    edge += [_mk([5.0, 5.0, 5.0], "p"), _mk([5.0, 5.0, 5.0], "q")]
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
        f"(pass ratio={v_pass.distinct_ratio:.6f} stdev={v_pass.norm_stdev:.4g}; "
        f"dup-fail ratio={v_dup.distinct_ratio:.6f}; "
        f"collinear-fail stdev={v_col.norm_stdev:.3g}; "
        f"edge ratio={v_edge.distinct_ratio:.6f})"
    )
    return 0


# ---------- entrypoint ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase E.2 vector-quality gate for the lexical Qdrant "
            "collection (RESEED_PLAN E.2: distinct-ratio >= 0.999 with "
            "the identical-gloss duplicate exception, and L2-norm stdev "
            ">= 0.001). Read-only; non-zero exit on violation."
        )
    )
    parser.add_argument(
        "--collection", default=COLLECTION_DEFAULT,
        help=f"Qdrant collection name (default: {COLLECTION_DEFAULT}).",
    )
    parser.add_argument(
        "--sample", type=int, default=SAMPLE_DEFAULT,
        help=(
            "Max points to scroll for the norm-variance sample; "
            "<= 0 means scan the whole collection. The distinct-ratio "
            "is computed over the same scrolled set."
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
            f"norm_stdev={verdict.norm_stdev:.6g} "
            f"(>= {NORM_STDEV_FLOOR})"
        )
        return 0
    print(f"FAIL: E.2 violated: {verdict.detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
