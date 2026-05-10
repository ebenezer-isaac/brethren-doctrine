"""Pydantic GraphRecord types — every record carries authority_level explicitly.

Per docs/TIER_2_SPEC.md §4.f, authority is stamped at the adapter boundary.
No defaults, no inference downstream. Records are the wire format between
adapters and `ingest/upsert.py`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


SourceType = Literal["sermon", "sof", "bible", "interlinear", "lexicon", "archaeology", "history", "external"]
ChunkType = Literal[
    "definition", "teaching", "quote", "perspective", "application",
    "illustration", "exegesis", "exhortation", "warning", "summary", "narrative", "other",
]


class ChunkRecord(_Strict):
    """A SermonChunk or SOFChunk row — covers both because the parsed shape is identical."""

    chunk_id: str
    source_doc: str
    source_type: SourceType
    text: str
    chunk_type: ChunkType
    section: str | None = None
    themes: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    scripture_refs: list[str] = Field(default_factory=list)
    perspectives_within_chunk: list[dict] = Field(default_factory=list)
    cross_references: list[str] = Field(default_factory=list)
    authority_level: int = Field(ge=0, le=4)
