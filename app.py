import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")

# --- 2. INSTITUTIONAL QUANT ENGINE ---
@st.cache_data(ttl=60)
def compute_institutional_indicators(df):
    # Calculations for dependencies
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    
    # RSI (Wilder's Smoothing)
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    # Bollinger Bandwidth for Volatility factor
    ma20 = df['Close'].rolling(window=20).mean()
    std20 = df['Close'].rolling(window=20).std()
    df['Vol_Bandwidth'] = ( (ma20 + (2 * std20)) - (ma20 - (2 * std20)) ) / ma20

    # Strict SMA
    df['SMA50'] = df['Close'].rolling(window=50, min_periods=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200, min_periods=200).mean()
    
    # Institutional Money Flow
    mf_flow = typical_price * df['Volume']
    pos_mf = np.where(typical_price > typical_price.shift(1), mf_flow, 0)
    neg_mf = np.where(typical_price < typical_price.shift(1), mf_flow, 0)
    mf_ratio = pd.Series(pos_mf, index=df.index).rolling(14).sum() / pd.Series(neg_mf, index=df.index).rolling(14).sum()
    df['MFI'] = 100 - (100 / (1 + mf_ratio))
    
    mf_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, np.nan)
    df['CMF'] = (mf_multiplier * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
    
    # Market Structure
    df['Swing_High'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))]
    df['Swing_Low'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))]
    
    # Composite Score (40/30/20/10 weighting)
    df['Composite_Score'] = (
        (df['SMA50'] > df['SMA200']).astype(int) * 0.4 +
        (df['RSI'] > 50).astype(int) * 0.3 +
        (df['CMF'] > 0).astype(int) * 0.2 +
        (df['Vol_Bandwidth'] < 0.1).astype(int) * 0.1
    )
    
    # ATR Stop Levels
    tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['Stop_1ATR'] = df['Close'] - (1 * df['ATR'])
    df['Stop_2ATR'] = df['Close'] - (2 * df['ATR'])
    
    return df

# --- 3. UI RENDERING ---
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()
df_raw = yf.Ticker(ticker).history(period="2y")
df = compute_institutional_indicators(df_raw)

st.subheader(f"Institutional Analysis: {ticker}")
col1, col2 = st.columns([3, 1])

with col1:
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Stop_2ATR'], name="2ATR Stop", line=dict(color='orange', dash='dot')), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['CMF'], name="CMF"), row=2, col=1)
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.metric("Composite Score", f"{df['Composite_Score'].iloc[-1]:.2f}")
    st.write("### Market Structure")
    st.write(f"Latest Swing High: ${df['Swing_High'].dropna().iloc[-1]:.2f}")
    st.write(f"Latest Swing Low: ${df['Swing_Low'].dropna().iloc[-1]:.2f}")
