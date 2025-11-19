# app/students/sol.py
from __future__ import annotations

import time
import requests
import numpy as np
import pandas as pd
import streamlit as st

# Use the package facade (make sure services/__init__.py exports these)
from services import fetch_cc_daily, fetch_sol_news_rss

def fmt_int(x) -> str:
    try:
        v = float(x)
        if pd.isna(v) or not np.isfinite(v):
            return "0"
        return f"{int(v):,}"
    except Exception:
        return "0"

def safe_int(x) -> int:
    try:
        v = float(x)
        if pd.isna(v) or not np.isfinite(v):
            return 0
        return int(v)
    except Exception:
        return 0

def fmt_usd(x) -> str:
    try:
        v = float(x)
        if pd.isna(v) or not np.isfinite(v):
            return "—"
        return f"${v:,.6f}"
    except Exception:
        return "—"

@st.cache_data(show_spinner=False)
def load_market_data(days: int, refresh_flag: int) -> pd.DataFrame:
    """Fetch daily OHLC market data for Solana via CoinDesk Index (cadli)."""
    return fetch_cc_daily(instrument="SOL-USD", market="cadli", limit=days)

def _ping_health(api_url: str, timeout: int = 10) -> tuple[bool, str]:
    try:
        r = requests.get(f"{api_url}/health", timeout=timeout)
        r.raise_for_status()
        return True, r.text
    except Exception as e:
        return False, str(e)

def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    st.markdown("## Solana → Next Day High Price Prediction")
    refresh_flag = 1 if refresh else 0

    # Market data
    try:
        df = load_market_data(days=days, refresh_flag=refresh_flag)
    except Exception as e:
        st.error(f"Failed to load market data: {e}")
        return

    if df.empty:
        st.warning("No market data returned.")
        return

    latest = df.iloc[-1]

    # Health
    st.subheader("API Health Check")
    col_h1, col_h2 = st.columns([1, 3])
    with col_h1:
        if st.button("Ping /health", key="sol_health", use_container_width=True):
            ok, msg = _ping_health(api_url)
            if ok:
                st.success("API reachable")
                st.code(msg)
            else:
                st.error("Health check failed")
                st.code(msg)
    with col_h2:
        st.caption(f"API base: `{api_url}`")

    st.divider()

    # Predict
    st.subheader("Predict Next-Day High Price")
    if st.button("Use Latest Price → /predict/solana", key="sol_predict", use_container_width=True):
        params = {
            "date": latest["timestamp"].date().isoformat(),
            "open":  float(latest.get("open")  or 0),
            "high":  float(latest.get("high")  or 0),
            "low":   float(latest.get("low")   or 0),
            "close": float(latest.get("close") or 0),
            "volume": safe_int(latest.get("volume")),
        }
        try:
            t0 = time.perf_counter()
            resp = requests.get(f"{api_url}/predict/solana", params=params, timeout=20)
            elapsed_ms = (time.perf_counter() - t0) * 1000
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
            return

        if resp.status_code != 200:
            st.error(f"API error {resp.status_code}")
            st.code(resp.text, language="json")
        else:
            data = resp.json()
            m1, m2, m3 = st.columns(3)
            m1.metric("Predicted Next-Day HIGH (USD)", fmt_usd(data.get("Predicted_Next_Day_High")))
            m2.metric("Input Date", data.get("input_date", "—"))
            m3.metric("Prediction Date", data.get("prediction_date", "—"))
            st.caption(f"Latency: {elapsed_ms:.0f} ms • Token: SOL")
            with st.expander("Raw response", expanded=False):
                st.json(data)

    st.divider()

    # Today’s candle
    st.subheader("Today’s Price (Latest Daily Candle)")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Date (UTC)", latest["timestamp"].date().isoformat())
    c2.metric("Open",  fmt_usd(latest.get("open")))
    c3.metric("High",  fmt_usd(latest.get("high")))
    c4.metric("Low",   fmt_usd(latest.get("low")))
    c5.metric("Close", fmt_usd(latest.get("close")))
    st.caption(
        f"Volume: {fmt_int(latest.get('volume'))} • "
        f"Market Cap: {fmt_usd(latest.get('marketCap') if 'marketCap' in latest else np.nan)}"
    )

    # Trend
    st.subheader("Closing Price Trend")
    try:
        st.line_chart(df.set_index("timestamp")["close"], use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render line chart ({e}).")

    # News
    st.subheader("Latest Solana News 📰")
    cols = st.columns([1, 2, 2])
    with cols[0]:
        do_fetch = st.button("Fetch Headlines", use_container_width=True, key="sol_news_btn")
    with cols[1]:
        max_items = st.slider("Items", 3, 12, 8, help="Number of Solana news headlines to display")
    with cols[2]:
        st.write("")  # spacer

    if do_fetch:
        with st.spinner("Fetching Solana News RSS…"):
            items, feed_url = fetch_sol_news_rss(
                query="Solana OR SOL crypto",
                max_items=max_items,
                within_days=14,
                hl="en-US", gl="US", ceid="US:en",
            )

        if not items:
            st.warning("No recent Solana headlines found. Try different keywords.")
        else:
            for it in items:
                st.markdown(
                    f"- **[{it['title']}]({it['url']})**  \n"
                    f"  _{it.get('source','')}_ • {it.get('published','')}"
                )
            with st.expander("Feed URL (debug)"):
                st.code(feed_url)

    # Table (robust to missing optional columns)
    st.subheader(f"Last {len(df)} Daily Candles")
    try:
        tbl = df.copy()
        # ensure timestamp exists and is naive for display
        if "timestamp" not in tbl.columns and tbl.index.name == "timestamp":
            tbl = tbl.reset_index()
        if getattr(tbl["timestamp"].dt, "tz", None) is not None:
            try:
                tbl["timestamp"] = tbl["timestamp"].dt.tz_convert(None)
            except Exception:
                tbl["timestamp"] = tbl["timestamp"].dt.tz_localize(None)
        # add optional columns if missing
        for c in ["marketCap"]:
            if c not in tbl.columns:
                tbl[c] = np.nan
        cols = [c for c in ["timestamp","open","high","low","close","volume","marketCap"] if c in tbl.columns]
        st.dataframe(tbl[cols], hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render candles table ({e}).")

    st.divider()
    st.caption(
        "Data source: CoinDesk Index (cc) API via 'cadli' market • "
        f"Provider: {provider or 'CoinDesk cc'} • Rows: {len(df)} (latest first)"
    )
