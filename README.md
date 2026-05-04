# Crypto Next-Day HIGH – Team Streamlit App

## Objective

An interactive web app for crypto-curious users to:
- Browse historical OHLC for four tokens (BTC, ETH, XRP, SOL) via free public APIs, and
- Call each student’s FastAPI service to get a next-day HIGH (USD) prediction for their token.

The repository of the experimentations of trained models that will be loaded by the FastAPI app can be found here: [Cryptocurrency-Prediction-Data-Product-Experiments](https://github.com/NaynaJahan/Cryptocurrency-Prediction-Data-Product-Experiments)

The repository for the FastAPI model endpoints for the Cryptocurrency Prediction can be found here: [Cryptocurrency-Prediction-API
Public](https://github.com/NaynaJahan/Cryptocurrency-Prediction-API)

----

## Repository Structure

```graphql
.
├─ app/
│  └─ main.py                 # Streamlit entry point (tabs for BTC/ETH/XRP/SOL)
├─ students/
│  ├─ __init__.py
│  ├─ btc.py                  # BTC tab 
│  ├─ eth.py                  # ETH tab
│  ├─ xrp.py                  # XRP tab 
│  └─ sol.py                  # SOL tab
├─ services/
│  ├─ __init__.py
│  ├─ coindesk.py             # CoinDesk/cc helpers (daily OHLC)
│  └─ news_rss.py             # Google News RSS helpers
├─ Dockerfile                 # Optional container build for Streamlit app
├─ pyproject.toml             # Python project metadata (Poetry)
├─ requirements.txt           # Runtime deps (pip)
├─ README.md
└─ github.txt                 # Link to the FastAPI repo

```

Each student owns one tab (file in students/). Tabs fetch public OHLC and hit that student’s FastAPI /predict endpoint.

----
## Quick Start (local)

### Requirements
- Python >= 3.11
- streamlit 1.36.0
- pandas 2.2.2
- numpy 1.26.4
- requests >= 2.31
- plotly >= 5.24.0
- feedparser 6.0.12

```bash
# 1) clone
git clone <this-repo-url>
cd <repo>

# 2) install (choose one)
pip install -r requirements.txt
# or
poetry install

# 3) run
streamlit run app/main.py

```
- Open the sidebar and paste your team’s FastAPI base URLs.
- Choose data provider (Kraken or CoinGecko) and the look-back window.

### Configuration (env vars – optional)
- Prefill the sidebar inputs with environment variables:

```bash
export ETH_API_URL="https://advmla-finalast-25238736-latest.onrender.com"
export BTC_API_URL="https://aml-at3-fastapi-btc.onrender.com"
export XRP_API_URL="https://three6120-at3-api-muhammad-iqbal-latest.onrender.com"
export SOL_API_URL="https://aml-at3-group24-experiments.onrender.com"

# Optional CoinGecko demo key
export CG_DEMO_KEY="<demo-key>"

```

### Docker (optional)
Build & run the Streamlit app in a container:
```bash
# build
docker build -t crypto-streamlit:latest .

# run (exposes 8501)
docker run --rm -p 8501:8501 \
  -e ETH_API_URL="https://advmla-finalast-25238736-latest.onrender.com" \
  -e BTC_API_URL="https://aml-at3-fastapi-btc.onrender.com" \
  -e XRP_API_URL="https://three6120-at3-api-muhammad-iqbal-latest.onrender.com" \
  -e SOL_API_URL="https://aml-at3-group24-experiments.onrender.com" \
  -e CG_DEMO_KEY="<demo-key>" \
  crypto-streamlit:latest
```

## Deploy (Streamlit Community Cloud)

1. New app → connect this GitHub repo, set app/main.py as the entry file.
2. Secrets / Env Vars: add any of ETH_API_URL, BTC_API_URL, XRP_API_URL, SOL_API_URL, CG_DEMO_KEY.
3. Deploy. Updates to main will auto-redeploy (or click Rerun).

## How each tab works

- Historical data:
    - Kraken public OHLC (no key) for daily candles, or
    - CoinGecko OHLC (resampled to daily; optional demo key).

- Prediction: calls the student’s FastAPI (e.g., /predict/eth, /predict/btc, etc.) and displays:
    - predicted next-day HIGH (USD),
    - delta vs last close, and
    - basic model metadata from the API response.

## License / Credits
Course project (UTS AML). Uses public data (Kraken, CoinGecko) and student-hosted FastAPI services on Render.
