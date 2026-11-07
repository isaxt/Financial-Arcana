"""Process the IBM AML transactions into aggregated metrics.

    python analysis/process_aml.py                      # uses data/raw/aml/HI-Small_Trans.csv
    python analysis/process_aml.py --file path/to.csv --max-rows 1000000

Reads the file in chunks (the larger variants have tens of millions of rows),
keeps only running totals, and writes to data/processed/:
    aml_metrics.csv            metric_name, value, unit, sample_size
    aml_by_payment_format.csv  payment_format, count, flagged, flagged_rate
    aml_amount_histogram.csv   bin_start (log10(amount+1)), nonflagged, flagged

You normally don't run this directly: `python3 arcana.py data` finds the file,
runs this, and loads the numbers into the site.
Expected columns: Timestamp, From Bank, Account, To Bank, Account(.1),
Amount Received, Receiving Currency, Amount Paid, Payment Currency,
Payment Format, Is Laundering. (Run inspect_dataset.py first if unsure.)
"""
import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "data" / "raw" / "aml" / "HI-Small_Trans.csv"
DEFAULT_OUT = ROOT / "data" / "processed"
REQUIRED = ["From Bank", "Account", "Amount Paid", "Payment Currency", "Payment Format", "Is Laundering"]
# Amounts are in many currencies and are not converted, so amount-based statistics
# (median, CV, histogram) use only payments made in this currency. Rates and counts use all rows.
AMOUNT_CURRENCY = "US Dollar"
BINS = np.arange(0, 13.5, 0.5)       # log10(amount + 1)


def run(file=DEFAULT_FILE, out_dir=DEFAULT_OUT, chunksize=500_000, max_rows=None):
    """Process one AML CSV and write the three summary files. Exits with a message on bad input."""
    args = SimpleNamespace(file=Path(file), out_dir=Path(out_dir), chunksize=chunksize, max_rows=max_rows)

    if not args.file.exists():
        sys.exit(f"Not found: {args.file}\nPut the Kaggle CSV in data/raw/aml/ (see README.md).")
    header = pd.read_csv(args.file, nrows=0).columns.tolist()
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        sys.exit(f"Missing columns {missing}.\nFound: {header}\nRun analysis/inspect_dataset.py and adjust REQUIRED.")

    total = flagged = 0
    usd_n = usd_flagged = 0
    s = ss = 0.0
    fmt_total, fmt_flag = {}, {}
    flag_amounts, flag_accounts = [], set()
    hist_all = np.zeros(len(BINS) - 1, dtype=np.int64)
    hist_flag = np.zeros(len(BINS) - 1, dtype=np.int64)

    reader = pd.read_csv(args.file, usecols=REQUIRED, chunksize=args.chunksize, nrows=args.max_rows)
    for i, chunk in enumerate(reader, start=1):
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

        flag_amounts.append(amt_usd[lab_usd].to_numpy())
        flag_accounts.update(zip(chunk.loc[lab, "From Bank"], chunk.loc[lab, "Account"]))

        logs = np.log10(amt_usd.clip(lower=0) + 1).clip(upper=BINS[-1] - 1e-9)
        hist_all += np.histogram(logs, bins=BINS)[0]
        hist_flag += np.histogram(logs[lab_usd], bins=BINS)[0]
        print(f"  chunk {i}: {total:,} rows so far", end="\r")
    print()

    if total == 0:
        sys.exit("No rows processed.")

    mean = s / usd_n if usd_n else np.nan
    std = float(np.sqrt(max(ss / usd_n - mean ** 2, 0.0))) if usd_n else np.nan
    flag_arr = np.concatenate(flag_amounts) if flag_amounts else np.array([])
    top_fmt = max(fmt_total.values())

    metrics = [
        ("aml_flagged_rate", flagged / total * 100, "%", total),
        ("aml_flagged_median_amount", float(np.median(flag_arr)) if flag_arr.size else np.nan, "USD", usd_flagged),
        ("aml_amount_cv", std / mean if usd_n and mean else np.nan, "ratio", usd_n),
        ("aml_flagged_account_count", len(flag_accounts), "count", flagged),
        ("aml_top_format_share", top_fmt / total * 100, "%", total),
    ]
    metrics_df = pd.DataFrame(metrics, columns=["metric_name", "value", "unit", "sample_size"]).dropna(subset=["value"])

    by_fmt = pd.DataFrame({
        "payment_format": list(fmt_total),
        "count": [fmt_total[k] for k in fmt_total],
        "flagged": [fmt_flag.get(k, 0) for k in fmt_total],
    })
    by_fmt["flagged_rate"] = by_fmt["flagged"] / by_fmt["count"] * 100
    by_fmt = by_fmt.sort_values("count", ascending=False)

    hist_df = pd.DataFrame({"bin_start": BINS[:-1], "nonflagged": hist_all - hist_flag, "flagged": hist_flag})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(args.out_dir / "aml_metrics.csv", index=False)
    by_fmt.to_csv(args.out_dir / "aml_by_payment_format.csv", index=False)
    hist_df.to_csv(args.out_dir / "aml_amount_histogram.csv", index=False)
    print(f"Processed {total:,} rows ({flagged:,} flagged). Wrote 3 files to {args.out_dir}")
    print(metrics_df.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--chunksize", type=int, default=500_000)
    ap.add_argument("--max-rows", type=int, default=None, help="process only the first N rows")
    a = ap.parse_args()
    run(a.file, a.out_dir, a.chunksize, a.max_rows)


if __name__ == "__main__":
    main()
