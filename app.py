
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("JL Quant - Full Dashboard")

ticker = st.text_input("Enter Ticker", "AAPL")

data = yf.Ticker(ticker)
hist = data.history(period="6mo")

# ===================== INDICATORS =====================
hist['SMA50'] = hist['Close'].rolling(50).mean()
hist['SMA200'] = hist['Close'].rolling(200).mean()

delta = hist['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
hist['RSI'] = 100 - (100 / (1 + rs))

exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
hist['MACD'] = exp1 - exp2
hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()

latest = hist.iloc[-1]

# ===================== FUNDAMENTALS =====================
st.markdown("### 🏢 Company Fundamentals")

info = data.info

def format_billions(x):
    return f"{x/1e9:.2f}B" if x else "N/A"

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Market Cap", format_billions(info.get('marketCap')))
    st.metric("EPS", info.get('trailingEps', 'N/A'))

with col2:
    st.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
    dy = info.get('dividendYield')
    st.metric("Dividend Yield", f"{dy*100:.2f}%" if dy else "N/A")

with col3:
    st.metric("52W High", info.get('fiftyTwoWeekHigh', 'N/A'))
    st.metric("52W Low", info.get('fiftyTwoWeekLow', 'N/A'))

# ===================== PRICE CHART =====================
st.markdown("### 📈 Price Chart")

fig = go.Figure()

fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price'))
fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], name='SMA50'))
fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], name='SMA200'))

fig.update_layout(template="plotly_dark", height=500)

st.plotly_chart(fig, use_container_width=True)

# ===================== INDICATORS =====================
st.markdown("### 📊 Indicators")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### RSI")
    st.line_chart(hist['RSI'])

with col2:
    st.markdown("#### MACD")
    st.line_chart(hist[['MACD', 'Signal']])

st.markdown("#### Volume")
st.bar_chart(hist['Volume'])

# ===================== EXTENDED HOURS =====================
premarket_price = info.get("preMarketPrice")
after_price = info.get("postMarketPrice")
premarket_change = info.get("preMarketChangePercent")
after_change = info.get("postMarketChangePercent")

# ===================== BOTTOM PANEL =====================
st.markdown("### 📊 Extended Hours & Smart Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🕒 Extended Hours")
    st.metric("Pre-Market",
              f"{premarket_price:.2f}" if premarket_price else "N/A",
              f"{premarket_change:.2f}%" if premarket_change else None)

    st.metric("After Hours",
              f"{after_price:.2f}" if after_price else "N/A",
              f"{after_change:.2f}%" if after_change else None)

with col2:
    st.markdown("#### 🧠 Smart Metrics")
    rsi = latest['RSI']
    macd = latest['MACD']
    signal = latest['Signal']

    st.metric("RSI", f"{rsi:.2f}", "Bullish" if rsi > 50 else "Bearish")
    st.metric("MACD", f"{macd:.2f}", "Bullish" if macd > signal else "Bearish")
    st.metric("Signal", f"{signal:.2f}")

with col3:
    st.markdown("#### 📈 Trend Structure")
    sma50 = latest['SMA50']
    sma200 = latest['SMA200']

    st.metric("SMA50", f"{sma50:.2f}")
    st.metric("SMA200", f"{sma200:.2f}")

    trend = "Bullish Trend" if sma50 > sma200 else "Bearish Trend"
    st.markdown(f"**{trend}**")

# ===================== STYLE =====================
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: #111;
    padding: 10px;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)
