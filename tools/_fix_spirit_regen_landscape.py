import json
from pathlib import Path

p = Path("evidence/doc-spirit-regeneration.json")
d = json.loads(p.read_text(encoding="utf-8"))

new = (
    "Every historic Christian lineage affirms that the Holy Spirit is the agent of "
    "regeneration. The substantive disagreement is on WHEN and HOW the Spirit regenerates, "
    "and it is the heart of the paedobaptist-vs-credobaptist divide. The Roman Catholic "
    "Catechism (paragraph 1213) teaches baptismal regeneration: baptism is the sacrament "
    "of regeneration through water in the word, freeing from sin and rebirthing as sons "
    "of God. Eastern Orthodoxy holds the same shape, treating baptism as new birth by "
    "water and the Holy Spirit. Classical Lutheran teaching (Augsburg IX) and high-church "
    "Anglican teaching (39 Articles 27) similarly tie regeneration to baptism, though the "
    "Anglican tradition has internally debated this since the Gorham case of 1850. Reformed "
    "and Baptist traditions distinguish the Spirit's inward regenerating work from the "
    "outward baptismal sign: the Westminster Confession teaches that regeneration is the "
    "sovereign work of the Spirit applying the gospel; Baptists and most evangelicals hold "
    "that regeneration occurs at conversion when the Spirit applies the word to the heart, "
    "and that water baptism follows as a public testimony. Methodist, Pentecostal and "
    "Anabaptist traditions also locate regeneration at the new birth in conversion. The "
    "agreement across lineages is that the Spirit alone regenerates. The disagreement is "
    "on the means and timing of that work. Public-record carriers of denial that the "
    "Spirit regenerates at all are rare. Religious traditions that deny the very category "
    "of new birth (some forms of liberal-mainline reductionism that treat conversion as "
    "merely psychological) collapse the doctrine, but most contemporary Christians inside "
    "any of the named lineages affirm Spirit-wrought regeneration as the core doctrine."
)
d["evidence"]["lay_summary"]["denominational_landscape"] = new
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"patched len={len(new)} words={len(new.split())}")
