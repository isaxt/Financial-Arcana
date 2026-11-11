# What the data analysis does, step by step

A reading guide for going through the code yourself. Line numbers (written "L123") match the files as shipped; if you
edit a file they will drift, so each reference also names the function or loop to look for.

---

## 0. How to use this guide

**Suggested reading order (about 80 minutes in total):**

1. Section 1 (the big picture) and Section 2 (five ideas used everywhere), 10 minutes.
2. `analysis/process_tarot.py` (69 lines) and `analysis/process_taxonomy.py` (94 lines): the easy ones, 15 minutes.
3. `analysis/process_aml.py` (164 lines): the model for the other big script, 30 minutes.
4. `analysis/process_transactions.py` (181 lines): same pattern, 15 minutes.
5. `analysis/card_mapping.py` and `seed_db.py`: how numbers end up in the database and on cards, 15 minutes.

**Try the code while reading.** Every script runs on its own and prints what it did:

```
python3 analysis/process_aml.py --max-rows 100000
python3 analysis/inspect_dataset.py <path to any csv>     # prints its columns, if you want to explore a file
```

Section 8 gives short pandas snippets that recompute each headline number independently, so you can check the scripts
against the raw data instead of trusting them.

---

## 1. The big picture

```
raw files ──► analysis/process_*.py ──► data/processed/ ──► seed_db.py ──► SQLite ──► app.py ──► templates
```

- A `process_*.py` script reads one raw dataset and writes **small summary files** (CSV or JSON).
- `seed_db.py` reads those summaries and the card text and fills the database. It runs by itself when the app starts.
- `app.py` reads the database (and a few of the summary CSVs, for charts) and hands the data to the templates.

The raw files are only ever touched by the `process_*.py` scripts, and only read, never modified.

Every dataset ends up in one or more of these places:

| Dataset | Script | Summary files written | What the site does with it |
|---|---|---|---|
| IBM AML | `process_aml.py` | `aml_metrics.csv`, `aml_by_payment_format.csv`, `aml_amount_histogram.csv`, `aml_daily.csv`, `aml_transactions_sample.csv` | 5 metrics tied to cards; 3 Ledger charts; the Underworld page |
| Transactions Fraud | `process_transactions.py` | `consumer_metrics.csv`, `consumer_by_category.csv`, `consumer_users_hist.csv` | 5 metrics tied to cards; 3 Ledger charts |
| Tarot JSON | `process_tarot.py` | `tarot_cards.json` | traditional meanings, reversed meanings, archetype and questions on every card |
| Divinatory Arts Taxonomy | `process_taxonomy.py` | `taxonomy.json` | Lexicon page; family and themes on Major Arcana cards; About page tables |

---

## 2. Five ideas used throughout

### 2.1 Reading in chunks

The AML and Transactions files have millions of rows, too many to hold comfortably in memory. Both scripts use
`pd.read_csv(..., chunksize=N)`, which returns an iterator that yields a DataFrame of N rows at a time. The scripts loop
over the chunks, update some **running totals**, and throw each chunk away before reading the next.

> Look for: `for i, chunk in enumerate(pd.read_csv(...chunksize=...))`.

### 2.2 Running totals instead of stored rows

You cannot compute a rate from "this chunk's rate". You keep counts and divide at the end:
`flagged rate = total flagged / total rows`. So the scripts keep things like `total`, `flagged`, dictionaries of counts
per payment format, and arrays of histogram counts that are **added** to on every chunk.

### 2.3 Mean and spread from running sums (the coefficient of variation)

The scripts report the **coefficient of variation (CV)**: standard deviation divided by mean. It is a unit-free measure of
how spread out amounts are. To get it without storing every amount, they keep three running numbers:

- `n`, the count,
- `s`, the sum of the amounts,
- `ss`, the sum of the squared amounts.

Then `mean = s / n` and `std = sqrt(ss / n − mean²)`. This is the **population** standard deviation (divide by n, not
n−1), which is the right choice when you have the whole data and not a sample of it. At millions of rows the difference
between the two is invisible anyway.

