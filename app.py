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
    "1 Month": {"period": "1mo"}, "3 Months": {"period": "3mo"}, "6 Months": {"period": "6mo"},
    "1 Year": {"period": "1y"}, "2 Years": {"period": "2y"}, "5 Years": {"period": "5y"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]
benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(f"""<script>window.setTimeout(function(){{window.location.reload();}}, {refresh_rate * 1000});</script>""", height=0)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- LONGLIVED RAW DATA & INFRASTRUCTURE CACHING ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try: return yf.Ticker(ticker_str).info
    except Exception: return {}

@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    payload = {
        "longName": ticker_str, "targetPrice": None, "pe_trailing": None, "pe_forward": None, "peg": None, 
        "pb": None, "roe": None, "net_margin": None, "op_margin": None, "eps_growth": None, "rev_growth": None, 
        "debt_equity": None, "current_ratio": None, "marketCap": None, "beta": None, "avg_volume": None, 
        "fiftyTwoWeekHigh": None, "fiftyTwoWeekLow": None, "dividendYield": None, "sharesOutstanding": None, 
        "floatShares": None, "shortInterest": None, "next_earnings": "N/A"
    }
    try:
        t = yf.Ticker(ticker_str)
        payload["longName"] = t.fast_info.get("shortName", ticker_str)
        info = fetch_ticker_info_blob(ticker_str)
        if info:
            payload.update({k: info.get(k) for k in payload if k != "longName" and k != "next_earnings"})
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty and "Earnings Date" in calendar.index:
            payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception: pass
    return payload

@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    stock = yf.Ticker(ticker_str)
    history = stock.history(period=period_str, interval="1d")
    bench = yf.Ticker(benchmark_str)
    bench_hist = bench.history(period=period_str, interval="1d")
    return history, bench_hist, {"prev_close": history['Close'].iloc[-2] if len(history) > 1 else history['Close'].iloc[-1]}

@st.cache_data(ttl=30)
def compute_technical_indicators(df, df_bench):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['Std20'] = df['Close'].rolling(20).std()
    
    # RSI
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_g = gain.ewm(14).mean()
    avg_l = loss.ewm(14).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_g / avg_l.replace(0, np.nan))))
    
    # MACD + Histogram
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Hist'] = df['MACD'] - df['Signal']
    
    # ATR & Pivots
    tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(span=14).mean()
    df['Pivot'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
    
    return df

# --- LAYOUT ENGINE ---
raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)
if raw_history is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    latest = df_view.iloc[-1]
    
    main, side = st.columns([2.3, 0.7])
    with main:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol}) — Terminal View")
        # 4-Panel Visualization
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.2, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Pivot'], line=dict(color='gray', dash='dot'), name='Daily Pivot'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume'), row=2, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Hist'], name='MACD Hist', marker_color=np.where(df_view['Hist']>=0, 'green', 'red')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['MACD'], name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['Signal'], name='Signal', line=dict(color='orange')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], name='RSI', line=dict(color='purple')), row=4, col=1)
        for y in [30, 50, 70]: fig.add_hline(y=y, line_dash="dash", line_color="gray", row=4, col=1)
        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Macro Calendar
        st.table(pd.DataFrame([{"Date": "2026-07-02", "Indicator": "NFP", "Impact": "🔥 Critical"}, {"Date": "2026-07-28", "Indicator": "FOMC", "Impact": "🔥 Pivot"}]))

    with side:
        st.markdown("### 📋 Quant Fundamentals")
        def fmt_v(v, f="num"):
            if v is None or pd.isna(v): return "N/A"
            if f == "pct": return f"{v * 100:.2f}%"
            if f == "mcap": return f"${v / 1e12:.2f}T" if v >= 1e12 else f"${v / 1e9:.2f}B"
            return f"{v:.2f}"
        
        for k, v in fnd.items():
            if k not in ["longName", "next_earnings"]: st.markdown(f"**{k.replace('_', ' ').title()}:** `{fmt_v(v)}`")
        
        st.markdown("---")
        st.markdown("### 🛡️ Risk & ATR Metrics")
        stop_px = latest['Close'] - (2 * latest['ATR'])
        st.metric("Suggested Stop (2xATR)", f"${stop_px:.2f}")
        st.write(f"Position Risk: {((latest['Close']-stop_px)/latest['Close'])*100:.2f}%")
