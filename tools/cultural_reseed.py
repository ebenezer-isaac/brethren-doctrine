"""Autonomous reseed harness for the Pipeline 1 cultural Neo4j corpus.

The cultural Neo4j store was wiped; the schema and Doctrine/Question seed
are reloaded but every Work/CulturalChunk node is gone. The faithful
captured per-source adapter output survives on disk as
``data/cultural_chunks/<source>.jsonl`` (one ``CulturalChunk`` JSON per
line, exactly ``CulturalChunk.model_dump_json()``) plus a
``<source>.status`` sidecar. This harness reseeds the graph from that
corpus deterministically, or re-scrapes live when an adapter's output
must be regenerated.

Two modes:

* ``--mode from-jsonl`` (DEFAULT, deterministic, fast, no network)
    For each source, read ``data/cultural_chunks/<source>.jsonl``,
    reconstruct each line with ``CulturalChunk.model_validate_json`` and
    upsert via ``ingest.cultural._common.upsert_chunks`` (the fixed
    upsert that gates copyrighted text behind the G-T1 redistribute
    guard ``check_redistribute(...)["allowed"]`` at _common.py:138).
    Sources processed in sorted order, jsonl lines in file order, no
    parallelism, no timestamps. This is the path for the 20 sources
    whose adapter ``scrape()`` output did not change.

* ``--mode scrape`` (robust, resumable, parallel, retrying)
    For the chosen sources, run ``mod.scrape()`` live, persist
    ``<source>.jsonl`` + ``<source>.status`` mirroring
    ``tools/run_cultural_scrape.py`` byte-for-byte, then upsert.
    Bounded worker pool (``--workers``, default 5), per-source
    exponential backoff retry on transient network errors (4 attempts,
    5/15/45/120s), ``--resume`` skips sources already captured
    successfully (unless in ``--force``), and any source that exhausts
    its retries is recorded with its error AND surfaced: the harness
    exits non-zero and prints the failed list. An incomplete corpus is
    never silently produced (brethren-on-trial: surface it).

Common:

* ``--source`` accepts ``all`` or a comma list. The source-of-truth
  source list is ``ingest.cultural.run.ADAPTERS`` (imported, never
  re-declared, so this harness cannot drift from the CLI).
* Structured per-source progress to stdout (started / chunks=N /
  upserted / DONE or RETRY n / FAILED) so a log tail shows real
  progress, then a final JSON summary and an explicit
  ``OVERALL: ok=<bool> sources_done=<n>/<total> failed=<list>``.
* ``--dry-run`` parses and reconstructs but does not open Neo4j.
* ``--self-test`` parses a couple of existing jsonl files into
  ``CulturalChunk`` objects with no network and no Neo4j and asserts
  round-trip field fidelity plus deterministic ordering.

Air-gap: only ``NEO4J_CULTURAL_*`` is ever touched (via the shared
``Settings``); the lexical store is never referenced. ``upsert_chunks``,
``Settings``, ``get_cultural_driver`` and the ``CulturalChunk`` model are
reused verbatim; nothing in ``_common.py``, the adapters or ``run.py``
is modified.

Exit codes: 0 every chosen source reseeded; 1 one or more sources
failed (listed); 2 argument or environment error.
"""

from __future__ import annotations

import argparse
import importlib
import json
import socket
import ssl
import sys
import time
import traceback
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ingest.cultural._common import Settings, get_cultural_driver, upsert_chunks
from ingest.cultural.run import ADAPTERS
from ingest.models import CulturalChunk

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "cultural_chunks"

# Retry policy for --mode scrape. Backoff seconds are applied between
# attempts, so 4 attempts means up to 3 sleeps of 5, 15, 45 then 120
# (the 4th entry covers a 5th attempt if MAX_ATTEMPTS is ever raised).
MAX_ATTEMPTS = 4
BACKOFF_SECONDS = (5, 15, 45, 120)

