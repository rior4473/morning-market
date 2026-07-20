"""Shared setup + mobile UI helpers for the phone dashboard.

Reuses the existing data layer in ../dashboard (config, data, utils) so there is
one refresh pipeline and one cache. This file is NOT a Streamlit page (only files
in pages/ become nav pages).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the shared dashboard package importable (works locally and on Streamlit Cloud).
DASH_DIR = Path(__file__).resolve().parent.parent / "dashboard"
if str(DASH_DIR) not in sys.path:
    sys.path.insert(0, str(DASH_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(DASH_DIR / ".env")

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from config import JPM_CHART_TIMEFRAMES, MARKET_GROUPS  # noqa: E402
from data import cache  # noqa: E402
from utils.formatting import (ACCENT, GREEN, MUTED, RED, build_briefing,  # noqa: E402
                              color_for, fmt_pct, fmt_time, latest_time,
                              now_local, section_rows, to_local)

# ---------------------------------------------------------------------------
# Mobile-first styling
# ---------------------------------------------------------------------------
MOBILE_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family:'Inter',sans-serif; }
  .block-container { padding:0.6rem 0.7rem 3rem; max-width:640px; }
  #MainMenu, footer { visibility:hidden; }
  h1,h2,h3 { letter-spacing:-0.01em; }

  .m-head { font-size:1.35rem; font-weight:700; margin:0; }
  .m-sub { color:#8b97a7; font-size:0.75rem; margin:2px 0 8px; }

  .m-brief { background:linear-gradient(135deg,#11161f,#1a2230);
             border:1px solid #232c3b; border-radius:14px; padding:12px 14px;
             margin:8px 0 12px; font-size:0.9rem; }
  .m-brief b { color:#cdd9ee; }
  .m-brief a { color:#9db4e0 !important; text-decoration:none; }

  .m-hgrid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:6px 0 12px; }
  .m-hcard { background:#10151e; border:1px solid #232c3b; border-radius:14px;
             padding:11px 13px; }
  .m-hlabel { color:#8b97a7; font-size:0.66rem; text-transform:uppercase;
              letter-spacing:0.5px; }
  .m-hval { font-size:1.28rem; font-weight:700; margin:2px 0 1px;
            font-variant-numeric:tabular-nums; }

  .m-panel { background:#0e131c; border:1px solid #1d2530; border-radius:14px;
             padding:2px 14px; margin:10px 0; }
  .m-ptitle { color:#cdd9ee; font-weight:700; font-size:0.92rem;
              padding:11px 0 8px; }
  .m-row { display:flex; justify-content:space-between; align-items:center;
           padding:9px 0; border-top:1px solid #161d27; }
  .m-name { color:#c2cad6; font-size:0.9rem; }
  .m-sub2 { color:#6b7686; font-size:0.72rem; }
  .m-ptitle2 { color:#cdd9ee; font-weight:700; font-size:0.92rem;
               padding:14px 2px 6px; border-bottom:1px solid #1d2530; }
  .m-wrap { background:#10151e; border:1px solid #232c3b; border-radius:12px;
            padding:12px 14px; margin:10px 0; }
  .m-wrap .lbl { color:#8b97a7; font-size:0.68rem; text-transform:uppercase;
                 letter-spacing:0.6px; margin-bottom:5px; }
  .m-wrap .txt { color:#dbe3ee; font-size:0.88rem; line-height:1.5; }
  .m-wrap .src { color:#6b7686; font-size:0.7rem; margin-top:7px; }
  .m-wrap .src a { color:#8fa8d6 !important; }
  .m-crow { display:flex; justify-content:space-between; align-items:center;
            padding:6px 0; }
  /* keep columns side-by-side on phones (don't stack) */
  [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:6px !important; }
  [data-testid="stColumn"] { min-width:0 !important; }
  /* compact the little chart buttons */
  div[data-testid="stButton"] button { padding:4px 0; min-height:34px; }
  .m-vals { display:flex; gap:12px; align-items:baseline; white-space:nowrap; }
  .m-val { font-weight:600; font-variant-numeric:tabular-nums; }
  .m-d { font-size:0.82rem; font-variant-numeric:tabular-nums; }
  .m-src { color:#5f6a78; font-size:0.7rem; margin:-4px 0 2px; }
</style>
"""


def setup(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="📊", layout="centered")
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def load() -> tuple[dict, list]:
    snap = cache.read_snapshot()
    return snap.get("sections", {}), cache.read_news()


# ---------------------------------------------------------------------------
# Formatting + row builders
# ---------------------------------------------------------------------------
def fmt_price(v, dec: int = 2) -> str:
    return "n/a" if v is None else f"{v:,.{dec}f}"


def _delta_html(dv, ds: str) -> str:
    if dv is None:
        return f"<span class='m-d' style='color:{MUTED}'>—</span>"
    c = color_for(dv)
    a = "▲" if dv > 0 else ("▼" if dv < 0 else "·")
    return f"<span class='m-d' style='color:{c}'>{a}&nbsp;{ds}</span>"


