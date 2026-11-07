"""FrontierFinance (Hugging Face: samaya-ai/FrontierFinance, CC BY 4.0) -> data/processed/

Writes frontier_queries.json (for the Library page) and frontier_metrics.csv.

Where the data comes from, in order:
  1. a file you put in data/raw/frontier_finance/  (.json, .jsonl or .csv)
  2. Hugging Face's free public "datasets-server" API (no account, no extra packages);
     the rows are saved to data/raw/frontier_finance/frontierfinance.json so the next
     run works offline.
If neither works, the Library page simply stays empty.

Columns used: query_id, query, query_date, use_cases (list), capabilities (list).
"""
import csv
import json
import ssl
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "frontier_finance"
OUT_DIR = ROOT / "data" / "processed"
DATASET = "samaya-ai/FrontierFinance"
API = "https://datasets-server.huggingface.co"


def get_json(url):
    with urllib.request.urlopen(url, timeout=30, context=ssl.create_default_context()) as resp:
        return json.load(resp)


def fetch_rows():
    """Download every row through the public datasets-server API (100 rows per request)."""
    q = urllib.parse.quote(DATASET, safe="")
    splits = get_json(f"{API}/splits?dataset={q}")["splits"]
    s = next((x for x in splits if x["split"] == "train"), splits[0])
    rows, offset = [], 0
    while True:
        page = get_json(f"{API}/rows?dataset={q}&config={urllib.parse.quote(s['config'])}"
                        f"&split={s['split']}&offset={offset}&length=100")
        got = [r["row"] for r in page.get("rows", [])]
        rows += got
        offset += 100
        if not got or offset >= page.get("num_rows_total", 0):
            return rows


def load_local():
    for path in sorted(RAW.glob("*")):
        text = path.suffix.lower()
        try:
            if text == ".csv":
                return pd.read_csv(path).to_dict("records")
            if text in (".json", ".jsonl"):
                raw = path.read_text(encoding="utf-8").strip()
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        data = data.get("train") or data.get("rows") or next(iter(data.values()))
                    return data
                except json.JSONDecodeError:                      # JSON Lines
                    return [json.loads(line) for line in raw.splitlines() if line.strip()]
        except Exception as err:
            print(f"  frontier: could not read {path.name}: {err}")
    return None


def as_list(v):
    if v is None or (isinstance(v, float) and v != v):
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    if s.startswith("["):
        try:
            return as_list(json.loads(s.replace("'", '"')))
        except ValueError:
            pass
    return [x.strip() for x in s.split(";") if x.strip()] if s else []


def as_date(v):
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)) and v > 1e11:                    # epoch milliseconds
        return datetime.fromtimestamp(v / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    return str(v)[:10]


def run():
    rows = load_local()
    if not rows:
        print("  frontier: no local file; asking Hugging Face's public API ...")
        try:
            rows = fetch_rows()
        except Exception as err:
            print(f"  frontier: skipped ({err.__class__.__name__}: {err}). "
                  f"Optional: save the dataset as .json in {RAW}.")
            return False
        RAW.mkdir(parents=True, exist_ok=True)
        (RAW / "frontierfinance.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    records = []
    for r in rows:
        if not r.get("query"):
            continue
        records.append(dict(external_id=str(r.get("query_id", "")), query=str(r["query"]).strip(),
                            query_date=as_date(r.get("query_date")),
                            use_cases=as_list(r.get("use_cases")), capabilities=as_list(r.get("capabilities"))))
    if not records:
        print("  frontier: file had no usable rows (expected a 'query' column).")
        return False

    n = len(records)
    top_use_case = Counter(u for rec in records for u in set(rec["use_cases"])).most_common(1)
    metrics = [("frontier_query_count", n, "count", n)]
    if top_use_case:
        metrics.append(("frontier_top_use_case_share", top_use_case[0][1] / n * 100, "%", n))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "frontier_queries.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    with open(OUT_DIR / "frontier_metrics.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric_name", "value", "unit", "sample_size"])
        w.writerows(metrics)
    print(f"  frontier: {n} queries -> frontier_queries.json, frontier_metrics.csv")
    return True


if __name__ == "__main__":
    run()
