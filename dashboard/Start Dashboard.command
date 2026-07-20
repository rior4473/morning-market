#!/bin/bash
# Double-click this file in Finder to launch the dashboard.
# It refreshes the data, then opens the dashboard in your browser.
cd "$(dirname "$0")"

echo "Starting Markets & News dashboard…"

# Use the project venv
if [ -x ".venv/bin/streamlit" ]; then
  PY=".venv/bin/python"
  ST=".venv/bin/streamlit"
else
  echo "Virtualenv not found. Run setup first (see README)."
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

# Pull fresh data (won't crash the app if a source is down)
"$PY" refresh.py || echo "(refresh had warnings — opening anyway)"

# Open the browser shortly after the server starts
( sleep 3 && open "http://localhost:8501" ) &

# Launch the app (Ctrl+C in this window stops it)
"$ST" run app.py --server.headless true
