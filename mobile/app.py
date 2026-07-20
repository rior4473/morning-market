"""Morning Market — phone edition (main page).

Curated, mobile-first view. Reads the shared cache written by the 6 AM refresh.
Extra detail lives on the Rates and FX & Crypto pages (sidebar / links below).
"""
from __future__ import annotations

import subprocess
import sys

from _shared import (DASH_DIR, by_asset, fmt_pct, fmt_price, latest_time, load,
                     now_local, render_hero, render_chart_panel,
                     render_market_wrap, render_panel, section_rows, setup, st)

setup("Morning Market")

sections, _ = load()
if not sections:
    st.title("📊 Morning Market")
    st.warning("No data yet. Run the refresh once (or wait for the 6 AM job).")
    st.stop()

snap_time = latest_time(s.get("fetched_at") for s in sections.values())

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(f"<div class='m-head'>📊 Morning Market</div>"
            f"<div class='m-sub'>{now_local():%A, %B %d} · updated {snap_time}</div>",
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.page_link("app.py", label="🏠 Home")
c2.page_link("pages/1_Rates.py", label="📉 Rates")
c3.page_link("pages/2_FX_and_Crypto.py", label="💱 FX")

if st.button("🔄 Refresh now", use_container_width=True):
    with st.spinner("Fetching latest…"):
        subprocess.run([sys.executable, str(DASH_DIR / "refresh.py"), "all"],
                       cwd=str(DASH_DIR))
    st.rerun()

# ---------------------------------------------------------------------------
# Why the market moved (previous trading day)
# ---------------------------------------------------------------------------
render_market_wrap(sections)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
def hero_card(group, asset, label):
    r = by_asset(sections, group).get(asset, {})
    p = r.get("pct_change")
    return (label, fmt_price(r.get("latest")), p, fmt_pct(p))

render_hero([
    hero_card("equity_index", "S&P 500", "S&P 500"),
    hero_card("equity_index", "Nasdaq Composite", "Nasdaq"),
    hero_card("global_indexes", "MSCI World", "MSCI World"),
    hero_card("jpm_focus", "JPM", "JPMorgan"),
    hero_card("commodities", "Gold", "Gold"),
    hero_card("commodities", "Silver", "Silver"),
])

# ---------------------------------------------------------------------------
# Equities & volatility (cash + futures for each index)
# ---------------------------------------------------------------------------
render_chart_panel(sections, "Equities & Volatility", [
    ("equity_index", "S&P 500", "S&P 500"),
    ("volatility_futures", "S&P 500 Futures", "S&P 500 fut"),
    ("equity_index", "Nasdaq Composite", "Nasdaq Comp"),
    ("volatility_futures", "Nasdaq 100 Futures", "Nasdaq fut"),
    ("equity_index", "Dow Jones", "Dow Jones"),
    ("volatility_futures", "Dow Futures", "Dow fut"),
    ("equity_index", "Russell 2000", "Russell 2000"),
    ("volatility_futures", "Russell 2000 Futures", "Russell fut"),
    ("volatility_futures", "VIX", "VIX"),
], source="Yahoo Finance (delayed) · tap 📈 for chart")

# ---------------------------------------------------------------------------
# Key rates (level % + 1-day % change)
# ---------------------------------------------------------------------------
kr = {r["rate"]: r for r in section_rows(sections, "key_rates")}

def rate_row(name, label):
    r = kr.get(name, {})
    v = r.get("latest")
    p = r.get("pct_change")
    return (label, f"{v:.2f}%" if v is not None else "n/a", p, fmt_pct(p))

render_panel("Key Rates", [
    rate_row("Fed Target Range — Upper", "Fed target (upper)"),
    rate_row("Fed Target Range — Lower", "Fed target (lower)"),
    rate_row("Effective Fed Funds (EFFR)", "EFFR"),
    rate_row("SOFR", "SOFR"),
    rate_row("Interest on Reserves (IORB)", "IORB"),
], source="FRED · latest / 1-day % change")

# ---------------------------------------------------------------------------
# Bonds & commodities
# ---------------------------------------------------------------------------
render_chart_panel(sections, "Bonds & Commodities", [
    ("fixed_income", "U.S. Agg Bond (AGG)", "AGG (US Agg)"),
    ("commodities", "Gold", "Gold"),
    ("commodities", "WTI Crude", "WTI crude"),
    ("commodities", "Brent Crude", "Brent crude"),
    ("commodities", "Silver", "Silver"),
], source="Yahoo Finance (delayed) · tap 📈 for chart")

# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------
render_chart_panel(sections, "Global Indexes", [
    ("global_indexes", "STOXX 600", "STOXX 600"),
    ("global_indexes", "FTSE 100", "FTSE 100"),
    ("global_indexes", "MSCI World", "MSCI World"),
], source="Yahoo Finance (delayed) · tap 📈 for chart")

# ---------------------------------------------------------------------------
# Macro (latest reading + change from prior print)
# ---------------------------------------------------------------------------
macro = {r["indicator"]: r for r in section_rows(sections, "macro")}

def macro_row(name, label):
    r = macro.get(name, {})
    v = r.get("latest")
    chg = r.get("change")
    return (f"{label}<br><span class='m-sub2'>as of {r.get('period', 'n/a')}</span>",
            f"{v:.2f}%" if v is not None else "n/a",
            chg, f"{chg:+.2f}" if chg is not None else "n/a")

render_panel("Macro Indicators", [
    macro_row("CPI (YoY)", "CPI (YoY)"),
    macro_row("Core PCE (YoY)", "Core PCE (YoY)"),
    macro_row("Unemployment Rate", "Unemployment"),
    macro_row("Real GDP (QoQ SAAR)", "Real GDP (QoQ)"),
], source="FRED (BLS/BEA) · updates on official release")

st.caption("Not investment advice · sources: Yahoo Finance, U.S. Treasury, FRED")
