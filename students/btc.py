import streamlit as st

def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    st.markdown("### Bitcoin (BTC)")
    st.info("This tab is reserved for the BTC student. Please implement your charts and prediction calls here.")
    st.caption("Tip: If possible, mirror the ETH tab structure; expose `/predict/btc` from your own FastAPI.")
