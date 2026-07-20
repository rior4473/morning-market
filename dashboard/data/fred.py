"""Thin FRED (Federal Reserve Economic Data) API client.

Public REST API + free key. Docs: https://fred.stlouisfed.org/docs/api/
"""
from __future__ import annotations

import io
import os
from datetime import date

import pandas as pd
import requests

FRED_BASE = "https://api.stlouisfed.org/fred"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"


class FredError(RuntimeError):
    pass


def _has_key() -> bool:
    return bool(os.getenv("FRED_API_KEY", "").strip())


def _get_series_api(series_id: str, start: str | None) -> pd.Series:
    params = {"series_id": series_id, "api_key": os.getenv("FRED_API_KEY", ""),
              "file_type": "json"}
    if start:
        params["observation_start"] = start
    resp = requests.get(f"{FRED_BASE}/series/observations", params=params, timeout=20)
    resp.raise_for_status()
    obs = resp.json().get("observations", [])
    if not obs:
        return pd.Series(dtype=float)
    df = pd.DataFrame(obs)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(subset=["value"]).set_index("date")["value"]


def _get_series_csv(series_id: str, start: str | None) -> pd.Series:
    """Keyless fallback: FRED's public CSV download endpoint (no API key)."""
    params = {"id": series_id}
    if start:
        params["cosd"] = start
    resp = requests.get(FRED_CSV, params=params, timeout=20)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    if df.shape[1] < 2:
        return pd.Series(dtype=float)
    date_col, val_col = df.columns[0], df.columns[1]
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")  # "." -> NaN
    df[date_col] = pd.to_datetime(df[date_col])
    return df.dropna(subset=[val_col]).set_index(date_col)[val_col]


def get_series(series_id: str, start: str | None = None) -> pd.Series:
    """Date-indexed float Series for a FRED series_id (NaN-dropped).

    Uses the official API when FRED_API_KEY is set, otherwise (or on failure)
    falls back to FRED's public CSV download endpoint, which needs no key.
    """
    if _has_key():
        try:
            s = _get_series_api(series_id, start)
            if not s.empty:
                return s
        except Exception:
            pass
    return _get_series_csv(series_id, start)


def latest_with_change(series_id: str) -> dict:
    """Latest, previous, daily change/%-change, YTD change, and YTD average."""
    start = f"{date.today().year - 1}-12-01"
    s = get_series(series_id, start=start)
    if s.empty:
        return {"latest": None, "previous": None, "change": None,
                "pct_change": None, "ytd_change": None, "ytd_avg": None,
                "as_of": None}

    latest = float(s.iloc[-1])
    previous = float(s.iloc[-2]) if len(s) >= 2 else None
    change = (latest - previous) if previous is not None else None
    pct_change = ((change / previous) * 100) if previous else None

    year = date.today().year
    prior = s[s.index < pd.Timestamp(f"{year}-01-01")]
    ytd_base = float(prior.iloc[-1]) if not prior.empty else None
    ytd_change = (latest - ytd_base) if ytd_base is not None else None

    ytd = s[s.index >= pd.Timestamp(f"{year}-01-01")]
    ytd_avg = float(ytd.mean()) if not ytd.empty else None

    return {"latest": latest, "previous": previous, "change": change,
            "pct_change": pct_change, "ytd_change": ytd_change,
            "ytd_avg": ytd_avg, "as_of": s.index[-1].strftime("%Y-%m-%d")}


def next_release_date(series_id: str) -> str | None:
    """Best-effort next scheduled release date for a series (or None)."""
    try:
        r = requests.get(f"{FRED_BASE}/series/release",
                         params={"series_id": series_id, "api_key": _api_key(),
                                 "file_type": "json"}, timeout=15)
        r.raise_for_status()
        releases = r.json().get("releases", [])
        if not releases:
            return None
        release_id = releases[0]["id"]

        today = date.today().isoformat()
        r2 = requests.get(f"{FRED_BASE}/release/dates",
                          params={"release_id": release_id, "api_key": _api_key(),
                                  "file_type": "json", "sort_order": "asc",
                                  "include_release_dates_with_no_data": "true",
                                  "realtime_start": today}, timeout=15)
        r2.raise_for_status()
        dates = [d["date"] for d in r2.json().get("release_dates", [])
                 if d["date"] >= today]
        return dates[0] if dates else None
    except Exception:
        return None
