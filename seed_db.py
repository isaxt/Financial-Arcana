"""Create and fill the SQLite database.

You normally never run this by hand: the app calls seed() automatically the first
time it starts, and `python3 arcana.py data` calls it again after processing the
datasets. Saved readings keep the metric snapshot they were drawn with.

    python seed_db.py            # refresh cards/metrics/spreads (keeps readings)
    python seed_db.py --reset    # drop everything first (deletes saved readings too)
"""
import argparse
import json
import os
import re
import pandas as pd

from analysis.card_content import NOTES, build_cards
from analysis.card_mapping import CARD_MAP, DATASETS, METRICS
from analysis.demo_data import DEMO_METRIC_VALUES, DEMO_SAMPLE_SIZE
from config import Config
from models import (Card, CardMetric, Dataset, FinancialMetric, Interpretation,
                    Spread, db, utcnow)

PROCESSED = Config.DATA_PROCESSED

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
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def load_metric_csvs():
    """Return {metric_name: (value, sample_size)} from data/processed/*_metrics.csv."""
    found = {}
    for fname in ("aml_metrics.csv", "consumer_metrics.csv"):
        path = os.path.join(PROCESSED, fname)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        for row in df.itertuples():
            found[row.metric_name] = (float(row.value), int(row.sample_size))
    return found


def load_tarot_overrides():
    """Optional: traditional meanings/keywords from analysis/process_tarot.py."""
    path = os.path.join(PROCESSED, "tarot_cards.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {norm(c["name"]): c for c in json.load(fh)}


def seed():
    # datasets
    ds = {}
    for key, d in DATASETS.items():
        row = Dataset.query.filter_by(key=key).first() or Dataset(key=key)
        row.name, row.source_url = d["name"], d["source_url"]
        row.description, row.license = d["description"], d["license"]
        row.processing_notes = d["notes"]
        db.session.add(row)
        ds[key] = row
    db.session.flush()

    # cards (upsert by name)
    overrides = load_tarot_overrides()
    merged = 0
    for c in build_cards():
        card = Card.query.filter_by(name=c["name"]).first() or Card(name=c["name"])
        card.arcana, card.suit, card.number = c["arcana"], c["suit"], c["number"]
        card.archetype, card.financial_domain = c["archetype"], c["domain"]
        card.traditional_meaning = c["traditional"]
        card.upright_meaning, card.reversed_meaning = c["upright"], c["reversed"]
        card.keywords = c["keywords"]
        ov = overrides.get(norm(c["name"]))
        if ov:
            if ov.get("traditional_meaning"):
                card.traditional_meaning = ov["traditional_meaning"]
            extra = [k for k in ov.get("keywords", []) if k.lower() not in c["keywords"].lower()]
            if extra:
                card.keywords = ", ".join([c["keywords"]] + extra[:3])
            merged += 1
        db.session.add(card)
    db.session.flush()

    # interpretations: rebuild
    Interpretation.query.delete()
    for card in Card.query.all():
        group = "Major" if card.arcana == "Major" else card.suit
        for orient in ("upright", "reversed"):
            db.session.add(Interpretation(
                card_id=card.card_id, orientation=orient, tone="Mystical",
                interpretation_text=NOTES[(group, orient)].format(archetype=card.archetype)))

    # spreads
    for slug, name, n, desc, pos in SPREADS:
        sp = Spread.query.filter_by(slug=slug).first() or Spread(slug=slug)
        sp.name, sp.card_count, sp.description, sp.position_labels = name, n, desc, pos
        db.session.add(sp)

    # metrics: real value if the pipeline produced one, otherwise flagged demo
    real = load_metric_csvs()
    n_real = 0
    for mname, m in METRICS.items():
        row = FinancialMetric.query.filter_by(metric_name=mname).first() or FinancialMetric(metric_name=mname)
        row.dataset_id = ds[m["dataset"]].dataset_id
        row.display_name, row.unit = m["display"], m["unit"]
        row.description, row.methodology = m["description"], m["methodology"]
        if mname in real:
            row.value, row.sample_size = real[mname]
            row.is_demo = False
            n_real += 1
        else:
            row.value, row.sample_size = DEMO_METRIC_VALUES[mname], DEMO_SAMPLE_SIZE
            row.is_demo = True
        row.calculation_date = utcnow()
        db.session.add(row)
    db.session.flush()

    # card <-> metric links: rebuild
    CardMetric.query.delete()
    for card_name, mname, rel, expl in CARD_MAP:
        card = Card.query.filter_by(name=card_name).one()
        metric = FinancialMetric.query.filter_by(metric_name=mname).one()
        db.session.add(CardMetric(card_id=card.card_id, metric_id=metric.metric_id,
                                  relationship_label=rel, explanation=expl))
    db.session.commit()
    print(f"Cards: {Card.query.count()}  Metrics: {len(METRICS)} "
          f"({n_real} real, {len(METRICS) - n_real} demo)  "
          f"Links: {len(CARD_MAP)}  Tarot-JSON merges: {merged}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop all tables first")
    args = ap.parse_args()
    from app import app
    with app.app_context():
        if args.reset:
            db.drop_all()
        db.create_all()
        seed()
