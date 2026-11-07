#!/bin/bash
# Double-click to start The Financial Arcana (Mac).
cd "$(dirname "$0")" || exit 1
python3 arcana.py
echo
read -n 1 -s -r -p "The site has stopped. Press any key to close this window."
