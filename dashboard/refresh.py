"""Fetch data for a given scope and write the cache.

Usage:
    python refresh.py            # scope = all
    python refresh.py market     # prices/futures/fx/commodities/global indexes
    python refresh.py rates      # yields, spreads, key rates, credit, curve
    python refresh.py macro      # CPI, PCE, unemployment, GDP
    python refresh.py news       # headlines only

Different scopes let you schedule each data type at its natural cadence.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from config import MARKET_GROUPS, SCOPE_SECTIONS
from data import cache
from data.fetch_macro import fetch_macro
from data.fetch_market import fetch_group
from data.fetch_news import fetch_news
from data.fetch_rates import (fetch_credit, fetch_key_rates, fetch_spreads,
                              fetch_yield_curve, fetch_yields)
from data.market_wrap import build_wrap


def refresh_market(want: set[str], out: dict, errors: list[str]) -> None:
    for key in MARKET_GROUPS:
        if key not in want:
            continue
        try:
            out[key] = fetch_group(key)
            print(f"  {key}: {len(out[key]['rows'])} items")
        except Exception as e:
            errors.append(f"{key}: {e}")


def refresh_rates(want: set[str], out: dict, errors: list[str]) -> None:
    yields = None
    if "yields" in want:
        try:
            yields = fetch_yields()
            out["yields"] = yields
            print(f"  yields: {len(yields['rows'])} maturities")
        except Exception as e:
            errors.append(f"yields: {e}")
    if "key_rates" in want:
        try:
            out["key_rates"] = fetch_key_rates()
            print(f"  key_rates: {len(out['key_rates']['rows'])} rates")
        except Exception as e:
            errors.append(f"key_rates: {e}")
    if "credit" in want:
        try:
            out["credit"] = fetch_credit()
            print(f"  credit: {len(out['credit']['rows'])} spreads")
        except Exception as e:
            errors.append(f"credit: {e}")
    if "spreads" in want and yields is not None:
        try:
            effr = next((r for r in out.get("key_rates", {}).get("rows", [])
                         if "EFFR" in r["rate"]), None)
            effr_l = effr["latest"] if effr else None
            effr_p = effr["previous"] if effr else None
            out["spreads"] = fetch_spreads(yields["rows"], effr_l, effr_p)
            print(f"  spreads: {len(out['spreads']['rows'])} spreads")
        except Exception as e:
            errors.append(f"spreads: {e}")
    if "curve" in want:
        try:
            curve = fetch_yield_curve()
            out["curve"] = curve
            if curve.get("points"):
                cache.append_yield_history(curve["points"], curve.get("as_of"))
            print(f"  curve: shape={curve.get('shape')}")
        except Exception as e:
            errors.append(f"curve: {e}")


def refresh_wrap() -> None:
    """Rebuild the 3-sentence 'why the market moved' synopsis from fresh cache."""
    snap = cache.read_snapshot()
    wrap = build_wrap(snap.get("sections", {}), cache.read_news())
    cache.update_sections({"market_wrap": wrap})
    print(f"  market_wrap: {wrap['mode']} mode")


def main(scope: str) -> int:
    started = datetime.now()
    print(f"[{started:%Y-%m-%d %H:%M:%S}] Refresh started (scope={scope})")

    if scope == "news":
        try:
            cache.write_news(fetch_news())
            print("  news refreshed")
            refresh_wrap()
        except Exception as e:
            print(f"  news error: {e}")
        return 0

    want = set(SCOPE_SECTIONS.get(scope, SCOPE_SECTIONS["all"]))
    out: dict = {}
    errors: list[str] = []

    refresh_market(want, out, errors)
    refresh_rates(want, out, errors)

    if "macro" in want:
        try:
            out["macro"] = fetch_macro()
            print(f"  macro: {len(out['macro']['rows'])} indicators")
        except Exception as e:
            errors.append(f"macro: {e}")

    if out:
        cache.update_sections(out)

    # News refreshes alongside any market/all run
    if scope in ("all", "market"):
        try:
            cache.write_news(fetch_news())
            print("  news refreshed")
        except Exception as e:
            errors.append(f"news: {e}")
        try:
            refresh_wrap()
        except Exception as e:
            errors.append(f"market_wrap: {e}")

    if errors:
        print("  WARNINGS:")
        for e in errors:
            print(f"    - {e}")

    elapsed = (datetime.now() - started).total_seconds()
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Done in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    scope_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        sys.exit(main(scope_arg))
    except Exception:
        traceback.print_exc()
        sys.exit(1)
