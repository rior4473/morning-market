"""Local cache backing the dashboard.

Snapshot shape:
{
  "generated_at": "<iso>",
  "sections": {
     "<section_key>": {"rows": [...]|..., "source": "...", "fetched_at": "<iso>"},
     ...
  }
}
The UI reads only from cache. refresh.py writes sections, merging so each
section keeps its own fetched_at and untouched sections are preserved.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from config import NEWS_FILE, SNAPSHOT_FILE, YIELDS_HISTORY_FILE


# Fields used to identify a row across refreshes (for carry-forward).
_ID_FIELDS = ("asset", "maturity", "rate", "name", "indicator", "spread")
# A row is considered "missing" if its primary value field is None.
_VALUE_FIELDS = ("latest", "latest_bps")


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def read_snapshot() -> dict:
    if not SNAPSHOT_FILE.exists():
        return {"generated_at": None, "sections": {}}
    return json.loads(SNAPSHOT_FILE.read_text())


def _row_id(row: dict):
    for f in _ID_FIELDS:
        if f in row:
            return (f, row[f])
    return None


def _has_value(row: dict) -> bool:
    for f in _VALUE_FIELDS:
        if f in row:
            return row[f] is not None
    return True  # rows without a tracked value field (always keep fresh)


def _merge_rows(new_rows: list, old_rows: list) -> list:
    """Keep last-known-good values: if a new row is missing data but the prior
    snapshot had a value for it, carry the old row forward (marked stale)."""
    old_by_id = {rid: r for r in old_rows if (rid := _row_id(r))}
    merged = []
    for nr in new_rows:
        rid = _row_id(nr)
        old = old_by_id.get(rid)
        if not _has_value(nr) and old is not None and _has_value(old):
            kept = dict(old)
            kept["stale"] = True
            merged.append(kept)
        else:
            nr = dict(nr)
            nr["stale"] = False
            merged.append(nr)
    return merged


def update_sections(new_sections: dict) -> None:
    """Merge sections into the snapshot, stamping each with fetched_at and
    carrying forward previous values for any rows that came back empty."""
    snap = read_snapshot()
    sections = snap.get("sections", {})
    stamp = _now()

    for key, payload in new_sections.items():
        payload = dict(payload)
        old = sections.get(key, {})

        if isinstance(payload.get("rows"), list) and isinstance(old.get("rows"), list):
            payload["rows"] = _merge_rows(payload["rows"], old["rows"])

        elif key == "curve":
            new_pts = payload.get("points", [])
            empty = not new_pts or all(p.get("yield") is None for p in new_pts)
            if empty and old.get("points") and any(
                    p.get("yield") is not None for p in old["points"]):
                # keep prior curve values; only the fetch time advances
                for field in ("points", "comparison", "shape",
                              "spread_10y_2y", "as_of", "source"):
                    if field in old:
                        payload[field] = old[field]

        payload["fetched_at"] = stamp
        sections[key] = payload

    snap["sections"] = sections
    snap["generated_at"] = stamp
    SNAPSHOT_FILE.write_text(json.dumps(snap, indent=2, default=str))


def write_news(items: list[dict]) -> None:
    NEWS_FILE.write_text(json.dumps(items, indent=2, default=str))


def read_news() -> list[dict]:
    if not NEWS_FILE.exists():
        return []
    return json.loads(NEWS_FILE.read_text())


def append_yield_history(points: list[dict], as_of: str | None) -> None:
    if not as_of:
        return
    row = {p["maturity"]: p["yield"] for p in points}
    row["date"] = as_of
    new = pd.DataFrame([row]).set_index("date")
    if YIELDS_HISTORY_FILE.exists():
        existing = pd.read_csv(YIELDS_HISTORY_FILE, index_col="date")
        combined = pd.concat([existing[~existing.index.isin(new.index)], new])
    else:
        combined = new
    combined.sort_index().to_csv(YIELDS_HISTORY_FILE)
