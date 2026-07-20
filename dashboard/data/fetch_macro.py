"""Macro indicators (CPI, PCE, unemployment, GDP) from FRED.

These only change when a new official print is released; the fetch is cheap and
idempotent, so it can run daily and will simply show the same numbers until the
next release. Next-release dates are best-effort from FRED's release calendar.
"""
from __future__ import annotations

import pandas as pd

from config import MACRO
from data.fred import get_series, next_release_date


def _transform(s: pd.Series, kind: str) -> pd.Series:
    if kind == "yoy":
        # monthly index -> YoY %; 12-period change
        return (s / s.shift(12) - 1.0) * 100.0
    return s  # "level": value is already the reading (rate or growth %)


def fetch_macro() -> dict:
    rows = []
    for label, cfg in MACRO.items():
        try:
            raw = get_series(cfg["series"], start="2018-01-01")
            series = _transform(raw, cfg["transform"]).dropna()
            if series.empty:
                raise ValueError("no data")
            latest = float(series.iloc[-1])
            previous = float(series.iloc[-2]) if len(series) >= 2 else None
            change = (latest - previous) if previous is not None else None
            period = series.index[-1].strftime("%Y-%m-%d")
            rows.append({
                "indicator": label,
                "latest": latest,
                "previous": previous,
                "change": change,
                "unit": cfg["unit"],
                "period": period,
                "next_release": next_release_date(cfg["series"]),
                "source": cfg["source"],
            })
        except Exception:
            rows.append({"indicator": label, "latest": None, "previous": None,
                         "change": None, "unit": cfg["unit"], "period": None,
                         "next_release": None, "source": cfg["source"]})
    return {"rows": rows, "source": "FRED (BLS/BEA)"}
