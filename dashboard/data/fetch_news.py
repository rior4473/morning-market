"""News aggregation from publisher RSS feeds (+ optional keyed APIs).

Only public RSS feeds and official APIs are used. We never scrape article
bodies or bypass paywalls — clicking a headline opens the publisher's page.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from config import (CATEGORY_KEYWORDS, MAX_HEADLINES, PRIORITY_KEYWORDS,
                    RSS_FEEDS)

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None, limit: int = 280) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub("", text)            # strip HTML
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:limit] + "…") if len(text) > limit else text


def _categorize(title: str, summary: str, default: str) -> str:
    blob = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in blob for kw in keywords):
            return category
    return default


def _priority_score(title: str, summary: str) -> int:
    blob = f"{title} {summary}".lower()
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in blob)


def _parse_dt(entry) -> datetime:
    for attr in ("published", "updated"):
        val = entry.get(attr)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return datetime.now(timezone.utc)


def _from_rss() -> list[dict]:
    items = []
    for source, url, default_cat in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for entry in feed.entries[:15]:
            title = _clean(entry.get("title"), 200)
            if not title:
                continue
            summary = _clean(entry.get("summary") or entry.get("description"))
            published = _parse_dt(entry)
            items.append({
                "title": title,
                "source": source.split(" — ")[0],
                "feed": source,
                "published": published.isoformat(),
                "published_ts": published.timestamp(),
                "summary": summary,
                "link": entry.get("link", ""),
                "category": _categorize(title, summary, default_cat),
            })
    return items


def _from_nyt() -> list[dict]:
    key = os.getenv("NYT_API_KEY", "").strip()
    if not key:
        return []
    items = []
    for section in ("business", "us"):
        try:
            url = f"https://api.nytimes.com/svc/topstories/v2/{section}.json"
            r = requests.get(url, params={"api-key": key}, timeout=20)
            r.raise_for_status()
            for a in r.json().get("results", [])[:10]:
                title = _clean(a.get("title"), 200)
                summary = _clean(a.get("abstract"))
                pub = a.get("published_date") or ""
                try:
                    dt = datetime.fromisoformat(pub)
                except ValueError:
                    dt = datetime.now(timezone.utc)
                items.append({
                    "title": title, "source": "NYT", "feed": "NYT API",
                    "published": dt.isoformat(), "published_ts": dt.timestamp(),
                    "summary": summary, "link": a.get("url", ""),
                    "category": _categorize(title, summary, "Markets"),
                })
        except Exception:
            continue
    return items


def _from_marketaux() -> list[dict]:
    key = os.getenv("MARKETAUX_API_KEY", "").strip()
    if not key:
        return []
    try:
        r = requests.get("https://api.marketaux.com/v1/news/all", params={
            "api_token": key, "language": "en", "filter_entities": "true",
            "limit": 20,
        }, timeout=20)
        r.raise_for_status()
        items = []
        for a in r.json().get("data", []):
            title = _clean(a.get("title"), 200)
            summary = _clean(a.get("description") or a.get("snippet"))
            pub = a.get("published_at", "")
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.now(timezone.utc)
            items.append({
                "title": title, "source": a.get("source", "Marketaux"),
                "feed": "Marketaux", "published": dt.isoformat(),
                "published_ts": dt.timestamp(), "summary": summary,
                "link": a.get("url", ""),
                "category": _categorize(title, summary, "Markets"),
            })
        return items
    except Exception:
        return []


def fetch_news() -> list[dict]:
    items = _from_rss() + _from_nyt() + _from_marketaux()

    # De-duplicate by normalized title
    seen, unique = set(), []
    for it in items:
        key = re.sub(r"[^a-z0-9]", "", it["title"].lower())[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(it)

    # Rank: priority keywords first, then most recent
    for it in unique:
        it["priority"] = _priority_score(it["title"], it["summary"])
    unique.sort(key=lambda x: (x["priority"], x["published_ts"]), reverse=True)

    return unique[:MAX_HEADLINES]
