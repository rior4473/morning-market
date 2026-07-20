"""Keyless U.S. Treasury Daily Par Yield Curve source.

Treasury publishes the daily par yield curve as a public XML feed (no API key).
Used as a fallback so yields / curve / spreads work without a FRED key.
Docs: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
"""
from __future__ import annotations

from datetime import date
from xml.etree import ElementTree as ET

import pandas as pd
import requests

_BASE = ("https://home.treasury.gov/resource-center/data-chart-center/"
         "interest-rates/pages/xml")

_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}

# our maturity label -> Treasury XML field
_FIELD = {
    "1M": "BC_1MONTH", "3M": "BC_3MONTH", "6M": "BC_6MONTH",
    "1Y": "BC_1YEAR", "2Y": "BC_2YEAR", "3Y": "BC_3YEAR",
    "5Y": "BC_5YEAR", "7Y": "BC_7YEAR", "10Y": "BC_10YEAR",
    "20Y": "BC_20YEAR", "30Y": "BC_30YEAR",
}


def _fetch_year(year: int) -> list[dict]:
    params = {"data": "daily_treasury_yield_curve",
              "field_tdr_date_value": str(year)}
    r = requests.get(_BASE, params=params, timeout=25)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    rows = []
    for props in root.iterfind(".//m:properties", _NS):
        date_el = props.find("d:NEW_DATE", _NS)
        if date_el is None or not date_el.text:
            continue
        row = {"date": date_el.text[:10]}
        for label, field in _FIELD.items():
            el = props.find(f"d:{field}", _NS)
            row[label] = (float(el.text) if el is not None and el.text
                          not in (None, "") else None)
        rows.append(row)
    return rows


def get_curve_df(years: int = 2) -> pd.DataFrame:
    """Date-indexed DataFrame of par yields (percent); columns = maturity labels."""
    this_year = date.today().year
    all_rows: list[dict] = []
    for y in range(this_year - years + 1, this_year + 1):
        try:
            all_rows.extend(_fetch_year(y))
        except Exception:
            continue
    if not all_rows:
        return pd.DataFrame(columns=list(_FIELD))
    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(how="all", subset=list(_FIELD)).set_index("date").sort_index()
