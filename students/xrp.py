# students/xrp.py
import streamlit as st

def render_tab(api_url: str, provider: str, days: int, cg_demo_key: str, refresh: bool):
    st.markdown("### XRP")
    st.info("This tab is reserved for the XRP student. Please implement your charts and prediction calls here.")
    st.caption("Tip: If possible, mirror the ETH tab structure; expose `/predict/xrp` from your own FastAPI.")
