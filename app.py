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
    "1 Month": {"period": "1mo"},
    "3 Months": {"period": "3mo"},
    "6 Months": {"period": "6mo"},
    "1 Year": {"period": "1y"},
    "2 Years": {"period": "2y"},
    "5 Years": {"period": "5y"}
}
selected_tf = st.sidebar.selectbox("Terminal Analysis Horizon:", list(timeframe_opts.keys()), index=3)
period_val = timeframe_opts[selected_tf]["period"]

benchmark_sym = st.sidebar.selectbox("Relative Strength Benchmark:", ["SPY", "QQQ", "XLK"], index=0)

# --- AUTO-REFRESH CONFIGURATION ---
refresh_rate = st.sidebar.slider("Live Data Auto-Refresh (Seconds):", min_value=10, max_value=60, value=15)
st.components.v1.html(
    f"""
    <script>
        window.setTimeout(function() {{
            window.location.reload();
        }}, {refresh_rate * 1000});
    </script>
    """,
    height=0,
)

if not ticker_symbol.isalnum():
    st.sidebar.warning("⚠️ Invalid ticker format detected.")
    st.stop()

# --- CACHING FUNCTIONS ---
@st.cache_data(ttl=86400, max_entries=100)
def fetch_ticker_info_blob(ticker_str):
    try:
        return yf.Ticker(ticker_str).info
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def fetch_longlived_metadata(ticker_str):
    payload = {
        "longName": ticker_str, "targetPrice": None, "pe_trailing": None, "pe_forward": None, 
        "peg": None, "pb": None, "roe": None, "net_margin": None, "op_margin": None,
        "eps_growth": None, "rev_growth": None, "debt_equity": None, "current_ratio": None,
        "marketCap": None, "beta": None, "avg_volume": None, "fiftyTwoWeekHigh": None,
        "fiftyTwoWeekLow": None, "dividendYield": None, "sharesOutstanding": None,
        "floatShares": None, "shortInterest": None, "next_earnings": "N/A"
    }
    try:
        t = yf.Ticker(ticker_str)
        payload["longName"] = t.fast_info.get("shortName", ticker_str)
        info = fetch_ticker_info_blob(ticker_str)
        if info:
            payload.update({k: info.get(k) for k in ["targetMeanPrice", "trailingPE", "forwardPE", "pegRatio", "priceToBook", "returnOnEquity", "profitMargins", "operatingMargins", "earningsGrowth", "revenueGrowth", "debtToEquity", "currentRatio", "marketCap", "beta", "averageVolume", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "dividendYield", "sharesOutstanding", "floatShares", "shortPercentOfFloat"]})
        calendar = getattr(t, "calendar", None)
        if calendar is not None and not calendar.empty and "Earnings Date" in calendar.index:
            payload["next_earnings"] = str(calendar.loc["Earnings Date"].iloc[0].date())
    except Exception:
        pass
    return payload

@st.cache_data(ttl=60, max_entries=50)
def get_raw_market_data(ticker_str, benchmark_str, period_str):
    try:
        stock = yf.Ticker(ticker_str)
        history = stock.history(period=period_str, interval="1d")
        if history.empty: return None, None, None
        bench = yf.Ticker(benchmark_str)
        bench_hist = bench.history(period=period_str, interval="1d")
        fast_payload = {"prev_close": history['Close'].tail(2).iloc[0] if len(history) > 1 else history['Close'].iloc[-1]}
        return history, bench_hist, fast_payload
    except Exception:
        return None, None, None

@st.cache_data(ttl=30)
def compute_technical_indicators(df_history, df_bench):
    df = df_history.copy()
    df['SMA50'] = df['Close'].rolling(window=min(50, len(df))).mean()
    df['SMA200'] = df['Close'].rolling(window=min(200, len(df))).mean()
    
    delta = df['Close'].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))
    
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    
    # Simple ADX proxy calculation
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    df['PlusDI'] = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['MinusDI'] = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['ATR'].replace(0, np.nan))
    df['ADX'] = ((abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI']).replace(0, np.nan)) * 100).ewm(alpha=1/14, adjust=False).mean()
    
    df['RVOL'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    stock_ret = (1 + df['Close'].pct_change()).cumprod()
    bench_ret = (1 + df_bench['Close'].pct_change().reindex(df.index, method='ffill')).cumprod()
    df['Alpha_Strength'] = stock_ret - bench_ret
    return df

# --- RENDER LAYER ---
raw_history, bench_history, info_payload = get_raw_market_data(ticker_symbol, benchmark_sym, period_val)

if raw_history is not None:
    fnd = fetch_longlived_metadata(ticker_symbol)
    df_view = compute_technical_indicators(raw_history, bench_history)
    latest = df_view.iloc[-1]
    
    main_layout, fundamental_sidebar = st.columns([2.3, 0.7])
    
    with main_layout:
        st.subheader(f"🏢 {fnd['longName']} ({ticker_symbol}) — Terminal View")
        
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.40, 0.15, 0.15, 0.15, 0.15])
        fig.add_trace(go.Candlestick(x=df_view.index, open=df_view['Open'], high=df_view['High'], low=df_view['Low'], close=df_view['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['Volume'], name='Volume', marker_color='rgba(33, 150, 243, 0.5)'), row=2, col=1)
        fig.add_trace(go.Bar(x=df_view.index, y=df_view['MACD_Hist'], name='MACD Hist', marker_color=['red' if v < 0 else 'green' for v in df_view['MACD_Hist']]), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['RSI'], name='RSI', line=dict(color='#FFCA28')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df_view.index, y=df_view['ADX'], name='ADX', line=dict(color='#FF9100')), row=5, col=1)

        fig.update_layout(
            title=dict(text=f"Technical Analysis: {ticker_symbol} ({selected_tf})", x=0.5, font=dict(size=24)),
            height=1000, margin=dict(l=50, r=20, t=80, b=20), template="plotly_dark", hovermode="x unified",
            annotations=[
                dict(text="Price Action", x=0, y=1.00, xref="paper", yref="paper", showarrow=False),
                dict(text="Volume", x=0, y=0.58, xref="paper", yref="paper", showarrow=False),
                dict(text="MACD", x=0, y=0.42, xref="paper", yref="paper", showarrow=False),
                dict(text="RSI", x=0, y=0.25, xref="paper", yref="paper", showarrow=False),
                dict(text="ADX", x=0, y=0.08, xref="paper", yref="paper", showarrow=False)
            ]
        )
        st.plotly_chart(fig, use_container_width=True)

    with fundamental_sidebar:
        st.markdown("### 📋 Quant Fundamentals")
        st.metric("Closing Price", f"${latest['Close']:.2f}")
        st.markdown(f"**Market Cap:** ${fnd.get('marketCap', 0)/1e9:.2f}B")
        st.markdown(f"**Beta:** {fnd.get('beta', 'N/A')}")
        st.markdown(f"**Next Earnings:** {fnd.get('next_earnings', 'N/A')}")
else:
    st.error("❌ Data retrieval failed. Please check the ticker symbol.")
