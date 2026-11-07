"""Tarot JSON (Kaggle: lsind18/tarot-json) -> data/processed/tarot_cards.json

Reads data/raw/tarot/tarot-images.json (78 cards). For each card it keeps the
traditional meanings (light = upright, shadow = reversed), keywords, the
archetype name and the "Questions to Ask". seed_db.py merges these into the
cards table by card name. The financial interpretations stay authored by you.

The card scans in that dataset are the 1971 U.S. Games recolor (copyright), so
only the JSON is used, never the images.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "tarot"
OUT = ROOT / "data" / "processed" / "tarot_cards.json"


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def join_meanings(items, limit=3):
    """['Being open-minded', 'Taking a leap'] -> 'Being open-minded; taking a leap.'"""
    parts = [str(x).strip().rstrip(".") for x in items[:limit] if str(x).strip()]
    if not parts:
        return ""
    parts = [parts[0]] + [p[0].lower() + p[1:] for p in parts[1:]]
    return "; ".join(parts) + "."


def normalise(card):
    name = card.get("name")
    if not name:
        return None
    suit = card.get("suit")
    is_major = "major" in str(card.get("arcana", "")).lower() or str(suit).lower() == "trump"
    meanings = card.get("meanings") or {}
    return dict(
        name=str(name).strip(),
        arcana="Major" if is_major else "Minor",
        suit=None if is_major else (str(suit).title() if suit else None),
        keywords=[str(k) for k in as_list(card.get("keywords"))],
        traditional_meaning=join_meanings(as_list(meanings.get("light"))),
        traditional_reversed=join_meanings(as_list(meanings.get("shadow"))),
        tarot_archetype=card.get("Archetype"),
        questions=[str(q) for q in as_list(card.get("Questions to Ask"))],
    )


def run(file=None):
    path = Path(file) if file else next(iter(sorted(RAW_DIR.glob("*.json"))), None)
    if path is None or not path.exists():
        sys.exit(f"No tarot JSON found in {RAW_DIR}.")
    cards = json.loads(path.read_text(encoding="utf-8")).get("cards")
    if not cards:
        sys.exit(f"{path.name}: expected a top-level 'cards' list.")
    out = [c for c in (normalise(x) for x in cards) if c]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  tarot: {len(out)} cards -> {OUT.name}" + ("" if len(out) == 78 else "  (expected 78!)"))
    return len(out)


if __name__ == "__main__":
    run()
