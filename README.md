# The Financial Arcana

A satirical tarot website for financial data. It draws from a deck of 78 financial tarot cards, and every reading pairs
a card with a real statistic calculated from transaction data.

Built with Flask, SQLite, Pandas and Jinja templates. It is a parody. Nothing on it is financial advice.

**Three files to know:**

| File | What it is |
|---|---|
| `README.md` | This file. How to run the project. |
| `ANALYSIS.md` | A walkthrough of the data-analysis code, for when you want to read it line by line. |
| `app.py` | The website itself. |

---

## Part 1 · Run the website

Everything is typed into **Terminal** (press Cmd+Space, type "Terminal", press Enter).

### Step 1 — Open the project folder in Terminal

Type `cd` followed by a space, then drag the `financial-arcana` folder from Finder into the Terminal window and press
Enter. Check you are in the right place:

```
ls
```

You should see `app.py` and `README.md` listed.

### Step 2 — Install the two packages it needs (once)

```
pip3 install -r requirements.txt
```

If Terminal replies `externally-managed-environment`, your Mac wants the packages kept in a project folder instead.
Do this instead, once:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After that, run `source .venv/bin/activate` each time you open a new Terminal window for this project.

### Step 3 — Start it

```
python3 app.py
```

Then open **http://127.0.0.1:5050** in your browser.

> Port 5050, not the usual 5000, because macOS uses 5000 for AirPlay.

### Step 4 — Stop it

Click the Terminal window and press `Ctrl+C`.

**That's the whole website.** The database builds itself the first time. Every page works right away.

The only thing missing is real numbers: until you do Part 2, the charts and statistics show invented placeholders
marked **DEMO**.

---

## Part 2 · Add the real data

Think of it as two separate jobs:

```
   ONE TIME, SLOW                           EVERY TIME, FAST
   python3 analysis/process_all.py          python3 app.py
   reads your huge data files        →      reads the small summaries
   writes small summaries                   shows the website
```

The website never opens the huge files. That is why it stays fast. You only redo the slow job when your data changes.

### Step 1 — Put the data where it can be found

| Dataset | Where it goes |
|---|---|
| IBM AML (`HI-Small_Trans.csv`) | `data/raw/aml/` |
| Transactions Fraud (`transactions_data.csv`, `mcc_codes.json`, `train_fraud_labels.json`) | `data/raw/transactions/` |

**If you already downloaded these with kagglehub, skip this step.** The scripts look inside
`~/.cache/kagglehub` automatically. To see what you have:

```
ls ~/.cache/kagglehub/datasets/*/*/versions/*
```

If you have not downloaded them yet:

```
pip3 install kagglehub
python3 -c "import kagglehub; print(kagglehub.dataset_download('ealtman2019/ibm-transactions-for-anti-money-laundering-aml'))"
python3 -c "import kagglehub; print(kagglehub.dataset_download('computingvictor/transactions-fraud-datasets'))"
```

Each prints where it saved the files. Kaggle may ask you to create an API token in your account settings.
Keep that token private: never paste it into a chat or commit it anywhere.

The two tarot datasets are already inside the project. There is nothing to download for those.

### Step 2 — Stop the website

`Ctrl+C` in the Terminal window.

### Step 3 — Do a quick trial run first

```
python3 analysis/process_all.py --max-rows 1000000
```

This reads only the first million rows of each big file, so it takes a minute or two instead of several. You will see
progress lines and a small table of results for each dataset.

> A line saying **skipped** just means a file wasn't found. Everything else still runs.

### Step 4 — Start the website again and look

```
python3 app.py
```

Refresh the browser. The DEMO badges should be gone, the Ledger charts should show your numbers, and The Underworld
should be full of transactions.

### Step 5 — When you're happy, run the full thing

```
python3 analysis/process_all.py
```

No `--max-rows` this time, so it reads every row. Expect several minutes and a lot of memory. Then start the website
again.

**If it runs out of memory**, try `python3 analysis/process_all.py --max-rows 5000000`, or process the consumer file
without its fraud labels, which is the memory-hungry part:

```
python3 analysis/process_transactions.py --skip-fraud
```

### Running one dataset at a time

`process_all.py` just runs these four in turn. You can run any of them on its own:

```
python3 analysis/process_aml.py
python3 analysis/process_transactions.py
python3 analysis/process_tarot.py
python3 analysis/process_taxonomy.py
```

---

## Part 3 · What's on the site

| Page | What it is |
|---|---|
| **Portal** | The front door |
| **The Oracle** | Pick a spread, draw cards, get a reading |
| **The Archive** | All 78 cards; click any one for its full page |
| **The Ledger** | Six charts and the full register of calculated statistics |
| **The Underworld** | A searchable table of flagged and unflagged transactions |
| **The Lexicon** | The vocabulary of divination, from the taxonomy dataset |
| **My Readings** | Your past readings, with favourites |
| **About the Order** | Methodology, sources, licences and limitations |

