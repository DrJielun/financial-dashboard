import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

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
# DATA FETCHER (FIXED)
# =========================
@st.cache_data(ttl=30)
def fetch_data(ticker):

    quote_url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
    chart_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=6mo"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        quote_res = requests.get(quote_url, headers=headers, timeout=10).json()
        chart_res = requests.get(chart_url, headers=headers, timeout=10).json()

        quote = quote_res["quoteResponse"]["result"][0]
        chart = chart_res["chart"]["result"][0]

        return quote, chart

    except Exception as e:
        st.error(f"Data fetch error: {e}")
        return None, None


quote, chart = fetch_data(ticker_symbol)

if quote is None:
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
# FUNDAMENTALS (REAL SOURCE)
# =========================
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
timestamps = pd.to_datetime(chart["timestamp"], unit="s")
prices = chart["indicators"]["quote"][0]

df = pd.DataFrame({
    "Date": timestamps,
    "Open": prices["open"],
    "High": prices["high"],
    "Low": prices["low"],
    "Close": prices["close"]
}).dropna()

# =========================
# HEADER
# =========================
st.title(f"{ticker_symbol} - {company_name}")
st.caption(f"Exchange: {exchange}")

st.metric(
    "Price",
    f"${price:.2f}",
    f"{change:+.2f} ({change_pct:+.2f}%)"
)

st.markdown("---")

# =========================
# TABLES
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Valuation Metrics")
    st.dataframe(pd.DataFrame([
        ["P/E", pe],
        ["Forward P/E", forward_pe],
        ["P/B", pb],
        ["P/S", ps],
        ["PEG", peg],
        ["Beta", beta],
        ["EPS", eps],
    ], columns=["Metric", "Value"]), hide_index=True)

with col2:
    st.subheader("Market Data")
    st.dataframe(pd.DataFrame([
        ["Market Cap", market_cap],
        ["52W High", high_52],
        ["52W Low", low_52],
        ["Dividend Yield", div],
    ], columns=["Metric", "Value"]), hide_index=True)

# =========================
# CHART
# =========================
st.subheader("Price Chart (6M)")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["Date"],
    y=df["Close"],
    mode="lines",
    line=dict(color="green")
))

fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

# =========================
# AUTO REFRESH
# =========================
st.markdown("Refreshing automatically...")

st.experimental_rerun()
