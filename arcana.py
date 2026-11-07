#!/usr/bin/env python3
"""The Financial Arcana: one command to set up and run.

    python3 arcana.py          start the site (the first run sets everything up)
    python3 arcana.py data     load the real datasets, then refresh the site
    python3 arcana.py reset    wipe the database (deletes saved readings) and rebuild it

On Windows use `python` instead of `python3`.
"""
import argparse
import importlib.util
import os
import socket
import subprocess
import sys
import threading
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
CORE_PACKAGES = ["flask", "flask_sqlalchemy", "pandas", "numpy"]


def ensure_environment():
    """Make sure the needed packages exist. If not, build a private .venv and re-run inside it."""
    if all(importlib.util.find_spec(m) for m in CORE_PACKAGES):
        return
    if os.environ.get("ARCANA_BOOTSTRAPPED"):
        sys.exit("The packages in requirements.txt could not be installed. "
                 "Try: pip install -r requirements.txt")
    py = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        print("First run: creating a private Python environment (.venv) ...")
        venv.create(VENV, with_pip=True)
    print("Installing the packages the site needs (first run only, about a minute) ...")
    subprocess.check_call([str(py), "-m", "pip", "install", "--quiet", "-r", str(ROOT / "requirements.txt")])
    env = dict(os.environ, ARCANA_BOOTSTRAPPED="1")
    sys.exit(subprocess.call([str(py), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))


def free_port(start):
    for port in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:      # nothing is listening there
                return port
    sys.exit(f"No free port between {start} and {start + 19}. Use --port to pick another.")


def cmd_start(args):
    from app import app                      # the first import creates and fills the database
    from models import FinancialMetric
    with app.app_context():
        has_real = FinancialMetric.query.filter_by(is_demo=False).count() > 0
    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}"
    print(f"\nThe Financial Arcana is open at {url}   (press Ctrl+C to stop)")
    if not has_real:
        print("Tip: the statistics are DEMO placeholders. Run  python3 arcana.py data  for real numbers.")
    if not args.no_browser and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.5, webbrowser.open, args=[url]).start()
    app.run(host="127.0.0.1", port=port, debug=args.debug)


def cmd_data(args):
    from analysis import get_data
    get_data.run(aml_file=args.aml_file, tx_dir=args.tx_dir, quick=args.quick, skip_fraud=args.skip_fraud)


def cmd_reset(_args):
    if input("This deletes all saved readings and rebuilds the database. Type yes to continue: ").strip().lower() != "yes":
        sys.exit("Cancelled.")
    from app import app
    from models import db
    from seed_db import seed
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed()


def main():
    ap = argparse.ArgumentParser(description="The Financial Arcana: set up and run the site.")
    ap.add_argument("command", nargs="?", default="start", choices=["start", "data", "reset"],
                    help="start (default), data (load the real datasets), reset (rebuild the database)")
    ap.add_argument("--port", type=int, default=5050, help="start: first port to try (default 5050)")
    ap.add_argument("--no-browser", action="store_true", help="start: don't open a browser tab")
    ap.add_argument("--debug", action="store_true", help="start: auto-reload when code changes")
    ap.add_argument("--quick", action="store_true", help="data: use only the first 1,000,000 rows (fast trial run)")
    ap.add_argument("--skip-fraud", action="store_true", help="data: skip the big fraud-labels file")
    ap.add_argument("--aml-file", help="data: path to HI-Small_Trans.csv if it isn't found automatically")
    ap.add_argument("--tx-dir", help="data: folder holding transactions_data.csv, mcc_codes.json, train_fraud_labels.json")
    args = ap.parse_args()

    ensure_environment()
    {"start": cmd_start, "data": cmd_data, "reset": cmd_reset}[args.command](args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
