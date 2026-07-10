
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")

st.title("JL Quant - Smart Panel")

ticker = st.text_input("Enter Ticker", "AAPL")

data = yf.Ticker(ticker)
hist = data.history(period="6mo")

# --- Indicators ---
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

# --- Extended Hours (Yahoo) ---
info = data.info
premarket_price = info.get("preMarketPrice")
after_price = info.get("postMarketPrice")
premarket_change = info.get("preMarketChangePercent")
after_change = info.get("postMarketChangePercent")

# --- Layout ---
st.markdown("### 📊 Extended Hours & Smart Metrics")

col1, col2, col3 = st.columns(3)

# Extended Hours
with col1:
    st.markdown("#### 🕒 Extended Hours")

    st.metric(
        "Pre-Market",
        f"{premarket_price:.2f}" if premarket_price else "N/A",
        f"{premarket_change:.2f}%" if premarket_change else None
    )

    st.metric(
        "After Hours",
        f"{after_price:.2f}" if after_price else "N/A",
        f"{after_change:.2f}%" if after_change else None
    )

# Smart Metrics
with col2:
    st.markdown("#### 🧠 Smart Metrics")

    rsi = latest['RSI']
    macd = latest['MACD']
    signal = latest['Signal']

    st.metric("RSI", f"{rsi:.2f}", "Bullish" if rsi > 50 else "Bearish")
    st.metric("MACD", f"{macd:.2f}", "Bullish" if macd > signal else "Bearish")
    st.metric("Signal", f"{signal:.2f}")

# Trend Structure
with col3:
    st.markdown("#### 📈 Trend Structure")

    sma50 = latest['SMA50']
    sma200 = latest['SMA200']

    st.metric("SMA50", f"{sma50:.2f}")
    st.metric("SMA200", f"{sma200:.2f}")

    trend = "Bullish Trend" if sma50 > sma200 else "Bearish Trend"
    st.markdown(f"**{trend}**")

# Styling
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
