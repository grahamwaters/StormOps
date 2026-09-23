#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install Python 3 and run this script again." >&2
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

echo "StormOps environment is ready."
echo "Run the Cloud Lab: .venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory frontend"
echo "Run the optional collector: .venv/bin/python backend/regex_unified.py"
