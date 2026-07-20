"""Display helpers: formatting, color, and the structured morning briefing."""
from __future__ import annotations

from datetime import date, datetime

GREEN = "#16c784"   # up
RED = "#ea3943"     # down
MUTED = "#8b97a7"
ACCENT = "#5b8def"


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------
def fmt_num(v, decimals: int = 2) -> str:
    return "n/a" if v is None else f"{v:,.{decimals}f}"


def fmt_pct(v, decimals: int = 2) -> str:
    return "n/a" if v is None else f"{v:+.{decimals}f}%"


def fmt_signed(v, decimals: int = 2) -> str:
    return "n/a" if v is None else f"{v:+,.{decimals}f}"


def color_for(v) -> str:
    if v is None:
        return MUTED
    return GREEN if v >= 0 else RED


def arrow(v) -> str:
    if v is None:
        return "•"
    return "▲" if v >= 0 else "▼"


# ---------------------------------------------------------------------------
# Section access helpers
# ---------------------------------------------------------------------------
def section_rows(sections: dict, key: str) -> list[dict]:
    return sections.get(key, {}).get("rows", [])


def _by_asset(rows: list[dict]) -> dict:
    return {r["asset"]: r for r in rows}


# ---------------------------------------------------------------------------
# Morning briefing (computed live from cached sections)
# ---------------------------------------------------------------------------
def _direction(pct, up="Higher", down="Lower", flat="Flat", thresh=0.05):
    if pct is None:
        return (flat, 0)
    if pct > thresh:
        return (up, 1)
    if pct < -thresh:
        return (down, -1)
    return (flat, 0)


def build_briefing(sections: dict, news: list[dict]) -> dict:
    vf = _by_asset(section_rows(sections, "volatility_futures"))
    comm = _by_asset(section_rows(sections, "commodities"))
    fx = _by_asset(section_rows(sections, "fx_crypto"))
    yields = {r["maturity"]: r for r in section_rows(sections, "yields")}
    curve = sections.get("curve", {})
    macro = section_rows(sections, "macro")

    # Equity futures: average direction
    fut_keys = ["S&P 500 Futures", "Nasdaq 100 Futures", "Dow Futures",
                "Russell 2000 Futures"]
    fut_pcts = [vf[k]["pct_change"] for k in fut_keys
                if vf.get(k) and vf[k].get("pct_change") is not None]
    if fut_pcts:
        signs = {1 if p > 0.05 else -1 if p < -0.05 else 0 for p in fut_pcts}
        if signs == {1}:
            fut = ("Higher", 1)
        elif signs == {-1}:
            fut = ("Lower", -1)
        else:
            fut = ("Mixed", 0)
    else:
        fut = ("n/a", 0)

    # VIX
    vix = vf.get("VIX", {})
    vix_chg = vix.get("pct_change")

    # Risk tone from futures + VIX
    avg_fut = sum(fut_pcts) / len(fut_pcts) if fut_pcts else 0
    if avg_fut > 0.1 and (vix_chg is None or vix_chg < 0):
        risk = ("Positive", 1)
    elif avg_fut < -0.1 and (vix_chg is None or vix_chg > 0):
        risk = ("Negative", -1)
    else:
        risk = ("Neutral", 0)

    # Treasury yields direction (2Y & 10Y)
    y2 = yields.get("2Y", {}).get("change")
    y10 = yields.get("10Y", {}).get("change")
    ychgs = [c for c in (y2, y10) if c is not None]
    if not ychgs:
        ytone = ("n/a", 0)
    elif all(c > 0.005 for c in ychgs):
        ytone = ("Higher", -1)   # higher yields = risk-off-ish for bonds
    elif all(c < -0.005 for c in ychgs):
        ytone = ("Lower", 1)
    else:
        ytone = ("Mixed", 0)

    items = [
        {"label": "Equity Futures", "value": fut[0], "sign": fut[1]},
        {"label": "Treasury Yields", "value": ytone[0], "sign": -ytone[1]},
        {"label": "Yield Curve", "value": curve.get("shape", "n/a"),
         "sign": {"Normal": 1, "Flat": 0, "Inverted": -1}.get(curve.get("shape"), 0)},
    ]

    dxy = fx.get("U.S. Dollar Index (DXY)", {}).get("pct_change")
    d_dir, d_sign = _direction(dxy, "Stronger", "Weaker", "Flat")
    items.append({"label": "Dollar", "value": d_dir, "sign": d_sign})

    oil = comm.get("WTI Crude", {}).get("pct_change")
    o_dir, o_sign = _direction(oil)
    items.append({"label": "Oil (WTI)", "value": o_dir, "sign": o_sign})

    gold = comm.get("Gold", {}).get("pct_change")
    g_dir, g_sign = _direction(gold)
    items.append({"label": "Gold", "value": g_dir, "sign": g_sign})

    btc = fx.get("Bitcoin", {}).get("pct_change")
    b_dir, b_sign = _direction(btc)
    items.append({"label": "Bitcoin", "value": b_dir, "sign": b_sign})

    # Macro theme from latest inflation print
    cpi = next((m for m in macro if m["indicator"].startswith("CPI")), None)
    theme = "Awaiting next major data print."
    if cpi and cpi.get("latest") is not None:
        theme = (f"Inflation: CPI at {cpi['latest']:.1f}% YoY "
                 f"(period {cpi.get('period', 'n/a')}); "
                 "watch Fed path and yields.")

    # Events to watch: nearest upcoming macro releases
    today = date.today().isoformat()
    upcoming = sorted(
        [m for m in macro if m.get("next_release") and m["next_release"] >= today],
        key=lambda m: m["next_release"])
    if upcoming:
        watch = "; ".join(f"{m['indicator']} ({m['next_release']})"
                          for m in upcoming[:3])
    else:
        watch = "No major scheduled releases found."

    top = news[0] if news else None
    return {"risk": risk, "items": items, "macro_theme": theme,
            "watch": watch, "top_headline": top}
