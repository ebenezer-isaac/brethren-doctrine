"""Batch 9 mechanical fixes:
1. Add missing denominational_landscape to doc-sinners-prayer-method.
2. Trim overlong reasoning + denominational_landscape on doc-christ-alone-head-of-church.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def trim_to_words(text: str, max_words: int = 460) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    trimmed = " ".join(words[:max_words])
    if not trimmed.rstrip().endswith((".", "!", "?")) and "." in trimmed:
        trimmed = trimmed.rsplit(".", 1)[0] + "."
    return trimmed


SINNERS_PRAYER_LANDSCAPE = (
    "Christian lineages divide along revivalist vs sacramental lines on this "
    "question. Pentecostal Assemblies of God, classical Methodist, Baptist, "
    "and broad evangelical traditions practice and defend the sinner's prayer "
    "as a faithful expression of repentance and faith in evangelism; Billy "
    "Graham's mid-twentieth-century crusades made the practice widespread. "
    "The Reformed-evangelical critique, voiced by Paul Washer (Shocking Youth "
    "Message 2002), Walter Chantry (Today's Gospel 1970), Paul Tripp, John "
    "MacArthur in some of his work, and A.W. Pink, holds that the prayer as a "
    "magic-formula moment severed from genuine repentance and abiding fruit "
    "fails to track the New Testament conversion pattern; their concern is "
    "the methodology, not the persons who have prayed sincerely. The Roman "
    "Catholic, Eastern Orthodox, Lutheran, and Anglican traditions are "
    "largely outside the dispute because their sacramental ecclesiology "
    "routes conversion through baptism, confirmation, and ongoing catechesis "
    "rather than through a discrete prayed moment. Carriers of the practice "
    "in the Global South include the New Apostolic Reformation, the "
    "Pentecostal-charismatic movements throughout Latin America and Africa, "
    "and the broader evangelical crusade tradition. There is no historic "
    "creed or council that names the sinner's prayer methodology one way or "
    "the other, since the form itself is a twentieth-century innovation; the "
    "biblical substance (verbalized repentance and trust in Christ) is "
    "universally affirmed."
)


def main() -> None:
    # 1) sinners-prayer-method
    p = EVIDENCE / "doc-sinners-prayer-method.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["evidence"]["lay_summary"]["denominational_landscape"] = SINNERS_PRAYER_LANDSCAPE
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"sinners-prayer: landscape={len(SINNERS_PRAYER_LANDSCAPE.split())}w")

    # 2) christ-alone-head-of-church: trim both
    p = EVIDENCE / "doc-christ-alone-head-of-church.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    lay = d["evidence"]["lay_summary"]
    for field in ("reasoning", "denominational_landscape"):
        orig = lay[field]
        new = trim_to_words(orig)
        lay[field] = new
        print(f"christ-alone-head.{field}: {len(orig.split())}w -> {len(new.split())}w")
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