# Transient network failures worth retrying. An HTTPError is retried only
# for 429 and 5xx; a 4xx (other than 429) is a hard, non-transient fault.
_TRANSIENT_EXC = (
    urllib.error.URLError,
    ssl.SSLError,
    socket.timeout,
    TimeoutError,
    ConnectionError,
)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or 500 <= exc.code < 600
    if isinstance(exc, urllib.error.URLError):
        return True
    return isinstance(exc, _TRANSIENT_EXC)


def _resolve_sources(spec: str) -> list[str]:
    """Resolve --source to a concrete ordered list against ADAPTERS.

    Unknown names are a hard argument error: a typo must never silently
    shrink the reseed set (brethren-on-trial: incomplete is unacceptable).
    """
    if spec.strip() == "all":
        return list(ADAPTERS)
    requested = [s.strip() for s in spec.split(",") if s.strip()]
    known = set(ADAPTERS)
    unknown = [s for s in requested if s not in known]
    if unknown:
        raise ValueError(
            f"unknown source(s) {unknown}; valid sources: {sorted(known)}"
        )
    # Preserve caller order but de-duplicate.
    seen: set[str] = set()
    ordered: list[str] = []
    for s in requested:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _jsonl_path(source: str) -> Path:
    return OUTPUT_DIR / f"{source}.jsonl"


def _status_path(source: str) -> Path:
    return OUTPUT_DIR / f"{source}.status"


def _log(msg: str) -> None:
    """Single-line, flushed progress so `tail -f` shows live progress."""
    print(msg, flush=True)


def _load_chunks_from_jsonl(source: str) -> list[CulturalChunk]:
    """Reconstruct CulturalChunk objects from the captured jsonl.

    Each line is exactly ``CulturalChunk.model_dump_json()`` output, so
    ``model_validate_json`` round-trips every field (including the nested
    source object and doctrine_tags). File order is preserved: the
    adapter's chunk ordering is the deterministic order and must not be
    re-sorted.
    """
    path = _jsonl_path(source)
    if not path.exists():
        raise FileNotFoundError(f"missing captured corpus: {path}")
    chunks: list[CulturalChunk] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                chunks.append(CulturalChunk.model_validate_json(line))
            except Exception as exc:  # noqa: BLE001 - surface exact line
                raise ValueError(
                    f"{source}.jsonl line {lineno} failed to parse as "
                    f"CulturalChunk: {exc}"
                ) from exc
    return chunks


def _status_indicates_success(source: str) -> bool:
    """True only if a prior capture clearly succeeded.

    Resume skips a source only when its jsonl exists AND its status
    sidecar shows chunks > 0 with ingest_error null. Anything ambiguous
    (missing status, zero chunks, recorded error) is treated as NOT done
    so it is reprocessed rather than silently left incomplete.
    """
    if not _jsonl_path(source).exists():
        return False
    sp = _status_path(source)
    if not sp.exists():
        return False
    try:
        data = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    chunks = data.get("chunks")
    if not isinstance(chunks, int) or chunks <= 0:
        return False
    return data.get("ingest_error") in (None, "")


def _upsert(
    chunks: list[CulturalChunk], settings: Settings, dry_run: bool
) -> dict[str, int]:
    if dry_run or not chunks:
        return {}
    driver = get_cultural_driver(settings)
    try:
        return upsert_chunks(driver, chunks)
    finally:
        driver.close()


