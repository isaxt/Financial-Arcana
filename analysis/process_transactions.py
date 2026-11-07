"""Process the consumer Transactions Fraud dataset into aggregated metrics.

    python analysis/process_transactions.py
    python analysis/process_transactions.py --skip-fraud          # if RAM is tight
    python analysis/process_transactions.py --max-rows 2000000

Expected files in data/raw/transactions/ (from the Kaggle download):
    transactions_data.csv     id, date, client_id, card_id, amount ("$-77.00"), ..., mcc, errors
    mcc_codes.json            {"5812": "Eating Places and Restaurants", ...}
    train_fraud_labels.json   {"target": {"<transaction id>": "Yes"/"No", ...}}   (optional)

Fraud labels exist only for part of the transactions, so fraud rate is
computed over the LABELLED rows and sample_size reflects that.
Loading the labels file needs a few GB of RAM; if memory runs out the fraud figure is skipped
(or pass --skip-fraud to omit it on purpose).

Writes to data/processed/:
    consumer_metrics.csv      metric_name, value, unit, sample_size
    consumer_by_category.csv  category, count, share_pct, labeled, fraud, fraud_rate_pct
    consumer_users_hist.csv   bucket, users  (transactions per client)
"""
import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "transactions"
DEFAULT_OUT = ROOT / "data" / "processed"
REQUIRED = ["id", "client_id", "amount", "mcc"]


