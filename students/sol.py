# students/sol.py
from __future__ import annotations

import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone

# Import helper functions if available
from services import fetch_cc_daily, build_query_url, fetch_sol_news_rss


def fmt_usd(x) -> str:
    """Format numeric value as USD."""
    try:
        return f"${float(x):,.6f}"
    except Exception:
        return "—"


@st.cache_data(show_spinner=False)
def load_market_data(days: int, refresh_flag: int) -> pd.DataFrame:
    """Fetch daily OHLC market data for Solana."""
    return fetch_cc_daily(instrument="SOL-USD", market="cadli", limit=days)


def _ping_health(api_url: str, timeout: int = 10) -> tuple[bool, str]:
    """Check FastAPI /health endpoint."""
    try:
        r = requests.get(f"{api_url}/health", timeout=timeout)
        r.raise_for_status()
        return True, r.text
    except Exception as e:
        return False, str(e)


def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    """Render Solana (SOL) dashboard tab."""
    st.markdown("## Solana → Next Day High Price Prediction")
    refresh_flag = 1 if refresh else 0

   
    try:
        df = load_market_data(days=days, refresh_flag=refresh_flag)
    except Exception as e:
        st.error(f"Failed to load market data: {e}")
        return

    if df.empty:
        st.warning("No market data returned.")
        return

    latest = df.iloc[-1]

   
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

   
    st.subheader("Predict Next-Day High Price")
    if st.button("Use Latest Price → /predict/solana", key="sol_predict", use_container_width=True):
        params = {
            "date": latest["timestamp"].date().isoformat(),
            "open": float(latest.get("open") or 0),
            "high": float(latest.get("high") or 0),
            "low": float(latest.get("low") or 0),
            "close": float(latest.get("close") or 0),
            "volume": int(latest.get("volume") or 0),
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

   
    st.subheader("Today’s Price (Latest Daily Candle)")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Date (UTC)", latest["timestamp"].date().isoformat())
    c2.metric("Open", fmt_usd(latest["open"]))
    c3.metric("High", fmt_usd(latest["high"]))
    c4.metric("Low", fmt_usd(latest["low"]))
    c5.metric("Close", fmt_usd(latest["close"]))

    st.caption(
        f"Volume: {int(latest.get('volume') or 0):,} • "
        f"Market Cap: {fmt_usd(latest.get('marketCap') or 0)}"
    )

  
    st.subheader("Closing Price Trend")
    st.line_chart(df.set_index("timestamp")["close"], use_container_width=True)

  
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
                hl="en-US", gl="US", ceid="US:en"
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

  
    st.subheader(f"Last {len(df)} Daily Candles")
    tbl = df.copy()
    if hasattr(tbl["timestamp"].dt, "tz_convert"):
        try:
            tbl["timestamp"] = tbl["timestamp"].dt.tz_convert(None)
        except Exception:
            pass

    st.dataframe(
        tbl[["timestamp", "open", "high", "low", "close", "volume", "marketCap"]],
        hide_index=True,
        use_container_width=True,
    )

    
    st.divider()
    st.caption(
        "Data source: CoinDesk Index (cc) API via 'cadli' market • "
        f"Provider: {provider or 'CoinDesk cc'} • Rows: {len(df)} (latest first)"
    )
