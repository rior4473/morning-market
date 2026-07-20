"""Yahoo-Finance-based fetcher for any instrument group (prices/levels)."""
from __future__ import annotations

from datetime import datetime

import yfinance as yf

from config import MARKET_GROUPS


def _row(label: str, ticker: str) -> dict:
    base = {"asset": label, "ticker": ticker, "latest": None, "previous": None,
            "change": None, "pct_change": None, "ytd_pct": None, "as_of": None}
    try:
        hist = yf.Ticker(ticker).history(period="1y", auto_adjust=False)
        if hist.empty or "Close" not in hist:
            return base
        closes = hist["Close"].dropna()
        # Yahoo sometimes appends a stale weekend bar that merely repeats the
        # Friday close (seen on index series like ^990100-USD-STRD). Left in, it
        # reports a 0.00% daily change and hides the real last session. Drop a
        # weekend-dated final bar only when it's flat vs. the prior close, so
        # genuinely weekend-traded assets (crypto, FX) are unaffected.
        if len(closes) >= 2 and closes.index[-1].weekday() >= 5:
            prev = float(closes.iloc[-2])
            if prev and abs(float(closes.iloc[-1]) - prev) / abs(prev) < 5e-4:
                closes = closes.iloc[:-1]
        if len(closes) < 2:
            return base

        latest = float(closes.iloc[-1])
        previous = float(closes.iloc[-2])
        change = latest - previous
        pct = (change / previous) * 100 if previous else None

        year = datetime.now().year
        ytd_slice = closes[closes.index.year == year]
        ytd_base = float(ytd_slice.iloc[0]) if not ytd_slice.empty else None
        ytd_pct = ((latest - ytd_base) / ytd_base * 100) if ytd_base else None

        return {"asset": label, "ticker": ticker, "latest": latest,
                "previous": previous, "change": change, "pct_change": pct,
                "ytd_pct": ytd_pct, "as_of": closes.index[-1].strftime("%Y-%m-%d")}
    except Exception:
        return base


def fetch_group(group_key: str) -> dict:
    """Return {rows, source} for one MARKET_GROUPS entry."""
    cfg = MARKET_GROUPS[group_key]
    rows = [_row(name, sym) for name, sym in cfg["tickers"].items()]
    return {"rows": rows, "source": cfg["source"]}


def fetch_all_market() -> dict:
    return {key: fetch_group(key) for key in MARKET_GROUPS}
