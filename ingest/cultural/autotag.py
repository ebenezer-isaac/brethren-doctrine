"""Autotag dispatcher for Pipeline 1 cultural (Phase 03).

Bridges the Python adapter chunks to the `cultural_autotag` Sonnet subagent
dispatched by the orchestrator. The dispatcher is testable: a `tag_batch_fn`
callable can be injected in tests to substitute a deterministic mock.

Confidence-routing:
  - Tags with confidence < 0.6 are written to tmp/cultural_autotag/<task_id>/
    low_confidence.jsonl and NOT persisted to the cultural store.
  - Tags with confidence >= 0.6 are persisted.

Batch payload integrity: the dispatcher's payload to the subagent contains
ONLY chunk_id and text keys per chunk. Other metadata (work_title, tradition,
author, anchor_id) is stripped so the subagent reasons from text only.
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from pathlib import Path

from ingest.models import CulturalChunk, DoctrineTag

BATCH_SIZE = 50
CONFIDENCE_THRESHOLD = 0.6
ALLOWED_PAYLOAD_KEYS = frozenset({"chunk_id", "text"})
ANTI_CANNED_EVIDENCE = "Great art Thou, O Lord, and greatly to be praised"


TagBatchFn = Callable[[list[dict[str, str]]], list[list[DoctrineTag]]]


def _batches(items: list[CulturalChunk], size: int) -> list[list[CulturalChunk]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _build_payload(chunks: list[CulturalChunk]) -> list[dict[str, str]]:
    return [{"chunk_id": c.chunk_id, "text": c.text} for c in chunks]


def _flag_canned(tags: list[DoctrineTag]) -> None:
    for tag in tags:
        if tag.evidence_phrase.strip() == ANTI_CANNED_EVIDENCE:
            warnings.warn(
                f"anti-canned-output: tag evidence matches prompt example phrase "
                f"({tag.evidence_phrase!r}); review subagent output",
                stacklevel=2,
            )


def tag_chunks(
    chunks: list[CulturalChunk],
    tag_batch_fn: TagBatchFn,
    low_confidence_dir: Path | None = None,
) -> tuple[list[CulturalChunk], list[CulturalChunk]]:
    """Run autotag over chunks. Returns (high_confidence_tagged, low_confidence_dropped).

    `tag_batch_fn` receives a list[dict] payload (chunk_id+text only) and returns
    a parallel list of tag-lists (one tag-list per input chunk).
    """
    high: list[CulturalChunk] = []
    low: list[CulturalChunk] = []
    low_records: list[dict[str, object]] = []

    for batch in _batches(chunks, BATCH_SIZE):
        payload = _build_payload(batch)
        for row in payload:
            extras = set(row.keys()) - ALLOWED_PAYLOAD_KEYS
            if extras:
                raise ValueError(f"payload contains forbidden keys: {extras}")
        tag_lists = tag_batch_fn(payload)
        if len(tag_lists) != len(batch):
            raise ValueError(
                f"tag_batch_fn returned {len(tag_lists)} tag-lists for {len(batch)} chunks"
            )
        for chunk, tags in zip(batch, tag_lists, strict=True):
            if len(tags) > 5:
                raise ValueError(
                    f"chunk {chunk.chunk_id}: subagent returned {len(tags)} tags "
                    f"(max 5 allowed)"
                )
            _flag_canned(tags)
            keep_tags = [t for t in tags if t.confidence >= CONFIDENCE_THRESHOLD]
            drop_tags = [t for t in tags if t.confidence < CONFIDENCE_THRESHOLD]
            if keep_tags:
                tagged = chunk.model_copy(update={"doctrine_tags": keep_tags})
                high.append(tagged)
            if drop_tags:
                low.append(chunk)
                low_records.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "dropped_tags": [t.model_dump() for t in drop_tags],
                    }
                )

    if low_confidence_dir is not None and low_records:
        low_confidence_dir.mkdir(parents=True, exist_ok=True)
        out_path = low_confidence_dir / "low_confidence.jsonl"
        with out_path.open("w", encoding="utf-8") as fh:
            for rec in low_records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return high, low