def by_asset(sections: dict, key: str) -> dict:
    return {r["asset"]: r for r in section_rows(sections, key)}


def render_hero(cards: list[tuple]) -> None:
    """cards: list of (label, value_str, delta_value, delta_str)."""
    items = "".join(
        f"<div class='m-hcard'><div class='m-hlabel'>{lab}</div>"
        f"<div class='m-hval'>{val}</div>{_delta_html(dv, ds)}</div>"
        for lab, val, dv, ds in cards)
    st.markdown(f"<div class='m-hgrid'>{items}</div>", unsafe_allow_html=True)


def render_panel(title: str, rows: list[tuple], source: str | None = None) -> None:
    """rows: list of (name, value_str, delta_value, delta_str)."""
    body = "".join(
        f"<div class='m-row'><span class='m-name'>{name}</span>"
        f"<span class='m-vals'><span class='m-val'>{val}</span>"
        f"{_delta_html(dv, ds)}</span></div>"
        for name, val, dv, ds in rows)
    src = f"<div class='m-src'>{source}</div>" if source else ""
    st.markdown(f"<div class='m-panel'><div class='m-ptitle'>{title}</div>"
                f"{body}</div>{src}", unsafe_allow_html=True)


def render_market_wrap(sections: dict) -> None:
    """3-sentence 'why the market moved' synopsis with source links."""
    w = sections.get("market_wrap") or {}
    text = w.get("text")
    if not text:
        return
    srcs = w.get("sources") or []
    links = " · ".join(
        f"<a href='{s['url']}' target='_blank'>{s['source']}</a>" if s.get("url")
        else s.get("source", "") for s in srcs)
    tag = "researched by Claude" if w.get("mode") == "claude" else "from wire headlines"
    label = f"Why the market moved · {w.get('as_of') or 'last session'}"
    st.markdown(
        f"<div class='m-wrap'><div class='lbl'>{label}</div>"
        f"<div class='txt'>{text}</div>"
        f"<div class='src'>{links}{' · ' if links else ''}{tag}</div></div>",
        unsafe_allow_html=True)


def price_row(sections: dict, group: str, asset: str, label: str | None = None):
    r = by_asset(sections, group).get(asset, {})
    p = r.get("pct_change")
    return (label or asset, fmt_price(r.get("latest")), p, fmt_pct(p))


# ---------------------------------------------------------------------------
# Interactive price chart (tap a row -> pop-up with timeframe toggles)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def load_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf
    h = yf.Ticker(ticker).history(period=period, interval=interval,
                                  auto_adjust=False)
    if h.empty or "Close" not in h:
        return pd.DataFrame()
    return h[["Close"]].dropna()


@st.dialog("Price chart", width="large")
def chart_dialog(ticker: str, label: str) -> None:
    st.markdown(f"**{label}** &nbsp;·&nbsp; `{ticker}`")
    tf = st.radio("Timeframe", list(JPM_CHART_TIMEFRAMES.keys()),
                  horizontal=True, index=2, key=f"tf_{ticker}")
    period, interval = JPM_CHART_TIMEFRAMES[tf]
    hist = load_history(ticker, period, interval)
    if hist.empty:
        st.info(f"No data for {tf}. Try a longer window.")
        return
    fig = go.Figure(go.Scatter(x=hist.index, y=hist["Close"], mode="lines",
                    line=dict(color=ACCENT, width=2)))
    fig.update_layout(height=300, margin=dict(l=6, r=6, t=6, b=6),
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified")
    fig.update_yaxes(gridcolor="#1d2530")
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False})
    first, last = float(hist["Close"].iloc[0]), float(hist["Close"].iloc[-1])
    ret = ((last / first - 1) * 100) if first else None
    st.caption(f"{tf} return {fmt_pct(ret)} · Yahoo Finance (delayed)")


def render_chart_panel(sections: dict, title: str, items: list[tuple],
                       source: str | None = None) -> None:
    """Each row is tappable (📈) to open the price-chart pop-up.

    items: list of (group, asset, label).
    """
    st.markdown(f"<div class='m-ptitle2'>{title}</div>", unsafe_allow_html=True)
    for group, asset, label in items:
        r = by_asset(sections, group).get(asset, {})
        p = r.get("pct_change")
        val = fmt_price(r.get("latest"))
        c1, c2 = st.columns([0.82, 0.18], vertical_alignment="center")
        c1.markdown(
            f"<div class='m-crow'><span class='m-name'>{label}</span>"
            f"<span class='m-vals'><span class='m-val'>{val}</span>"
            f"{_delta_html(p, fmt_pct(p))}</span></div>", unsafe_allow_html=True)
        ticker = MARKET_GROUPS.get(group, {}).get("tickers", {}).get(asset, asset)
        if c2.button("📈", key=f"chart_{group}_{asset}"):
            chart_dialog(ticker, label)
    if source:
        st.markdown(f"<div class='m-src'>{source}</div>", unsafe_allow_html=True)
