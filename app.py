"""The Financial Arcana: Flask application."""
import json
import os
import random
import uuid
from datetime import date, datetime

import pandas as pd
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

from analysis.demo_data import DEMO_CHARTS
from config import Config
from models import (Card, CardMetric, Dataset, FinancialMetric, Interpretation,
                    Reading, ReadingCard, Spread, db)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]

COMMENTARY = [
    "The ledger records {value} ({name}). The Order declines to say whether this is good news.",
    "{name}: {value}. The cards did not cause this. They merely noticed.",
    "Observe {value}. The Order has observed it too, and has scheduled a meeting about it.",
    "The numbers say {value}. The oracle says {orient}. Both are very confident.",
    "{value}. Capital allocation is subject to divine discretion.",
]
NO_METRIC_COMMENTARY = ("No figure in the ledger corresponds to this card. "
                        "The Order offers symbolism only, and a disclaimer.")


# ---------------------------------------------------------------- helpers
def fmt_value(value, unit):
    if value is None:
        return "n/a"
    if unit == "%":
        return f"{value:,.2f}%"
    if unit == "count":
        return f"{value:,.0f}"
    if unit == "USD":
        return f"${value:,.2f}"
    if unit == "ratio":
        return f"{value:,.2f}"
    return f"{value:,.2f}"


app.jinja_env.filters["fmt_value"] = fmt_value


@app.before_request
def ensure_session():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
        session.permanent = True


@app.context_processor
def inject_globals():
    try:
        visitors = 481 + Reading.query.count()
    except Exception:
        visitors = 481
    return dict(visitor_count=f"{visitors:07,}", this_year=date.today().year)


def metric_snapshots(card):
    """Freeze the metrics linked to a card (point-in-time copy for a reading)."""
    snaps = []
    for link in card.metric_links:
        m = link.metric
        snaps.append(dict(
            metric_name=m.metric_name, display_name=m.display_name,
            value=m.value, unit=m.unit, sample_size=m.sample_size,
            dataset=m.dataset.name if m.dataset else None,
            is_demo=bool(m.is_demo), methodology=m.methodology,
            calculated=m.calculation_date.strftime("%Y-%m-%d") if m.calculation_date else None,
            relationship=link.relationship_label, explanation=link.explanation))
    return snaps


def make_commentary(orientation, snaps):
    if not snaps:
        return NO_METRIC_COMMENTARY
    s = snaps[0]
    text = random.choice(COMMENTARY).format(
        value=fmt_value(s["value"], s["unit"]), name=s["display_name"].lower(),
        orient=orientation)
    if s["is_demo"]:
        text += " (Demo figure: the real ledger has not been processed yet.)"
    return text


def generate_reading(spread, sid):
    """Draw cards without replacement, store the reading, return it."""
    cards = Card.query.all()
    if len(cards) < spread.card_count:
        raise ValueError("Not enough cards available")
    chosen = random.sample(cards, spread.card_count)     # without replacement
    try:
        reading = Reading(spread_id=spread.spread_id, spread_type=spread.slug,
                          title=f"{spread.name}", session_id=sid)
        db.session.add(reading)
        db.session.flush()
        for pos, card in enumerate(chosen, start=1):
            orientation = random.choice(["upright", "reversed"])
            snaps = metric_snapshots(card)
            note = (Interpretation.query
                    .filter_by(card_id=card.card_id, orientation=orientation)
                    .order_by(db.func.random()).first())
            db.session.add(ReadingCard(
                reading_id=reading.reading_id, card_id=card.card_id, position=pos,
                orientation=orientation, metric_snapshot=json.dumps(snaps),
                commentary=make_commentary(orientation, snaps),
                note=note.interpretation_text if note else None))
        db.session.commit()
        return reading
    except Exception:
        db.session.rollback()
        raise


def read_chart_csv(name, demo_key):
    path = os.path.join(app.config["DATA_PROCESSED"], name)
    if os.path.exists(path):
        return pd.read_csv(path).to_dict("records"), False
    return DEMO_CHARTS[demo_key], True


# ----------------------------------------------------------------- routes
@app.route("/")
def index():
    rng = random.Random(date.today().isoformat())
    cards = Card.query.order_by(Card.card_id).all()
    omen = rng.choice(cards) if cards else None
    orientation = rng.choice(["upright", "reversed"])
    return render_template("index.html", omen=omen, orientation=orientation,
                           today=date.today().strftime("%m/%d/%Y"))


@app.route("/oracle")
def oracle():
    return render_template("oracle.html", spreads=Spread.query.order_by(Spread.spread_id).all())


