"""Treasury yields, spreads, policy/money-market rates, credit, and the curve.

Yields/curve/spreads use FRED when a key is set, otherwise fall back to the
keyless U.S. Treasury par-yield feed so they work out of the box. Money-market
rates, credit spreads, and macro require a (free) FRED key.
"""
from __future__ import annotations

import os
from datetime import date
from functools import lru_cache

import pandas as pd

from config import CREDIT_SPREADS, KEY_RATES, SPREADS, YIELD_CURVE
from data import treasury
from data.fred import get_series, latest_with_change


def _metrics(s: pd.Series) -> dict:
    """latest/previous/change/ytd/as_of from a date-indexed yield series."""
    if s is None or s.empty:
        return {"latest": None, "previous": None, "change": None,
                "ytd_change": None, "as_of": None}
    latest = float(s.iloc[-1])
    previous = float(s.iloc[-2]) if len(s) >= 2 else None
    change = (latest - previous) if previous is not None else None
    year = date.today().year
    prior = s[s.index < pd.Timestamp(f"{year}-01-01")]
    base = float(prior.iloc[-1]) if not prior.empty else None
    ytd = (latest - base) if base is not None else None
    return {"latest": latest, "previous": previous, "change": change,
            "ytd_change": ytd, "as_of": s.index[-1].strftime("%Y-%m-%d")}


@lru_cache(maxsize=1)
def load_yield_series() -> tuple[dict, str]:
    """Per-maturity yield Series (percent) + source label.

    Tries FRED first (if key present and returns data); else U.S. Treasury feed.
    """
    start = f"{date.today().year - 2}-01-01"
    if os.getenv("FRED_API_KEY", "").strip():
        out, any_data = {}, False
        for label, (series_id, _y) in YIELD_CURVE.items():
            try:
                s = get_series(series_id, start=start)
            except Exception:
                s = pd.Series(dtype=float)
            out[label] = s
            any_data = any_data or not s.empty
        if any_data:
            return out, "U.S. Treasury via FRED"

    # Fallback: keyless Treasury par-yield feed
    df = treasury.get_curve_df(years=3)
    out = {lbl: (df[lbl].dropna() if lbl in df.columns else pd.Series(dtype=float))
           for lbl in YIELD_CURVE}
    return out, "U.S. Treasury (Daily Par Yields)"


def fetch_yields() -> dict:
    series_map, source = load_yield_series()
    rows = [{"maturity": label, **_metrics(series_map.get(label))}
            for label in YIELD_CURVE]
    return {"rows": rows, "source": source}


def fetch_key_rates() -> dict:
    rows = []
    for label, (series_id, source) in KEY_RATES.items():
        try:
            d = latest_with_change(series_id)
        except Exception:
            d = {"latest": None, "previous": None, "change": None,
                 "pct_change": None, "ytd_change": None, "ytd_avg": None,
                 "as_of": None}
        rows.append({"rate": label, "series_id": series_id, "source": source, **d})
    return {"rows": rows, "source": "FRED"}


def fetch_credit() -> dict:
    rows = []
    for label, (series_id, source) in CREDIT_SPREADS.items():
        try:
            d = latest_with_change(series_id)
        except Exception:
            d = {"latest": None, "previous": None, "change": None,
                 "pct_change": None, "ytd_change": None, "ytd_avg": None,
                 "as_of": None}
        rows.append({"name": label, "series_id": series_id, "source": source, **d})
    return {"rows": rows, "source": "ICE BofA / Moody's via FRED"}


def fetch_spreads(yield_rows: list[dict], effr_latest: float | None,
                  effr_prev: float | None) -> dict:
    by_mat = {r["maturity"]: r for r in yield_rows}

    def val(token: str, field: str):
        if token == "EFFR":
            return effr_latest if field == "latest" else effr_prev
        r = by_mat.get(token)
        return r.get(field) if r else None

    rows = []
    for name, (a, b) in SPREADS.items():
        a_l, b_l = val(a, "latest"), val(b, "latest")
        a_p, b_p = val(a, "previous"), val(b, "previous")
        latest = (a_l - b_l) * 100 if (a_l is not None and b_l is not None) else None
        prev = (a_p - b_p) * 100 if (a_p is not None and b_p is not None) else None
        change = (latest - prev) if (latest is not None and prev is not None) else None
        rows.append({"spread": name, "latest_bps": latest,
                     "previous_bps": prev, "change_bps": change})
    return {"rows": rows, "source": "U.S. Treasury (+ EFFR via FRED)"}


def fetch_yield_curve() -> dict:
    series_map, source = load_yield_series()

    def curve_on_or_before(target: pd.Timestamp) -> dict[str, float | None]:
        out = {}
        for label, s in series_map.items():
            if s is None or s.empty:
                out[label] = None
                continue
            sub = s[s.index <= target]
            out[label] = float(sub.iloc[-1]) if not sub.empty else None
        return out

    today_ts = pd.Timestamp(date.today())
    today_curve = curve_on_or_before(today_ts)

    points, latest_as_of = [], None
    for label, (series_id, years) in YIELD_CURVE.items():
        s = series_map.get(label)
        as_of = s.index[-1].strftime("%Y-%m-%d") if (s is not None and not s.empty) else None
        if as_of and (latest_as_of is None or as_of > latest_as_of):
            latest_as_of = as_of
        points.append({"maturity": label, "years": years,
                       "yield": today_curve[label], "as_of": as_of})

    comparison = {
        "1d": curve_on_or_before(today_ts - pd.Timedelta(days=1)),
        "1m": curve_on_or_before(today_ts - pd.DateOffset(months=1)),
        "1y": curve_on_or_before(today_ts - pd.DateOffset(years=1)),
    }

    y10, y2 = today_curve.get("10Y"), today_curve.get("2Y")
    spread = (y10 - y2) if (y10 is not None and y2 is not None) else None
    if spread is None:
        shape = "Unknown"
    elif spread < -0.05:
        shape = "Inverted"
    elif spread < 0.20:
        shape = "Flat"
    else:
        shape = "Normal"

    return {"points": points, "comparison": comparison, "shape": shape,
            "spread_10y_2y": spread, "as_of": latest_as_of, "source": source}
