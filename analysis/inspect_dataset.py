"""Step 1 for any new dataset: look before you process.

    python analysis/inspect_dataset.py data/raw/aml/HI-Small_Trans.csv
    python analysis/inspect_dataset.py data/raw/transactions/transactions_data.csv
    python analysis/inspect_dataset.py data/raw/transactions/mcc_codes.json
    python analysis/inspect_dataset.py data/raw/tarot/tarot_cards.json

CSV files: reads only the first --nrows rows, prints shape, columns, dtypes,
missing values, duplicates and a head() preview.
JSON files: prints the nested structure (keys, types, a sample value).
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def show_json(obj, indent=0, depth=0, max_depth=4):
    pad = "  " * indent
    if isinstance(obj, dict):
        print(f"{pad}dict with {len(obj)} keys")
        if depth >= max_depth:
            return
        for k in list(obj)[:8]:
            print(f"{pad}  [{k!r}] ->", end=" ")
            v = obj[k]
            if isinstance(v, (dict, list)):
                print()
                show_json(v, indent + 2, depth + 1, max_depth)
            else:
                print(f"{type(v).__name__}: {str(v)[:70]!r}")
        if len(obj) > 8:
            print(f"{pad}  ... {len(obj) - 8} more keys")
    elif isinstance(obj, list):
        print(f"{pad}list of {len(obj)} items")
        if obj and depth < max_depth:
            print(f"{pad}  first item:")
            show_json(obj[0], indent + 2, depth + 1, max_depth)
    else:
        print(f"{pad}{type(obj).__name__}: {str(obj)[:70]!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--nrows", type=int, default=50_000)
    args = ap.parse_args()
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Not found: {path}\nSee README.md for where each dataset goes.")

    if path.suffix.lower() == ".json":
        with open(path, encoding="utf-8") as fh:
            show_json(json.load(fh))
        return

    df = pd.read_csv(path, nrows=args.nrows)
    print(f"File: {path}  (first {len(df):,} rows)")
    print(f"\nShape: {df.shape}")
    print("\nColumns / dtypes / missing:")
    summary = pd.DataFrame({"dtype": df.dtypes.astype(str), "missing": df.isna().sum(),
                            "unique": df.nunique()})
    print(summary.to_string())
    print(f"\nDuplicate rows: {df.duplicated().sum():,}")
    print("\nHead:")
    print(df.head(5).to_string())


if __name__ == "__main__":
    main()
