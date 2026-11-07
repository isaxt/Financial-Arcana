"""Contemporary Divinatory Arts Taxonomy (Kaggle, CC BY 4.0) -> data/processed/taxonomy.json

Source: Arianne Galfre / Arianne G Voyance, "Contemporary Divinatory Arts Taxonomy", 2026.
Reads the four CSVs in data/raw/divinatory_taxonomy/ and keeps only English fields:

  tarot_major_arcana_symbolic_taxonomy.csv   -> symbolic family + themes for each Major card
  divinatory_terms_taxonomy.csv              -> the Lexicon page (glossary)
  digital_trust_signals_divinatory_practices -> trust signals (About page)
  ethical_boundaries_divinatory_practice.csv -> what a responsible reader refuses to divine (About page)

The boundaries file is French only, so its short domain and principle labels are
translated below (the translation is this project's, not the dataset's).
The taxonomy numbers the Major Arcana in the Marseille order (Justice 8, Strength 11),
so cards are matched by NAME, never by number.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "divinatory_taxonomy"
OUT = ROOT / "data" / "processed" / "taxonomy.json"

DOMAIN_EN = {
    "Santé": "Health", "Décès": "Death", "Mineurs": "Minors", "Justice": "Legal matters",
    "Finance": "Finance", "Dépendance consultative": "Dependence on consultations",
    "Retour affectif": "Winning an ex back", "Contrôle d’autrui": "Controlling other people",
    "Question intrusive sur un tiers": "Intrusive questions about a third party",
    "Occultisme coercitif": "Coercive occultism", "Urgence émotionnelle": "Emotional emergencies",
    "Grossesse": "Pregnancy", "Paternité": "Paternity", "Orientation professionnelle": "Career direction",
    "Addictions": "Addictions", "Violence": "Violence", "Deuil": "Bereavement",
    "Tarification": "Pricing", "Données personnelles": "Personal data",
    "IA et automatisation": "AI and automation",
}
PRINCIPLE_EN = {
    "non-substitution médicale": "no substitute for medical advice",
    "protection émotionnelle": "emotional protection",
    "protection des mineurs": "protection of minors",
    "non-substitution juridique": "no substitute for legal advice",
    "responsabilité décisionnelle": "the client stays responsible for their decisions",
    "prévention de la dépendance": "preventing dependence",
    "libre arbitre": "free will",
    "respect d’autrui": "respect for others",
    "confidentialité et respect des tiers": "confidentiality and respect for third parties",
    "non-coercition": "no coercion",
    "protection des vulnérables": "protection of vulnerable people",
    "non-substitution biologique et juridique": "no substitute for biological or legal findings",
    "non-substitution thérapeutique": "no substitute for therapy",
    "sécurité et protection": "safety and protection",
    "respect du deuil": "respect for grief",
    "transparence tarifaire": "price transparency",
    "confidentialité": "confidentiality",
    "transparence technologique": "transparency about technology",
}


def read(name):
    path = RAW / name
    if not path.exists():
        sys.exit(f"Missing {path}")
    return pd.read_csv(path).fillna("")


def run():
    major = [dict(name=r.arcana_en.strip(), family=r.symbolic_family.strip(), themes=r.main_themes_en.strip())
             for r in read("tarot_major_arcana_symbolic_taxonomy.csv").itertuples()]

    entries = []
    for r in read("divinatory_terms_taxonomy.csv").itertuples():
        entries.append(dict(kind="lexicon", category=r.category, title=r.term_en,
                            body=r.definition_en, note=r.subcategory))
    for r in read("digital_trust_signals_divinatory_practices.csv").itertuples():
        entries.append(dict(kind="trust", category=r.category, title=r.description_en,
                            body=r.verification_level, note=""))
    missing = set()
    for r in read("ethical_boundaries_divinatory_practice.csv").itertuples():
        dom, pri = r.domain.strip(), r.ethical_principle.strip()
        if dom not in DOMAIN_EN or pri not in PRINCIPLE_EN:
            missing.add(dom if dom not in DOMAIN_EN else pri)
        entries.append(dict(kind="boundary", category="", title=DOMAIN_EN.get(dom, dom),
                            body=PRINCIPLE_EN.get(pri, pri), note=""))
    if missing:
        print(f"  note: no English label for {sorted(missing)}; the French original is shown.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(major=major, entries=entries), indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {k: sum(e["kind"] == k for e in entries) for k in ("lexicon", "trust", "boundary")}
    print(f"  taxonomy: {len(major)} Major Arcana families, {counts} -> {OUT.name}")


if __name__ == "__main__":
    run()
