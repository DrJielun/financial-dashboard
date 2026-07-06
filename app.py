import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- 2. ENGINE: MATHEMATICALLY RIGOROUS INDICATORS ---
@st.cache_data(ttl=60)
def compute_institutional_indicators(df):
    d = df.copy()
    
    # SMA: Strict windowing to prevent partial-window distortion
    d['SMA50'] = d['Close'].rolling(window=50, min_periods=50).mean()
    d['SMA200'] = d['Close'].rolling(window=200, min_periods=200).mean()
    
    # RSI: Handle singularity (if loss=0, RSI=100)
    delta = d['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    d['avg_gain'] = gain.ewm(alpha=1/14, adjust=False).mean()
    d['avg_loss'] = loss.ewm(alpha=1/14, adjust=False).mean()
    d['RSI'] = np.where(d['avg_loss'] == 0, 100, 100 - (100 / (1 + (d['avg_gain'] / d['avg_loss']))))
    
    # Volatility Suite (BB & KC)
    d['MA20'] = d['Close'].rolling(20).mean()
    std20 = d['Close'].rolling(20).std()
    d['BB_Upper'] = d['MA20'] + (2 * std20)
    d['BB_Lower'] = d['MA20'] - (2 * std20)
    
    tr = pd.concat([d['High']-d['Low'], abs(d['High']-d['Close'].shift(1)), abs(d['Low']-d['Close'].shift(1))], axis=1).max(axis=1)
    d['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    d['KC_Upper'] = d['MA20'] + (1.5 * d['ATR'])
    d['KC_Lower'] = d['MA20'] - (1.5 * d['ATR'])
    d['BB_Squeeze'] = (d['BB_Upper'] < d['KC_Upper']) & (d['BB_Lower'] > d['KC_Lower'])
    
    # Wilder's DMI & ADX
    up = d['High'] - d['High'].shift(1)
    down = d['Low'].shift(1) - d['Low']
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    d['PlusDI'] = 100 * (pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean() / d['ATR'])
    d['MinusDI'] = 100 * (pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean() / d['ATR'])
    d['ADX'] = (abs(d['PlusDI'] - d['MinusDI']) / (d['PlusDI'] + d['MinusDI'])).ewm(alpha=1/14, adjust=False).mean() * 100
    
    return d

# --- 3. UI LAYER ---
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()
df_raw = yf.Ticker(ticker).history(period="2y")
df = compute_institutional_indicators(df_raw)

# Dashboard Layout
col1, col2 = st.columns([3, 1])

with col1:
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50", line=dict(color='yellow')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ADX'], name="ADX", line=dict(color='orange')), row=2, col=1)
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.metric("Trend Strength (ADX)", f"{df['ADX'].iloc[-1]:.1f}")
    st.write(f"**BB Squeeze Active:** {df['BB_Squeeze'].iloc[-1]}")
    st.write(f"**RSI (Wilder):** {df['RSI'].iloc[-1]:.2f}")
