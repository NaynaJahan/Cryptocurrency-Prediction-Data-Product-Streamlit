# services/news_rss.py
from __future__ import annotations
import time, datetime as dt
from typing import List, Dict, Any, Tuple
from urllib.parse import quote_plus
import feedparser  # pip install feedparser

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

def build_query_url(query: str, hl: str = "en-US", gl: str = "US", ceid: str = "US:en") -> str:
    return f"{_GOOGLE_NEWS_RSS}?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"

def fetch_xrp_news_rss(
    query: str = "XRP OR Ripple",
    max_items: int = 8,
    within_days: int | None = 14,
    hl: str = "en-US",
    gl: str = "US",
    ceid: str = "US:en",
) -> Tuple[List[Dict[str, Any]], str]:
    url = build_query_url(query, hl=hl, gl=gl, ceid=ceid)
    feed = feedparser.parse(url)
    items: List[Dict[str, Any]] = []

    cutoff = None
    if within_days:
        cutoff = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc) - dt.timedelta(days=within_days)

    for e in getattr(feed, "entries", []):
        title = e.get("title", "")
        link = e.get("link", "")          
        source = (e.get("source") or {}).get("title", "")
        published = ""

        # Parse published date (if available)
        if e.get("published_parsed"):
            ts = time.mktime(e.published_parsed)
            dt_utc = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
            if cutoff and dt_utc < cutoff:
                continue
            published = dt_utc.date().isoformat()

        if title and link:
            items.append({"title": title, "url": link, "source": source, "published": published})
            if len(items) >= max_items:
                break

    return items, url
