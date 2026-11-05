"""Normalise the Kaggle Tarot JSON into data/processed/tarot_cards.json.

    python analysis/inspect_dataset.py data/raw/tarot/tarot_cards.json   # look first!
    python analysis/process_tarot.py

seed_db.py merges the result into the cards table by card name: it replaces
the built-in traditional meaning and appends a few extra keywords. The
financial interpretations (upright/reversed, archetype) stay authored by you.

The Kaggle file's exact layout varies, so normalise() is defensive: it looks
for a list of card objects anywhere in the JSON and tries common key names.
If your file looks different, adjust normalise() after inspecting it.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "tarot"
OUT = ROOT / "data" / "processed" / "tarot_cards.json"


def find_card_list(obj):
    """Return the first list of dicts found in the JSON."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = find_card_list(v)
            if found:
                return found
    return None


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def normalise(card):
    suit = card.get("suit")
    rank = card.get("rank") or card.get("value") or card.get("number")
    name = card.get("name")
    if not name and suit and rank:
        name = f"{str(rank).title()} of {str(suit).title()}"
    if not name:
        return None
    meanings = card.get("meanings") or {}
    light = as_list(meanings.get("light")) or as_list(card.get("meaning_up"))
    shadow = as_list(meanings.get("shadow")) or as_list(card.get("meaning_rev"))
    return dict(
        name=str(name).strip(),
        arcana=(card.get("arcana") or ("Minor" if suit else "Major")),
        suit=str(suit).title() if suit else None,
        keywords=[str(k) for k in as_list(card.get("keywords"))],
        traditional_meaning=" ".join(str(x) for x in light[:2]),
        traditional_reversed=" ".join(str(x) for x in shadow[:2]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=None)
    args = ap.parse_args()
    path = args.file
    if path is None:
        candidates = sorted(RAW_DIR.glob("*.json"))
        if not candidates:
            sys.exit(f"No JSON found in {RAW_DIR}. Put the Kaggle tarot file there (see README.md).")
        path = candidates[0]
    with open(path, encoding="utf-8") as fh:
        cards = find_card_list(json.load(fh))
    if not cards:
        sys.exit("Could not find a list of card objects. Run inspect_dataset.py and adjust normalise().")
    out = [c for c in (normalise(x) for x in cards) if c]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"Normalised {len(out)} cards from {path.name} -> {OUT}")
    if len(out) != 78:
        print(f"Warning: expected 78 cards, got {len(out)}. Check the source file.")


if __name__ == "__main__":
    main()
