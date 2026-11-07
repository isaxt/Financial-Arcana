#!/bin/bash
# Double-click to load the real datasets into The Financial Arcana (Mac).
cd "$(dirname "$0")" || exit 1
python3 arcana.py data
echo
read -n 1 -s -r -p "Finished. Press any key to close this window."
