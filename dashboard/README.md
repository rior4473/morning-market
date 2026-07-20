# Morning Market — Markets & Macro Dashboard

A modern, dark, executive-style morning dashboard for a markets analyst:
market-moving headlines, equity/futures/FX/commodity/crypto/global prices, the full
Treasury curve with spreads, money-market & policy rates, credit spreads, macro prints,
and a structured morning briefing — each updated on the cadence its data actually
releases on.

Stack: **Python · Streamlit · Pandas · Plotly**. Sources are **official APIs and
publisher RSS only** — no scraping, no paywall bypass.

---

## 1. Categories shown

0. **J.P. Morgan focus** — JPM stock (large box) + lead funds JEPI / JEPQ / JPST, with a price chart toggleable across 1D / 1M / YTD / Since Inception
1. **Market Volatility & U.S. Equity Futures** — VIX, S&P 500 / Nasdaq 100 / Dow / Russell 2000 futures
2. **Treasury Yields & Yield Curve** — 1M→30Y yields, the curve chart (normal/flat/inverted + comparisons), and spreads: 10Y-2Y, 10Y-3M, 30Y-10Y, 5Y-2Y, 10Y-5Y, 2Y-FedFunds, 10Y-FedFunds
3. **Key Interest & Money-Market Rates** — Fed target range, EFFR, SOFR, IORB, Prime, 3M/6M/1Y T-bills, 30Y mortgage
4. **Fixed Income Assets** — AGG, LQD, HYG, MUB, TLT, SHY, SGOV, TIP + **Credit spreads** (IG OAS, HY OAS, high-grade yield)
5. **Commodities** — Gold, WTI, Brent, Copper, Silver
6. **Currencies & Crypto** — DXY, EUR/USD, USD/JPY, GBP/USD, USD/CNY, Bitcoin, Ethereum
7. **Global Market Indexes** — STOXX 600, FTSE 100, DAX, Nikkei 225, Hang Seng, CSI 300, EEM, EFA
8. **Macro Indicators** — CPI (YoY), Core PCE (YoY), Unemployment, Real GDP (QoQ SAAR), with period + next-release date
9. **Morning Marketing** — risk tone, futures/yields/dollar/oil/gold/bitcoin direction, curve shape, macro theme, events to watch, top headline
10. **Headlines** — ranked, category-tagged, with source, time, summary, link

Every item shows latest value, daily change, % change (where applicable), YTD change/return,
previous close/reading, an "as of" date, and the source. Each category shows its own
**source** and **last-updated** time.

---

## 2. Data sources — free / paid / keys

| Category | Source | Key? | Cost |
|----------|--------|------|------|
| JPM stock + funds, futures, VIX, ETFs, commodities, FX, crypto, global indexes | Yahoo Finance (`yfinance`) | No | Free (15-min delayed) |
| Treasury yields + curve + spreads | U.S. Treasury par-yield feed | No | Free |
| Money-market & policy rates (EFFR/SOFR/IORB/Prime/target/mortgage/T-bills) | FRED public CSV endpoint | No | Free |
| Credit spreads (ICE BofA OAS) | FRED public CSV endpoint | No | Free |
| Macro (CPI, PCE, unemployment, GDP) | FRED public CSV (BLS/BEA data) | No | Free |
| Headlines + summaries + links | Publisher RSS (CNBC, NYT, WSJ, MarketWatch, Yahoo, Fed) | No | Free |
| Extra news (optional) | NYT API, Marketaux, Finnhub | Yes (free tiers) | Free tier |

