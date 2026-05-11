"""One-shot length fixer for batch 7 evidence files.

Trims overlong lay_summary fields and adds missing denominational_landscape
to doc-inclusivism-denial. Idempotent.
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
    if not trimmed.rstrip().endswith((".", "!", "?")):
        if "." in trimmed:
            trimmed = trimmed.rsplit(".", 1)[0] + "."
    return trimmed


INCLUSIVISM_LANDSCAPE = (
    "Christian lineages disagree on whether explicit conscious faith in Christ "
    "is required for salvation, even while all of them affirm Christ as the "
    "unique Saviour. The Reformed, Baptist, classical evangelical, and "
    "Pentecostal traditions hold the strict exclusivist line: salvation "
    "requires hearing, believing, and confessing the name of Jesus, anchored "
    "in Romans 10:13-17 and Acts 4:12. The Lutheran tradition follows the same "
    "line through means-of-grace theology (Augsburg Confession Article V). "
    "The Anglican 39 Articles Article 18 explicitly anathematizes those who "
    "say every person can be saved by the religion they profess, a Reformation "
    "exclusivist statement. The Roman Catholic Church teaches inclusivism in "
    "its modern form, with the Catechism (846 to 848) affirming that those "
    "who through no fault of their own do not know the gospel may attain "
    "salvation by sincerely seeking God; Karl Rahner's anonymous-Christians "
    "framework develops this. The Eastern Orthodox Church likewise tends "
    "toward inclusivism, trusting Christ to save through ways God knows even "
    "for those who never explicitly heard his name. Wesleyan-Methodist "
    "tradition has streams that read prevenient grace as potentially reaching "
    "sincere non-Christian seekers. Among twentieth and early twenty-first "
    "century evangelicals, Clark Pinnock's later writings, John Sanders, and "
    "some Lausanne Movement voices have argued qualified inclusivism. Public "
    "carriers of strict pluralism (which is rejected universally as denying "
    "Christ's unique role) include John Hick, Paul Knitter, Unitarian "
    "Universalists, and mainline-Protestant pluralist theology. The "
    "exclusivism-vs-inclusivism debate is genuine in-house Christian "
    "disagreement and is not gospel-stake at the cult-marker level; the "
    "Christ-alone proposition is universal across all traditions."
)


def main() -> None:
    # 1) inclusivism: add missing denominational_landscape + trim reasoning
    p = EVIDENCE / "doc-inclusivism-denial.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["evidence"]["lay_summary"]["reasoning"] = trim_to_words(
        d["evidence"]["lay_summary"]["reasoning"], max_words=460
    )
    d["evidence"]["lay_summary"]["denominational_landscape"] = INCLUSIVISM_LANDSCAPE
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"inclusivism: reasoning {len(d['evidence']['lay_summary']['reasoning'].split())}w, landscape {len(INCLUSIVISM_LANDSCAPE.split())}w")

    # 2) repentance: trim denominational_landscape
    p = EVIDENCE / "doc-repentance.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    orig = d["evidence"]["lay_summary"]["denominational_landscape"]
    trimmed = trim_to_words(orig, max_words=460)
    d["evidence"]["lay_summary"]["denominational_landscape"] = trimmed
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"repentance: landscape {len(trimmed.split())}w (was {len(orig.split())}w)")

    # 3) adoption: trim reasoning
    p = EVIDENCE / "doc-adoption.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    orig = d["evidence"]["lay_summary"]["reasoning"]
    trimmed = trim_to_words(orig, max_words=460)
    d["evidence"]["lay_summary"]["reasoning"] = trimmed
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"adoption: reasoning {len(trimmed.split())}w (was {len(orig.split())}w)")


if __name__ == "__main__":
    main()
