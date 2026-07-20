#!/bin/bash
# Wrapper used by the scheduler. Self-locating — safe to move the project.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Use the project's virtualenv if it exists, else system python3.
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  PY="$PROJECT_DIR/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

SCOPE="${1:-all}"   # all | market | rates | macro | news
mkdir -p "$PROJECT_DIR/cache/logs"
"$PY" refresh.py "$SCOPE" >> "$PROJECT_DIR/cache/logs/refresh.log" 2>&1
