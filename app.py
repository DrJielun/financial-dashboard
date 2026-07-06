import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- CONFIGURATION & INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- DATA ENGINE ---
@st.cache_data(ttl=60)
def get_institutional_data(ticker, bench, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval="1d")
    bench_df = yf.Ticker(bench).history(period=period, interval="1d")
    
    # 1. Strict SMA Logic (Institutional Grade)
    df['SMA50'] = df['Close'].rolling(window=50, min_periods=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200, min_periods=200).mean()
    
    # 2. Money Flow & Volume
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    mf_flow = typical * df['Volume']
    df['CMF'] = (mf_flow * np.where(typical > typical.shift(1), 1, -1)).rolling(20).sum() / df['Volume'].rolling(20).sum()
    
    # 3. Market Structure Pivots
    df['Swing_High'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))]
    df['Swing_Low'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))]
    
    return df, bench_df

def get_factor_scores(fnd, df):
    # Normalized Scoring (0-100)
    q = (fnd.get('roe', 0) * 100).clip(0, 100)
    g = (fnd.get('eps_growth', 0) * 100).clip(0, 100)
    v = (100 - (fnd.get('pe_trailing', 20)) * 2).clip(0, 100)
    m = df['RSI'].iloc[-1] if 'RSI' in df else 50
    t = 100 if df['Close'].iloc[-1] > df['SMA200'].iloc[-1] else 0
    
    rating = (0.3*q) + (0.25*g) + (0.2*m) + (0.15*t) + (0.1*v)
    return {"Quality": q, "Growth": g, "Momentum": m, "Trend": t, "Value": v, "Rating": rating}

# --- UI LAYER ---
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()
period = st.sidebar.selectbox("Horizon", ["1y", "2y", "5y"], index=0)
df, bench_df = get_institutional_data(ticker, "SPY", period)
fnd = yf.Ticker(ticker).info # Basic info fetch

if not df.empty:
    scores = get_factor_scores(fnd, df)
    
    # Main Dashboard
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"Institutional Profile: {ticker}")
        
        # Factor Radar Chart
        fig_radar = go.Figure(go.Scatterpolar(
            r=[scores['Trend'], scores['Momentum'], scores['Value'], scores['Quality'], scores['Growth']],
            theta=['Trend', 'Momentum', 'Value', 'Quality', 'Growth'],
            fill='toself'
        ))
        fig_radar.update_layout(height=400, polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with col2:
        st.metric("Institutional Rating", f"{scores['Rating']:.1f} / 100")
        for k, v in scores.items():
            if k != "Rating": st.write(f"**{k}:** {v:.1f}")

    # Technical Visualization
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200", line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['CMF'], name="CMF"), row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Data Unavailable")
