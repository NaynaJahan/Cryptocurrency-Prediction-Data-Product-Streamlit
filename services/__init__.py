# services/__init__.py

# Market data helpers (CoinDesk Index "cc" API)
from .coindesk import fetch_cc_daily

# News / RSS helpers
from .news_rss import build_query_url, fetch_xrp_news_rss
from .news import fetch_sol_news_rss  # <-- lives in news.py, not news_rss.py

__all__ = [
    "fetch_cc_daily",
    "build_query_url",
    "fetch_xrp_news_rss",
    "fetch_sol_news_rss",
]