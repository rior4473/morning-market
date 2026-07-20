"""Central configuration: instrument groups, FRED series, news feeds.

Each data group carries:
  - source:  human-readable provenance shown in the UI
  - policy:  refresh cadence -> "intraday" | "daily" | "release"
Edit here to add/remove instruments without touching fetch logic.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

SNAPSHOT_FILE = CACHE_DIR / "snapshot.json"
NEWS_FILE = CACHE_DIR / "news.json"
YIELDS_HISTORY_FILE = CACHE_DIR / "yields_history.csv"

LOCAL_TZ = "America/Denver"  # your local time (Boulder/Denver)

# Refresh scopes -> which sections they update
SCOPE_SECTIONS = {
    "market": ["jpm_focus", "equity_index", "volatility_futures", "fixed_income",
               "commodities", "fx_crypto", "global_indexes"],
    "rates":  ["yields", "spreads", "key_rates", "credit", "curve"],
    "macro":  ["macro"],
}
SCOPE_SECTIONS["all"] = (SCOPE_SECTIONS["market"]
                         + SCOPE_SECTIONS["rates"]
                         + SCOPE_SECTIONS["macro"])

YF_SOURCE = "Yahoo Finance (delayed)"

# ---------------------------------------------------------------------------
# Yahoo-Finance-based groups (prices/levels). policy = intraday.
# group_key -> {label, source, policy, tickers: {display_name: yahoo_symbol}}
# ---------------------------------------------------------------------------
MARKET_GROUPS = {
    "jpm_focus": {
        "label": "J.P. Morgan — Stock & Lead Funds",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "JPM":  "JPM",    # JPMorgan Chase & Co. common stock
            "JEPI": "JEPI",   # JPM Equity Premium Income ETF
            "JEPQ": "JEPQ",   # JPM Nasdaq Equity Premium Income ETF
            "JPST": "JPST",   # JPM Ultra-Short Income ETF
        },
    },
    "equity_index": {
        "label": "U.S. Equity Indexes (cash)",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "S&P 500":          "^GSPC",
            "Nasdaq Composite": "^IXIC",
            "Dow Jones":        "^DJI",
            "Russell 2000":     "^RUT",
        },
    },
    "volatility_futures": {
        "label": "Market Volatility & U.S. Equity Futures",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "VIX":               "^VIX",
            "S&P 500 Futures":   "ES=F",
            "Nasdaq 100 Futures": "NQ=F",
            "Dow Futures":       "YM=F",
            "Russell 2000 Futures": "RTY=F",
        },
    },
    "fixed_income": {
        "label": "Fixed Income Assets & Indexes",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "U.S. Agg Bond (AGG)":       "AGG",
            "IG Corporate (LQD)":        "LQD",
            "High Yield (HYG)":          "HYG",
            "Municipal (MUB)":           "MUB",
            "Long Treasury (TLT)":       "TLT",
            "Short Treasury (SHY)":      "SHY",
            "Ultra-Short T-Bill (SGOV)": "SGOV",
            "TIPS (TIP)":                "TIP",
        },
    },
    "commodities": {
        "label": "Commodities",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "Gold":      "GC=F",
            "WTI Crude": "CL=F",
            "Brent Crude": "BZ=F",
            "Copper":    "HG=F",
            "Silver":    "SI=F",
        },
    },
    "fx_crypto": {
        "label": "Currencies & Crypto",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "U.S. Dollar Index (DXY)": "DX-Y.NYB",
            "EUR/USD":  "EURUSD=X",
            "USD/JPY":  "JPY=X",
            "GBP/USD":  "GBPUSD=X",
            "USD/CNY":  "CNY=X",
            "Bitcoin":  "BTC-USD",
            "Ethereum": "ETH-USD",
        },
    },
    "global_indexes": {
        "label": "Global Market Indexes",
        "source": YF_SOURCE,
        "policy": "intraday",
        "tickers": {
            "STOXX 600":     "^STOXX",
            "FTSE 100":      "^FTSE",
            "DAX":           "^GDAXI",
            "Nikkei 225":    "^N225",
            "Hang Seng":     "^HSI",
            "CSI 300":       "000300.SS",
            "EM Equity (EEM)": "EEM",
            "Dev ex-US (EFA)": "EFA",
            # The MSCI World *index* level (not the URTH ETF's share price)
            "MSCI World": "^990100-USD-STRD",
        },
    },
}

# J.P. Morgan focus box — stock + lead funds, and chart timeframe options.
JPM_TICKER = "JPM"
JPM_FUNDS = [
    ("JEPI", "Equity Premium Income"),
    ("JEPQ", "Nasdaq Equity Premium Income"),
    ("JPST", "Ultra-Short Income"),
]
# label -> (yfinance period, interval)
JPM_CHART_TIMEFRAMES = {
    "1D": ("1d", "5m"),
    "1M": ("1mo", "1d"),
    "YTD": ("ytd", "1d"),
    "Since Inception": ("max", "1wk"),
}

# ---------------------------------------------------------------------------
# Treasury yield curve (FRED constant-maturity, percent). policy = daily.
# label -> (fred_series_id, maturity_years)
# ---------------------------------------------------------------------------
YIELD_CURVE = {
    "1M":  ("DGS1MO", 1 / 12),
    "3M":  ("DGS3MO", 3 / 12),
    "6M":  ("DGS6MO", 6 / 12),
    "1Y":  ("DGS1", 1),
    "2Y":  ("DGS2", 2),
    "3Y":  ("DGS3", 3),
    "5Y":  ("DGS5", 5),
    "7Y":  ("DGS7", 7),
    "10Y": ("DGS10", 10),
    "20Y": ("DGS20", 20),
    "30Y": ("DGS30", 30),
}
YIELDS_SOURCE = "U.S. Treasury via FRED"

# Spreads to compute (in basis points). Each entry: name -> (a, b) where
# value = a - b. Tokens reference YIELD_CURVE labels or "EFFR".
SPREADS = {
    "10Y - 2Y":   ("10Y", "2Y"),
    "10Y - 3M":   ("10Y", "3M"),
    "30Y - 10Y":  ("30Y", "10Y"),
    "5Y - 2Y":    ("5Y", "2Y"),
    "10Y - 5Y":   ("10Y", "5Y"),
    "2Y - Fed Funds":  ("2Y", "EFFR"),
    "10Y - Fed Funds": ("10Y", "EFFR"),
}

# ---------------------------------------------------------------------------
# Key policy / money-market rates (FRED, percent). policy = daily.
# label -> (series_id, source)
# ---------------------------------------------------------------------------
KEY_RATES = {
    "Fed Target Range — Upper":    ("DFEDTARU", "Federal Reserve via FRED"),
    "Fed Target Range — Lower":    ("DFEDTARL", "Federal Reserve via FRED"),
    "Effective Fed Funds (EFFR)":  ("EFFR", "NY Fed via FRED"),
    "SOFR":                        ("SOFR", "NY Fed via FRED"),
    "Interest on Reserves (IORB)": ("IORB", "Federal Reserve via FRED"),
    "Prime Rate":                  ("DPRIME", "Federal Reserve via FRED"),
    "3M T-Bill":                   ("DGS3MO", "U.S. Treasury via FRED"),
    "6M T-Bill":                   ("DGS6MO", "U.S. Treasury via FRED"),
    "1Y T-Bill":                   ("DGS1", "U.S. Treasury via FRED"),
    "30Y Fixed Mortgage":          ("MORTGAGE30US", "Freddie Mac via FRED (weekly)"),
}

# Credit spreads / ratios (FRED OAS in percent). policy = daily.
CREDIT_SPREADS = {
    "IG Corporate OAS":  ("BAMLC0A0CM", "ICE BofA via FRED"),
    "High Yield OAS":    ("BAMLH0A0HYM2", "ICE BofA via FRED"),
    "AAA Muni Yield":    ("DAAA", "Moody's via FRED"),  # high-grade corp/muni proxy
}

# ---------------------------------------------------------------------------
# Macro indicators (FRED). policy = release (only changes on new prints).
# label -> {series, transform: level|yoy, unit, source}
# ---------------------------------------------------------------------------
MACRO = {
    "CPI (YoY)":            {"series": "CPIAUCSL",        "transform": "yoy",   "unit": "%", "source": "BLS via FRED"},
    "Core PCE (YoY)":       {"series": "PCEPILFE",        "transform": "yoy",   "unit": "%", "source": "BEA via FRED"},
    "Unemployment Rate":    {"series": "UNRATE",          "transform": "level", "unit": "%", "source": "BLS via FRED"},
    "Real GDP (QoQ SAAR)":  {"series": "A191RL1Q225SBEA", "transform": "level", "unit": "%", "source": "BEA via FRED"},
}

# ---------------------------------------------------------------------------
# News: publisher RSS feeds (free, no key, no scraping).
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    ("CNBC — Top News",    "https://www.cnbc.com/id/100003114/device/rss/rss.html", "Markets"),
    ("CNBC — Economy",     "https://www.cnbc.com/id/20910258/device/rss/rss.html",  "Economy"),
    ("CNBC — Finance",     "https://www.cnbc.com/id/10000664/device/rss/rss.html",  "Markets"),
    ("MarketWatch — Top",  "https://feeds.content.dowjones.io/public/rss/mw_topstories", "Markets"),
    ("MarketWatch — Markets", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "Markets"),
    ("WSJ — Markets",      "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "Markets"),
    ("WSJ — Economy",      "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed", "Economy"),
    ("NYT — Business",     "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "Markets"),
    ("NYT — Economy",      "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "Economy"),
    ("Yahoo Finance",      "https://finance.yahoo.com/news/rssindex", "Markets"),
    ("Federal Reserve",    "https://www.federalreserve.gov/feeds/press_all.xml", "Fed"),
    ("Investing.com — Economy", "https://www.investing.com/rss/news_25.rss", "Economy"),
]

CATEGORY_KEYWORDS = [
    ("Fed",          ["federal reserve", "fed ", "fomc", "powell", "rate cut", "rate hike", "interest rate decision"]),
    ("Fixed Income", ["treasury", "yield", "bond", "credit spread", "duration", "coupon"]),
    ("Commodities",  ["oil", "crude", "gold", "copper", "opec", "natural gas", "commodit"]),
    ("Crypto",       ["bitcoin", "crypto", "ethereum", "btc", "blockchain"]),
    ("Geopolitics",  ["war", "sanction", "tariff", "election", "geopolit", "russia", "china", "middle east", "ukraine", "iran"]),
    ("Economy",      ["inflation", "cpi", "ppi", "gdp", "jobs", "payroll", "unemployment", "pce", "recession", "consumer"]),
    ("Equities",     ["stock", "shares", "earnings", "s&p", "nasdaq", "dow", "equit", "ipo"]),
    ("Wealth Mgmt",  ["wealth", "private bank", "estate", "high net worth", "family office", "advisor"]),
    ("Markets",      []),
]

PRIORITY_KEYWORDS = [
    "fed", "fomc", "powell", "inflation", "cpi", "pce", "treasury", "yield",
    "rate", "gdp", "jobs", "payroll", "recession", "tariff", "earnings",
    "oil", "gold", "dollar", "credit", "bond",
]

MAX_HEADLINES = 40
