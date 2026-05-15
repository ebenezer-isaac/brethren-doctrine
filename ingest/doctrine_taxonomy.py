"""Doctrine taxonomy: coarse and fine slug sets, plus fine to coarse mapping.

Per architecture delta #17 from POC_FINDINGS.md.
"""

from typing import Final

# fmt: off
COARSE_SLUGS: Final[frozenset[str]] = frozenset({
    "scripture", "theology-proper", "christology", "pneumatology",
    "anthropology", "hamartiology", "soteriology", "ecclesiology",
    "sacraments", "eschatology", "ethics",
})

FINE_SLUGS: Final[frozenset[str]] = frozenset({
    "bibliology", "theology-proper", "christology", "pneumatology",
    "anthropology", "hamartiology", "soteriology", "ecclesiology",
    "sacraments", "leadership-and-polity", "church-discipline",
    "worship-structure", "inter-church-relations", "eschatology",
    "angelology", "demonology", "cult-marker", "heterodoxy-marker",
    "spiritual-gifts", "worship-style", "christian-ethics",
    "marriage-and-sexuality", "family-and-discipleship",
    "money-and-stewardship", "engagement-with-world", "calendar-and-customs",
})

FINE_TO_COARSE: Final[dict[str, str]] = {
    "bibliology": "scripture",
    "theology-proper": "theology-proper",
    "christology": "christology",
    "pneumatology": "pneumatology",
    "anthropology": "anthropology",
    "hamartiology": "hamartiology",
    "soteriology": "soteriology",
    "ecclesiology": "ecclesiology",
    "sacraments": "sacraments",
    "leadership-and-polity": "ecclesiology",
    "church-discipline": "ecclesiology",
    "worship-structure": "ecclesiology",
    "inter-church-relations": "ecclesiology",
    "eschatology": "eschatology",
    "angelology": "theology-proper",
    "demonology": "theology-proper",
    "cult-marker": "theology-proper",
    "heterodoxy-marker": "theology-proper",
    "spiritual-gifts": "pneumatology",
    "worship-style": "ecclesiology",
    "christian-ethics": "ethics",
    "marriage-and-sexuality": "ethics",
    "family-and-discipleship": "ethics",
    "money-and-stewardship": "ethics",
    "engagement-with-world": "ethics",
    "calendar-and-customs": "ethics",
}
# fmt: on

assert set(FINE_TO_COARSE.keys()) == FINE_SLUGS, "FINE_TO_COARSE must cover every FINE_SLUG"
assert set(FINE_TO_COARSE.values()) <= COARSE_SLUGS, "Every coarse must be in COARSE_SLUGS"
