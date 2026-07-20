"""Morning Markets & News Dashboard — modern Streamlit UI.

Reads from the local cache written by refresh.py. Each category shows its own
source and last-updated time, reflecting that data types refresh on different
schedules. Use the sidebar buttons to refresh a scope on demand.

Run:  streamlit run app.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from config import (BASE_DIR, JPM_CHART_TIMEFRAMES, JPM_FUNDS, MARKET_GROUPS)
from data import cache
from utils.formatting import (ACCENT, GREEN, MUTED, RED, build_briefing,
                              color_for, fmt_num, fmt_pct, fmt_signed,
                              latest_time, now_local, section_rows)

st.set_page_config(page_title="Morning Market — Markets", page_icon="📊",
                   layout="wide")

# ---------------------------------------------------------------------------
# Styling — modern dark, card-based
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
      html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
      .block-container { padding-top: 1.5rem; max-width: 1500px; }
      h1,h2,h3,h4 { letter-spacing:-0.01em; font-weight:700; }

      .hero { background:linear-gradient(135deg,#11161f 0%,#1a2230 100%);
              border:1px solid #232c3b; border-radius:16px; padding:20px 24px;
              margin-bottom:8px; }
      .hero h2 { margin:0 0 2px 0; }
      .chip { display:inline-flex; flex-direction:column; gap:2px;
              background:#10151e; border:1px solid #232c3b; border-radius:12px;
              padding:10px 14px; min-width:120px; }
      .chip .lbl { color:#8b97a7; font-size:0.7rem; text-transform:uppercase;
                   letter-spacing:0.6px; }
      .chip .val { font-size:1.05rem; font-weight:700; }

      .kpi { border:1px solid #232c3b; border-radius:14px; padding:14px 16px;
             background:#10151e; }
      .kpi .label { color:#8b97a7; font-size:0.72rem; text-transform:uppercase;
                    letter-spacing:0.6px; }
      .kpi .value { font-size:1.45rem; font-weight:700; margin-top:3px;
                    font-variant-numeric:tabular-nums; }
      .kpi .delta { font-size:0.82rem; margin-top:2px;
                    font-variant-numeric:tabular-nums; }
      .kpi .sub2 { color:#6b7686; font-size:0.7rem; margin-top:4px; }

      .jpm-big { background:linear-gradient(135deg,#0d1b2e 0%,#10233d 100%);
                 border:1px solid #25406b; border-radius:16px; padding:20px 22px; }
      .jpm-big .lbl { color:#9db4e0; font-size:0.72rem; letter-spacing:0.6px;
                      text-transform:uppercase; }
      .jpm-big .price { font-size:2.6rem; font-weight:700; line-height:1.1;
                        margin-top:4px; font-variant-numeric:tabular-nums; }
      .jpm-big .d { font-size:1rem; font-weight:600; margin-top:4px;
                    font-variant-numeric:tabular-nums; }
      .jpm-big .sub { color:#8b97a7; font-size:0.82rem; margin-top:6px; }

      .secsrc { color:#6b7686; font-size:0.74rem; margin:-6px 0 6px 0; }
      .news-card { border-bottom:1px solid #1d2530; padding:10px 0; }
      .news-meta { color:#8b97a7; font-size:0.76rem; }
      .cat { background:#1b2433; color:#9db4e0; border:1px solid #2a3850;
             border-radius:6px; padding:1px 7px; font-size:0.7rem; font-weight:600; }
      a { color:#cdd9ee !important; text-decoration:none; }
      a:hover { color:#fff !important; }
      [data-testid="stDataFrame"] { border:1px solid #232c3b; border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Refresh control
# ---------------------------------------------------------------------------
def run_refresh(scope: str) -> None:
    with st.spinner(f"Refreshing {scope}…"):
        proc = subprocess.run([sys.executable, str(BASE_DIR / "refresh.py"), scope],
                              capture_output=True, text=True, cwd=str(BASE_DIR))
    if proc.returncode == 0:
        st.success(f"Refreshed: {scope}")
    else:
        st.error("Refresh failed.")
        st.code(proc.stderr or proc.stdout)


snapshot = cache.read_snapshot()
sections = snapshot.get("sections", {})
news = cache.read_news()


def fetched_caption(*keys: str) -> str:
    stamp = latest_time(sections.get(k, {}).get("fetched_at") for k in keys)
    return stamp or "not yet fetched"


def section_source(key: str) -> str:
    return sections.get(key, {}).get("source", "—")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Controls")
    if st.button("🔄 Refresh All", use_container_width=True):
        run_refresh("all"); st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("Prices", use_container_width=True):
        run_refresh("market"); st.rerun()
    if c2.button("Rates", use_container_width=True):
        run_refresh("rates"); st.rerun()
    c3, c4 = st.columns(2)
    if c3.button("Macro", use_container_width=True):
        run_refresh("macro"); st.rerun()
    if c4.button("News", use_container_width=True):
        run_refresh("news"); st.rerun()

    st.divider()
    st.caption("**Refresh cadence**")
    st.caption("• Prices/FX/commodities/crypto — intraday & pre-6 AM")
    st.caption("• Yields & rates — when sources update (~daily)")
    st.caption("• Macro (CPI/PCE/GDP/jobs) — on official release only")
    st.divider()
    st.caption("Sources: FRED, Yahoo Finance, publisher RSS. Not investment advice.")

if not sections:
    st.title("📊 Morning Market")
    st.warning("No data yet. Click **Refresh All** in the sidebar "
               "or run `python refresh.py` once.")
    st.stop()

# ---------------------------------------------------------------------------
# Header + structured morning briefing
# ---------------------------------------------------------------------------
brief = build_briefing(sections, news)

st.markdown(
    f"""<div class="hero">
      <h2>📊 Morning Market — Markets &amp; Macro</h2>
      <div style="color:#8b97a7;font-size:0.85rem;">
        {now_local():%A, %B %d, %Y}
        &nbsp;·&nbsp; Overall last update: {fetched_caption(*sections.keys())}
      </div>
    </div>""",
    unsafe_allow_html=True,
)

st.markdown(f"**Macro theme:** {brief['macro_theme']}")
st.markdown(f"**Watch today:** {brief['watch']}")
if brief["top_headline"]:
    t = brief["top_headline"]
    st.markdown(f"**Top headline ({t['source']}):** [{t['title']}]({t['link']})")

st.divider()

# ---------------------------------------------------------------------------
# J.P. Morgan focus — stock (large box) + lead funds + price chart
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def load_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf
    h = yf.Ticker(ticker).history(period=period, interval=interval,
                                  auto_adjust=False)
    if h.empty or "Close" not in h:
        return pd.DataFrame()
    return h[["Close"]].dropna()


def _money(v, prefix="$"):
    return f"{prefix}{v:,.2f}" if v is not None else "n/a"


st.markdown("### 🏦 J.P. Morgan — Stock & Lead Funds")
jmap = {r["asset"]: r for r in section_rows(sections, "jpm_focus")}

jc1, jc2 = st.columns([1, 1.55])
with jc1:
    jpm = jmap.get("JPM", {})
    pct = jpm.get("pct_change")
    c = GREEN if (pct or 0) >= 0 else RED
    a = "▲" if (pct or 0) >= 0 else "▼"
    jpm_d = (f"{a} {fmt_signed(jpm.get('change'))} ({fmt_pct(pct)}) today")
    jpm_sub = (f"YTD {fmt_pct(jpm.get('ytd_pct'))} &nbsp;·&nbsp; "
               f"Prev close {_money(jpm.get('previous'))} &nbsp;·&nbsp; "
               f"as of {jpm.get('as_of', 'n/a')}")
    st.markdown(
        f"""<div class="jpm-big">
          <div class="lbl">JPMorgan Chase &amp; Co. · NYSE: JPM</div>
          <div class="price">{_money(jpm.get('latest'))}</div>
          <div class="d" style="color:{c}">{jpm_d}</div>
          <div class="sub">{jpm_sub}</div>
        </div>""",
        unsafe_allow_html=True)
with jc2:
    fcols = st.columns(3)
    for fcol, (tk, nm) in zip(fcols, JPM_FUNDS):
        fr = jmap.get(tk, {})
        p = fr.get("pct_change")
        fc = GREEN if (p or 0) >= 0 else RED
        fa = "▲" if (p or 0) >= 0 else "▼"
        fcol.markdown(
            f"""<div class="kpi"><div class="label">{tk}</div>
            <div class="value">{_money(fr.get('latest'))}</div>
            <div class="delta" style="color:{fc}">{fa} {fmt_pct(p)}</div>
            <div class="sub2">{nm}<br>YTD {fmt_pct(fr.get('ytd_pct'))}</div></div>""",
            unsafe_allow_html=True)

ctl1, ctl2 = st.columns([1.1, 1.3])
inst = ctl1.radio("Instrument", ["JPM"] + [f[0] for f in JPM_FUNDS],
                  horizontal=True, key="jpm_inst")
tf = ctl2.radio("Timeframe", list(JPM_CHART_TIMEFRAMES.keys()),
                horizontal=True, index=2, key="jpm_tf")
period, interval = JPM_CHART_TIMEFRAMES[tf]
hist = load_history(inst, period, interval)
if not hist.empty:
    fig = go.Figure(go.Scatter(
        x=hist.index, y=hist["Close"], mode="lines", name=inst,
        line=dict(color=ACCENT, width=2)))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Price ($)",
                      hovermode="x unified")
    fig.update_yaxes(gridcolor="#1d2530", tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)
    first, last = float(hist["Close"].iloc[0]), float(hist["Close"].iloc[-1])
    ret = (last / first - 1) * 100 if first else None
    st.markdown(f"<div class='secsrc'>{inst} · {tf} return {fmt_pct(ret)} · "
                f"Source: Yahoo Finance (delayed)</div>", unsafe_allow_html=True)
else:
    st.info(f"No chart data for {inst} ({tf}). Try a longer timeframe "
            "(some funds are newer than others).")

st.divider()

# ---------------------------------------------------------------------------
# Shared renderers
# ---------------------------------------------------------------------------
def color_cols(df: pd.DataFrame, cols: list[str]):
    def _c(col):
        return [f"color: {color_for(v)}" for v in col]
    return df.style.apply(_c, subset=[c for c in cols if c in df.columns])


def market_table(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)[["asset", "latest", "change", "pct_change",
                             "ytd_pct", "previous", "as_of"]]
    df.columns = ["Asset", "Last", "Chg", "% Chg", "YTD %", "Prev Close", "As of"]
    return df


def render_market(key: str):
    rows = section_rows(sections, key)
    if not rows:
        st.info("No data — refresh **Prices**.")
        return
    df = market_table(rows)
    styled = (color_cols(df, ["Chg", "% Chg", "YTD %"])
              .format({"Last": "{:,.2f}", "Chg": "{:+,.2f}", "% Chg": "{:+.2f}%",
                       "YTD %": "{:+.2f}%", "Prev Close": "{:,.2f}"}, na_rep="n/a"))
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.markdown(f"<div class='secsrc'>Source: {section_source(key)} · "
                f"Updated {fetched_caption(key)}</div>", unsafe_allow_html=True)


def section_header(title: str, *keys: str):
    st.subheader(title)


# ---------------------------------------------------------------------------
# Top KPI strip
# ---------------------------------------------------------------------------
def kpi(col, label, value, delta_txt, sign):
    c = {1: GREEN, 0: MUTED, -1: RED}[sign]
    arrow = "▲" if sign > 0 else ("▼" if sign < 0 else "•")
    col.markdown(
        f"""<div class="kpi"><div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="delta" style="color:{c}">{arrow} {delta_txt}</div></div>""",
        unsafe_allow_html=True)

vf = {r["asset"]: r for r in section_rows(sections, "volatility_futures")}
comm = {r["asset"]: r for r in section_rows(sections, "commodities")}
fx = {r["asset"]: r for r in section_rows(sections, "fx_crypto")}
yields_map = {r["maturity"]: r for r in section_rows(sections, "yields")}

def pct_kpi(col, label, row):
    p = row.get("pct_change")
    sign = 0 if p is None else (1 if p >= 0 else -1)
    val = f"{row.get('latest'):,.2f}" if row.get("latest") is not None else "n/a"
    txt = f"{p:+.2f}%" if p is not None else "n/a"
    kpi(col, label, val, txt, sign)

cols = st.columns(6)
pct_kpi(cols[0], "S&P 500 Fut", vf.get("S&P 500 Futures", {}))
pct_kpi(cols[1], "Nasdaq Fut", vf.get("Nasdaq 100 Futures", {}))
pct_kpi(cols[2], "VIX", vf.get("VIX", {}))
ten = yields_map.get("10Y", {})
ten_chg = ten.get("change")
kpi(cols[3], "10Y Yield",
    f"{ten.get('latest'):.2f}%" if ten.get("latest") is not None else "n/a",
    f"{ten_chg*100:+.0f} bps" if ten_chg is not None else "n/a",
    0 if ten_chg is None else (1 if ten_chg >= 0 else -1))
pct_kpi(cols[4], "Gold", comm.get("Gold", {}))
pct_kpi(cols[5], "Bitcoin", fx.get("Bitcoin", {}))

st.divider()

# ---------------------------------------------------------------------------
# 1. Volatility & Futures   2. Yield curve (side by side)
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    section_header(MARKET_GROUPS["volatility_futures"]["label"])
    render_market("volatility_futures")

with right:
    st.subheader("U.S. Treasury Yield Curve")
    curve = sections.get("curve", {})
    shape = curve.get("shape", "Unknown")
    spread = curve.get("spread_10y_2y")
    badge = {"Normal": GREEN, "Flat": "#c9a227", "Inverted": RED}.get(shape, MUTED)
    spread_txt = f"{spread*100:+.0f} bps" if spread is not None else "n/a"
    st.markdown(
        f"<span style='background:{badge};color:#0e1117;padding:3px 10px;"
        f"border-radius:10px;font-weight:700'>{shape}</span> "
        f"&nbsp; 2s10s: <b>{spread_txt}</b>", unsafe_allow_html=True)

    points = curve.get("points", [])
    if points:
        xs = [p["maturity"] for p in points]
        fig = go.Figure()
        comp = curve.get("comparison", {})
        for key, name, color in [("1y", "1 yr ago", "#4a5568"),
                                 ("1m", "1 mo ago", "#6b7d99"),
                                 ("1d", "Prev day", "#8fa8d6")]:
            cv = comp.get(key, {})
            ys = [cv.get(p["maturity"]) for p in points]
            if any(v is not None for v in ys):
                fig.add_trace(go.Scatter(x=xs, y=ys, name=name, mode="lines",
                              line=dict(color=color, width=1.5, dash="dot")))
        fig.add_trace(go.Scatter(x=xs, y=[p["yield"] for p in points],
                      name="Today", mode="lines+markers",
                      line=dict(color=ACCENT, width=3), marker=dict(size=7)))
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                          template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)",
                          xaxis_title="Maturity", yaxis_title="Yield (%)",
                          legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
                          hovermode="x unified")
        fig.update_yaxes(ticksuffix="%", gridcolor="#1d2530")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<div class='secsrc'>Source: {curve.get('source','—')} · "
                    f"Curve as of {curve.get('as_of','n/a')} · "
                    f"Updated {fetched_caption('curve')}</div>",
                    unsafe_allow_html=True)
    else:
        st.info("Yield curve unavailable — add FRED_API_KEY and refresh **Rates**.")

st.divider()

# ---------------------------------------------------------------------------
# 2b. Treasury yields table + spreads
# ---------------------------------------------------------------------------
st.subheader("Treasury Yields & Spreads")
yc1, yc2 = st.columns([1.1, 1])
with yc1:
    yrows = section_rows(sections, "yields")
    if yrows:
        ydf = pd.DataFrame(yrows)[["maturity", "latest", "change",
                                   "ytd_change", "previous", "as_of"]]
        ydf.columns = ["Maturity", "Yield %", "Chg", "YTD Chg", "Prev", "As of"]
        styled = (color_cols(ydf, ["Chg", "YTD Chg"])
                  .format({"Yield %": "{:.2f}", "Chg": "{:+.2f}",
                           "YTD Chg": "{:+.2f}", "Prev": "{:.2f}"}, na_rep="n/a"))
        st.dataframe(styled, hide_index=True, use_container_width=True, height=420)
    else:
        st.info("No yields — refresh **Rates**.")
    st.markdown(f"<div class='secsrc'>Source: {section_source('yields')} · "
                f"Updated {fetched_caption('yields')}</div>", unsafe_allow_html=True)

with yc2:
    srows = section_rows(sections, "spreads")
    if srows:
        sdf = pd.DataFrame(srows)[["spread", "latest_bps", "change_bps", "previous_bps"]]
        sdf.columns = ["Spread", "Now (bps)", "Δ (bps)", "Prev (bps)"]
        styled = (color_cols(sdf, ["Now (bps)", "Δ (bps)"])
                  .format({"Now (bps)": "{:+.0f}", "Δ (bps)": "{:+.0f}",
                           "Prev (bps)": "{:+.0f}"}, na_rep="n/a"))
        st.dataframe(styled, hide_index=True, use_container_width=True, height=420)
    else:
        st.info("No spreads — refresh **Rates**.")
    st.markdown("<div class='secsrc'>Negative = inverted. Source: U.S. Treasury via FRED</div>",
                unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# 3. Key rates    4. Credit spreads
# ---------------------------------------------------------------------------
kr1, kr2 = st.columns([1.3, 1])
with kr1:
    st.subheader("Key Interest & Money-Market Rates")
    krows = section_rows(sections, "key_rates")
    if krows:
        kdf = pd.DataFrame(krows)[["rate", "latest", "ytd_avg", "pct_change",
                                   "as_of", "source"]]
        kdf.columns = ["Rate", "Latest %", "Avg YTD %", "% Chg (1d)",
                       "As of", "Source"]
        styled = (color_cols(kdf, ["% Chg (1d)"])
                  .format({"Latest %": "{:.2f}", "Avg YTD %": "{:.2f}",
                           "% Chg (1d)": "{:+.2f}%"}, na_rep="n/a"))
        st.dataframe(styled, hide_index=True, use_container_width=True)
    else:
        st.info("No rates — refresh **Rates**.")
    st.markdown(f"<div class='secsrc'>Updated {fetched_caption('key_rates')}</div>",
                unsafe_allow_html=True)

with kr2:
    st.subheader("Credit Spreads")
    crows = section_rows(sections, "credit")
    if crows:
        cdf = pd.DataFrame(crows)[["name", "latest", "change", "previous", "as_of"]]
        cdf.columns = ["Series", "Latest %", "Chg", "Prev", "As of"]
        styled = (color_cols(cdf, ["Chg"])
                  .format({"Latest %": "{:.2f}", "Chg": "{:+.2f}",
                           "Prev": "{:.2f}"}, na_rep="n/a"))
        st.dataframe(styled, hide_index=True, use_container_width=True)
    else:
        st.info("No credit data — refresh **Rates**.")
    st.markdown(f"<div class='secsrc'>Source: {section_source('credit')} · "
                f"Updated {fetched_caption('credit')}</div>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# 4b. Fixed income ETFs   5. Commodities
# ---------------------------------------------------------------------------
fi1, fi2 = st.columns([1.2, 1])
with fi1:
    section_header(MARKET_GROUPS["fixed_income"]["label"])
    render_market("fixed_income")
with fi2:
    section_header(MARKET_GROUPS["commodities"]["label"])
    render_market("commodities")

st.divider()

# ---------------------------------------------------------------------------
# 6. FX & Crypto   7. Global indexes
# ---------------------------------------------------------------------------
g1, g2 = st.columns(2)
with g1:
    section_header(MARKET_GROUPS["fx_crypto"]["label"])
    render_market("fx_crypto")
with g2:
    section_header(MARKET_GROUPS["global_indexes"]["label"])
    render_market("global_indexes")

st.divider()

# ---------------------------------------------------------------------------
# 8. Macro indicators
# ---------------------------------------------------------------------------
st.subheader("Macroeconomic Indicators")
mrows = section_rows(sections, "macro")
if mrows:
    mdf = pd.DataFrame(mrows)[["indicator", "latest", "previous", "change",
                              "period", "next_release", "source"]]
    mdf.columns = ["Indicator", "Latest", "Previous", "Change", "Period",
                   "Next Release", "Source"]
    mdf["Next Release"] = mdf["Next Release"].map(lambda v: v if v else "n/a")
    styled = (color_cols(mdf, ["Change"])
              .format({"Latest": "{:.2f}", "Previous": "{:.2f}",
                       "Change": "{:+.2f}"}, na_rep="n/a"))
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.markdown(f"<div class='secsrc'>Updates on official release only · "
                f"Source: {section_source('macro')} · "
                f"Last checked {fetched_caption('macro')}</div>",
                unsafe_allow_html=True)
else:
    st.info("No macro data — refresh **Macro**.")

st.divider()

# ---------------------------------------------------------------------------
# 9. News
# ---------------------------------------------------------------------------
st.subheader("📰 Market-Moving Headlines")
categories = sorted({n["category"] for n in news})
chosen = st.multiselect("Filter by category", categories, default=[])
filtered = [n for n in news if not chosen or n["category"] in chosen]
if not filtered:
    st.info("No headlines — refresh **News**.")
for n in filtered:
    try:
        when = datetime.fromisoformat(n["published"]).strftime("%b %d, %I:%M %p")
    except Exception:
        when = ""
    st.markdown(
        f"<div class='news-card'>"
        f"<a href='{n['link']}' target='_blank'><b>{n['title']}</b></a><br>"
        f"<span class='news-meta'><span class='cat'>{n['category']}</span> &nbsp; "
        f"{n['source']} · {when}</span><br>"
        f"<span style='color:#c2cad6;font-size:0.9rem'>{n['summary']}</span></div>",
        unsafe_allow_html=True)
