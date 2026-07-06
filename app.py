import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Stock Analysis Dashboard")

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Dashboard Controls")

ticker_symbol = st.sidebar.text_input(
    "Enter Stock Ticker:",
    value="NVDA"
).upper().strip()

refresh_rate = st.sidebar.slider(
    "Auto-Refresh Interval (Seconds):",
    min_value=10,
    max_value=300,
    value=30
)

st.sidebar.caption(f"🔄 Auto-refresh every {refresh_rate}s")

# =========================
# DATA FETCHER (WITH EXPLICIT ERROR ROUTING)
# =========================
@st.cache_data(ttl=refresh_rate)
def fetch_data(ticker):
    quote_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    chart_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6mo"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        quote_res = requests.get(quote_url, headers=headers, timeout=10).json()
        chart_res = requests.get(chart_url, headers=headers, timeout=10).json()

        # STTRIC TICKER CHECK (Point 2): Halt and notify user if the asset profile cannot be found
        quote_results = quote_res.get("quoteResponse", {}).get("result", [])
        chart_results = chart_res.get("chart", {}).get("result")

        if not quote_results or chart_results is None:
            return None, None

        return quote_results[0], chart_results[0]

    except Exception:
        return None, None

# Execute live data fetch
quote, chart = fetch_data(ticker_symbol)

# --- STRICT ERROR STATE HANDLER ---
if quote is None or chart is None:
    st.error(f"❌ Error: Fundamental market profile data for ticker '{ticker_symbol}' could not be resolved.")
    st.info("Please verify the ticker formatting stands completely accurate against standard active exchange assets (e.g., NVDA, AMD, MSFT, TSM, AAPL).")
    st.stop()

# =========================
# PRICE DATA
# =========================
company_name = quote.get("longName", ticker_symbol)
exchange = quote.get("fullExchangeName", "N/A")

price = quote.get("regularMarketPrice", 0)
prev_close = quote.get("regularMarketPreviousClose", 0)

change = quote.get("regularMarketChange", price - prev_close)
change_pct = quote.get("regularMarketChangePercent", 0)

# =========================
# FUNDAMENTALS (CLEAN STRUCTURAL PARSING)
# =========================
def format_val(val, style="num"):
    if val is None or pd.isna(val) or val == 0:
        return "N/A"
    if style == "pct":
        return f"{val * 100:.2f}%"
    if style == "mcap":
        return f"${val / 1e9:,.2f}B"
    return f"{val:,.2f}"

pe = quote.get("trailingPE")
forward_pe = quote.get("forwardPE")
pb = quote.get("priceToBook")
ps = quote.get("priceToSales")
peg = quote.get("pegRatio")
beta = quote.get("beta")
eps = quote.get("trailingEps")
div = quote.get("trailingAnnualDividendYield")

high_52 = quote.get("fiftyTwoWeekHigh")
low_52 = quote.get("fiftyTwoWeekLow")
market_cap = quote.get("marketCap")

# =========================
# CHART DATA
# =========================
df = pd.DataFrame()
try:
    timestamps = pd.to_datetime(chart["timestamp"], unit="s")
    prices = chart["indicators"]["quote"][0]

    df = pd.DataFrame({
        "Date": timestamps,
        "Open": prices["open"],
        "High": prices["high"],
        "Low": prices["low"],
        "Close": prices["close"]
    }).dropna()
except Exception:
    pass

# =========================
# HEADER
# =========================
st.title(f"{ticker_symbol} - {company_name}")
st.caption(f"Exchange: {exchange}")

st.metric(
    "Price",
    f"${price:.2f}" if price else "N/A",
    f"{change:+.2f} ({change_pct:+.2f}%)" if change else "0.00 (0.00%)"
)

st.markdown("---")

# =========================
# TABLES
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Valuation Metrics")
    st.dataframe(pd.DataFrame([
        ["P/E", format_val(pe)],
        ["Forward P/E", format_val(forward_pe)],
        ["P/B", format_val(pb)],
        ["P/S", format_val(ps)],
        ["PEG", format_val(peg)],
        ["Beta", format_val(beta)],
        ["EPS", format_val(eps)],
    ], columns=["Metric", "Value"]), hide_index=True, use_container_width=True)

with col2:
    st.subheader("Market Data")
    st.dataframe(pd.DataFrame([
        ["Market Cap", format_val(market_cap, "mcap")],
        ["52W High", format_val(high_52)],
        ["52W Low", format_val(low_52)],
        ["Dividend Yield", format_val(div, "pct")],
    ], columns=["Metric", "Value"]), hide_index=True, use_container_width=True)

# =========================
# CHART
# =========================
if not df.empty:
    st.subheader("Price Chart (6M)")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        mode="lines",
        name="Closing Price",
        line=dict(color="green", width=2.5)
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=40, r=40, t=10, b=10),
        yaxis=dict(title="Price (USD)")
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================
# SAFE AUTO REFRESH WORKSPACE (NO INIFINITE RERUN LOCKS)
# =========================
@st.fragment
def auto_refresh_executor():
    import time
    time.sleep(refresh_rate)
    st.rerun()

auto_refresh_executor()
