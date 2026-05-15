"""Shared Pydantic v2 models used by Pipeline 1 across both stores."""

from __future__ import annotations

import unicodedata
import warnings
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TRADITION_VALUES = Literal[
    "patristic",
    "catholic-magisterial",
    "eastern-orthodox",
    "oriental-orthodox",
    "lutheran",
    "reformed",
    "anglican",
    "methodist",
    "anabaptist",
    "pentecostal",
    "plymouth-brethren",
    "other",
]


class LicenseTag(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    license: str
    redistribute: bool
    license_note: str | None = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_id: str
    rel_type: str
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LexicalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_type: Literal[
        "Word",
        "Lemma",
        "Verse",
        "CrossRef",
        "Variant",
        "Person",
        "Place",
        "Event",
        "Clause",
        "Phrase",
        "Morpheme",
        "TFNode",
    ]
    id: str
    properties: dict[str, str | int | float | bool | None]
    edges: list[GraphEdge] = Field(default_factory=list)
    text_to_embed: str | None = None
    license: str
    redistribute: bool
    license_note: str | None = None


class CulturalChunkSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_id: str
    work_title: str
    author: str | None
    date_written: str
    is_confessional_text: bool
    anchor_id: str
    language: str
    translator: str | None = None


class DoctrineTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doctrine_coarse: Literal[
        "scripture",
        "theology-proper",
        "christology",
        "pneumatology",
        "anthropology",
        "hamartiology",
        "soteriology",
        "ecclesiology",
        "sacraments",
        "eschatology",
        "ethics",
    ]
    doctrine_fine: str
    stance: Literal["affirms", "denies", "qualifies", "disputed"]
    confidence: float = Field(ge=0.0, le=1.0)
    # 500-char ceiling is a sanity bound; the canonical rule per CULTURAL_SCHEMA.md
    # is the 30-word semantic cap enforced by max_thirty_words below.
    evidence_phrase: str = Field(min_length=1, max_length=500)

    @field_validator("doctrine_fine")
    @classmethod
    def fine_in_set(cls, v: str) -> str:
        from ingest.doctrine_taxonomy import FINE_SLUGS

        if v not in FINE_SLUGS:
            raise ValueError(f"doctrine_fine {v!r} not in taxonomy")
        return v

    @field_validator("evidence_phrase")
    @classmethod
    def max_thirty_words(cls, v: str) -> str:
        if len(v.split()) > 30:
            raise ValueError("evidence_phrase exceeds 30 words")
        return v


_KNOWN_DOGMATIC_WORKS = frozenset(
    {
        "ccc",
        "vatican-i",
        "vatican-ii",
        "trent",
        "nicaea-i",
        "nicaea-ii",
        "chalcedon",
        "ephesus",
        "constantinople-i",
        "constantinople-ii",
        "constantinople-iii",
    }
)


class CulturalChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    tradition: TRADITION_VALUES
    source: CulturalChunkSource
    doctrine_tags: list[DoctrineTag] = Field(default_factory=list, max_length=5)
    text: str = Field(min_length=1)
    text_to_embed: str = Field(min_length=1)
    license: str
    redistribute: bool
    license_note: str | None = None

    @field_validator("text")
    @classmethod
    def nfc_normalize(cls, v: str) -> str:
        return unicodedata.normalize("NFC", v)

    @model_validator(mode="after")
    def warn_on_non_confessional_magisterial(self) -> CulturalChunk:
        if (
            self.source.is_confessional_text is False
            and self.tradition == "catholic-magisterial"
            and self.source.work_id.lower() in _KNOWN_DOGMATIC_WORKS
        ):
            warnings.warn(
                f"CulturalChunk {self.chunk_id}: is_confessional_text=False but "
                f"tradition=catholic-magisterial and work_id={self.source.work_id!r} "
                f"is a known dogmatic source. Audit the confessional flag.",
                stacklevel=2,
            )
        return self
