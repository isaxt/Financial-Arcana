# The Financial Arcana

A satirical financial tarot oracle built with Flask, SQLite/SQLAlchemy and Pandas.
*Your wealth has already been written.*

## Quick start

```bash
pip install -r requirements.txt
python seed_db.py        # creates instance/financial_arcana.db with all 78 cards
flask --app app run --debug      # or: python app.py
```

Open http://127.0.0.1:5000. The app works immediately. Until you process the real
datasets, every statistic is a placeholder marked **DEMO** in the UI.

## Where each dataset goes

Raw downloads never go in the database. They are processed offline into small
summary files, and `seed_db.py` loads those summaries.

| Dataset | Put the downloaded file(s) in | Run | Produces (in `data/processed/`) |
|---|---|---|---|
| **IBM AML** (Kaggle) | `data/raw/aml/` e.g. `HI-Small_Trans.csv` | `python analysis/process_aml.py` | `aml_metrics.csv`, `aml_by_payment_format.csv`, `aml_amount_histogram.csv` |
| **Transactions Fraud** (Kaggle) | `data/raw/transactions/`: `transactions_data.csv`, `mcc_codes.json`, `train_fraud_labels.json` | `python analysis/process_transactions.py` | `consumer_metrics.csv`, `consumer_by_category.csv` |
| **Tarot JSON** (Kaggle) | `data/raw/tarot/` | `python analysis/process_tarot.py` | `tarot_cards.json` |
| **FrontierFinance** (Hugging Face) | `data/raw/frontier_finance/` | not used in the MVP | |
| **Divinatory Arts Taxonomy** (Kaggle) | `data/raw/divinatory_taxonomy/` | not used in the MVP | |

### Workflow for each dataset

1. **Download** it and drop the file(s) in the folder above.
2. **Inspect** it before trusting my column assumptions:
   `python analysis/inspect_dataset.py data/raw/aml/HI-Small_Trans.csv`
   If a column name differs, edit the `REQUIRED` list at the top of the matching `process_*.py`.
3. **Process** it with the script in the table. Use `--max-rows 1000000` first to test quickly.
   The scripts read in chunks, keep only running totals, and print the metrics they calculate.
4. **Load** the results: `python seed_db.py` (no `--reset` needed; saved readings are kept).
   Metrics that now have real values lose their DEMO badge.
5. Open **/ledger** to check the charts and the metric register.

Tips:
- `HI-Small_Trans.csv` (about 5M rows) is plenty for the class project. The Medium/Large variants are much bigger.
- `train_fraud_labels.json` needs a few GB of RAM. If it struggles, run with `--skip-fraud`
  (the fraud-rate metric then stays DEMO).
- Fraud labels only cover part of the consumer transactions. `sample_size` for the fraud rate is the labelled count.

## How data reaches a card

```
raw CSV/JSON -> analysis/process_*.py -> data/processed/*.csv -> seed_db.py -> SQLite -> Flask
```

- `analysis/card_mapping.py` defines every metric (description + methodology) and which card cites which
  metric (`CARD_MAP`). Edit it to change the symbolic mappings. Then re-run `python seed_db.py`.
- `analysis/card_content.py` holds the authored text for all 78 cards.
- When a reading is drawn, the linked metric values are **frozen** into `reading_cards.metric_snapshot`,
  so old readings stay interpretable after you update the data.

## Project layout

```
app.py              routes and reading generation
models.py           SQLAlchemy models (cards, metrics, card_metrics, interpretations, spreads, readings, reading_cards, datasets)
config.py           settings
seed_db.py          creates tables and loads cards / metrics / spreads
analysis/           card content, metric mapping, dataset processing scripts
data/raw/           downloaded datasets (git-ignored)
data/processed/     aggregated outputs of the analysis scripts
instance/           SQLite database (git-ignored)
templates/ static/  Jinja templates, CSS, JS
```

## What's in the MVP

Archive with search/filter and card pages, Oracle (daily, three-card, risk, five-card), upright/reversed
draws without replacement, persistent per-browser reading history with delete, Ledger with three charts and a
metric register, About page with methodology and limitations. The Underworld is a placeholder for Phase 04.
Cards currently render as CSS card faces; drop illustrations into `static/images/<suit>/` and set
`cards.image_path` (for example `images/cups/ace.png`) to show them.

## Data caveats (also shown on the About page)

The datasets are synthetic. Fraud and laundering labels are dataset classifications, not proof of
wrongdoing. Card-to-metric mappings are symbolic choices, not findings. Readings are entertainment.
