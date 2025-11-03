# services/market.py
from __future__ import annotations
import requests
import numpy as np
import pandas as pd

# Build a debug/trace URL (optional)
def build_query_url(instrument: str, market: str = "coingecko", limit: int = 365, vs: str = "usd") -> str:
    sym = instrument.split("-")[0].upper()
    coin = {"SOL": "solana", "ETH": "ethereum", "BTC": "bitcoin", "XRP": "ripple"}.get(sym, "solana")
    return f"https://api.coingecko.com/api/v3/coins/{coin}/ohlc?vs_currency={vs}&days={limit}"

def fetch_cc_daily(
    instrument: str = "SOL-USD",
    market: str = "coingecko",
    limit: int = 365,
    vs: str = "usd",
    demo_key: str = "",
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: timestamp(UTC tz-aware), open, high, low, close, volume, marketCap
    Uses CoinGecko OHLC and resamples to daily.
    """
    sym = instrument.split("-")[0].upper()
    coin = {"SOL": "solana", "ETH": "ethereum", "BTC": "bitcoin", "XRP": "ripple"}.get(sym, "solana")

    url = "https://api.coingecko.com/api/v3/coins/{coin}/ohlc".format(coin=coin)
    params = {"vs_currency": vs, "days": str(limit)}
    headers = {}
    if demo_key:
        headers["x-cg-demo-api-key"] = demo_key

    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    arr = r.json()  # rows: [ms, open, high, low, close]

    df = pd.DataFrame(arr, columns=["ts", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop(columns=["ts"]).set_index("timestamp").sort_index()

    # Daily resample
    daily = pd.DataFrame()
    daily["open"] = df["open"].resample("1D").first()
    daily["close"] = df["close"].resample("1D").last()
    daily["high"] = df["high"].resample("1D").max()
    daily["low"]  = df["low"].resample("1D").min()
    daily["volume"] = np.nan
    daily["marketCap"] = np.nan
    daily = daily.dropna(how="all").reset_index()
    return daily
