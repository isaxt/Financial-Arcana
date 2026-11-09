# The Financial Arcana

A satirical financial tarot oracle: 78 financial tarot cards, readings, and pages built from five real datasets.
Built with Flask, SQLite, Pandas, Jinja templates and Chart.js. It is a parody of the "Order of the Financial Arcana";
nothing here is financial advice.

---

## Contents

1. [Quick start](#1-quick-start)
2. [What each step does](#2-what-each-step-does)
3. [Adding the real data](#3-adding-the-real-data)
4. [Getting each dataset](#4-getting-each-dataset)
5. [FrontierFinance via Hugging Face, step by step](#5-frontierfinance-via-hugging-face-step-by-step)
6. [The pages of the site](#6-the-pages-of-the-site)
7. [Project layout](#7-project-layout)
8. [How the data flows](#8-how-the-data-flows)
9. [Customising the look](#9-customising-the-look)
10. [Troubleshooting](#10-troubleshooting)
11. [Data notes, licences and limits](#11-data-notes-licences-and-limits)

---

## 1. Quick start

Everything below is typed into **Terminal** on a Mac (press Cmd+Space, type "Terminal", press Enter).

1. **Unzip.** Double-click `financial-arcana.zip`. Move the `financial-arcana` folder somewhere easy, such as Documents.
2. **Open Terminal in the folder.** In Terminal type `cd ` (with a space after it), drag the `financial-arcana` folder
   from Finder into the Terminal window, press Enter. Check with `ls`: you should see `app.py` and `README.md`.
3. **Install the requirements (once).**
   ```
   pip3 install -r requirements.txt
   ```
   If Terminal says `externally-managed-environment`, use a virtual environment instead:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   With a virtual environment, run `source .venv/bin/activate` again every time you open a new Terminal window.
4. **Start the site.**
   ```
   python3 app.py
   ```
   (Use `python app.py` inside a virtual environment.) Open http://127.0.0.1:5050 in your browser.
5. **Stop the site.** Click the Terminal window and press `Ctrl+C`.

On first launch the database is created and filled automatically. Before you add real data, the Ledger charts and card
statistics show placeholder numbers marked **DEMO**.

The site uses port 5050 because macOS uses port 5000 for AirPlay.

---

## 2. What each step does

The site has two kinds of information:

- **Authored content** such as the card meanings and the Order's commentary. It is built in and always works.
- **Real numbers** such as "the share of transactions that were flagged". These come from your datasets.

The datasets are far too large for a website to read on every page load, so the work is split in two:

| Step | Command | What it does |
|---|---|---|
| Process | `python3 analysis/process_all.py` | Opens the big data files, counts and averages in chunks, and saves **small summary files** into `data/processed/`. Run once, or again when the data changes. |
| Run | `python3 app.py` | Starts the website. At startup it notices new or changed files in `data/processed/` and loads them into its database (`instance/financial_arcana.db`). |

So: **processing is the slow step you do once; the website only reads the small results.**

- *"Restart the app"* means stop it with `Ctrl+C` and run `python3 app.py` again.
- *DEMO badges* mark placeholder numbers shown before real data exists. They disappear once real data is processed.
- *"skipped"* in the processing output means a dataset's file was not found. The other datasets still run.
- *Deleting `instance/financial_arcana.db`* resets the database. It rebuilds from `data/processed/` on the next start.
  Your saved readings live in that file, so deleting it clears them.

---

## 3. Adding the real data

Do these in order, in Terminal, from the project folder.

1. **Stop the app** if it is running (`Ctrl+C`).
2. **Trial run** (fast, about a minute or two). It reads only the first million rows of each big file:
   ```
   python3 analysis/process_all.py --max-rows 1000000
   ```
   You will see progress lines and a table of results for each dataset.
3. **Restart the app** and refresh the browser:
   ```
   python3 app.py
   ```
   The DEMO badges on the Ledger should be gone and the numbers real. The Underworld, Library and Lexicon should be filled.
   If the Ledger still says DEMO, read the output of step 2 for a "skipped" line.
4. **Full run (optional).** Stop the app, then:
   ```
   python3 analysis/process_all.py
   ```
   This reads every row, so it may take several minutes and a lot of memory. If it runs out of memory, use
   `--max-rows 5000000`. Restart the app afterwards.

You can also process a single dataset:

```
python3 analysis/process_aml.py
python3 analysis/process_transactions.py
python3 analysis/process_transactions.py --skip-fraud     # if memory is tight
python3 analysis/process_frontier.py
python3 analysis/process_tarot.py
python3 analysis/process_taxonomy.py
```

Each script prints what it found and what it wrote. Nothing is changed in your original data files.

---

## 4. Getting each dataset

| Dataset | Where the file goes | Used for |
|---|---|---|
| **IBM AML** (`HI-Small_Trans.csv`) | `data/raw/aml/` | Three Ledger charts, card metrics, The Underworld |
| **Transactions Fraud** (`transactions_data.csv`, `mcc_codes.json`, `train_fraud_labels.json`) | `data/raw/transactions/` | Three Ledger charts, card metrics |
| **FrontierFinance** | `data/raw/frontier_finance/` (or downloaded automatically) | The Library page, two card metrics |
| **Tarot JSON** | `data/raw/tarot/` (included) | Traditional meanings, reversed meanings and questions on every card |
| **Divinatory Arts Taxonomy** | `data/raw/divinatory_taxonomy/` (included) | The Lexicon, symbolic families on Major Arcana cards, About page |

### IBM AML and Transactions Fraud (Kaggle)

You do **not** need to copy these large files into the project if you already downloaded them with `kagglehub`.
The scripts look in your kagglehub cache automatically:

```
/Users/<you>/.cache/kagglehub/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml/versions/<n>/HI-Small_Trans.csv
/Users/<you>/.cache/kagglehub/datasets/computingvictor/transactions-fraud-datasets/versions/<n>/
```

The newest version folder is used. To find where a file is, or to check it exists:
```
ls ~/.cache/kagglehub/datasets/*/*/versions/*
```

If you have not downloaded them yet, in Terminal:
```
pip3 install kagglehub
python3 -c "import kagglehub; print(kagglehub.dataset_download('ealtman2019/ibm-transactions-for-anti-money-laundering-aml'))"
python3 -c "import kagglehub; print(kagglehub.dataset_download('computingvictor/transactions-fraud-datasets'))"
```
Each command prints the folder it saved to. Kaggle may ask for an API token; create it in your Kaggle account
settings and keep it private (never paste it into a chat or commit it to a repository).

If you would rather keep files inside the project, copy them to `data/raw/aml/` and `data/raw/transactions/`.
The project folder is checked first, then the kagglehub cache.

Other IBM AML files (for example `HI-Medium_Trans.csv`) can be used by putting them in `data/raw/aml/` (any file with
`Trans` in its name and `.csv` ending is picked up). The files are large; start with the Small one.

### Tarot JSON and the Divinatory Arts Taxonomy

Both are already in `data/raw/`, and their processed versions are already in `data/processed/`. To regenerate after
changing something, run `python3 analysis/process_tarot.py` and `python3 analysis/process_taxonomy.py`.

---

## 5. FrontierFinance via Hugging Face, step by step

The Hugging Face dataset page suggests this code:

```python
from datasets import load_dataset
ds = load_dataset("samaya-ai/FrontierFinance")
```

The project already does exactly that for you. These are the steps.

1. **Install Hugging Face's `datasets` library (once).** In Terminal, in the project folder
   (and inside your virtual environment, if you made one):
   ```
   pip3 install datasets
   ```
   This is optional. Without it the project falls back to Hugging Face's public web API and still works.
2. **Run the processor.**
   ```
   python3 analysis/process_frontier.py
   ```
   It tries these sources, in order:
   1. a file you placed in `data/raw/frontier_finance/` (`.json`, `.jsonl` or `.csv`),
   2. the `datasets` library, calling `load_dataset("samaya-ai/FrontierFinance")`,
   3. Hugging Face's public datasets-server API.

   The first run downloads the data and saves a copy as `data/raw/frontier_finance/frontierfinance.json`. Later runs use
   that copy and work offline. (To fetch it again, delete that file.)
3. **Check the output.** You should see something like `frontier: 130 queries -> frontier_queries.json, frontier_metrics.csv`.
4. **Restart the app** (`Ctrl+C`, then `python3 app.py`) and open **The Library** at http://127.0.0.1:5050/library.
   The Ledger's metric register also gains two FrontierFinance rows, which link to two cards
   (The Magician and The High Priestess).

The columns used are `query_id`, `query`, `query_date`, `use_cases` and `capabilities`.

If the download fails (no internet, or Hugging Face asks for a login), you will see a line starting
`frontier: skipped`. The rest of the site keeps working. Fallback: open the dataset page on huggingface.co, use its
**Files and versions** tab to download the data file, put it in `data/raw/frontier_finance/`, and run the processor again.

You can run all datasets together with `python3 analysis/process_all.py`; FrontierFinance is included.

---

## 6. The pages of the site

| Page | Address | What it shows |
|---|---|---|
| Portal | `/` | Home page |
| The Oracle | `/oracle` | Pick a spread and draw cards. Each reading has authored symbolic text, a calculated statistic frozen at draw time, and satirical commentary |
| The Archive | `/archive` | All 78 cards, filterable. Each card page shows traditional meanings, questions, symbolic family and linked statistics |
| The Ledger | `/ledger` | Six charts plus a register of every metric, with its sample size and DEMO flag |
| The Underworld | `/underworld` | Explorer for a sample of IBM AML transactions: filters, pagination, account connections |
| The Library | `/library` | FrontierFinance research questions, searchable by text and use case |
| The Lexicon | `/lexicon` | Vocabulary of divination from the taxonomy, searchable |
| My Readings | `/history` | Your saved readings, with favourites and delete |
| About the Order | `/about` | History, methodology, data sources and licences, ethical boundaries and trust signals |

Readings are stored per browser session, so each visitor sees their own history.

---

## 7. Project layout

```
financial-arcana/
├── app.py               The website: routes and helper functions
├── config.py            Settings (secret key, database location, data folders)
├── models.py            Database tables
├── seed_db.py           Loads cards and processed data into the database
├── requirements.txt     Python packages
├── analysis/
│   ├── process_all.py          Runs every processor below
│   ├── process_aml.py          IBM AML -> summary files + explorer sample
│   ├── process_transactions.py Consumer transactions -> summary files
│   ├── process_frontier.py     FrontierFinance -> Library data
│   ├── process_tarot.py        Tarot JSON -> card text
│   ├── process_taxonomy.py     Divinatory taxonomy -> Lexicon, families, boundaries
│   ├── card_content.py         The 78 authored card texts
│   ├── card_mapping.py         Which card is linked to which metric (and why)
│   ├── demo_data.py            Placeholder numbers shown before real data exists
│   └── inspect_dataset.py      Helper: prints the columns of a file
├── data/
│   ├── raw/                 Your source files (large files can stay in the kagglehub cache)
│   └── processed/           Small computed files the website reads
├── templates/               Jinja HTML pages (base.html is the shared frame)
├── static/
│   ├── css/style.css        All styling
│   └── js/                  visualizations.js (charts), archive.js, vendor/chart.umd.js
└── instance/                Created on first run; holds financial_arcana.db
```

---

## 8. How the data flows

```
raw datasets ──► analysis/process_*.py ──► data/processed/*.csv|json ──► seed_db.py ──► SQLite ──► Flask ──► pages
 (big)            (chunked Pandas)          (small summaries)           (auto, at start)
```

- The website never reads the big files. It reads summaries plus small samples.
- A fingerprint of `data/processed/` and the card text is stored in the database. When it changes, the database is
  refreshed on the next start. If an older database has a different structure, it is moved aside to a backup file
  rather than deleted.
- **Three layers in every reading**, kept separate on purpose:
  1. *Authored symbolic text*: fiction written for the project.
  2. *Calculated statistic*: a real number from a dataset, with its sample size, frozen when the card was drawn.
  3. *Satirical commentary*.
  The link between a card and a metric is a symbolic choice, never a finding. See `analysis/card_mapping.py`.

---

## 9. Customising the look

You can edit these without touching the data:

- `templates/base.html`: the frame shared by every page (header, navigation, footer, ticker).
- `templates/*.html`: each page. `_macros.html` holds reusable pieces such as the window boxes and card faces.
- `static/css/style.css`: colours, fonts and layout. Colours are defined once at the top as variables.
- `static/js/visualizations.js`: chart colours, types and labels for the Ledger.
- Card images: none are bundled (see below). Put your own in `static/` and reference them in `templates/_macros.html`.

While the app is running, save a file and refresh the browser to see changes. Python changes (`app.py`, etc.) need a
restart unless Flask's debug reloader is active.

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `command not found: python3` or `pip3` | Install Python from python.org, then reopen Terminal |
| `externally-managed-environment` | Use the virtual environment steps in section 1 |
| `ModuleNotFoundError: flask` (or pandas) | Run `pip3 install -r requirements.txt` (and `source .venv/bin/activate` first if you use a venv) |
| Browser cannot connect | The app must be running in Terminal. Use http://127.0.0.1:5050 (not 5000) |
| `Address already in use` | Another copy is running. Press `Ctrl+C` in the old Terminal window, or change the port at the bottom of `app.py` |
| Ledger still shows DEMO | Run `process_all.py`, check for `skipped`, then restart the app |
| `skipped: No AML file found` | Check the file exists (`ls ~/.cache/kagglehub/datasets/*/*/versions/*`) or copy it to `data/raw/aml/` |
| Processing is very slow or the Mac runs out of memory | Use `--max-rows 1000000`, or `--skip-fraud` for the transactions script |
| `frontier: skipped (...)` | No internet or Hugging Face blocked it. See the fallback in section 5 |
| Pages look stale after changing data | Stop the app, run the processor, start the app. If still wrong, delete `instance/financial_arcana.db` |
| Want to start completely fresh | Delete `instance/financial_arcana.db` and restart |

Never paste Kaggle or Hugging Face tokens into a chat, a screenshot, or a file you share.

---

## 11. Data notes, licences and limits

- **Synthetic data.** The two transaction datasets are synthetic. They are not real financial histories.
  Fraud and laundering labels are the datasets' own classifications, not proof of anything.
- **Underworld sample.** The explorer holds every flagged transaction up to a cap plus randomly chosen others. Flagged
  rows are over-represented on purpose, so the flagged share in that table is **not** the real rate. The Ledger shows the real rate.
- **Currencies.** Amounts in the AML data are in many currencies and are not converted. Amount-based statistics use
  US-dollar payments only; the Underworld's amount filters compare unlike currencies.
- **Consumer fraud rate.** Fraud labels exist for only part of the consumer transactions, so the rate is computed
  over labelled rows and the sample size shown is the labelled count.
- **Taxonomy.** *Contemporary Divinatory Arts Taxonomy* by Arianne Galfre is CC BY 4.0. Attribution appears on the About
  page and on card pages. The taxonomy uses Marseille numbering (Justice 8, Strength 11), so cards are matched to it by
  **name**, not by number. The ethical-boundary labels were translated from French by this project.
- **FrontierFinance** (samaya-ai, Hugging Face) is CC BY 4.0.
- **Tarot card images are not included.** The images in the tarot dataset are from the 1971 U.S. Games deck, which is
  copyrighted. Use your own artwork or public-domain decks.
- **Disclaimer.** Readings are random entertainment. Nothing on the site is financial advice, a prediction, or a
  fraud-detection service.