def load_labels(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    target = raw.get("target", raw)
    s = pd.Series(target)
    s.index = s.index.astype("int64")
    return s


def find_folder():
    """data/raw/transactions/ if it holds the data, else your newest kagglehub download."""
    if (RAW / "transactions_data.csv").exists():
        return RAW
    cache = Path(os.environ.get("KAGGLEHUB_CACHE", Path.home() / ".cache" / "kagglehub"))
    versions = cache / "datasets" / "computingvictor" / "transactions-fraud-datasets" / "versions"
    cached = sorted((p.parent for p in versions.glob("*/transactions_data.csv")),
                    key=lambda p: int(p.name) if p.name.isdigit() else 0)
    return cached[-1] if cached else RAW


def run(file=None, mcc=None, labels=None, out_dir=DEFAULT_OUT,
        chunksize=1_000_000, max_rows=None, skip_fraud=False):
    """Process the consumer transactions and write the summary files. Exits with a message on bad input."""
    folder = find_folder()
    file = file or folder / "transactions_data.csv"
    mcc = mcc or folder / "mcc_codes.json"
    labels = labels or folder / "train_fraud_labels.json"
    args = SimpleNamespace(file=Path(file), mcc=Path(mcc), labels=Path(labels), out_dir=Path(out_dir),
                           chunksize=chunksize, max_rows=max_rows, skip_fraud=skip_fraud)

    if not args.file.exists():
        sys.exit(f"Not found: {args.file}\nPut the Kaggle files in data/raw/transactions/ (see README.md).")
    header = pd.read_csv(args.file, nrows=0).columns.tolist()
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        sys.exit(f"Missing columns {missing}.\nFound: {header}\nRun analysis/inspect_dataset.py and adjust REQUIRED.")

    labels = None
    if not args.skip_fraud and args.labels.exists():
        print("Loading fraud labels…")
        try:
            labels = load_labels(args.labels)
        except MemoryError:
            print("Not enough memory for the fraud labels; continuing without them "
                  "(the fraud-rate figure will stay a DEMO placeholder).")
    elif not args.skip_fraud:
        print(f"Note: {args.labels.name} not found; fraud metrics will be skipped.")

    mcc_names = {}
    if args.mcc.exists():
        with open(args.mcc, encoding="utf-8") as fh:
            mcc_names = {str(k): v for k, v in json.load(fh).items()}

    total = 0
    pos_n = 0
    s = ss = 0.0
    pos_amounts = []
    user_counts = pd.Series(dtype="int64")
    mcc_counts = pd.Series(dtype="int64")
    lab_by_mcc = pd.Series(dtype="int64")
    fraud_by_mcc = pd.Series(dtype="int64")
    labeled = fraud = 0

    reader = pd.read_csv(args.file, usecols=REQUIRED, chunksize=args.chunksize, nrows=args.max_rows)
    for i, chunk in enumerate(reader, start=1):
        amt = pd.to_numeric(chunk["amount"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
        chunk = chunk.assign(amt=amt).dropna(subset=["amt"])
        total += len(chunk)

        pos = chunk.loc[chunk["amt"] > 0, "amt"].astype("float64")
        pos_n += len(pos)
        s += float(pos.sum())
        ss += float((pos ** 2).sum())
        pos_amounts.append(pos.to_numpy(dtype="float32"))

        user_counts = user_counts.add(chunk["client_id"].value_counts(), fill_value=0)
        mcc_counts = mcc_counts.add(chunk["mcc"].astype(str).value_counts(), fill_value=0)

        if labels is not None:
            lab = chunk["id"].map(labels)
            has = lab.notna()
            mcc_key = chunk["mcc"].astype(str)
            labeled += int(has.sum())
            fraud += int((lab == "Yes").sum())
            lab_by_mcc = lab_by_mcc.add(mcc_key[has].value_counts(), fill_value=0)
            fraud_by_mcc = fraud_by_mcc.add(mcc_key[lab == "Yes"].value_counts(), fill_value=0)
        print(f"  chunk {i}: {total:,} rows so far", end="\r")
    print()

    if total == 0 or pos_n == 0:
        sys.exit("No usable rows processed.")

    all_pos = np.concatenate(pos_amounts)
    mean = s / pos_n
    std = float(np.sqrt(max(ss / pos_n - mean ** 2, 0.0)))

    metrics = [
        ("consumer_txns_per_user_mean", total / len(user_counts), "count", total),
        ("consumer_top_category_share", float(mcc_counts.max()) / total * 100, "%", total),
        ("consumer_median_amount", float(np.median(all_pos)), "USD", pos_n),
        ("consumer_amount_cv", std / mean if mean else np.nan, "ratio", pos_n),
    ]
    if labels is not None and labeled > 0:
        metrics.append(("consumer_fraud_rate", fraud / labeled * 100, "%", labeled))
    metrics_df = pd.DataFrame(metrics, columns=["metric_name", "value", "unit", "sample_size"]).dropna(subset=["value"])

    cat = pd.DataFrame({"mcc": mcc_counts.index, "count": mcc_counts.values.astype("int64")})
    cat["category"] = cat["mcc"].map(lambda m: mcc_names.get(m, f"MCC {m}"))
    cat["share_pct"] = cat["count"] / total * 100
    cat["labeled"] = cat["mcc"].map(lab_by_mcc).fillna(0).astype("int64")
    cat["fraud"] = cat["mcc"].map(fraud_by_mcc).fillna(0).astype("int64")
    cat["fraud_rate_pct"] = np.where(cat["labeled"] > 0, cat["fraud"] / cat["labeled"].where(cat["labeled"] > 0) * 100, np.nan)
    cat = cat.sort_values("count", ascending=False)[["category", "count", "share_pct", "labeled", "fraud", "fraud_rate_pct"]]

    # How many transactions each client made, in roughly log-spaced buckets
    counts = user_counts.to_numpy().astype("int64")
    edges = np.unique(np.round(np.geomspace(1, counts.max() + 1, 13)).astype("int64"))
    users, _ = np.histogram(counts, bins=edges)
    users_hist = pd.DataFrame({"bucket": [f"{edges[i]:,}-{edges[i + 1] - 1:,}" for i in range(len(edges) - 1)],
                               "users": users})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    users_hist.to_csv(args.out_dir / "consumer_users_hist.csv", index=False)
    metrics_df.to_csv(args.out_dir / "consumer_metrics.csv", index=False)
    cat.to_csv(args.out_dir / "consumer_by_category.csv", index=False)
    print(f"Processed {total:,} rows. Wrote 3 files to {args.out_dir}")
    print(metrics_df.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=None)
    ap.add_argument("--mcc", type=Path, default=None)
    ap.add_argument("--labels", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--chunksize", type=int, default=1_000_000)
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--skip-fraud", action="store_true")
    a = ap.parse_args()
    run(a.file, a.mcc, a.labels, a.out_dir, a.chunksize, a.max_rows, a.skip_fraud)


if __name__ == "__main__":
    main()
