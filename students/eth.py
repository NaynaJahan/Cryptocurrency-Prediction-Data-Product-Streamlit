from __future__ import annotations
import math, time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

# Cached data fetchers
@st.cache_data(ttl=300, show_spinner=False)
def fetch_kraken_ohlc(pair: str = "ETHUSD", interval_min: int = 1440, days: int = 365) -> pd.DataFrame:
    since_secs = int((datetime.now(timezone.utc) - timedelta(days=int(days) + 2)).timestamp())
    url = "https://api.kraken.com/0/public/OHLC"
    params = {"pair": pair, "interval": interval_min, "since": since_secs}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    result = data.get("result", {})
    key = next((k for k in result.keys() if k != "last"), None)
    if not key:
        raise RuntimeError(f"Kraken response malformed: {data}")

    df = pd.DataFrame(result[key], columns=["time","open","high","low","close","vwap","volume","count"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for c in ["open","high","low","close","vwap","volume","count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.set_index("time").sort_index()

    # --- FIX: build an aware UTC cutoff and ensure index is UTC-aware ---
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    now_utc = pd.Timestamp.now(tz="UTC")
    cutoff = now_utc - pd.Timedelta(days=int(days))
    # --------------------------------------------------------------------
    return df.loc[df.index >= cutoff, ["open","high","low","close","volume"]]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_coingecko_ohlc(days: int = 365, vs="usd", demo_key: str = "") -> pd.DataFrame:
    """CoinGecko demo OHLC (hourly-sort of)"""
    url = "https://api.coingecko.com/api/v3/coins/ethereum/ohlc"
    params = {"vs_currency": vs, "days": str(days)}
    headers = {}
    if demo_key.strip():
        headers["x-cg-demo-api-key"] = demo_key.strip()
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    arr = r.json()
    # arr rows: [timestamp_ms, open, high, low, close]
    df = pd.DataFrame(arr, columns=["ts","open","high","low","close"])
    df["time"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("time").sort_index().drop(columns=["ts"])
    daily = pd.DataFrame()
    daily["open"]  = df["open"].resample("1D").first()
    daily["close"] = df["close"].resample("1D").last()
    daily["high"]  = df["high"].resample("1D").max()
    daily["low"]   = df["low"].resample("1D").min()
    daily["volume"] = np.nan
    return daily.dropna(how="all")

def _candlestick(df: pd.DataFrame, title: str):
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["open"], high=df["high"],
                low=df["low"], close=df["close"],
                name="OHLC"
            )
        ]
    )
    fig.update_layout(
        title=title, xaxis_title="Date (UTC)", yaxis_title="Price (USD)",
        height=520, margin=dict(l=40, r=20, t=60, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

def _cards(df: pd.DataFrame):
    last = df.dropna().tail(1)
    if last.empty:
        st.info("No recent OHLC rows available.")
        return
    last_close = float(last["close"].iloc[0])
    last_open  = float(last["open"].iloc[0])
    last_high  = float(last["high"].iloc[0])
    last_low   = float(last["low"].iloc[0])
    chg = last_close - last_open
    chg_pct = 100.0 * chg / last_open if last_open else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Close (last)", f"${last_close:,.2f}", f"{chg:+.2f} ({chg_pct:+.2f}%)")
    c2.metric("High (last)", f"${last_high:,.2f}")
    c3.metric("Low (last)", f"${last_low:,.2f}")
    c4.metric("Range (last)", f"${(last_high-last_low):,.2f}")

def _predict(api_url: str) -> Optional[Dict[str, Any]]:
    if not api_url:
        return None
    try:
        r = requests.get(api_url.rstrip("/") + "/predict/eth", timeout=25)
        if r.status_code != 200:
            st.warning(f"Prediction call failed: {r.status_code} – {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        st.warning(f"Prediction call error: {e}")
        return None

def _predict_card(pred: Dict[str, Any], last_close: float):
    pred_usd = float(pred["prediction_usd"])
    as_of_utc = pred.get("as_of_utc", "")
    # predict-for date is next UTC day after as_of
    try:
        dt = pd.to_datetime(as_of_utc, utc=True)
        pred_date = (dt + pd.Timedelta(days=1)).date().isoformat()
    except Exception:
        pred_date = "T+1"
    delta = pred_usd - float(last_close)
    delta_pct = 100.0 * delta / float(last_close) if last_close else 0.0

    st.subheader("📈 Model Forecast (ETH)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted next-day HIGH", f"${pred_usd:,.2f}", f"{delta:+.2f} USD")
    c2.metric("Δ vs last close (%)", f"{delta_pct:+.2f}%")
    c3.metric("Prediction date (UTC)", pred_date)

    with st.expander("Model details"):
        st.json({
            "as_of_utc": pred.get("as_of_utc"),
            "close_t_usd": pred.get("close_t_usd"),
            "yhat_ratio": pred.get("yhat_ratio"),
            "alpha_used": pred.get("alpha_used"),
            "features_used": pred.get("features_used"),
            "source": pred.get("source")
        })

# Public entry
def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    st.markdown("### Ethereum (ETH)")

    # Fetch OHLC
    try:
        if provider.startswith("Kraken"):
            df = fetch_kraken_ohlc(pair="ETHUSD", interval_min=1440, days=days)
            src = "Kraken (ETHUSD, 1D)"
        else:
            df = fetch_coingecko_ohlc(days=days, vs="usd", demo_key=cg_demo_key)
            src = "CoinGecko OHLC (resampled daily)"
        if refresh:
            # bust caches on manual refresh
            fetch_kraken_ohlc.clear()
            fetch_coingecko_ohlc.clear()
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to fetch OHLC: {e}")
        return

    # Top metrics + chart
    _cards(df)
    _candlestick(df, title=f"ETH OHLC – last {days} days • source: {src}")

    # Forecast card
    last_close = float(df["close"].dropna().iloc[-1]) if not df.empty else np.nan
    pred = _predict(api_url)
    if pred:
        _predict_card(pred, last_close=last_close)
    else:
        st.info("Enter a valid ETH FastAPI URL in the sidebar to fetch a forecast.")