### Every reading has three layers, kept deliberately separate

1. **Symbolic text** — written for the project. Fiction.
2. **A calculated statistic** — a real number from a dataset, with its sample size, frozen at the moment you drew.
3. **Commentary** — the Order's satirical remark.

Which card is paired with which statistic is a **symbolic choice by the author**, not a finding. That is the joke and
the point. `analysis/card_mapping.py` holds every pairing and its stated reason.

### The four datasets

| Dataset | Gives the site |
|---|---|
| **IBM AML** (finance) | 3 Ledger charts, 5 statistics, The Underworld |
| **Transactions Fraud** (finance) | 3 Ledger charts, 5 statistics |
| **Tarot JSON** (tarot) | Traditional upright and reversed meanings, archetypes and reflection questions on every card |
| **Divinatory Arts Taxonomy** (tarot) | The Lexicon, the symbolic family on each Major Arcana card, the About page tables |

---

## Part 4 · Making it yours

These are the files to edit for the look. None of them touch the data.

| File | What it controls |
|---|---|
| `templates/base.html` | The frame around every page: header, navigation, footer |
| `templates/*.html` | Each individual page |
| `templates/_macros.html` | Reusable bits, like the window boxes and the card faces |
| `static/css/style.css` | All colours, fonts and layout. The colours are variables at the very top |
| `static/js/visualizations.js` | How the Ledger charts look |
| `analysis/card_content.py` | The written text of all 78 cards |

Save a file, refresh the browser, see the change. Templates and CSS update instantly. Changes to Python files need the
app restarted.

**Card images:** none are included. The images in the tarot dataset are the 1971 U.S. Games deck, which is still under
copyright. Put your own artwork in `static/` and reference it in `templates/_macros.html`.

---

## Part 5 · Where everything lives

```
financial-arcana/
├── app.py              the website: one function per page
├── models.py           the database tables
├── seed_db.py          fills the database (runs by itself)
├── config.py           settings
│
├── analysis/           ← the data work
│   ├── process_all.py        runs all four processors
│   ├── process_*.py          one per dataset
│   ├── card_content.py       the 78 card texts
│   ├── card_mapping.py       which card is paired with which statistic
│   └── demo_data.py          the DEMO placeholders
│
├── data/
│   ├── raw/            your source files
│   └── processed/      the small summaries the website reads
│
├── templates/          ← the HTML
└── static/             ← the CSS and JavaScript
```

---

## Part 6 · If something goes wrong

| What you see | What to do |
|---|---|
| `command not found: python3` | Install Python from python.org, then open a new Terminal window |
| `externally-managed-environment` | Use the virtual environment steps in Part 1, Step 2 |
| `ModuleNotFoundError: flask` | Run `pip3 install -r requirements.txt` (after `source .venv/bin/activate` if you made a venv) |
| The browser won't connect | The app has to be running in Terminal. Use http://127.0.0.1:5050, not 5000 |
| `Address already in use` | A copy is already running. Press `Ctrl+C` in the older Terminal window |
| Still showing DEMO badges | Run `process_all.py`, look for a `skipped` line, then restart the app |
| `skipped: No AML file found` | Check the file is there: `ls ~/.cache/kagglehub/datasets/*/*/versions/*`, or copy it into `data/raw/aml/` |
| It runs out of memory | Use `--max-rows 1000000`, or `--skip-fraud` on the transactions script |
| A page looks stale after new data | Stop the app, run the processor, start the app again |
| You want a completely clean slate | Delete `instance/financial_arcana.db` and restart. It rebuilds itself |

Deleting `instance/financial_arcana.db` also deletes your saved readings. Nothing else is lost; the database is rebuilt
from `data/processed/`.

---

## Part 7 · Honest limitations

- **The transaction data is synthetic.** It was generated by simulators. It is not real people or real banks.
- **"Flagged" and "fraud" are the datasets' own labels**, not judgements made by this project or evidence of a crime.
- **Amounts are not converted between currencies.** Anything based on the size of an amount uses US-dollar payments only.
- **The Underworld is not a representative sample.** It holds every flagged transaction up to a cap plus a random
  selection of others, so flagged rows are heavily over-represented there on purpose. The true rate is on the Ledger.
- **Consumer fraud labels cover only part of the data.** That rate describes the labelled subset, nothing more.
- **`--max-rows` takes the first N rows, not a random N.** The files are ordered by time, so trial figures can differ
  from a full run. Use it to check things work, not to quote numbers.
- **The card-to-statistic pairings are symbolic jokes.** They are not statistical claims.
- **Testing:** the code was tested end to end on stand-in files with the same layout as the real ones, not on the
  full-size downloads.

**Licences:** the Divinatory Arts Taxonomy (Arianne Galfre, 2026) is CC BY 4.0 and is credited on the About page and on
card pages. See each Kaggle dataset page for the terms of the other three. Tarot card images are not included, as above.

*Please consult your financial representative before interpreting this omen.*
