"""Normalise the Kaggle Tarot JSON into data/processed/tarot_cards.json.

    python analysis/inspect_dataset.py data/raw/tarot/tarot_cards.json   # look first!
    python analysis/process_tarot.py

seed_db.py merges the result into the cards table by card name: it replaces
the built-in traditional meaning and appends a few extra keywords. The
financial interpretations (upright/reversed, archetype) stay authored by you.

Written against lsind18/tarot-json (tarot-images.json, 78 cards). The
accompanying card scans are NOT used by this project: the ones in that dataset
are the 1971 U.S. Games recolor (marked (c) 1971), not the public-domain 1909
originals. If your file looks different, adjust normalise() after inspecting it.
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


def join_meanings(items, limit=3):
    """['Being open-minded', 'Taking a leap'] -> 'Being open-minded; taking a leap.'"""
    parts = [str(x).strip().rstrip(".") for x in items[:limit] if str(x).strip()]
    if not parts:
        return ""
    parts = [parts[0]] + [p[0].lower() + p[1:] for p in parts[1:]]
    return "; ".join(parts) + "."


def normalise(card):
    """Handles the Kaggle 'tarot-images.json' layout (lsind18/tarot-json):
    cards[] with name, number, arcana ('Major Arcana'/'Minor Arcana'),
    suit ('Trump' for Major Arcana), keywords[], meanings{light[], shadow[]}.
    """
    name = card.get("name")
    if not name:
        return None
    suit = card.get("suit")
    is_major = "major" in str(card.get("arcana", "")).lower() or str(suit).lower() == "trump"
    meanings = card.get("meanings") or {}
    light = as_list(meanings.get("light")) or as_list(card.get("meaning_up"))
    shadow = as_list(meanings.get("shadow")) or as_list(card.get("meaning_rev"))
    return dict(
        name=str(name).strip(),
        arcana="Major" if is_major else "Minor",
        suit=None if is_major else (str(suit).title() if suit else None),
        keywords=[str(k) for k in as_list(card.get("keywords"))],
        traditional_meaning=join_meanings(light),
        traditional_reversed=join_meanings(shadow),
        fortune_telling=[str(x) for x in as_list(card.get("fortune_telling"))],
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
