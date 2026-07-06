import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- SIDEBAR CONTROLS ---
ticker_symbol = st.sidebar.text_input("Ticker:", value="AAPL").upper().strip()
timeframe_opts = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y"}
selected_tf = st.sidebar.selectbox("Horizon:", list(timeframe_opts.keys()))
benchmark_sym = st.sidebar.selectbox("Benchmark:", ["SPY", "QQQ", "XLK"])

# --- DATA PIPELINE ---
@st.cache_data(ttl=60)
def get_data(ticker, period):
    df = yf.Ticker(ticker).history(period=period)
    bench = yf.Ticker(benchmark_sym).history(period=period)
    return df, bench

def compute_indicators(df, df_bench):
    # Base Indicators
    df['MA20'] = df['Close'].rolling(20).mean()
    df['ATR'] = (df['High'] - df['Low']).ewm(span=14).mean()
    
    # Advanced Metrics
    daily_rets = df['Close'].pct_change().dropna()
    df['Volatility'] = daily_rets.std() * np.sqrt(252)
    df['Sharpe'] = (daily_rets.mean() / daily_rets.std()) * np.sqrt(252)
    
    # Pivots (Daily)
    p_high, p_low, p_close = df['High'].shift(1), df['Low'].shift(1), df['Close'].shift(1)
    df['PP'] = (p_high + p_low + p_close) / 3
    
    # Volume Profile (POC)
    bins = pd.cut(df['Close'], bins=20)
    df['POC'] = df.groupby(bins)['Volume'].transform(lambda x: x.sum()).idxmax().mid if len(df) > 0 else 0
    
    # Swing Points
    df['SwingHigh'] = df.iloc[argrelextrema(df.High.values, np.greater_equal, order=5)[0]]['High']
    df['SwingLow'] = df.iloc[argrelextrema(df.Low.values, np.less_equal, order=5)[0]]['Low']
    
    return df

# --- EXECUTION ---
raw_df, bench_df = get_data(ticker_symbol, timeframe_opts[selected_tf])
df = compute_indicators(raw_df, bench_df)
latest = df.iloc[-1]

# --- UI LAYER ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("ATR (14)", f"{latest['ATR']:.2f}")
c2.metric("Suggested Stop", f"${(latest['Close'] - 2*latest['ATR']):.2f}")
c3.metric("Volatility (Ann.)", f"{latest['Volatility']:.2%}")
c4.metric("Sharpe Ratio", f"{latest['Sharpe']:.2f}")

# --- CHARTING ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)

# Overlay Features
fig.add_hline(y=latest['PP'], line_dash="dash", line_color="white", annotation_text="Pivot")
fig.add_hline(y=latest['POC'], line_dash="dot", line_color="yellow", annotation_text="POC")

# Swing Points
fig.add_trace(go.Scatter(x=df.index, y=df['SwingHigh'], mode='markers', marker_symbol='triangle-down', marker_color='red', name='Swing High'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['SwingLow'], mode='markers', marker_symbol='triangle-up', marker_color='green', name='Swing Low'), row=1, col=1)

fig.update_layout(template="plotly_dark", height=700)
st.plotly_chart(fig, use_container_width=True)