**No key is required for anything.** Everything — prices, news, the full yield curve,
all spreads, money-market & policy rates, credit spreads, and macro — loads via keyless
public endpoints (Yahoo, the U.S. Treasury feed, and FRED's public CSV download endpoint).

A free FRED API key (→ https://fredaccount.stlouisfed.org/apikeys, paste into `.env`)
is **optional**: when set, FRED series use the official JSON API (higher rate limits,
plus macro "Next Release" dates). Without it they use the public CSV endpoint.

**Carry-forward:** once any value has loaded, a later failed/empty fetch keeps the
last-known-good figure (flagged `stale`) instead of showing "n/a".

The **Key Interest & Money-Market Rates** table shows: latest %, average YTD %, and
1-day % change, per rate, with source and as-of date.

### Paid / unavailable — and substitutes
- **Bloomberg** — no free API → covered by CNBC/MarketWatch/Reuters.
- **WSJ / FT / NYT full text** — paywalled. We use their **public RSS** (headline + summary + link).
  Clicking through may hit the publisher's paywall — expected. NYT also has a free official API (optional).
- **Reuters** — no public RSS now; Reuters items arrive via Marketaux/Finnhub if you add those free keys.
- **Real-time/intraday tick data, official index levels (Bloomberg US Agg, etc.)** — require paid
  market-data licenses. We use free delayed prices and ETF proxies (e.g. AGG for the Bloomberg US Agg).

---

## 3. Refresh cadence (data updates on its own schedule)

`refresh.py` takes a **scope** so each data type runs at its natural frequency:

| Scope | Updates | Suggested schedule |
|-------|---------|--------------------|
| `market` | futures, VIX, ETFs, commodities, FX, crypto, global indexes, **news** | every ~30 min during market hours + once pre-6 AM |
| `rates` | yields, spreads, key rates, credit, curve | daily, early AM (FRED posts ~next business day) |
| `macro` | CPI, PCE, unemployment, GDP | daily check; values only change on official release |
| `news` | headlines only | as desired |
| `all` | everything | **6:00 AM daily** |

The UI reads only from the cache, so it loads instantly and survives a failed fetch.
Each cache section keeps its own `fetched_at`, shown under every table.

---

## 4. Project structure

```
dashboard/
├── app.py                 # Streamlit UI (modern dark theme)
├── refresh.py             # python refresh.py [all|market|rates|macro|news]
├── config.py              # all instruments, FRED series, feeds, scopes
├── requirements.txt
├── .env / .env.example    # FRED key (+ optional news keys)
├── .streamlit/config.toml # dark theme
├── run_refresh.sh         # scheduler wrapper (takes a scope arg)
├── com.intern.dashboard.refresh.plist    # launchd: 6:00 AM `all`
├── com.intern.dashboard.intraday.plist   # launchd: every 30 min `market`
├── data/
│   ├── fred.py            # FRED client + next-release-date lookup
│   ├── fetch_market.py    # yfinance groups
│   ├── fetch_rates.py     # yields, spreads, key rates, credit, curve
│   ├── fetch_macro.py     # CPI/PCE/unemployment/GDP + release calendar
│   ├── fetch_news.py      # RSS + optional APIs, ranking, categorizing
│   └── cache.py           # partial-section snapshot cache
├── utils/formatting.py    # formatting + structured briefing
└── cache/                 # generated: snapshot.json, news.json, yields_history.csv
```

---

## 5. Run locally

```bash
cd "dashboard"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # paste FRED_API_KEY
python refresh.py all         # fetch everything once
streamlit run app.py          # http://localhost:8501
```

Or just **double-click `Start Dashboard.command`** in Finder.

Sidebar buttons (**Refresh All / Prices / Rates / Macro / News**) fetch on demand.

---

## 6. Schedule automatic updates (macOS launchd)

```bash
chmod +x run_refresh.sh
# 6:00 AM full refresh:
cp com.intern.dashboard.refresh.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.intern.dashboard.refresh.plist
# (optional) intraday price refresh every 30 min:
cp com.intern.dashboard.intraday.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.intern.dashboard.intraday.plist

launchctl start com.intern.dashboard.refresh    # test now
cat cache/logs/refresh.log
```

**cron alternative** (`crontab -e`):
```
0 6 * * *    "/Users/ricardoorozco/Claude intern dashboard/dashboard/run_refresh.sh" all
*/30 * * * * "/Users/ricardoorozco/Claude intern dashboard/dashboard/run_refresh.sh" market
```

> If the Mac is asleep at 6:00 AM, launchd runs the job on next wake. For a true 6 AM
> update keep the laptop awake/plugged in. The dashboard itself must be running
> (or launched in the morning) to display the freshly cached data.

For a cloud option (always-on, runs the refresh on a schedule without your Mac):
**GitHub Actions** can run `refresh.py` on a cron and commit the cache, with the app on
**Streamlit Community Cloud** (put keys in its Secrets UI, not `.env`).

---

## 7. Security: keys

Keys live in `.env` (git-ignored). `.gitignore` also excludes `secrets.toml` and the
`cache/` data. For cloud deploys use the platform's secrets manager.

---

## 8. Limitations & data notes

- **Prices are EOD/15-min delayed** (free Yahoo data). Real-time intraday needs paid feeds.
- **FRED rates lag ~1 business day** (EFFR/SOFR post next morning); the "As of" column shows each value's true date.
- **30Y mortgage is weekly** (Thursdays); its change is week-over-week.
- **Macro "Period"** is the observation period; **"Next Release"** is FRED's scheduled date
  (best-effort). The displayed reading is YoY% for CPI/PCE, the rate for unemployment, and
  QoQ SAAR growth for GDP.
- **USD/CNY** (onshore) is used instead of USD/CNH because Yahoo doesn't serve CNH history.
- **AGG** is the ETF proxy for the Bloomberg U.S. Aggregate (the index itself is licensed/paid).
- **News is headline-level only** — full WSJ/FT/NYT/Bloomberg text requires a paid subscription.
- **Not investment advice.** Personal/educational morning prep. Confirm with your team before
  deploying anything publicly under a J.P. Morgan context.
```
