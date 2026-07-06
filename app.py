import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- DATA MANAGEMENT ---
@st.cache_data(ttl=3600)
def get_macro_calendar(ticker_str):
    t = yf.Ticker(ticker_str)
    cal = t.calendar
    events = [{"Date": "2026-07-14", "Event": "CPI Inflation Data"},
              {"Date": "2026-07-28", "Event": "FOMC Rate Decision"}]
    if cal is not None and not cal.empty:
        events.append({"Date": str(cal.index[0].date()), "Event": "Earnings Release"})
    return pd.DataFrame(events).sort_values("Date")

@st.cache_data(ttl=60)
def get_data_and_compute(ticker, benchmark, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval="1d")
    if df.empty: return None
    
    # Technicals
    df['MA20'] = df['Close'].rolling(20).mean()
    df['Std20'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['MA20'] + (2 * df['Std20'])
    df['BB_Lower'] = df['MA20'] - (2 * df['Std20'])
    
    # RSI
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14).mean()
    avg_loss = loss.ewm(alpha=1/14).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
    
    # ATR & Risk
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14).mean()
    
    # MACD
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['MACD_Sig'] = df['MACD'].ewm(span=9).mean()
    
    return df

# --- UI CONTROLS ---
ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
benchmark = st.sidebar.selectbox("Benchmark", ["SPY", "QQQ"], index=0)
df = get_data_and_compute(ticker, benchmark, "2y")

if df is not None:
    latest = df.iloc[-1]
    # Metrics
    returns = df['Close'].pct_change().dropna()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    atr = latest['ATR']
    stop_price = latest['Close'] - (2 * atr)
    
    # Dashboard Columns
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"${latest['Close']:.2f}")
    c2.metric("Sharpe Ratio", f"{sharpe:.2f}")
    c3.metric("ATR (14)", f"{atr:.2f}")
    c4.metric("2xATR Stop", f"${stop_price:.2f}", f"{(latest['Close']-stop_price)/latest['Close']:.1%} Risk")

    # Plotting
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.2, 0.2, 0.2])
    
    # Price
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    # Volume
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='gray'), row=2, col=1)
    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD"), row=3, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='yellow')), row=4, col=1)
    for lvl in [30, 50, 70]: fig.add_hline(y=lvl, row=4, col=1, line_dash="dot", line_color="white", opacity=0.3)

    fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Dynamic Calendar
    st.subheader("🗓️ Macro & Earnings Calendar")
    st.table(get_macro_calendar(ticker))
else:
    st.error("Invalid Ticker or No Data Found.")
