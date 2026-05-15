"""Versification mapper backed by STEPBible TVTMS.

Phase 01 supports a stub mode: when the TVTMS file is missing on disk, resolve()
returns identity (input ref unchanged with rule_type=identity). Phase 02 ingests
the actual TVTMS file; full bridging activates once the file is present.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

_REF_RE = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)([a-z]?)$")


class ResolvedRef(TypedDict):
    from_scheme: str
    from_ref: str
    to_scheme: str
    to_ref: str
    rule_type: str
    block_scope: str


class VersificationMapper:
    """STEPBible TVTMS-backed reference mapper."""

    def __init__(self, tvtms_path: Path | str | None = None) -> None:
        self.tvtms_path = Path(tvtms_path) if tvtms_path is not None else None
        self._rules: list[dict[str, str]] = []
        self._stub = self.tvtms_path is None or not self.tvtms_path.exists()
        if not self._stub:
            assert self.tvtms_path is not None
            self._load(self.tvtms_path)

    @property
    def is_stub(self) -> bool:
        return self._stub

    def _load(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="strict")
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) < 5:
                continue
            rule = {
                "from_scheme": parts[0],
                "from_ref": parts[1],
                "to_scheme": parts[2],
                "to_ref": parts[3],
                "rule_type": parts[4],
                "block_scope": parts[5] if len(parts) > 5 else "",
            }
            self._rules.append(rule)

    def resolve(self, ref: str, from_scheme: str, to_scheme: str) -> ResolvedRef:
        self._validate_ref(ref)
        self._validate_scheme(from_scheme)
        self._validate_scheme(to_scheme)

        if from_scheme == to_scheme:
            return {
                "from_scheme": from_scheme,
                "from_ref": ref,
                "to_scheme": to_scheme,
                "to_ref": ref,
                "rule_type": "identity",
                "block_scope": "",
            }

        if self._stub:
            return {
                "from_scheme": from_scheme,
                "from_ref": ref,
                "to_scheme": to_scheme,
                "to_ref": ref,
                "rule_type": "identity",
                "block_scope": "stub-mode",
            }

        for rule in self._rules:
            if (
                rule["from_scheme"] == from_scheme
                and rule["to_scheme"] == to_scheme
                and rule["from_ref"] == ref
            ):
                return {
                    "from_scheme": from_scheme,
                    "from_ref": ref,
                    "to_scheme": to_scheme,
                    "to_ref": rule["to_ref"],
                    "rule_type": rule["rule_type"],
                    "block_scope": rule["block_scope"],
                }

        return {
            "from_scheme": from_scheme,
            "from_ref": ref,
            "to_scheme": to_scheme,
            "to_ref": ref,
            "rule_type": "identity",
            "block_scope": "no-rule",
        }

    def bridge_set(self, refs: list[str], from_scheme: str, to_scheme: str) -> list[ResolvedRef]:
        return [self.resolve(r, from_scheme, to_scheme) for r in refs]

    @staticmethod
    def _validate_ref(ref: str) -> None:
        if not isinstance(ref, str) or not _REF_RE.match(ref):
            raise ValueError(f"malformed ref: {ref!r}")

    @staticmethod
    def _validate_scheme(scheme: str) -> None:
        if not isinstance(scheme, str) or not scheme:
            raise ValueError(f"invalid scheme: {scheme!r}")
        allowed = {"english", "hebrew", "greek", "latin", "lxx", "kjv"}
        if scheme not in allowed:
            raise ValueError(f"unknown scheme: {scheme!r}")
