"""FX & Crypto page — currencies and crypto detail."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _shared import load, price_row, render_panel, setup, st  # noqa: E402

setup("FX & Crypto")

sections, _ = load()
st.markdown("<div class='m-head'>💱 Currencies & Crypto</div>",
            unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.page_link("app.py", label="🏠 Home")
c2.page_link("pages/1_Rates.py", label="📉 Rates")
c3.page_link("pages/2_FX_and_Crypto.py", label="💱 FX")

render_panel("Currencies", [
    price_row(sections, "fx_crypto", "U.S. Dollar Index (DXY)", "Dollar Index (DXY)"),
    price_row(sections, "fx_crypto", "EUR/USD", "EUR/USD"),
    price_row(sections, "fx_crypto", "USD/JPY", "USD/JPY"),
    price_row(sections, "fx_crypto", "GBP/USD", "GBP/USD"),
    price_row(sections, "fx_crypto", "USD/CNY", "USD/CNY"),
], source="Yahoo Finance (delayed)")

render_panel("Crypto", [
    price_row(sections, "fx_crypto", "Bitcoin", "Bitcoin"),
], source="Yahoo Finance (delayed)")
