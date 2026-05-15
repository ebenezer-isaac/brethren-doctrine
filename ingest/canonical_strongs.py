"""Canonical Strong's normalization across the five source encodings.

Per docs/INGESTION_PATTERNS.md "Canonical Strong's normalization": leading letter
(H or G), zero-padded to 4 digits, optional suffix letter (Strong's extension
disambiguation) appended to the canonical AND returned separately as the
second tuple element.
"""

import re
from typing import Literal

Lang = Literal["hb", "gk"]

_RE_PREFIXED = re.compile(r"^([HhGg])(\d{1,5})([A-Za-z])?$")
_RE_NUM_SPACE_LETTER = re.compile(r"^(\d{1,5})\s+([A-Za-z])$")
_RE_NUM_LETTER = re.compile(r"^(\d{1,5})([A-Za-z])$")
_RE_NUM = re.compile(r"^(\d{1,5})$")


def canonical_strongs(raw: str, lang: Lang | None = None) -> tuple[str, str | None]:
    """Normalize a Strong's reference. Returns (canonical_string, suffix_or_None).

    Ambiguous plain digits (no H or G prefix, no lang hint) raise ValueError.
    """
    if not isinstance(raw, str):
        raise ValueError(f"raw must be str, got {type(raw).__name__}")
    s = raw.strip()
    if not s:
        raise ValueError("empty input")

    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
        if not s:
            raise ValueError(f"empty curly-brace content: {raw!r}")

    if "/" in s:
        parts = s.split("/", 1)
        if len(parts[1]) > 0:
            s = parts[1]

    m = _RE_PREFIXED.match(s)
    if m:
        prefix = m.group(1).upper()
        digits = m.group(2)
        suffix_letter = m.group(3)
        suffix = suffix_letter.upper() if suffix_letter else None
        canonical = f"{prefix}{digits.zfill(4)}{suffix or ''}"
        return canonical, suffix

    m = _RE_NUM_SPACE_LETTER.match(s)
    if m:
        digits, suffix = m.group(1), m.group(2).upper()
        prefix = _prefix_from_lang(lang)
        if prefix is None:
            raise ValueError(f"ambiguous {raw!r}: provide lang='hb' or lang='gk'")
        return f"{prefix}{digits.zfill(4)}{suffix}", suffix

    m = _RE_NUM_LETTER.match(s)
    if m:
        digits, suffix = m.group(1), m.group(2).upper()
        prefix = _prefix_from_lang(lang)
        if prefix is None:
            raise ValueError(f"ambiguous {raw!r}: provide lang='hb' or lang='gk'")
        return f"{prefix}{digits.zfill(4)}{suffix}", suffix

    m = _RE_NUM.match(s)
    if m:
        digits = m.group(1)
        prefix = _prefix_from_lang(lang)
        if prefix is None:
            raise ValueError(f"ambiguous {raw!r}: provide lang='hb' or lang='gk'")
        return f"{prefix}{digits.zfill(4)}", None

    raise ValueError(f"unrecognized Strong's encoding: {raw!r}")


def _prefix_from_lang(lang: Lang | None) -> str | None:
    if lang == "hb":
        return "H"
    if lang == "gk":
        return "G"
    return None
