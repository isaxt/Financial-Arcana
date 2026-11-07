"""Process every dataset in one go:

    python analysis/process_all.py

Then start (or restart) the app with `python app.py`. It notices the new files and
loads them by itself. Each dataset is independent: if one is missing it is skipped
and the others still run.

    python analysis/process_all.py --max-rows 1000000    # quick trial of the two big files
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis import (process_aml, process_frontier, process_taxonomy,   # noqa: E402
                      process_tarot, process_transactions)


def attempt(label, func, *args, **kwargs):
    print(f"\n== {label}")
    try:
        func(*args, **kwargs)
    except SystemExit as stop:                    # the scripts exit with a plain-English message
        print(f"  skipped: {stop}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows", type=int, default=None, help="only read the first N rows of the two big files")
    a = ap.parse_args()
    attempt("Tarot JSON", process_tarot.run)
    attempt("Divinatory Arts Taxonomy", process_taxonomy.run)
    attempt("FrontierFinance", process_frontier.run)
    attempt("IBM AML transactions", process_aml.run, max_rows=a.max_rows)
    attempt("Consumer transactions", process_transactions.run, max_rows=a.max_rows)
    print("\nDone. Start the app with:  python app.py")


if __name__ == "__main__":
    main()
