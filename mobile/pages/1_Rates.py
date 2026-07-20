"""Rates page — full U.S. Treasury yield curve + yields table."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402

from _shared import (ACCENT, GREEN, MUTED, RED, fmt_pct, load,  # noqa: E402
                     render_panel, section_rows, setup, st)

setup("Rates")

sections, _ = load()
st.markdown("<div class='m-head'>📉 Treasury Yields & Curve</div>",
            unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.page_link("app.py", label="🏠 Home")
c2.page_link("pages/1_Rates.py", label="📉 Rates")
c3.page_link("pages/2_FX_and_Crypto.py", label="💱 FX")

curve = sections.get("curve", {})
shape = curve.get("shape", "Unknown")
spread = curve.get("spread_10y_2y")
badge = {"Normal": GREEN, "Flat": "#c9a227", "Inverted": RED}.get(shape, MUTED)
spread_txt = f"{spread * 100:+.0f} bps" if spread is not None else "n/a"
st.markdown(
    f"<div style='margin:6px 0'><span style='background:{badge};color:#0e1117;"
    f"padding:3px 10px;border-radius:10px;font-weight:700'>{shape}</span> "
    f"&nbsp; 2s10s: <b>{spread_txt}</b></div>", unsafe_allow_html=True)

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
                          line=dict(color=color, width=1.4, dash="dot")))
    fig.add_trace(go.Scatter(x=xs, y=[p["yield"] for p in points], name="Today",
                  mode="lines+markers", line=dict(color=ACCENT, width=3),
                  marker=dict(size=6)))
    fig.update_layout(height=300, margin=dict(l=6, r=6, t=6, b=6),
                      template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Yield (%)",
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right",
                                  font=dict(size=10)), hovermode="x unified")
    fig.update_yaxes(ticksuffix="%", gridcolor="#1d2530")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"<div class='m-src'>Source: {curve.get('source', '—')} · "
                f"as of {curve.get('as_of', 'n/a')}</div>", unsafe_allow_html=True)
else:
    st.info("Yield curve unavailable — try Refresh on the Home page.")

# Yields table (maturity · yield · 1-day change in bps)
yrows = section_rows(sections, "yields")
rows = []
for r in yrows:
    y = r.get("latest")
    chg = r.get("change")
    rows.append((r["maturity"], f"{y:.2f}%" if y is not None else "n/a",
                 chg, f"{chg * 100:+.0f} bps" if chg is not None else "n/a"))
if rows:
    render_panel("Yields — level & 1-day change", rows,
                 source="U.S. Treasury · change in basis points")