### 2.4 Medians need the values

Unlike a mean, a median cannot be built from running sums. So the scripts do keep the relevant amounts: for AML only the
**flagged USD amounts** (a tiny fraction of rows); for Transactions, all purchase amounts stored as 32-bit numbers
(about 50 MB for 13 million rows).

### 2.5 Reservoir-style random sampling (AML explorer only)

The Underworld page needs actual rows, but millions of them are too many to put on a web page. The function
`reservoir()` (about L52–L56) keeps a **uniform random sample** across all chunks:

1. Give every row in the new chunk a random number between 0 and 1 (`_k`).
2. Append them to the rows kept so far.
3. If more than `k` rows are held, keep only the `k` with the smallest random numbers (`nsmallest`).

Because every row gets an independent random number and only the smallest `k` survive, every row in the whole file has
the same chance of being in the final sample, no matter which chunk it came from. The random generator is seeded
(`default_rng(42)`), so re-running gives the same sample.

---

## 3. `process_aml.py`: the IBM anti-money-laundering file

**Input:** `HI-Small_Trans.csv` (found in `data/raw/aml/` first, else in your kagglehub cache; `find_file()` ≈ L41).
Each row is one transaction: timestamp, sender bank and account, receiver bank and account, amounts and currencies,
payment format, and `Is Laundering` (1 or 0, assigned by the dataset's simulation).

### 3.1 Setup (≈ L24–L38)

- `REQUIRED` lists the 11 columns the script needs. It reads only those (`usecols=REQUIRED`), which saves time and memory.
- The raw file has **two columns both named "Account"**. Pandas renames the second one to `Account.1`. That is why you
  see `Account.1` in the code: `Account` is the sender, `Account.1` the receiver.
- `BINS = np.arange(0, 13.5, 0.5)` are the edges of the histogram, in `log10(amount + 1)` units (0 to 13 in half steps).
- `SAMPLE_SIZE = 20_000` is how many rows each explorer sample group keeps.
- `AMOUNT_CURRENCY = "US Dollar"`: see 3.3.

### 3.2 Safety checks (≈ L59–L67)

`run()` finds the file, reads only the header (`nrows=0`) and exits with a plain message if columns are missing, instead
of failing later with a confusing error.

### 3.3 The chunk loop (≈ L78–L112), the heart of the script

For each chunk:

1. **Clean.** `dropna` removes rows missing the amount, label, format or currency (normally none).
2. **Make three helper columns:** `amt` (amount paid), `lab` (True where `Is Laundering == 1`), and `usd`
   (True where the payment currency is US dollars). `amt_usd` and `lab_usd` are those same series restricted to USD rows.
   - **Why USD only?** The file mixes many currencies and the script does **not** convert them. Averaging 1,000 yen with
     1,000 dollars would be meaningless, so everything that depends on the size of an amount uses USD payments only.
     Counts and rates (which don't depend on amounts) use every row.
3. **Update the overall counters:** rows, flagged rows, USD rows, flagged USD rows, `s`, `ss` (see 2.3).
4. **Per payment format** (`groupby("Payment Format")`): add this chunk's row count and flagged count to two
   dictionaries, `fmt_total` and `fmt_flag`.
5. **Per day:** the first 10 characters of the timestamp are the date. Count rows per day (`day_total`) and flagged rows
   per day (`day_flag`) in dictionaries.
6. **Flagged-only collections:** append the flagged USD amounts (for the median) and add each flagged sender's
   `(bank, account)` pair to a Python `set` (for counting distinct accounts).
7. **Histogram:** `np.log10(amount + 1)` turns amounts into a scale where 1, 10, 100, 1,000 … are evenly spaced
   (without the log, a few giant payments would flatten everything else). The `+1` avoids `log10(0)`. `.clip` forces
   values into range. `np.histogram` counts how many land in each bin; counts are added to `hist_all` and, for flagged
   rows, `hist_flag`.
8. **Samples:** call `reservoir()` once for flagged rows and once for non-flagged rows.

### 3.4 After the loop (≈ L117–L152): turning running totals into outputs

| Output | How it is calculated |
|---|---|
| `aml_flagged_rate` | `flagged / total × 100`, all rows |
| `aml_flagged_median_amount` | median of the flagged USD amounts |
| `aml_amount_cv` | `std / mean` of USD amounts, from the running sums |
| `aml_flagged_account_count` | number of distinct `(From Bank, Account)` pairs among flagged rows |
| `aml_top_format_share` | the largest per-format count divided by total rows × 100 |

Written to:

- `aml_metrics.csv`: the five rows above, each with its `unit` and `sample_size` (how many rows it is based on).
- `aml_by_payment_format.csv`: per format: count, flagged, `flagged_rate`. → Ledger chart "Flagged share by payment format".
- `aml_amount_histogram.csv`: per bin: non-flagged and flagged counts (the flagged count is subtracted from the
  overall to get the non-flagged one). → Ledger chart "Transaction amounts".
- `aml_daily.csv`: per day: count and flagged count. → Ledger chart "Transactions per day".
- `aml_transactions_sample.csv`: the two samples combined and sorted by time, with columns renamed by `RENAME`
  (e.g. `Account.1` → `to_account`). → The Underworld table.

### 3.5 Things to know when reading the results

- **The Underworld is not representative.** It holds up to 20,000 *flagged* rows plus 20,000 other rows. In the real
  data flagged rows are well under 1%, so they are heavily over-represented there. The page says so; the true rate is
  `aml_flagged_rate` on the Ledger.
- **"Flagged" is the dataset's label,** created by the simulation that generated the data. It is not a judgement by this
  project.
- **`--max-rows` takes the first N rows, not a random N.** The file is ordered by time, so a trial run covers the
  earliest days only and its numbers can differ from a full run. Use it to test that things work, not to quote figures.
- **The sample size column matters.** `aml_flagged_median_amount` is based on flagged *USD* payments only, so its
  sample size is smaller than the flagged count.

---

## 4. `process_transactions.py`: the consumer transactions file

**Inputs** (found in `data/raw/transactions/` first, else the kagglehub cache; `find_folder()` ≈ L47):

- `transactions_data.csv`: one row per card transaction (`id`, `client_id`, `amount` like `"$-77.00"`, `mcc`, …).
- `mcc_codes.json`: dictionary from merchant category code to its name (`"5812"` → "Eating Places and Restaurants").
- `train_fraud_labels.json`: `{"target": {"<transaction id>": "Yes"/"No"}}`. **Only some transactions have a label.**

### 4.1 Setup and checks (≈ L58–L90)

- Reads the header and checks that `id`, `client_id`, `amount` and `mcc` exist (`REQUIRED`).
- **Loads the fraud labels** with `load_labels()` (≈ L38): the JSON becomes a pandas Series indexed by transaction id.
  This is the **memory-hungry step**: millions of ids and strings can need several gigabytes of RAM. If Python raises
  `MemoryError`, the script carries on without labels (so the fraud rate stays a DEMO placeholder). If your Mac simply
  kills the process instead, run with `--skip-fraud`.
- Loads `mcc_codes.json` into a dictionary, if present.

### 4.2 The chunk loop (≈ L101–L125)

For each chunk of 1,000,000 rows:

1. **Clean the amount.** `"$-77.00"` is text. The script removes `$` and `,` with a regular expression, then converts to a
   number (`pd.to_numeric(..., errors="coerce")` turns anything unreadable into missing, and those rows are dropped).
2. **Purchases only.** `pos` = rows where the amount is greater than 0. Refunds and zero rows are excluded from
   amount statistics. Running totals `pos_n`, `s`, `ss` are updated (see 2.3), and the amounts are stored for the
   median (see 2.4).
3. **Per client:** `chunk["client_id"].value_counts()` counts transactions per client in this chunk; `.add(..., fill_value=0)`
   adds them to the running totals (clients absent from one chunk count as 0 there).
4. **Per merchant category:** same idea with `mcc`, giving `mcc_counts`.
5. **Fraud, if labels are loaded:** `chunk["id"].map(labels)` looks up each transaction's label (missing → no label).
   - `has` = rows that have a label; `labeled` counts them.
   - `fraud` counts the labels equal to `"Yes"`.
   - `lab_by_mcc` / `fraud_by_mcc` do the same per merchant category.

### 4.3 After the loop (≈ L127–L163)

| Output | How it is calculated |
|---|---|
| `consumer_txns_per_user_mean` | total transactions / number of distinct clients |
| `consumer_top_category_share` | count of the busiest category / total × 100 |
| `consumer_median_amount` | median of purchase amounts (> 0) |
| `consumer_amount_cv` | `std / mean` of purchase amounts, from running sums |
| `consumer_fraud_rate` | `Yes` labels / labelled transactions × 100 (**labelled rows only**) |

Written to:

- `consumer_metrics.csv`: the metrics above with sample sizes. The fraud rate's sample size is the **labelled** count, not
  the total, and the Ledger shows it.
- `consumer_by_category.csv`: per category: count, `share_pct`, `labeled`, `fraud`, `fraud_rate_pct`. The category name
  comes from `mcc_codes.json` (falling back to "MCC 1234"). `fraud_rate_pct` is left empty where nothing is labelled, to
  avoid dividing by zero. → Ledger charts "Busiest merchant categories" and "Fraud rate by category".
- `consumer_users_hist.csv`: how many clients made 1–2 transactions, 3–5, and so on. The bucket edges come from
  `np.geomspace` (evenly spaced on a log scale) so a few very active clients don't hide everyone else.
  → Ledger chart "Transactions per client".

### 4.4 Things to know

- The Ledger only draws a category in the fraud chart if it has **at least 100 labelled transactions** (`app.py`, in
  `ledger()`), because a rate based on 3 rows is noise.
- The fraud rate describes only the labelled subset. How labels were chosen is not documented in the file, so treat it as
  "the share of labelled transactions marked as fraud", not "the fraud rate of consumers".
- Same `--max-rows` caveat as AML: first rows, not random rows.

---

## 5. `process_tarot.py`: traditional tarot meanings

**Input:** `data/raw/tarot/tarot-images.json`, with a top-level list `cards` (78 entries).
**Output:** `data/processed/tarot_cards.json`.

This script does no statistics; it tidies text.

- `normalise(card)` (≈ L35) builds one clean record per card:
  - `arcana`: "Major" if the arcana field says so (or the suit is "trump"), otherwise "Minor"; Major cards get no suit.
  - `traditional_meaning` and `traditional_reversed`: the dataset's `meanings.light` (upright) and `meanings.shadow`
    (reversed), passed through `join_meanings()`.
  - `keywords`, `tarot_archetype` and `questions` (the dataset's "Questions to Ask").
- `join_meanings(items, limit=3)` (≈ L26) takes at most three meanings and joins them into one sentence:
  `['Being open-minded', 'Taking a leap']` → `Being open-minded; taking a leap.`
- It reads **only the JSON**. The card images in that dataset are not used (see the README's rights note).
- The script warns if it doesn't end up with 78 cards.

`seed_db.py` later matches these records to the authored cards **by card name** (lower-cased, punctuation removed).
The financial interpretations (upright and reversed) are never replaced; they are authored in `card_content.py`.

---

## 6. `process_taxonomy.py`: the Divinatory Arts Taxonomy

**Inputs:** four CSVs in `data/raw/divinatory_taxonomy/`. **Output:** `data/processed/taxonomy.json`
(`{"major": [...], "entries": [...]}`).

- `tarot_major_arcana_symbolic_taxonomy.csv` → `major`: for each Major Arcana card, its symbolic family and main themes.
- `divinatory_terms_taxonomy.csv` → entries of kind `lexicon` (term, definition, subcategory). → the Lexicon page.
- `digital_trust_signals_divinatory_practices.csv` → entries of kind `trust`. → the About page.
- `ethical_boundaries_divinatory_practice.csv` → entries of kind `boundary`. → the About page.

Details worth knowing:

- Only the **English columns** are kept (`arcana_en`, `term_en`, `definition_en`, `description_en`, …).
- The boundaries file has **French-only** labels. `DOMAIN_EN` and `PRINCIPLE_EN` (≈ L95–L125) are translation tables
  **written by this project**, not part of the dataset. If a label isn't in the tables, the French original is kept and
  the script prints a note.
- **Matching by name, not number.** The taxonomy numbers the Major Arcana in the Marseille order (Justice 8, Strength 11),
  which differs from the usual Rider-Waite order. Matching by number would give Justice the wrong family, so the project
  matches by name.
- `fillna("")` replaces empty cells so text fields never become the string `nan`.

---

## 7. Check the numbers yourself

Because the scripts only stream through the data, the easiest independent check is to recompute each headline number
with plain pandas on the same first N rows. Run the trial first so both use the same rows:

```
python3 analysis/process_all.py --max-rows 1000000
```

Then in a Python session (adjust the file paths to where your data is):

```python
import pandas as pd, json

# ---- AML ----
df  = pd.read_csv("HI-Small_Trans.csv", nrows=1_000_000)
usd = df[df["Payment Currency"] == "US Dollar"]
print("aml_flagged_rate           ", (df["Is Laundering"] == 1).mean() * 100)
print("aml_flagged_median_amount  ", usd.loc[usd["Is Laundering"] == 1, "Amount Paid"].median())
print("aml_amount_cv              ", usd["Amount Paid"].std(ddof=0) / usd["Amount Paid"].mean())
print("aml_flagged_account_count  ", df[df["Is Laundering"] == 1][["From Bank", "Account"]].drop_duplicates().shape[0])
print("aml_top_format_share       ", df["Payment Format"].value_counts(normalize=True).max() * 100)

# ---- Consumer transactions ----
t = pd.read_csv("transactions_data.csv", nrows=1_000_000)
t["amt"] = pd.to_numeric(t["amount"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
pos = t.loc[t["amt"] > 0, "amt"]
print("consumer_txns_per_user_mean", len(t) / t["client_id"].nunique())
print("consumer_top_category_share", t["mcc"].astype(str).value_counts(normalize=True).max() * 100)
print("consumer_median_amount     ", pos.median())
print("consumer_amount_cv         ", pos.std(ddof=0) / pos.mean())

labels = pd.Series(json.load(open("train_fraud_labels.json"))["target"])
labels.index = labels.index.astype("int64")
lab = t["id"].map(labels)
print("consumer_fraud_rate        ", (lab == "Yes").sum() / lab.notna().sum() * 100)
```

Compare with `data/processed/aml_metrics.csv` and `consumer_metrics.csv`. (`ddof=0` is the population standard deviation,
matching the script; pandas defaults to `ddof=1`.) These snippets were tested against the scripts' output on
stand-in files and matched to four decimal places. Note the AML file's duplicate "Account" header: pandas names the
sender `Account` and the receiver `Account.1`.

---

## 8. `card_mapping.py`: turning numbers into card statistics

Three dictionaries/lists, read by both the processors' consumers and `seed_db.py`:

- **`DATASETS`** (≈ L11): name, source link, description, licence and processing notes for each of the five datasets.
  This is what the About page lists.
- **`METRICS`** (≈ L43): for each metric name, its display name, unit, description and a one-line **methodology**. The
  methodology strings are what the metric detail pages (`/ledger/<name>`) show, so they should always match what the
  scripts really do. If you change a calculation, change its methodology line.
- **`CARD_MAP`** (≈ L93): a list of `(card, metric, relationship label, explanation)`. For example
  `("The Tower", "aml_flagged_rate", "Instability signal", ...)`. 13 links over 10 metrics: a metric can serve more than
  one card, and most of the 78 cards have no metric at all and stay purely symbolic.

**The card-to-metric links are symbolic, chosen by the project author** ("the tower falls on a small fraction of
records"). They are jokes with an argument attached, not findings. The reading page says so in its method note.

There are 10 metrics in total: 5 from AML and 5 from the consumer transactions.

---

## 9. `seed_db.py`: from files to SQL

You never run this yourself; `app.py` calls `seed()` at startup when something changed.

1. **`data_signature()`** (≈ L48): builds a fingerprint (an MD5 hash) from the name, size and modified time of every
   file in `data/processed/` plus the card-text files. It is stored in the `Meta` table. If the fingerprint at startup
   differs from the stored one, `seed()` runs again. That is why re-processing data and restarting is enough.
2. **Datasets:** one row per entry in `DATASETS`.
3. **Cards** (≈ L119–L146): for each of the 78 authored cards, fill the card row, then merge in the Tarot JSON record
   with the same normalised name (traditional meaning, reversed, archetype, questions, up to 3 extra keywords), and for
   Major Arcana the taxonomy's family and themes.
4. **Interpretations and spreads:** generic per-suit notes and the four spreads (Daily Omen, Past/Present/Future,
   Risk/Exposure/Consequence, The State of Capitalism).
5. **Metrics** (≈ L161–L175): for each metric in `METRICS`, if the processed CSVs contain a value use it and set
   `is_demo = False`; otherwise use the placeholder from `demo_data.py` and set `is_demo = True`. That flag is what
   makes the DEMO badges appear.
6. **Card ↔ metric links** from `CARD_MAP`.
7. **Row-level data:** `load_aml_sample()` bulk-inserts the explorer sample into `AmlTransaction` and
   `load_taxonomy_entries()` fills `TaxonomyEntry`. `bulk_insert_mappings` inserts 5,000 rows at a time, which is much
   faster than adding objects one by one.

Saved readings are **kept** across re-seeding (they are not deleted); each reading stores a frozen copy of the metric
values it displayed, so an old reading never changes when data is re-processed.

---

## 10. From the database to the pages (`app.py`)

- **`ledger()`** (≈ L246): lists every metric grouped by dataset, and reads the five chart CSVs with `read_chart_csv()`.
  That function turns missing values (`NaN`) into `None`, because `NaN` is not valid JSON and would break the charts. If a
  chart CSV doesn't exist, it supplies the DEMO version and flags it. The data is passed to the template as JSON, and
  `static/js/visualizations.js` draws it with Chart.js.
- **`underworld()`** (≈ L282): builds one SQL query from the filters in the URL (amount range, payment format,
  flagged / not flagged, account number), paginates 50 rows per page, and for an account search counts the accounts it
  dealt with (inside the sample only).
- **Readings:** `generate_reading()` draws cards without replacement, picks upright or reversed, looks up each card's
  linked metrics, **freezes** them as `metric_snapshot`, and adds a templated commentary (`make_commentary()`).

---

## 11. Honest limitations (worth keeping in mind when you read the numbers)

- The two transaction datasets are **synthetic**. The patterns in them were produced by simulators, so they say nothing
  about real people or banks.
- Labels (laundering, fraud) are the datasets' own, not independent evidence.
- AML amounts are not converted between currencies; amount statistics use USD payments only.
- Consumer fraud labels exist for only part of the data.
- Trial runs (`--max-rows`) use the first rows of time-ordered files and are not random samples.
- All code was tested end to end on **stand-in files with the same layout** as the real ones, not on the full-size Kaggle
  downloads. If a script fails on your real files, the error message is usually about a column name or about memory;
  `inspect_dataset.py` helps with the first and `--skip-fraud` / `--max-rows` with the second.
- Card-to-metric links are symbolic jokes, not statistical claims.
