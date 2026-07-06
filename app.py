import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & APP INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Institutional Quant Terminal")
st.title("⚡ Institutional Quant Terminal")

# --- WATCHLIST & TICKER MANAGEMENT ---
st.sidebar.header("Navigation & Watchlist")
watchlist = ["AAPL", "MSFT", "NVDA", "GOOG", "META", "AMZN"]
selected_watch = st.sidebar.selectbox("Quick Select Watchlist:", [""] + watchlist)

default_ticker = selected_watch if selected_watch else "AAPL"
ticker_symbol = st.sidebar.text_input("Manual Ticker Input:", value=default_ticker).upper().strip()

# --- TIMEFRAME SUPPORT CONTROLS ---
timeframe_opts = {
    "1 Month": {"period": "1mo"}, "3 Months": {"period": "3mo"},
    "6 Months": {"period": "6mo"}, "1 Year": {"period": "1y"},
    "2 Years": {"period": "2y"}, "5 Years": {"period": "5y"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]
benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(
    f"""<script>window.setTimeout(function(){{window.location.reload();}}, {refresh_rate * 1000});</script>""",
    height=0,
)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- CACHING FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    payload = {
        "longName": ticker_str, "targetPrice": None, "pe_trailing": None, "pe_forward": None, 
        "peg": None, "pb": None, "roe": None, "net_margin": None, "op_margin": None,
        "marketCap": None, "beta": None, "avg_volume": None, "fiftyTwoWeekHigh": None,
        "fiftyTwoWeekLow": None, "next_earnings": "N/A"
    }
    try:
        t = yf.Ticker(ticker_str)
        info = t.info
        if info:
            payload.update({k: info.get(k) for k in ["longName", "targetMeanPrice", "trailingPE", "forwardPE", "pegRatio", "priceToBook", "returnOnEquity", "profitMargins", "operatingMargins", "marketCap", "beta", "averageVolume", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]})
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty and "Earnings Date" in calendar.index:
            payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception: pass
    return payload

@st.cache_data(ttl=60)
def get_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        bench = yf.Ticker(benchmark_str).history(period=period_str, interval="1d")
        return history, bench
    except: return None, None

def compute_indicators(df, df_bench):
    df = df.copy()
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    # RSI
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain, avg_loss = gain.ewm(span=14).mean(), loss.ewm(span=14).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    # MACD
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    # ATR
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(span=14).mean()
    # ADX Proxy
    df['ADX'] = 0 # Placeholder for brevity
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()
    return df

# --- RENDER LAYER ---
history, bench = get_market_data(ticker_symbol, benchmark_sym, period_val)

if history is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df = compute_indicators(history, bench)
    latest = df.iloc[-1]
    
    main_layout, sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4,0.15,0.15,0.15,0.15])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='rgba(33, 150, 243, 0.5)'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD', marker_color=['red' if v < 0 else 'green' for v in df['MACD_Hist']]), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#FFCA28')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ADX'], name='ADX', line=dict(color='#FF9100')), row=5, col=1)

        fig.update_layout(
            title=dict(text=f"Technical Analysis: {ticker_symbol} ({selected_tf})", x=0.5, font=dict(size=24)),
            height=1000, margin=dict(l=50, r=20, t=80, b=20), template="plotly_dark",
            annotations=[
                dict(text="Price Action", x=0, y=1.00, xref="paper", yref="paper", showarrow=False),
                dict(text="Volume", x=0, y=0.58, xref="paper", yref="paper", showarrow=False),
                dict(text="MACD", x=0, y=0.42, xref="paper", yref="paper", showarrow=False),
                dict(text="RSI", x=0, y=0.25, xref="paper", yref="paper", showarrow=False),
                dict(text="ADX", x=0, y=0.08, xref="paper", yref="paper", showarrow=False)
            ]
        )
        st.plotly_chart(fig, use_container_width=True)

    with sidebar:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt(v, mode="num"):
            if v is None or pd.isna(v): return "N/A"
            if mode == "mcap": return f"${v / 1e12:.2f}T" if v >= 1e12 else f"${v / 1e9:.2f}B"
            if mode == "vol": return f"{v / 1e6:.2f}M"
            return f"{v:.2f}"
        
        st.markdown(f"**Market Cap:** `{fmt(fnd['marketCap'], 'mcap')}`")
        st.markdown(f"**Beta:** `{fmt(fnd['beta'])}`")
        st.markdown("---")
        st.markdown("#### **Volatility Metrics**")
        st.markdown(f"**ATR (14):** `{latest['ATR']:.2f}`")
        st.markdown(f"**Suggested Stop:** `${latest['Close'] - (latest['ATR'] * 2):.2f}`")
        st.markdown("---")
        st.markdown("#### **Valuation Matrix**")
        st.markdown(f"**Trailing P/E:** `{fmt(fnd['pe_trailing'])}`")
        st.markdown(f"**Next Earnings:** `{fnd['next_earnings']}`")
