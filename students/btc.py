# app/students/btc.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

@st.cache_data(ttl=300, show_spinner=False)
def fetch_kraken_ohlc(pair: str = "BTCUSD", interval_min: int = 1440, days: int = 365) -> pd.DataFrame:
    """BTC OHLC from Kraken (no key)."""
    since_secs = int((datetime.now(timezone.utc) - timedelta(days=int(days)+2)).timestamp())
    url = "https://api.kraken.com/0/public/OHLC"
    r = requests.get(url, params={"pair": pair, "interval": interval_min, "since": since_secs}, timeout=20)
    r.raise_for_status()
    data = r.json().get("result", {})
    key = next((k for k in data.keys() if k != "last"), None)
    if not key:
        raise RuntimeError(f"Kraken response malformed: {data}")
    df = pd.DataFrame(data[key], columns=["time","open","high","low","close","vwap","volume","count"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for c in ["open","high","low","close","vwap","volume","count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.set_index("time").sort_index()
    cutoff = pd.Timestamp.utcnow().tz_localize("UTC") - pd.Timedelta(days=days)
    out = df.loc[df.index >= cutoff][["open","high","low","close","volume"]]
    out["quote_volume"] = np.nan
    return out

@st.cache_data(ttl=300, show_spinner=False)
def fetch_coingecko_ohlc(days: int = 365, vs="usd", demo_key: str = "") -> pd.DataFrame:
    """BTC OHLC from CoinGecko (hourly-like → resampled daily)."""
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc"
    headers = {"x-cg-demo-api-key": demo_key.strip()} if demo_key.strip() else {}
    r = requests.get(url, params={"vs_currency": vs, "days": str(days)}, headers=headers, timeout=20)
    r.raise_for_status()
    arr = r.json()
    df = pd.DataFrame(arr, columns=["ts","open","high","low","close"])
    df["time"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("time").sort_index().drop(columns=["ts"])
    daily = pd.DataFrame({
        "open":  df["open"].resample("1D").first(),
        "high":  df["high"].resample("1D").max(),
        "low":   df["low"].resample("1D").min(),
        "close": df["close"].resample("1D").last()
    })
    daily["volume"] = np.nan
    daily["quote_volume"] = np.nan
    return daily.dropna(how="all")

def _api_base(api_url: str) -> Optional[str]:
    api_url = (api_url or "").strip()
    if not api_url:
        return None
    return api_url[:-1] if api_url.endswith("/") else api_url

def ping_health(api_url: str) -> Optional[Dict[str, Any]]:
    base = _api_base(api_url)
    if not base:
        return None
    for path in ("/health", "/ping", "/api/health"):
        try:
            r = requests.get(base + path, timeout=15)
            if r.ok:
                return {"path": path, "status": r.status_code, "json": r.json() if "application/json" in r.headers.get("content-type","") else r.text}
        except Exception:
            continue
    return None

def predict_nextday_high(api_url: str) -> Optional[Dict[str, Any]]:
    base = _api_base(api_url)
    if not base:
        return None
    for path in ("/predict/btc", "/predict"):
        try:
            r = requests.get(base + path, timeout=25)
            if r.ok:
                return {"path": path, "json": r.json()}
        except Exception:
            continue
    return None

def _today_metrics(df: pd.DataFrame):
    last = df.dropna().tail(1)
    if last.empty:
        st.info("No recent OHLC rows available.")
        return None
    row = last.iloc[0]
    date_utc = (last.index[0] if isinstance(last.index[0], pd.Timestamp) else pd.to_datetime(last.index[0])).date().isoformat()
    c = st.columns(5)
    c[0].metric("Date (UTC)", date_utc)
    c[1].metric("Open",  f"${float(row['open']):,.6f}")
    c[2].metric("High",  f"${float(row['high']):,.6f}")
    c[3].metric("Low",   f"${float(row['low']):,.6f}")
    c[4].metric("Close", f"${float(row['close']):,.6f}")
    vol  = row.get("volume", np.nan)
    qvol = row.get("quote_volume", np.nan)
    if pd.notna(vol) or pd.notna(qvol):
        st.caption(f"Volume: {vol if pd.isna(vol) else int(vol):,} • Quote Volume: {qvol if pd.isna(qvol) else int(qvol):,}")
    else:
        st.caption("Volume data not available for this provider.")
    return float(row["close"])

def _close_line_chart(df: pd.DataFrame, title: str):
    fig = go.Figure(
        data=[go.Scatter(x=df.index, y=df["close"], mode="lines", name="Close")]
    )
    fig.update_layout(title=title, xaxis_title="Date (UTC)", yaxis_title="Price (USD)", height=420, margin=dict(l=40, r=20, t=60, b=40))
    st.plotly_chart(fig, use_container_width=True)

def _candles_table(df: pd.DataFrame):
    tbl = df.copy().reset_index().rename(columns={"time":"timestamp"})
    if "timestamp" not in tbl.columns:
        tbl["timestamp"] = pd.Timestamp.utcnow().tz_localize("UTC")
    # ensure columns exist
    for c in ["open","high","low","close","volume","quote_volume"]:
        if c not in tbl.columns:
            tbl[c] = np.nan
    # show naive timestamps
    tbl["timestamp"] = pd.to_datetime(tbl["timestamp"])
    if getattr(tbl["timestamp"].dt, "tz", None) is not None:
        try:
            tbl["timestamp"] = tbl["timestamp"].dt.tz_convert(None)
        except Exception:
            tbl["timestamp"] = tbl["timestamp"].dt.tz_localize(None)
    cols = ["timestamp","open","high","low","close","volume","quote_volume"]
    tbl = tbl[cols].sort_values("timestamp", ascending=False)
    st.subheader("Last 365 daily candles")
    try:
        st.dataframe(tbl, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Could not render candles table ({e}).")

def _forecast_card(pred: Dict[str, Any], last_close: float):
    payload = pred.get("json", {})
    yhat = float(payload.get("prediction_usd", np.nan))
    as_of_utc = payload.get("as_of_utc", "")
    try:
        dt = pd.to_datetime(as_of_utc, utc=True)
        pred_date = (dt + pd.Timedelta(days=1)).date().isoformat()
    except Exception:
        pred_date = "T+1"
    delta = yhat - last_close if last_close == last_close else np.nan
    delta_pct = 100.0 * delta / last_close if last_close and last_close == last_close else np.nan

    st.subheader("📈 Predict next-day High Price")
    st.caption(f"Used endpoint: `{pred.get('path','')}`")
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted next-day HIGH", f"${yhat:,.2f}", f"{delta:+.2f} USD" if pd.notna(delta) else None)
    c2.metric("Δ vs last close (%)", f"{delta_pct:+.2f}%" if pd.notna(delta_pct) else "—")
    c3.metric("Prediction date (UTC)", pred_date)
    with st.expander("Model details (raw)"):
        st.json(payload)

def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    st.markdown("## Bitcoin (BTC)")
    st.caption("Historical OHLC + next-day HIGH prediction via your FastAPI.")

    with st.container():
        st.subheader("Health check")
        base = _api_base(api_url) or ""
        st.caption(f"API base: {base or '—'}")
        if st.button("Ping /health"):
            res = ping_health(api_url)
            if res:
                st.success(f"OK {res['status']} from {res['path']}")
                st.json(res["json"])
            else:
                st.warning("Health endpoint not found. Add /health (or /ping) on your API.")

    try:
        if provider.startswith("Kraken"):
            df = fetch_kraken_ohlc(pair="BTCUSD", interval_min=1440, days=days)
            src = "Kraken (BTCUSD, 1D)"
        else:
            df = fetch_coingecko_ohlc(days=days, vs="usd", demo_key=cg_demo_key)
            src = "CoinGecko OHLC (resampled daily)"
        if refresh:
            fetch_kraken_ohlc.clear(); fetch_coingecko_ohlc.clear()
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Failed to fetch OHLC: {e}")
        return

    st.subheader("Today’s price (latest daily candle)")
    last_close = _today_metrics(df)

    _close_line_chart(df, title="Close price — time series")

    base = _api_base(api_url)
    if base:
        pred = predict_nextday_high(base)
        if pred:
            _forecast_card(pred, last_close=last_close if last_close is not None else np.nan)
        else:
            st.info("Enter a valid BTC FastAPI base URL in the sidebar (no trailing path).")
    else:
        st.info("Enter a valid BTC FastAPI base URL in the sidebar.")

    _candles_table(df)