@app.route("/oracle/draw", methods=["POST"])
def oracle_draw():
    slug = request.form.get("spread", "")
    spread = Spread.query.filter_by(slug=slug).first()
    if spread is None:
        flash("The Order does not recognise that spread.")
        return redirect(url_for("oracle"))
    try:
        reading = generate_reading(spread, session["sid"])
    except Exception:
        app.logger.exception("reading failed")
        flash("The oracle is under maintenance. Please try again.")
        return redirect(url_for("oracle"))
    return redirect(url_for("reading", reading_id=reading.reading_id))


@app.route("/reading/<int:reading_id>")
def reading(reading_id):
    r = db.session.get(Reading, reading_id)
    if r is None:
        abort(404)
    return render_template("reading.html", reading=r,
                           positions=r.spread.positions if r.spread else [],
                           is_owner=(r.session_id == session.get("sid")))


@app.route("/reading/<int:reading_id>/delete", methods=["POST"])
def reading_delete(reading_id):
    r = db.session.get(Reading, reading_id)
    if r is None:
        abort(404)
    if r.session_id != session.get("sid"):
        abort(403)
    db.session.delete(r)
    db.session.commit()
    flash("Reading struck from the record.")
    return redirect(url_for("history"))


@app.route("/archive")
def archive():
    q = Card.query
    text = request.args.get("q", "").strip()
    arcana = request.args.get("arcana", "")
    suit = request.args.get("suit", "")
    domain = request.args.get("domain", "")
    if arcana in ("Major", "Minor"):
        q = q.filter(Card.arcana == arcana)
    if suit in SUITS:
        q = q.filter(Card.suit == suit)
    if domain:
        q = q.filter(Card.financial_domain == domain)
    if text:
        like = f"%{text}%"
        q = q.filter(db.or_(Card.name.ilike(like), Card.archetype.ilike(like),
                            Card.keywords.ilike(like)))
    cards = q.order_by(Card.card_id).all()
    domains = [d for (d,) in db.session.query(Card.financial_domain).distinct()
               .order_by(Card.financial_domain)]
    return render_template("archive.html", cards=cards, domains=domains, suits=SUITS,
                           f=dict(q=text, arcana=arcana, suit=suit, domain=domain))


@app.route("/card/<int:card_id>")
def card_detail(card_id):
    card = db.session.get(Card, card_id)
    if card is None:
        abort(404)
    links = (CardMetric.query.filter_by(card_id=card_id).all())
    prev_card = Card.query.filter(Card.card_id < card_id).order_by(Card.card_id.desc()).first()
    next_card = Card.query.filter(Card.card_id > card_id).order_by(Card.card_id).first()
    related = (Card.query.filter(Card.financial_domain == card.financial_domain,
                                 Card.card_id != card_id)
               .order_by(Card.card_id).limit(4).all())
    notes = Interpretation.query.filter_by(card_id=card_id).all()
    return render_template("card.html", card=card, links=links, prev_card=prev_card,
                           next_card=next_card, related=related, notes=notes)


@app.route("/ledger")
def ledger():
    metrics = (FinancialMetric.query.join(Dataset)
               .order_by(Dataset.key, FinancialMetric.metric_name).all())
    groups = {}
    for m in metrics:
        groups.setdefault(m.dataset, []).append(m)
    aml_fmt, aml_demo = read_chart_csv("aml_by_payment_format.csv", "aml_by_payment_format")
    hist, hist_demo = read_chart_csv("aml_amount_histogram.csv", "aml_amount_histogram")
    cats, cat_demo = read_chart_csv("consumer_by_category.csv", "consumer_by_category")
    chart_data = dict(aml_format=aml_fmt, histogram=hist, categories=cats[:12])
    return render_template("ledger.html", groups=groups, chart_data=chart_data,
                           demo=dict(aml=aml_demo, hist=hist_demo, cat=cat_demo))


@app.route("/ledger/<metric_name>")
def ledger_metric(metric_name):
    m = FinancialMetric.query.filter_by(metric_name=metric_name).first()
    if m is None:
        abort(404)
    return render_template("metric.html", m=m)


@app.route("/underworld")
def underworld():
    return render_template("underworld.html")


@app.route("/history")
def history():
    readings = (Reading.query.filter_by(session_id=session["sid"])
                .order_by(Reading.created_at.desc()).all())
    return render_template("history.html", readings=readings)


@app.route("/about")
def about():
    return render_template("about.html", datasets=Dataset.query.order_by(Dataset.dataset_id).all())


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404,
                           message="This page has been moved, cached, or never existed."), 404


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403,
                           message="Member access: denied. This reading belongs to another member."), 403


if __name__ == "__main__":
    app.run(debug=True)
