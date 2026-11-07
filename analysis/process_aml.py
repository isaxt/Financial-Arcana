"""IBM Transactions for Anti-Money Laundering (Kaggle: ealtman2019) -> data/processed/

Reads the big CSV in chunks (millions of rows), keeping only running totals plus two
small random samples, and writes:

  aml_metrics.csv            headline statistics (metric_name, value, unit, sample_size)
  aml_by_payment_format.csv  transactions and flagged share per payment format
  aml_amount_histogram.csv   log10(amount) histogram, flagged vs not (US-dollar payments)
  aml_daily.csv              transactions per day, total and flagged
  aml_transactions_sample.csv  a SAMPLE for the Underworld explorer: up to 20,000 flagged
                             rows plus 20,000 other rows, each chosen uniformly at random

Amounts are in many currencies and are not converted, so amount-based statistics use only
payments made in US dollars. Rates and counts use every row.

Expected columns: Timestamp, From Bank, Account, To Bank, Account(.1), Amount Received,
Receiving Currency, Amount Paid, Payment Currency, Payment Format, Is Laundering.
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "aml"
DEFAULT_OUT = ROOT / "data" / "processed"
REQUIRED = ["Timestamp", "From Bank", "Account", "To Bank", "Account.1", "Amount Received",
            "Receiving Currency", "Amount Paid", "Payment Currency", "Payment Format", "Is Laundering"]
RENAME = {"Timestamp": "timestamp", "From Bank": "from_bank", "Account": "from_account", "To Bank": "to_bank",
          "Account.1": "to_account", "Amount Received": "amount_received", "Receiving Currency": "receiving_currency",
          "Amount Paid": "amount_paid", "Payment Currency": "payment_currency",
          "Payment Format": "payment_format", "Is Laundering": "is_laundering"}
AMOUNT_CURRENCY = "US Dollar"
BINS = np.arange(0, 13.5, 0.5)          # log10(amount + 1)
SAMPLE_SIZE = 20_000                    # per group (flagged / not flagged)


def find_file():
    """HI-Small_Trans.csv (or another *Trans*.csv) in data/raw/aml/, else in your kagglehub download cache."""
    here = sorted(RAW_DIR.glob("*Trans*.csv"))
    if here:
        return here[0]
    cache = Path(os.environ.get("KAGGLEHUB_CACHE", Path.home() / ".cache" / "kagglehub"))
    versions = cache / "datasets" / "ealtman2019" / "ibm-transactions-for-anti-money-laundering-aml" / "versions"
    cached = sorted(versions.glob("*/HI-Small_Trans.csv"), key=lambda p: int(p.parent.name) if p.parent.name.isdigit() else 0)
    return cached[-1] if cached else None


def reservoir(kept, rows, k, rng):
    """Keep a uniform random sample of k rows across all chunks seen so far."""
    rows = rows.assign(_k=rng.random(len(rows)))
    kept = rows if kept is None else pd.concat([kept, rows])
    return kept.nsmallest(k, "_k") if len(kept) > k else kept


def run(file=None, out_dir=DEFAULT_OUT, chunksize=500_000, max_rows=None):
    file = Path(file) if file else find_file()
    out_dir = Path(out_dir)
    if file is None or not file.exists():
        sys.exit(f"No AML file found. Put HI-Small_Trans.csv in {RAW_DIR} (or download it with kagglehub).")
    header = pd.read_csv(file, nrows=0).columns.tolist()
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        sys.exit(f"{file.name}: missing columns {missing}. Found: {header}")

    rng = np.random.default_rng(42)
    total = flagged = usd_n = usd_flagged = 0
    s = ss = 0.0
    fmt_total, fmt_flag, day_total, day_flag = {}, {}, {}, {}
    flag_amounts, flag_accounts = [], set()
    hist_all = np.zeros(len(BINS) - 1, dtype=np.int64)
    hist_flag = np.zeros(len(BINS) - 1, dtype=np.int64)
    kept_flag = kept_other = None

    for i, chunk in enumerate(pd.read_csv(file, usecols=REQUIRED, chunksize=chunksize, nrows=max_rows), start=1):
        chunk = chunk.dropna(subset=["Amount Paid", "Is Laundering", "Payment Format", "Payment Currency"])
        amt = chunk["Amount Paid"].astype(float)
        lab = chunk["Is Laundering"].astype(int) == 1
        usd = chunk["Payment Currency"].eq(AMOUNT_CURRENCY)
        amt_usd, lab_usd = amt[usd], lab[usd]

        total += len(chunk)
        flagged += int(lab.sum())
        usd_n += len(amt_usd)
        usd_flagged += int(lab_usd.sum())
        s += float(amt_usd.sum())
        ss += float((amt_usd ** 2).sum())

        for fmt, g in chunk.groupby("Payment Format")["Is Laundering"]:
            fmt_total[fmt] = fmt_total.get(fmt, 0) + len(g)
            fmt_flag[fmt] = fmt_flag.get(fmt, 0) + int((g.astype(int) == 1).sum())

        day = chunk["Timestamp"].astype(str).str.slice(0, 10)
        for d, n in day.value_counts().items():
            day_total[d] = day_total.get(d, 0) + int(n)
        for d, n in day[lab].value_counts().items():
            day_flag[d] = day_flag.get(d, 0) + int(n)

        flag_amounts.append(amt_usd[lab_usd].to_numpy())
        flag_accounts.update(zip(chunk.loc[lab, "From Bank"], chunk.loc[lab, "Account"]))

        logs = np.log10(amt_usd.clip(lower=0) + 1).clip(upper=BINS[-1] - 1e-9)
        hist_all += np.histogram(logs, bins=BINS)[0]
        hist_flag += np.histogram(logs[lab_usd], bins=BINS)[0]

        kept_flag = reservoir(kept_flag, chunk[lab], SAMPLE_SIZE, rng)
        kept_other = reservoir(kept_other, chunk[~lab], SAMPLE_SIZE, rng)
        print(f"  chunk {i}: {total:,} rows so far", end="\r")
    print()

    if total == 0:
        sys.exit("No rows processed.")

    mean = s / usd_n if usd_n else np.nan
    std = float(np.sqrt(max(ss / usd_n - mean ** 2, 0.0))) if usd_n else np.nan
    flag_arr = np.concatenate(flag_amounts) if flag_amounts else np.array([])

    metrics = [
        ("aml_flagged_rate", flagged / total * 100, "%", total),
        ("aml_flagged_median_amount", float(np.median(flag_arr)) if flag_arr.size else np.nan, "USD", usd_flagged),
        ("aml_amount_cv", std / mean if usd_n and mean else np.nan, "ratio", usd_n),
        ("aml_flagged_account_count", len(flag_accounts), "count", flagged),
        ("aml_top_format_share", max(fmt_total.values()) / total * 100, "%", total),
    ]
    metrics_df = pd.DataFrame(metrics, columns=["metric_name", "value", "unit", "sample_size"]).dropna(subset=["value"])

    by_fmt = pd.DataFrame({"payment_format": list(fmt_total), "count": list(fmt_total.values()),
                           "flagged": [fmt_flag.get(k, 0) for k in fmt_total]})
    by_fmt["flagged_rate"] = by_fmt["flagged"] / by_fmt["count"] * 100
    by_fmt = by_fmt.sort_values("count", ascending=False)

    hist_df = pd.DataFrame({"bin_start": BINS[:-1], "nonflagged": hist_all - hist_flag, "flagged": hist_flag})
    daily = pd.DataFrame({"date": sorted(day_total)})
    daily["count"] = daily["date"].map(day_total)
    daily["flagged"] = daily["date"].map(day_flag).fillna(0).astype(int)

    parts = [k.drop(columns="_k") for k in (kept_flag, kept_other) if k is not None]
    sample = pd.concat(parts).rename(columns=RENAME).sort_values("timestamp")
    sample["is_laundering"] = sample["is_laundering"].astype(int)

    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(out_dir / "aml_metrics.csv", index=False)
    by_fmt.to_csv(out_dir / "aml_by_payment_format.csv", index=False)
    hist_df.to_csv(out_dir / "aml_amount_histogram.csv", index=False)
    daily.to_csv(out_dir / "aml_daily.csv", index=False)
    sample.to_csv(out_dir / "aml_transactions_sample.csv", index=False)
    print(f"  aml: {total:,} rows read ({flagged:,} flagged); explorer sample of {len(sample):,} rows")
    print(metrics_df.to_string(index=False))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=None)
    ap.add_argument("--max-rows", type=int, default=None, help="process only the first N rows")
    a = ap.parse_args()
    run(a.file, max_rows=a.max_rows)


if __name__ == "__main__":
    main()
