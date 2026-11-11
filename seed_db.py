"""Fill the database from the authored card text and the processed dataset files.

You never run this by hand. app.py calls seed() on first start, and again whenever the
files in data/processed/ or the card text in analysis/ have changed. Saved readings are kept.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from analysis.card_content import NOTES, build_cards
from analysis.card_mapping import CARD_MAP, DATASETS, METRICS
from analysis.demo_data import DEMO_METRIC_VALUES, DEMO_SAMPLE_SIZE
from config import Config
from models import (AmlTransaction, Card, CardMetric, Dataset, FinancialMetric, Interpretation,
                    Spread, TaxonomyEntry, db, utcnow)

ROOT = Path(__file__).resolve().parent
PROCESSED = Path(Config.DATA_PROCESSED)
METRIC_FILES = ("aml_metrics.csv", "consumer_metrics.csv")
# If any of these change, the database is reloaded the next time the app starts.
WATCHED = [ROOT / "analysis" / "card_content.py", ROOT / "analysis" / "card_mapping.py",
           ROOT / "analysis" / "demo_data.py", Path(__file__).resolve()]

SPREADS = [
    ("daily", "Daily Omen", 1,
     "One card, one statistic, one remark. The Order's quickest service.",
     "The Omen"),
    ("three_card", "Past / Present / Future", 3,
     "Three cards examining a fictional financial situation through time.",
     "Past|Present|Future"),
    ("risk", "Risk / Exposure / Consequence", 3,
     "Three cards on risk and uncertainty. Please consult your financial representative.",
     "Risk|Exposure|Consequence"),
    ("five_card", "The State of Capitalism", 5,
     "Five cards on the condition of the system as a whole.",
     "The Foundation|The Pressure|The Hidden Hand|The Crowd|The Reckoning"),
]


def norm(name):
    return re.sub(r"[^a-z0-9 ]", "", str(name).lower()).strip()


def data_signature():
    """A fingerprint of every input file; it changes when you re-process data or edit card text."""
    parts = []
    for p in sorted(PROCESSED.glob("*")) + WATCHED:
        if p.is_file() and p.name != ".gitkeep":
            st = p.stat()
            parts.append(f"{p.name}:{st.st_size}:{int(st.st_mtime)}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def read_json(name):
    path = PROCESSED / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_metric_csvs():
    """{metric_name: (value, sample_size, file_modified)} from the processed *_metrics.csv files."""
    found = {}
    for fname in METRIC_FILES:
        path = PROCESSED / fname
        if path.exists():
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            for row in pd.read_csv(path).itertuples():
                found[row.metric_name] = (float(row.value), int(row.sample_size), modified)
    return found


def bulk_insert(model, records):
    for i in range(0, len(records), 5000):
        db.session.bulk_insert_mappings(model, records[i:i + 5000])


def load_aml_sample():
    AmlTransaction.query.delete()
    path = PROCESSED / "aml_transactions_sample.csv"
    if not path.exists():
        return 0
    df = pd.read_csv(path, dtype={"from_account": str, "to_account": str}).dropna(subset=["amount_paid"])
    df["is_laundering"] = df["is_laundering"].astype(int).astype(bool)
    records = df.where(df.notna(), None).to_dict("records")
    bulk_insert(AmlTransaction, records)
    return len(records)


def load_taxonomy_entries():
    TaxonomyEntry.query.delete()
    data = read_json("taxonomy.json") or {"entries": []}
    bulk_insert(TaxonomyEntry, data["entries"])
    return len(data["entries"])


def seed():
    ds = {}
    for key, d in DATASETS.items():
        row = Dataset.query.filter_by(key=key).first() or Dataset(key=key)
        row.name, row.source_url = d["name"], d["source_url"]
        row.description, row.license = d["description"], d["license"]
        row.processing_notes = d["notes"]
        db.session.add(row)
        ds[key] = row
    db.session.flush()

    # cards: authored text, plus the Tarot JSON and the taxonomy matched by NAME
    tarot = {norm(c["name"]): c for c in (read_json("tarot_cards.json") or [])}
    families = {norm(m["name"]): m for m in (read_json("taxonomy.json") or {"major": []})["major"]}
    n_tarot = n_family = 0
    for c in build_cards():
        card = Card.query.filter_by(name=c["name"]).first() or Card(name=c["name"])
        card.arcana, card.suit, card.number = c["arcana"], c["suit"], c["number"]
        card.archetype, card.financial_domain = c["archetype"], c["domain"]
        card.traditional_meaning = c["traditional"]
        card.upright_meaning, card.reversed_meaning = c["upright"], c["reversed"]
        card.keywords = c["keywords"]
        card.traditional_reversed = card.questions = card.tarot_archetype = None
        t = tarot.get(norm(c["name"]))
        if t:
            n_tarot += 1
            card.traditional_meaning = t.get("traditional_meaning") or card.traditional_meaning
            card.traditional_reversed = t.get("traditional_reversed") or None
            card.questions = "\n".join(t.get("questions") or []) or None
            card.tarot_archetype = t.get("tarot_archetype")
            extra = [k for k in t.get("keywords", []) if k.lower() not in c["keywords"].lower()]
            if extra:
                card.keywords = ", ".join([c["keywords"]] + extra[:3])
        f = families.get(norm(c["name"])) if c["arcana"] == "Major" else None
        card.symbolic_family = f["family"] if f else None
        card.symbolic_themes = f["themes"] if f else None
        n_family += bool(f)
        db.session.add(card)
    db.session.flush()

    Interpretation.query.delete()
    for card in Card.query.all():
        group = "Major" if card.arcana == "Major" else card.suit
        for orient in ("upright", "reversed"):
            db.session.add(Interpretation(
                card_id=card.card_id, orientation=orient, tone="Mystical",
                interpretation_text=NOTES[(group, orient)].format(archetype=card.archetype)))

    for slug, name, n, desc, pos in SPREADS:
        sp = Spread.query.filter_by(slug=slug).first() or Spread(slug=slug)
        sp.name, sp.card_count, sp.description, sp.position_labels = name, n, desc, pos
        db.session.add(sp)

    # metrics: a real value if a pipeline produced one, otherwise a flagged DEMO placeholder
    real = load_metric_csvs()
    for mname, m in METRICS.items():
        row = FinancialMetric.query.filter_by(metric_name=mname).first() or FinancialMetric(metric_name=mname)
        row.dataset_id = ds[m["dataset"]].dataset_id
        row.display_name, row.unit = m["display"], m["unit"]
        row.description, row.methodology = m["description"], m["methodology"]
        if mname in real:
            row.value, row.sample_size, row.calculation_date = real[mname]
            row.is_demo = False
        else:
            row.value, row.sample_size = DEMO_METRIC_VALUES[mname], DEMO_SAMPLE_SIZE
            row.is_demo = True
            row.calculation_date = row.calculation_date or utcnow()
        db.session.add(row)
    db.session.flush()

    CardMetric.query.delete()
    for card_name, mname, rel, expl in CARD_MAP:
        card = Card.query.filter_by(name=card_name).one()
        metric = FinancialMetric.query.filter_by(metric_name=mname).one()
        db.session.add(CardMetric(card_id=card.card_id, metric_id=metric.metric_id,
                                  relationship_label=rel, explanation=expl))

    n_aml, n_tax = load_aml_sample(), load_taxonomy_entries()
    db.session.commit()
    print(f"Database loaded: {Card.query.count()} cards ({n_tarot} with Tarot JSON, {n_family} with taxonomy) | "
          f"{len(real)}/{len(METRICS)} real metrics | {n_aml:,} AML sample rows | "
          f"{n_tax} taxonomy entries")
