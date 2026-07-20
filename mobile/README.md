# Morning Market — Phone Edition

A curated, mobile-first version of the markets dashboard, designed to open on your
phone each morning. Reuses the same data layer as `../dashboard` (one refresh, one
cache) and deploys free to **Streamlit Community Cloud** so it's always available —
even when your Mac is off.

## What's on it
- **Home:** briefing summary (macro theme + top headline), hero cards (S&P 500,
  Nasdaq, MSCI World, JPMorgan, Gold, Silver), then panels for Equities & Volatility
  (cash + futures), Key Rates (Fed target, EFFR, SOFR, IORB), Bonds & Commodities
  (AGG, Gold, WTI, Brent, Silver), Global (STOXX 600, FTSE 100, MSCI World), Macro
  (CPI, Core PCE, Unemployment, Real GDP).
- **Rates page:** full Treasury yield curve chart + yields table (1M–30Y).
- **FX & Crypto page:** DXY, EUR/USD, USD/JPY, GBP/USD, USD/CNY, Bitcoin, Ethereum.

All keyless (Yahoo Finance, U.S. Treasury, FRED's public CSV endpoint).

## Try it on your phone right now (local, same Wi-Fi)
```bash
cd "/Users/ricardoorozco/Claude intern dashboard"
dashboard/.venv/bin/streamlit run mobile/app.py --server.address 0.0.0.0 --server.port 8502
```
Then on your phone (same Wi-Fi) open `http://<your-mac-ip>:8502`
(find the IP with `ipconfig getifaddr en0`). Add to Home Screen for an app icon.
This only works while your Mac is awake — the cloud deploy below fixes that.

## Deploy to Streamlit Cloud (always-on, auto-refresh at 6 AM)

1. **Put the project on GitHub** (from the project root):
   ```bash
   git init && git add -A && git commit -m "Markets dashboard + phone edition"
   gh repo create markets-dashboard --private --source=. --push
   ```
   (or create a repo on github.com and `git remote add origin … && git push -u origin main`)

2. **Deploy the app:** go to https://share.streamlit.io → *New app* →
   pick your repo → set **Main file path** to `mobile/app.py` → Deploy.
   You get a URL like `https://<name>.streamlit.app`. Open it on your phone and
   **Add to Home Screen** for an app-like icon.

3. **Auto-refresh at 6 AM** is already wired via `.github/workflows/refresh.yml`:
   GitHub Actions runs `dashboard/refresh.py all` on a cron and commits the cache;
   Streamlit Cloud redeploys with fresh numbers. No action needed beyond pushing.
   - Enable Actions on the repo (Settings → Actions → allow) if prompted.
   - The cron runs at 12:00 & 13:00 UTC to cover 6 AM Denver year-round (DST).

## Notes / limits
- **Private by design:** no "J.P. Morgan" branding on the phone app. Keep the repo
  **private** and, if you want, add a password via Streamlit Cloud settings. Check
  your firm's policy before sharing any market dashboard externally.
- **Prices are 15-min delayed** (free Yahoo data); rates/macro update on their own
  official cadence. Each panel shows its source; carry-forward keeps last-good values
  if a fetch hiccups.
- The **Refresh now** button fetches live on demand (works on the cloud too).
