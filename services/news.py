# services/news.py
from __future__ import annotations
import requests
import xml.etree.ElementTree as ET

def fetch_sol_news_rss(
    query: str = "Solana OR SOL crypto",
    max_items: int = 8,
    within_days: int = 14,
    hl: str = "en-US",
    gl: str = "US",
    ceid: str = "US:en",
):
    """
    Fetch Solana headlines from Google News RSS. Returns (items, feed_url),
    where items is a list of dicts: title, url, published, source.
    """
    q = requests.utils.quote(f"{query} when:{within_days}d")
    feed_url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

    r = requests.get(feed_url, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    # Namespaces sometimes used by Google News RSS
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "gn": "http://news.google.com",
    }

    items = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        pub   = (
            item.findtext("pubDate")
            or item.findtext("atom:updated", namespaces=ns)
            or ""
        ).strip()

        # Try namespaced source; fall back to plain 'source'
        source = ""
        src = item.find("gn:source", namespaces=ns) or item.find("source")
        if src is not None and (src.text or "").strip():
            source = src.text.strip()

        items.append({"title": title, "url": link, "published": pub, "source": source})

    return items, feed_url
