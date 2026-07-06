import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- NAV & TICKER MANAGEMENT ---
st.sidebar.header("Navigation & Watchlist")
watchlist = ["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN"]
selected_watch = st.sidebar.selectbox("Quick Select:", [""] + watchlist)
ticker_symbol = st.sidebar.text_input("Ticker Input:", value=selected_watch if selected_watch else "AAPL").upper().strip()

timeframe_opts = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
selected_tf = st.sidebar.selectbox("Horizon:", list(timeframe_opts.keys()), index=3)
benchmark_sym = st.sidebar.selectbox("Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- DATA CACHING ---
@st.cache_data(ttl=86400)
def fetch_metadata(ticker_str):
    t = yf.Ticker(ticker_str)
    info = t.info
    return {
        "longName": info.get("longName", ticker_str),
        "marketCap": info.get("marketCap"),
        "beta": info.get("beta"),
        "avg_volume": info.get("averageVolume"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "floatShares": info.get("floatShares"),
        "shortInterest": info.get("shortPercentOfFloat"),
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "peg": info.get("pegRatio"),
        "pb": info.get("priceToBook"),
        "dividendYield": info.get("dividendYield"),
        "roe": info.get("returnOnEquity"),
        "net_margin": info.get("profitMargins"),
        "op_margin": info.get("operatingMargins"),
        "eps_growth": info.get("earningsGrowth"),
        "rev_growth": info.get("revenueGrowth"),
        "debt_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
    }

@st.cache_data(ttl=60)
def get_data(ticker, bench, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    bench_df = yf.Ticker(bench).history(period=period)
    
    # Technicals
    df['MA20'] = df['Close'].rolling(20).mean()
    df['Std20'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    
    # RSI
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_g = gain.ewm(14).mean()
    avg_l = loss.ewm(14).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_g / avg_l.replace(0, np.nan))))
    
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    
    # ATR & Pivots
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(span=14).mean()
    df['Pivot'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
    
    return df, bench_df

# --- EXECUTION ---
if not ticker_symbol.isalnum(): st.stop()
fnd = fetch_metadata(ticker_symbol)
df, bench_df = get_data(ticker_symbol, benchmark_sym, timeframe_opts[selected_tf])
latest = df.iloc[-1]

# --- LAYOUT ---
main, side = st.columns([2.3, 0.7])
with main:
    st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol})")
    
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.2, 0.2, 0.2])
    # Price
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Pivot'], line=dict(color='gray', width=1, dash='dot'), name='Daily Pivot'), row=1, col=1)
    # Vol
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume'), row=2, col=1)
    # MACD
    fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name='MACD Hist', marker_color=np.where(df['Hist']>=0, 'green', 'red')), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue')), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal', line=dict(color='orange')), row=3, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=4, col=1)
    for y in [30, 70]: fig.add_hline(y=y, line_dash="dash", row=4, col=1)
    
    fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with side:
    st.markdown("### 📋 Quant Fundamentals")
    # ... (Re-insert your full list of metrics here from the previous code) ...
    st.markdown("### 🛡️ Risk Metrics")
    atr = latest['ATR']
    stop_px = latest['Close'] - (2 * atr)
    st.metric("Suggested Stop (2xATR)", f"${stop_px:.2f}")
    st.write(f"Position Risk: {((latest['Close']-stop_px)/latest['Close'])*100:.2f}%")
