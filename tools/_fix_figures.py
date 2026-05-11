"""One-shot remap of invalid figure labels in evidence/*.json to controlled vocab.

Run from repo root: `uv run python tools/_fix_figures.py`. Idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"

REMAP = {
    "craftsman-equipment-metaphor": "metaphor",
    "lamp-light-metaphor": "metaphor",
    "paternal-metaphor": "metaphor",
    "repetition": "parallelism",
    "antiphonal-refrain": "parallelism",
    "theophany": "typology",
    "covenantal-contrast": "idiom",
}
DROP = {"allusion", "rhetorical question", "predication", "imprecation",
        "personal-address", "divine-condescension"}

EXTRA_FIGURES = {
    ("doc-divine-love", "Hos.11.1-Hos.11.4"): ["anthropomorphism"],
}


def remap_figures(figures: list[str]) -> list[str]:
    out: list[str] = []
    for f in figures:
        if f in DROP:
            continue
        out.append(REMAP.get(f, f))
    seen = set()
    result = []
    for f in out:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def main() -> None:
    for path in sorted(EVIDENCE.glob("*.json")):
        qid = path.stem
        d = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for s in d.get("evidence", {}).get("scripture", []):
            ref = s.get("ref", "")
            figs = s.get("figures") or []
            new_figs = remap_figures(figs)
            extra = EXTRA_FIGURES.get((qid, ref), [])
            for e in extra:
                if e not in new_figs:
                    new_figs.append(e)
            if new_figs != figs:
                s["figures"] = new_figs
                changed = True
        if changed:
            path.write_text(
                json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"fixed {qid}")


if __name__ == "__main__":
    main()