def _write_capture(source: str, chunks: list[CulturalChunk]) -> None:
    """Persist jsonl + status exactly as tools/run_cultural_scrape.py.

    Same field order (model_dump_json), one chunk per line, no trailing
    sort, no injected timestamps/uuids in jsonl content. The status
    sidecar mirrors run_cultural_scrape's schema so downstream tooling
    and --resume read an identical shape.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with _jsonl_path(source).open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(chunk.model_dump_json() + "\n")


def _write_status(
    source: str,
    chunks: int,
    elapsed: float,
    neo4j_counts: dict[str, int],
    ingest_error: str | None,
) -> None:
    status = {
        "source": source,
        "chunks": chunks,
        "elapsed_seconds": elapsed,
        "jsonl_path": str(Path("data") / "cultural_chunks" / f"{source}.jsonl"),
        "neo4j_counts": neo4j_counts,
        "ingest_error": ingest_error,
    }
    _status_path(source).write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )


def _write_failure_status(source: str, error: str, tb: str, elapsed: float) -> None:
    """Hard-fail sidecar mirroring run_cultural_scrape's error branch."""
    _status_path(source).write_text(
        json.dumps(
            {
                "source": source,
                "error": error,
                "traceback": tb,
                "elapsed_seconds": round(elapsed, 1),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _process_from_jsonl(
    source: str, settings: Settings | None, dry_run: bool
) -> dict[str, Any]:
    """Deterministic reseed of one source from its captured jsonl."""
    _log(f"[{source}] started mode=from-jsonl")
    chunks = _load_chunks_from_jsonl(source)
    _log(f"[{source}] chunks={len(chunks)}")
    counts = _upsert(chunks, settings, dry_run) if settings is not None else {}
    _log(
        f"[{source}] upserted "
        f"CulturalChunk={counts.get('CulturalChunk', 0)} "
        f"Work={counts.get('Work', 0)}"
    )
    _log(f"[{source}] DONE")
    return {
        "chunks": len(chunks),
        "upserted": counts.get("CulturalChunk", 0),
        "mode": "from-jsonl",
        "attempts": 1,
        "error": None,
    }


def _scrape_with_retry(source: str) -> tuple[list[CulturalChunk], int]:
    """Run mod.scrape() with bounded exponential-backoff retry.

    Returns (chunks, attempts). Transient network faults are retried up
    to MAX_ATTEMPTS times; a non-transient fault (e.g. a 4xx, an adapter
    bug) fails fast. The final exception is re-raised so the caller can
    record a hard failure rather than silently skipping the source.
    """
    mod = importlib.import_module(f"ingest.cultural.{source}")
    last_exc: BaseException | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            chunks: list[CulturalChunk] = mod.scrape()
            return chunks, attempt
        except Exception as exc:  # noqa: BLE001 - classify then re-raise
            last_exc = exc
            transient = _is_transient(exc)
            if not transient or attempt == MAX_ATTEMPTS:
                raise
            backoff = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
            _log(
                f"[{source}] RETRY {attempt}/{MAX_ATTEMPTS - 1} after "
                f"transient {type(exc).__name__}: {exc}; sleeping {backoff}s"
            )
            time.sleep(backoff)
    # Unreachable: loop either returns or raises.
    assert last_exc is not None
    raise last_exc


def _process_scrape(
    source: str, settings: Settings | None, dry_run: bool
) -> dict[str, Any]:
    """Live re-scrape of one source, persist capture, then upsert."""
    _log(f"[{source}] started mode=scrape")
    start = time.monotonic()
    try:
        chunks, attempts = _scrape_with_retry(source)
    except Exception as exc:  # noqa: BLE001 - hard fail, recorded + surfaced
        elapsed = time.monotonic() - start
        _write_failure_status(source, str(exc), traceback.format_exc(), elapsed)
        _log(f"[{source}] FAILED after retries: {type(exc).__name__}: {exc}")
        return {
            "chunks": 0,
            "upserted": 0,
            "mode": "scrape",
            "attempts": MAX_ATTEMPTS,
            "error": f"{type(exc).__name__}: {exc}",
        }

    _log(f"[{source}] chunks={len(chunks)} (attempt {attempts})")
    _write_capture(source, chunks)

    counts: dict[str, int] = {}
    ingest_error: str | None = None
    if settings is not None and not dry_run and chunks:
        try:
            counts = _upsert(chunks, settings, dry_run=False)
        except Exception as exc:  # noqa: BLE001 - record, do not swallow
            ingest_error = f"{type(exc).__name__}: {exc}"

    elapsed = round(time.monotonic() - start, 1)
    _write_status(source, len(chunks), elapsed, counts, ingest_error)

    if ingest_error is not None:
        _log(f"[{source}] FAILED upsert: {ingest_error}")
        return {
            "chunks": len(chunks),
            "upserted": 0,
            "mode": "scrape",
            "attempts": attempts,
            "error": ingest_error,
        }

    _log(
        f"[{source}] upserted "
        f"CulturalChunk={counts.get('CulturalChunk', 0)} "
        f"Work={counts.get('Work', 0)}"
    )
    _log(f"[{source}] DONE")
    return {
        "chunks": len(chunks),
        "upserted": counts.get("CulturalChunk", 0),
        "mode": "scrape",
        "attempts": attempts,
        "error": None,
    }


def _run_from_jsonl(
    sources: list[str], settings: Settings | None, dry_run: bool
) -> dict[str, dict[str, Any]]:
    """Deterministic: sorted source order, serial, no network."""
    results: dict[str, dict[str, Any]] = {}
    for source in sorted(sources):
        try:
            results[source] = _process_from_jsonl(source, settings, dry_run)
        except Exception as exc:  # noqa: BLE001 - surface, never skip
            _log(f"[{source}] FAILED: {type(exc).__name__}: {exc}")
            results[source] = {
                "chunks": 0,
                "upserted": 0,
                "mode": "from-jsonl",
                "attempts": 1,
                "error": f"{type(exc).__name__}: {exc}",
            }
    return results


def _run_scrape(
    sources: list[str],
    settings: Settings | None,
    dry_run: bool,
    workers: int,
    resume: bool,
    force: set[str],
) -> dict[str, dict[str, Any]]:
    """Robust: bounded parallel pool, resumable, retrying, hard-fail.

    The 22 sources are independent (no inter-adapter dependency per
    docs/PHASE_G_CULTURAL_DEFECT_MAP.md G-SHARED-4), so a thread pool is
    safe. _common.py enforces a 2s per-host politeness gap via a shared
    dict, which throttles same-host concurrency naturally.
    """
    results: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    for source in sorted(sources):
        if resume and source not in force and _status_indicates_success(source):
            _log(f"[{source}] SKIP (resume: prior success)")
            results[source] = {
                "chunks": None,
                "upserted": None,
                "mode": "scrape",
                "attempts": 0,
                "error": None,
                "skipped": "resume",
            }
            continue
        pending.append(source)

    if not pending:
        return results

    effective_workers = max(1, min(workers, len(pending)))
    with ThreadPoolExecutor(max_workers=effective_workers) as pool:
        future_map = {
            pool.submit(_process_scrape, src, settings, dry_run): src
            for src in pending
        }
        for fut in as_completed(future_map):
            src = future_map[fut]
            try:
                results[src] = fut.result()
            except Exception as exc:  # noqa: BLE001 - never lose a source
                _log(f"[{src}] FAILED (unexpected): {type(exc).__name__}: {exc}")
                results[src] = {
                    "chunks": 0,
                    "upserted": 0,
                    "mode": "scrape",
                    "attempts": MAX_ATTEMPTS,
                    "error": f"{type(exc).__name__}: {exc}",
                }
    return results


def _self_test() -> int:
    """No network, no Neo4j. Round-trip + deterministic-order checks."""
    samples = ["schleitheim", "conciliar"]
    available = [s for s in samples if _jsonl_path(s).exists()]
    if not available:
        # Fall back to any present jsonl so the check is meaningful.
        present = sorted(p.stem for p in OUTPUT_DIR.glob("*.jsonl"))
        available = present[:2]
    if not available:
        print("self-test FAIL: no jsonl files to validate", file=sys.stderr)
        return 1

    for source in available:
        path = _jsonl_path(source)
        raw_lines = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        chunks = _load_chunks_from_jsonl(source)
        if len(chunks) != len(raw_lines):
            print(
                f"self-test FAIL: {source} parsed {len(chunks)} != "
                f"{len(raw_lines)} non-empty lines",
                file=sys.stderr,
            )
            return 1

        # Round-trip fidelity: re-serialising each reconstructed chunk
        # must reproduce the captured line byte-for-byte (proves every
        # field, the nested source object and doctrine_tags survive).
        for idx, (chunk, original) in enumerate(zip(chunks, raw_lines)):
            redumped = chunk.model_dump_json()
            if redumped != original:
                print(
                    f"self-test FAIL: {source} line {idx + 1} round-trip "
                    "mismatch (field fidelity lost)",
                    file=sys.stderr,
                )
                return 1

        # Required-field presence on the reconstructed object: these are
        # exactly what upsert_chunks reads in _common.py.
        first = chunks[0]
        for attr in ("chunk_id", "tradition", "text", "text_to_embed",
                     "license", "redistribute"):
            if getattr(first, attr, None) in (None, ""):
                print(
                    f"self-test FAIL: {source} chunk[0].{attr} empty; "
                    "upsert_chunks would reject",
                    file=sys.stderr,
                )
                return 1
        if not getattr(first.source, "work_id", ""):
            print(
                f"self-test FAIL: {source} chunk[0].source.work_id empty",
                file=sys.stderr,
            )
            return 1

        # Deterministic ordering: parsing the same file twice yields the
        # same chunk_id sequence in the same order (no set/dict reorder).
        ids_a = [c.chunk_id for c in _load_chunks_from_jsonl(source)]
        ids_b = [c.chunk_id for c in _load_chunks_from_jsonl(source)]
        if ids_a != ids_b:
            print(
                f"self-test FAIL: {source} non-deterministic parse order",
                file=sys.stderr,
            )
            return 1

        print(
            f"self-test OK: {source} {len(chunks)} chunks round-trip + "
            "deterministic order verified"
        )

    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reseed the cultural Neo4j corpus deterministically "
        "from captured jsonl, or via robust resumable parallel re-scrape."
    )
    parser.add_argument(
        "--mode",
        choices=("from-jsonl", "scrape"),
        default="from-jsonl",
        help="from-jsonl (default, deterministic, no network) or scrape "
        "(live, parallel, resumable, retrying).",
    )
    parser.add_argument(
        "--source",
        default="all",
        help="'all' or comma-separated source list "
        "(validated against ingest.cultural.run.ADAPTERS).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Bounded concurrency for --mode scrape (default 5).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="--mode scrape: skip sources whose jsonl+status show a prior "
        "success, unless listed in --force.",
    )
    parser.add_argument(
        "--force",
        default="",
        help="Comma-separated sources to re-scrape even under --resume.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse/reconstruct (and scrape, if that mode) but never "
        "open Neo4j.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="No network, no Neo4j: assert jsonl round-trip fidelity and "
        "deterministic ordering, then exit.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        sources = _resolve_sources(args.source)
    except ValueError as exc:
        print(f"argument error: {exc}", file=sys.stderr)
        return 2

    if args.workers < 1:
        print("argument error: --workers must be >= 1", file=sys.stderr)
        return 2

    settings: Settings | None = None
    if not args.dry_run:
        try:
            settings = Settings()  # type: ignore[call-arg]
        except Exception as exc:  # noqa: BLE001 - env misconfig is fatal
            print(
                f"environment error: cannot load NEO4J_CULTURAL_* "
                f"Settings: {exc}",
                file=sys.stderr,
            )
            return 2

    force = {s.strip() for s in args.force.split(",") if s.strip()}
    total = len(sources)
    _log(
        f"OVERALL: starting mode={args.mode} sources={total} "
        f"dry_run={args.dry_run}"
    )

    if args.mode == "from-jsonl":
        results = _run_from_jsonl(sources, settings, args.dry_run)
    else:
        results = _run_scrape(
            sources,
            settings,
            args.dry_run,
            args.workers,
            args.resume,
            force,
        )

    failed = sorted(
        s for s, r in results.items() if r.get("error") not in (None, "")
    )
    done = sorted(
        s
        for s, r in results.items()
        if r.get("error") in (None, "") and not r.get("skipped")
    )
    skipped = sorted(s for s, r in results.items() if r.get("skipped"))

    print(json.dumps(results, indent=2, sort_keys=True), flush=True)
    ok = len(failed) == 0
    _log(
        f"OVERALL: ok={ok} sources_done={len(done) + len(skipped)}/{total} "
        f"failed={failed}"
        + (f" skipped(resume)={skipped}" if skipped else "")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
