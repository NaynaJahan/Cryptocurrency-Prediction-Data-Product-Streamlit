import requests
import pandas as pd
from datetime import datetime, timezone

def fetch_cc_daily(instrument: str, market: str, limit: int = 200,
                   to_ts: int | None = None,
                   base_url: str = "https://data-api.coindesk.com/index/cc/v1/historical/days",
                   groups: list[str] | None = None) -> pd.DataFrame:
    if groups is None:
        groups = ["OHLC", "VOLUME"]

    params = {
        "market": market, "instrument": instrument, "limit": int(limit),
        "groups": ",".join(groups), "response_format": "JSON"
    }
    if to_ts is not None:
        params["to_ts"] = int(to_ts)

    r = requests.get(base_url, params=params, timeout=30)
    r.raise_for_status()
    rows = r.json().get("Data", [])

    parsed = []
    for d in rows:
        ts = d.get("TIMESTAMP")
        if ts is None: continue
        if ts > 1_000_000_000_000: ts //= 1000
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        parsed.append({
            "timestamp": dt, "open": d.get("OPEN"), "high": d.get("HIGH"),
            "low": d.get("LOW"), "close": d.get("CLOSE"),
            "volume": d.get("VOLUME"), "quote_volume": d.get("QUOTE_VOLUME")
        })

    df = pd.DataFrame(parsed)
    return df.sort_values("timestamp").reset_index(drop=True)