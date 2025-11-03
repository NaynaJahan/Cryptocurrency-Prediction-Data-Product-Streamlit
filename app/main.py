import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    
import streamlit as st

from students.eth import render_tab as render_eth
from students.btc import render_tab as render_btc
from students.xrp import render_tab as render_xrp
from students.sol import render_tab as render_sol

st.set_page_config(
    page_title="Crypto Next-Day High – Team App",
    page_icon="🪙",
    layout="wide"
)

st.title("Crypto Next-Day HIGH Prediction – Team App")

# Sidebar: global options + per-student FastAPI URLs
st.sidebar.header("Global Options")

provider = st.sidebar.selectbox(
    "OHLC Data Provider",
    ["Kraken (no key)", "CoinGecko (demo key optional)"],
    index=0
)

days = st.sidebar.select_slider(
    "Historical window (days)",
    options=[7, 30, 90, 180, 365],
    value=365
)

cg_demo_key = st.sidebar.text_input(
    "CoinGecko demo API key (optional)",
    value=os.getenv("CG_DEMO_KEY", "")
)

st.sidebar.markdown("---")
st.sidebar.header("Student API Endpoints")
eth_api_default = os.getenv(
    "ETH_API_URL",
    "https://advmla-finalast-25238736-latest.onrender.com"
)
eth_api = st.sidebar.text_input("ETH FastAPI (your service)", value=eth_api_default)

# Teammates leave blank by default; they’ll fill their own
btc_api = st.sidebar.text_input("BTC FastAPI (teammate)", value=os.getenv("BTC_API_URL", ""))
xrp_api = st.sidebar.text_input("XRP FastAPI (teammate)", value=os.getenv("XRP_API_URL", "https://three6120-at3-api-muhammad-iqbal-latest.onrender.com"))
sol_api = st.sidebar.text_input("SOL FastAPI (teammate)", value=os.getenv("SOL_API_URL", ""))

st.sidebar.markdown("---")
refresh = st.sidebar.button("🔄 Refresh live data")

# ---- Tabs ----
tab_btc, tab_eth, tab_xrp, tab_sol = st.tabs(["Bitcoin (BTC)", "Ethereum (ETH) – You", "XRP", "Solana (SOL)"])

with tab_btc:
    render_btc(api_url=btc_api, provider=provider, days=days, cg_demo_key=cg_demo_key, refresh=refresh)

with tab_eth:
    render_eth(api_url=eth_api, provider=provider, days=days, cg_demo_key=cg_demo_key, refresh=refresh)

with tab_xrp:
    render_xrp(api_url=xrp_api, provider=provider, days=days, cg_demo_key=cg_demo_key, refresh=refresh)

with tab_sol:
    render_sol(api_url=sol_api, provider=provider, days=days, cg_demo_key=cg_demo_key, refresh=refresh)
