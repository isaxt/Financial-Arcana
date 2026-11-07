"""Find (or download) the two big datasets, process them, and refresh the database.

Run it with:  python3 arcana.py data

For each dataset it looks, in this order, in:
  1. data/raw/<dataset>/        (if you placed the files there yourself)
  2. your kagglehub cache       (~/.cache/kagglehub, where an earlier download landed)
  3. Kaggle itself              (downloads once; needs a free Kaggle API token)
Nothing is copied: files are processed where they are found.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

AML_HANDLE = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
AML_FILE = "HI-Small_Trans.csv"
TX_HANDLE = "computingvictor/transactions-fraud-datasets"

KAGGLE_HELP = """
Could not download from Kaggle:
  {err}

Most likely you need a free Kaggle API token:
  1. Sign in at kaggle.com, open your profile picture > Settings > API > "Create New Token".
  2. Move the file that downloads (kaggle.json) into the hidden folder
       Mac/Linux:  ~/.kaggle/kaggle.json
       Windows:    C:\\Users\\<you>\\.kaggle\\kaggle.json
  3. Run this command again.

Or download the files by hand from the dataset pages and put them in
  data/raw/aml/            HI-Small_Trans.csv
  data/raw/transactions/   transactions_data.csv, mcc_codes.json, train_fraud_labels.json
"""


def kaggle_cache():
    return Path(os.environ.get("KAGGLEHUB_CACHE", Path.home() / ".cache" / "kagglehub"))


def cached_dir(handle):
    """Newest downloaded version folder of a Kaggle dataset in the kagglehub cache, or None."""
    base = kaggle_cache() / "datasets" / handle / "versions"
    if not base.is_dir():
        return None
    versions = sorted((p for p in base.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))
    return versions[-1] if versions else None


def kaggle_download(handle, filename=None):
    try:
        import kagglehub
    except ImportError:
        print("Installing kagglehub ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "kagglehub"])
        import kagglehub
    print(f"Downloading {handle} from Kaggle (one time only; this can take a few minutes) ...")
    try:
        path = kagglehub.dataset_download(handle, path=filename) if filename else kagglehub.dataset_download(handle)
    except Exception as err:                      # auth, network, dataset moved ...
        raise SystemExit(KAGGLE_HELP.format(err=err))
    return Path(path)


def find_aml(explicit=None):
    if explicit:
        return Path(explicit)
    mine = RAW / "aml" / AML_FILE
    if mine.exists():
        return mine
    cached = cached_dir(AML_HANDLE)
    if cached and (cached / AML_FILE).exists():
        return cached / AML_FILE
    return kaggle_download(AML_HANDLE, AML_FILE)       # only the one file, not the 8 GB bundle


def find_transactions(explicit=None):
    candidates = [Path(explicit)] if explicit else [RAW / "transactions", cached_dir(TX_HANDLE)]
    for folder in candidates:
        if folder and (folder / "transactions_data.csv").exists():
            return folder
    return kaggle_download(TX_HANDLE)


def run(aml_file=None, tx_dir=None, quick=False, skip_fraud=False):
    from analysis import process_aml, process_transactions
    max_rows = 1_000_000 if quick else None
    start = time.time()
    if quick:
        print("Quick mode: using only the first 1,000,000 rows of each file.")

    print("\n[1/3] IBM AML transactions")
    aml = find_aml(aml_file)
    print(f"  using {aml}")
    process_aml.run(aml, max_rows=max_rows)

    print("\n[2/3] Consumer transactions")
    folder = find_transactions(tx_dir)
    print(f"  using {folder}")
    process_transactions.run(folder / "transactions_data.csv", folder / "mcc_codes.json",
                             folder / "train_fraud_labels.json", max_rows=max_rows, skip_fraud=skip_fraud)

    print("\n[3/3] Loading the results into the site")
    from app import app
    from seed_db import seed
    with app.app_context():
        seed()

    print(f"\nDone in {time.time() - start:.0f} seconds. Start the site with:  python3 arcana.py")
    print("The DEMO badges are gone wherever real numbers were calculated.")
