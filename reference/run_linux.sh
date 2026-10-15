#!/bin/sh
set -e

if command -v python3.10 >/dev/null 2>&1; then
  PYTHON_BIN=python3.10
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
else
  echo "Python 3 is not installed. Install Python 3.10+ and run this file again."
  exit 1
fi

if [ ! -d "venv" ]; then
  "$PYTHON_BIN" -m venv venv
fi
. venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
