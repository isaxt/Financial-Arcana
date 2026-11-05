"""SQLAlchemy models for The Financial Arcana.

Tables: datasets, cards, financial_metrics, card_metrics, interpretations,
spreads, readings, reading_cards.
"""
import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
         "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
         "XX", "XXI"]
RANK_LABELS = {1: "A", 11: "Pg", 12: "Kn", 13: "Q", 14: "K"}
SUIT_SYMBOLS = {"Wands": "✦", "Cups": "♥", "Swords": "†", "Pentacles": "✪"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Dataset(db.Model):
    __tablename__ = "datasets"
    dataset_id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(32), unique=True, nullable=False)  # aml, consumer, tarot...
    name = db.Column(db.String(120), nullable=False)
    source_url = db.Column(db.String(300))
    description = db.Column(db.Text)
    license = db.Column(db.String(200))
    processing_notes = db.Column(db.Text)

    metrics = db.relationship("FinancialMetric", back_populates="dataset")


class Card(db.Model):
    __tablename__ = "cards"
    card_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    arcana = db.Column(db.String(10), nullable=False)       # Major / Minor
    suit = db.Column(db.String(12))                          # NULL for Major
    number = db.Column(db.Integer, nullable=False)           # 0-21 major, 1-14 minor
    archetype = db.Column(db.String(120), nullable=False)
    traditional_meaning = db.Column(db.Text)
    upright_meaning = db.Column(db.Text)
    reversed_meaning = db.Column(db.Text)
    keywords = db.Column(db.Text)
    financial_domain = db.Column(db.String(60))
    image_path = db.Column(db.String(200))

    interpretations = db.relationship("Interpretation", back_populates="card",
                                      cascade="all, delete-orphan")
    metric_links = db.relationship("CardMetric", back_populates="card",
                                   cascade="all, delete-orphan")

    @property
    def code(self):
        return f"{self.card_id:03d}"

    @property
    def numeral(self):
        if self.arcana == "Major":
            return ROMAN[self.number]
        return RANK_LABELS.get(self.number, ROMAN[self.number])

    @property
    def symbol(self):
        return "☽" if self.arcana == "Major" else SUIT_SYMBOLS.get(self.suit, "✠")

    @property
    def keyword_list(self):
        return [k.strip() for k in (self.keywords or "").split(",") if k.strip()]


class FinancialMetric(db.Model):
    __tablename__ = "financial_metrics"
    metric_id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.dataset_id"))
    metric_name = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120))
    value = db.Column(db.Float)
    unit = db.Column(db.String(20))                          # %, count, ratio, amount
    sample_size = db.Column(db.Integer)
    calculation_date = db.Column(db.DateTime, default=utcnow)
    description = db.Column(db.Text)
    methodology = db.Column(db.Text)
    # True until the real pipeline has produced this number.
    is_demo = db.Column(db.Boolean, default=True, nullable=False)

    dataset = db.relationship("Dataset", back_populates="metrics")
    card_links = db.relationship("CardMetric", back_populates="metric",
                                 cascade="all, delete-orphan")


class CardMetric(db.Model):
    __tablename__ = "card_metrics"
    card_id = db.Column(db.Integer, db.ForeignKey("cards.card_id"), primary_key=True)
    metric_id = db.Column(db.Integer, db.ForeignKey("financial_metrics.metric_id"),
                          primary_key=True)
    relationship_label = db.Column("relationship", db.String(80))
    explanation = db.Column(db.Text)

    card = db.relationship("Card", back_populates="metric_links")
    metric = db.relationship("FinancialMetric", back_populates="card_links")


class Interpretation(db.Model):
    __tablename__ = "interpretations"
    interpretation_id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.card_id"), nullable=False)
    orientation = db.Column(db.String(10), nullable=False)   # upright / reversed
    interpretation_text = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(20), default="Mystical")

    card = db.relationship("Card", back_populates="interpretations")


class Spread(db.Model):
    __tablename__ = "spreads"
    spread_id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    card_count = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    position_labels = db.Column(db.String(300))              # "Past|Present|Future"

    @property
    def positions(self):
        return (self.position_labels or "").split("|")


class Reading(db.Model):
    __tablename__ = "readings"
    reading_id = db.Column(db.Integer, primary_key=True)
    spread_id = db.Column(db.Integer, db.ForeignKey("spreads.spread_id"))
    spread_type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    session_id = db.Column(db.String(40), index=True)         # anonymous owner

    spread = db.relationship("Spread")
    cards = db.relationship("ReadingCard", back_populates="reading",
                            order_by="ReadingCard.position",
                            cascade="all, delete-orphan")


class ReadingCard(db.Model):
    __tablename__ = "reading_cards"
    draw_id = db.Column(db.Integer, primary_key=True)
    reading_id = db.Column(db.Integer, db.ForeignKey("readings.reading_id"), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.card_id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    orientation = db.Column(db.String(10), nullable=False)
    # Frozen at draw time so old readings stay interpretable if metrics change.
    metric_snapshot = db.Column(db.Text, default="[]")
    commentary = db.Column(db.Text)
    note = db.Column(db.Text)

    reading = db.relationship("Reading", back_populates="cards")
    card = db.relationship("Card")

    @property
    def snapshot(self):
        try:
            return json.loads(self.metric_snapshot or "[]")
        except ValueError:
            return []
