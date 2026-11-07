# The Financial Arcana

A satirical financial tarot oracle (Flask · SQLite · Pandas · Jinja · Chart.js).

## Run it

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5050. The database is created and filled automatically the first time.
(Optional: use a virtual environment first: `python -m venv .venv`, then activate it.)

Out of the box the 78 cards, tarot text and the taxonomy pages work. The charts and explorers show
clearly labelled DEMO placeholders until you process the real datasets.

## Use the real datasets

1. Put the files where the table says (or skip this: AML and Transactions are also found automatically
   in your `~/.cache/kagglehub` download folder).
2. Run `python analysis/process_all.py` (add `--max-rows 1000000` for a quick trial), then restart `python app.py`.

| Dataset | Put it in | Used for |
|---|---|---|
| IBM AML (`HI-Small_Trans.csv`) | `data/raw/aml/` | Ledger charts, card metrics, The Underworld |
| Transactions Fraud (`transactions_data.csv`, `mcc_codes.json`, `train_fraud_labels.json`) | `data/raw/transactions/` | Ledger charts, card metrics |
| FrontierFinance | `data/raw/frontier_finance/` (or fetched automatically from Hugging Face) | The Library, 2 card metrics |
| Tarot JSON | `data/raw/tarot/` (included) | Traditional meanings and questions on every card |
| Divinatory Arts Taxonomy | `data/raw/divinatory_taxonomy/` (included) | The Lexicon, symbolic families, About page |

Each dataset is optional; a missing one is skipped.

## Where things are

```
app.py            routes            models.py / seed_db.py   database + loading
config.py         settings          analysis/                dataset processing + card text
templates/        Jinja pages       static/css, static/js    your visual layer
data/raw/         source files      data/processed/          small computed files the app reads
```

Start the visual work in `templates/base.html`, `static/css/style.css` and `static/js/visualizations.js`.
To reset everything, delete `instance/financial_arcana.db` and restart.

## Notes

- The tarot dataset's card images are © 1971 U.S. Games Systems and are not included. Use your own or public-domain art.
- Taxonomy and FrontierFinance are CC BY 4.0; attribution is on the About page.
- The transaction datasets are synthetic. Labels are the datasets' classifications, not proof of anything.
- The Underworld uses a sample (all flagged rows up to a cap, plus random others); its flagged share is not the real rate.
- AML amount statistics use US-dollar payments only (currencies are not converted).
