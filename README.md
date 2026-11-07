# The Financial Arcana

A satirical financial tarot oracle (Flask, SQLite, Pandas). *Your wealth has already been written.*

## Run it

```
python3 arcana.py
```

(Windows: `python arcana.py`.) Or double-click **Start.command** (Mac) / **Start.bat** (Windows).

The first run sets everything up by itself: a private Python environment, the packages, and the
database with all 78 cards. Then your browser opens on the site. There is nothing else to do.
Press Ctrl+C in the window to stop it.

## Load the real data (optional, one command)

```
python3 arcana.py data
```

Or double-click **Get Real Data.command** / **Get Real Data.bat**. It finds the IBM AML and
Transactions Fraud files (in `data/raw/`, in your kagglehub cache, or by downloading them from
Kaggle), calculates the statistics, and refreshes the site. Until you run it, every statistic
is a placeholder marked **DEMO**.

- Trial run in a couple of minutes: `python3 arcana.py data --quick`
- Out of memory on the fraud labels: add `--skip-fraud`
- Downloading needs a free Kaggle token. If it isn't set up, the command tells you exactly what to do.
- Files not found automatically: `--aml-file path/to/HI-Small_Trans.csv --tx-dir path/to/folder`

If double-clicking a `.command` file is blocked on a Mac, right-click it and choose Open once,
or just use `python3 arcana.py` in Terminal.

## Other commands

`python3 arcana.py reset` rebuilds the database from scratch (deletes saved readings).

## Where things live

```
arcana.py            the one command (setup, start, data, reset)
app.py  models.py    the website and its database tables
seed_db.py           loads cards/metrics into the database (the app does this for you)
analysis/            card text, the card-to-metric mapping, and the Pandas processing scripts
data/raw/            optional: put downloaded datasets here instead of using the cache
data/processed/      the small summary files the processing scripts produce
templates/ static/   pages, styling, charts (Chart.js is bundled, so it works offline)
```

The Tarot JSON is already processed and built in. The Divinatory Arts Taxonomy and
FrontierFinance are supporting material and are not used yet.

## How data reaches a card

`raw datasets -> analysis/process_*.py -> data/processed/*.csv -> seed_db.py -> SQLite -> website`

`analysis/card_mapping.py` defines every metric and which card cites which one (a symbolic choice,
not a finding). `analysis/card_content.py` holds the authored text for all 78 cards. When a reading is
drawn, the metric values are frozen into it, so old readings stay readable after you update the data.

## Card images: rights warning

The card scans bundled with the Kaggle tarot dataset are the **1971 U.S. Games recolor** (marked
"(c) 1971 U.S. Games"), which is still under copyright, so they are not included. Use your own
illustrations or verified public-domain 1909 scans, and set `cards.image_path` (relative to `static/`).

## Data caveats

The datasets are synthetic. Fraud and laundering labels are dataset classifications, not proof of
wrongdoing. Card-to-metric mappings are symbolic. Readings are entertainment.
